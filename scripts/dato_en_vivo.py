"""El tribunal cambia un dato en vivo: se recalcula sólo lo que ese dato toca, y se ve por qué.

El domingo pueden pedirnos «cambiad este dato y volved a decidir». Esto lo hace en un comando y
sobre una COPIA de la BD (`dist/vivo.db`): no se toca `dist/albertitos.db` ni `dist/entrega/`, así
que se puede repetir delante del tribunal las veces que haga falta y siempre parte del mismo sitio.

Qué se puede cambiar: lo que dicen el ERP o el Excel, nunca una decisión.

    --pagada PO-2026-0007                  el asiento de ese pedido pasa a PAGADA en el ERP
    --importe PO-2026-0007=1234,56         cambia el importe esperado del asiento
    --iban P003=ES9121000418450200051332   cambia el IBAN del proveedor en el maestro
    --estado-pedido PO-2026-0007=ANULADO   cambia el estado del pedido en el maestro
    --fecha-corte 2026-06-30               no toca ningún dato: decide con otra fecha de corte

El dato cambiado se guarda como un snapshot NUEVO (el ERP con la etiqueta `vivo`; el maestro con su
versión recalculada), nunca encima del que se usó para entregar. El linaje compara las dos versiones,
mira qué pedidos y qué NIF cambian, y `reprocess --impacted` recalcula sólo esas facturas: las demás
conservan su decisión y su versión (ADR-0006). Eso es lo que se enseña, con el cronómetro delante.

Uso:
    uv run python scripts/dato_en_vivo.py --listar
    uv run python scripts/dato_en_vivo.py --pagada PO-2026-0007
    uv run python scripts/dato_en_vivo.py --iban P003=ES9121000418450200051332 --json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping
from contextlib import closing
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import ErpSnapshot, EstadoEvento, Etapa, Event, MasterSnapshot
from albertitos.core.hashing import hash_canonico
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.formatos import normalizar_iban, normalizar_pedido, parse_importe_es
from albertitos.pipeline import linaje
from albertitos.sources import snapshot

ORIGEN = Path("dist/albertitos.db")
COPIA = Path("dist/vivo.db")
TAG_ERP = "vivo"
CORTE_POR_DEFECTO = "2026-09-18"


# ----------------------------------------------------------------------------- la copia


def copiar_bd(origen: Path, destino: Path) -> None:
    """Copia coherente con la API de backup; nunca `cp`, que con el WAL a medias la deja rota."""
    for resto in (
        destino,
        destino.with_name(destino.name + "-wal"),
        destino.with_name(destino.name + "-shm"),
    ):
        resto.unlink(missing_ok=True)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with (
        closing(sqlite3.connect(f"file:{origen}?mode=ro", uri=True)) as src,
        closing(sqlite3.connect(destino)) as dst,
    ):
        src.backup(dst)


# ----------------------------------------------------------------------------- los cambios


def parsear_asignacion(texto: str, que: str) -> tuple[str, str]:
    """'PO-2026-0007=1234,56' → ('PO-2026-0007', '1234,56')."""
    clave, sep, valor = texto.partition("=")
    if not sep or not clave.strip() or not valor.strip():
        raise ValueError(f"{que} se escribe CLAVE=VALOR (llegó {texto!r})")
    return clave.strip(), valor.strip()


def erp_con_cambios(
    e: ErpSnapshot,
    *,
    tag: str,
    pagadas: Iterable[str] = (),
    importes: Mapping[str, Decimal] | None = None,
    ahora: datetime | None = None,
) -> tuple[ErpSnapshot, list[str]]:
    """Copia del snapshot del ERP con esos pedidos cambiados. El original no se toca.

    `consultas` y `reintentos` quedan a 0 a propósito: esto no es una descarga del ERP, es el
    snapshot anterior con un dato cambiado a mano, y la traza no debe decir lo contrario.
    """
    pedidos = {normalizar_pedido(p) for p in pagadas}
    nuevos_importes = {normalizar_pedido(k): v for k, v in dict(importes or {}).items()}
    conocidos = {a.pedido for a in e.asientos.values()}
    faltan = sorted((pedidos | set(nuevos_importes)) - conocidos)
    if faltan:
        raise ValueError(f"el ERP {e.version} no tiene asientos de {faltan}")
    nuevo = e.model_copy(deep=True)
    nuevo.version = tag
    nuevo.descargado_en = ahora or datetime.now(UTC)
    nuevo.consultas = 0
    nuevo.reintentos = 0
    cambios: list[str] = []
    for a in nuevo.asientos.values():
        if a.pedido in pedidos and a.estado != "PAGADA":
            cambios.append(f"ERP · {a.asiento_id} ({a.pedido}): estado {a.estado} → PAGADA")
            a.estado = "PAGADA"
        if a.pedido in nuevos_importes and a.importe_esperado != nuevos_importes[a.pedido]:
            destino = nuevos_importes[a.pedido]
            cambios.append(
                f"ERP · {a.asiento_id} ({a.pedido}): importe esperado"
                f" {a.importe_esperado} → {destino}"
            )
            a.importe_esperado = destino
    return nuevo, cambios


def version_maestro(m: MasterSnapshot) -> str:
    """La misma huella que `sources.excel.cargar_maestro`: si cambia un dato, cambia la versión.

    Está duplicada aquí a propósito (el maestro de este script no sale de un Excel), y
    `tests/test_dato_en_vivo.py` la compara con la del Excel real para que no se desincronicen.
    """
    return hash_canonico(
        {
            "p": {k: v.model_dump(mode="json") for k, v in m.proveedores.items()},
            "o": {k: v.model_dump(mode="json") for k, v in m.pedidos.items()},
        }
    )[:12]


def maestro_con_cambios(
    m: MasterSnapshot,
    *,
    ibanes: Mapping[str, str] | None = None,
    estados: Mapping[str, str] | None = None,
    ahora: datetime | None = None,
) -> tuple[MasterSnapshot, list[str]]:
    """Copia del maestro con esos proveedores o pedidos cambiados, y su versión recalculada."""
    nuevo = m.model_copy(deep=True)
    cambios: list[str] = []
    for pid, iban in dict(ibanes or {}).items():
        prov = nuevo.proveedores.get(pid.strip().upper())
        if prov is None:
            raise ValueError(f"el maestro {m.version} no tiene el proveedor {pid}")
        limpio = normalizar_iban(iban)
        if prov.iban != limpio:
            quien = f"{prov.id} ({prov.razon_social})"
            cambios.append(f"maestro · {quien}: IBAN {prov.iban} → {limpio}")
            prov.iban = limpio
    for num, estado in dict(estados or {}).items():
        ped = nuevo.pedidos.get(normalizar_pedido(num))
        if ped is None:
            raise ValueError(f"el maestro {m.version} no tiene el pedido {num}")
        destino = estado.strip().upper()
        if ped.estado != destino:
            cambios.append(f"maestro · {ped.pedido}: estado {ped.estado} → {destino}")
            ped.estado = destino
    nuevo.version = version_maestro(nuevo)
    nuevo.origen = f"{m.origen} · dato cambiado en vivo"
    nuevo.cargado_en = ahora or datetime.now(UTC)
    return nuevo, cambios


# ----------------------------------------------------------------------------- qué enseñar


def candidatos(conn: sqlite3.Connection, limite: int = 10) -> list[dict[str, Any]]:
    """Pedidos que hoy se pagan y cuyo asiento sigue PENDIENTE: son los que se notan en la sala.

    Sólo lectura. Marcarlos PAGADA en el ERP hace que la norma deje de pagarlos, que es el cambio
    más fácil de contar en diez segundos.
    """
    por_pedido: dict[str, list[str]] = {}
    for fila in conn.execute(
        """SELECT d.file_id, h.hechos_json FROM decisiones d
           JOIN hechos h ON h.sha256 = d.sha256 AND h.extractor_version = ?
           WHERE d.vigente = 1 AND d.resultado = 'PAGAR' ORDER BY d.file_id""",
        (EXTRACTOR_VERSION,),
    ):
        pedido = json.loads(fila["hechos_json"]).get("pedido")
        if pedido:
            por_pedido.setdefault(str(pedido), []).append(str(fila["file_id"]))
    asientos = snapshot.cargar_erp_bd(conn, None).por_pedido()
    salida = []
    for pedido, ficheros in sorted(por_pedido.items()):
        pendientes = [a for a in asientos.get(pedido, []) if a.estado != "PAGADA"]
        if pendientes:
            salida.append(
                {
                    "pedido": pedido,
                    "ficheros": ficheros,
                    "asientos": [a.asiento_id for a in pendientes],
                    "importe_esperado": str(pendientes[0].importe_esperado),
                }
            )
    return salida[:limite]


def albertitos(*args: str, bd: Path, corte: str) -> tuple[int, str, float]:
    """Un comando de la CLI contra la copia. Devuelve (código, salida, segundos de pared)."""
    entorno = {
        **os.environ,
        "ALBERTITOS_DB": str(bd),
        "ALBERTITOS_FECHA_CORTE": corte,
        "PYTHONUTF8": "1",
    }
    print(f"\n$ ALBERTITOS_DB={bd} albertitos {' '.join(args)}", flush=True)
    t0 = time.perf_counter()
    p = subprocess.run(
        [sys.executable, "-m", "albertitos.cli", *args],
        env=entorno,
        capture_output=True,
        text=True,
    )
    segundos = time.perf_counter() - t0
    salida = (p.stdout + p.stderr).strip()
    if salida:
        print(salida)
    return p.returncode, salida, segundos


# ----------------------------------------------------------------------------- CLI


def parsear_argumentos(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origen", type=Path, default=ORIGEN, help="BD de la que se hace la copia")
    ap.add_argument("--copia", type=Path, default=COPIA, help="dónde trabajar (se rehace entera)")
    ap.add_argument("--tag", default=TAG_ERP, help="etiqueta del snapshot nuevo del ERP")
    ap.add_argument(
        "--listar",
        action="store_true",
        help="pedidos que hoy se pagan y siguen PENDIENTE en el ERP (buenos para la demo)",
    )
    ap.add_argument("--limite", type=int, default=10, help="cuántos candidatos enseña --listar")
    ap.add_argument("--pagada", action="append", default=[], metavar="PEDIDO")
    ap.add_argument("--importe", action="append", default=[], metavar="PEDIDO=IMPORTE")
    ap.add_argument("--iban", action="append", default=[], metavar="PROVEEDOR=IBAN")
    ap.add_argument("--estado-pedido", action="append", default=[], metavar="PEDIDO=ESTADO")
    ap.add_argument("--fecha-corte", default=None, help="decide con otra fecha de corte")
    ap.add_argument("--norma", default="v3", help="norma con la que redecidir")
    ap.add_argument(
        "--lote",
        type=int,
        default=1,
        help="lote que se redecide (ADR-0021: cada lote en su contexto; el 2 va con --norma v4)",
    )
    ap.add_argument(
        "--con-traza",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="al terminar, la traza legible de la primera decisión que cambia",
    )
    ap.add_argument("--json", action="store_true", help="además, una línea JSON con lo medido")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()
    a = parsear_argumentos(argv)
    if not a.origen.is_file():
        print(f"no existe {a.origen}: este escenario se enseña sobre la BD ya decidida")
        return 1

    if a.listar:
        with closing(db.conectar(a.origen, solo_lectura=True)) as conn:
            encontrados = candidatos(conn, a.limite)
        print(f"pedidos que hoy se pagan y siguen PENDIENTE en el ERP ({len(encontrados)}):")
        for c in encontrados:
            print(
                f"  {c['pedido']} · {c['importe_esperado']} EUR · asientos {c['asientos']}"
                f" · {c['ficheros']}"
            )
        print("\nel más limpio para la sala:  --pagada <PEDIDO>  (pasa de PAGAR a NO_PAGAR)")
        return 0

    try:
        importes = {}
        for texto in a.importe:
            clave, valor = parsear_asignacion(texto, "--importe")
            importe = parse_importe_es(valor)
            if importe is None:
                print(f"--importe: no entiendo el importe {valor!r}")
                return 2
            importes[clave] = importe
        ibanes = dict(parsear_asignacion(x, "--iban") for x in a.iban)
        estados = dict(parsear_asignacion(x, "--estado-pedido") for x in a.estado_pedido)
    except ValueError as e:
        print(str(e))
        return 2

    toca_erp = bool(a.pagada or importes)
    toca_maestro = bool(ibanes or estados)
    if not (toca_erp or toca_maestro or a.fecha_corte):
        print(
            "no has pedido ningún cambio. Elige uno: --pagada · --importe · --iban ·"
            " --estado-pedido · --fecha-corte (y --listar para ver candidatos)"
        )
        return 2
    corte = a.fecha_corte or os.environ.get("ALBERTITOS_FECHA_CORTE", CORTE_POR_DEFECTO)
    try:
        date.fromisoformat(corte)
    except ValueError:
        print(f"--fecha-corte tiene que ser AAAA-MM-DD (llegó {corte!r})")
        return 2

    copiar_bd(a.origen, a.copia)
    print(f"copia de {a.origen} en {a.copia}: lo real no se toca en ningún momento")
    cambios: list[str] = []
    with closing(db.conectar(a.copia)) as conn:
        erp_destino = None
        try:
            if toca_erp:
                base = snapshot.cargar_erp_bd(conn, None)
                nuevo_erp, hechos_erp = erp_con_cambios(
                    base, tag=a.tag, pagadas=a.pagada, importes=importes
                )
                if not hechos_erp:
                    print("el ERP ya estaba así: el cambio que pides no cambia ningún asiento")
                    return 2
                snapshot.guardar_erp(conn, nuevo_erp)
                erp_destino = nuevo_erp.version
                cambios += hechos_erp
                print(f"ERP {base.version} → {nuevo_erp.version} (derivado, no es una descarga)")
            if toca_maestro:
                base_m = snapshot.cargar_maestro_bd(conn)
                nuevo_m, hechos_m = maestro_con_cambios(base_m, ibanes=ibanes, estados=estados)
                if not hechos_m:
                    print("el maestro ya estaba así: el cambio que pides no cambia ningún dato")
                    return 2
                snapshot.guardar_maestro(conn, nuevo_m)
                cambios += hechos_m
                print(f"maestro {base_m.version} → {nuevo_m.version}")
        except (LookupError, ValueError) as e:
            print(str(e))
            return 2
        if a.fecha_corte:
            cambios.append(f"fecha de corte → {corte} (parámetro, nunca date.today())")
        for c in cambios:
            print(f"  cambio: {c}")
        db.registrar_evento(
            conn,
            Event(
                etapa=Etapa.ENRICH,
                estado=EstadoEvento.OK,
                version=erp_destino or a.norma,
                detalle=json.dumps(
                    {"tipo": "dato_en_vivo", "cambios": cambios, "fecha_corte": corte},
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()
        desde = linaje.ultima_decision(conn)

    # ADR-0021: con --norma o --erp y sin --lote, reprocess se niega (cambiaría el contexto del lote 1).
    orden = [
        "reprocess",
        "--impacted",
        "--lote",
        str(a.lote),
        "--norma",
        a.norma,
        "--fecha-corte",
        corte,
    ]
    if erp_destino:
        orden += ["--erp", erp_destino]
    codigo, _, segundos = albertitos(*orden, bd=a.copia, corte=corte)
    if codigo != 0:
        print(f"\nel reproceso falló (exit {codigo}): no se enseña nada que no haya funcionado")
        return 1

    with closing(db.conectar(a.copia, solo_lectura=True)) as conn:
        distintas = linaje.diff_decisiones(conn, desde_id=desde)
    print(f"\n{len(distintas)} decisiones cambian · {segundos:.1f} s de pared (arranque incluido)")
    for c in distintas:
        print(f"  {c['file_id']}: {c['antes']} → {c['despues']}")
    if not distintas:
        print("  ninguna: el dato que has cambiado no afecta a ninguna decisión vigente")

    if distintas:
        primero = str(distintas[0]["file_id"])
        if a.con_traza:
            albertitos("trace", primero, bd=a.copia, corte=corte)
        else:
            print(f"\nla traza:  ALBERTITOS_DB={a.copia} uv run albertitos trace {primero}")

    if a.json:
        print(
            json.dumps(
                {
                    "cambios": cambios,
                    "erp": erp_destino,
                    "fecha_corte": corte,
                    "decisiones_que_cambian": len(distintas),
                    "cambios_de_decision": distintas,
                    "segundos_reprocess": round(segundos, 2),
                    "copia": str(a.copia),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
