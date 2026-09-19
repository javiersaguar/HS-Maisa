"""Contingencia del lote 2 (ADR-0009): ESCALAR explícito, registrado y reversible para lo que no tiene hechos
a la hora de entregar.

Por qué existe. La validación es binaria: un outcome por cada PDF, 540 en total, o no hay premio. `package` se
niega a escribir un JSONL si a algún fichero le falta la decisión vigente (regla 6: nunca se paga sin hechos
validados), y eso es lo correcto. Pero si a la hora de entregar un PDF del lote 2 sigue PENDIENTE (el LLM caído,
una escaneada ilegible, un 429 que no se va), no hay `outcomes_lote2.jsonl` y la entrega entera es NO APTA. Esta es
la salida prevista: lo que la norma haría con una factura que nadie ha podido leer, ESCALAR, con motivo y
registro, y deshecho solo en cuanto lleguen los hechos.

Condiciones de Miguel (dueño de pipeline/; aceptó con ellas el 19/09 a las 09:10):
  C1 · Manual y último recurso. Sólo con `--aplicar --motivo "…"`. Se niega con el caos encendido en esa BD, y se
       niega a tocar un fichero que no haya tenido ningún intento de extracción REAL (con el caos apagado y
       llegando al proveedor): antes hay que reintentar de verdad. Enseña los intentos de cada fichero.
  C2 · Sólo ESCALAR, sólo ficheros SIN decisión vigente y nunca en el lote 1.
  C3 · Reversible sin hacer nada: la decisión lleva `hechos_hash="sin-hechos"`; cuando llegan los hechos, el hash
       real es otro, `linaje.evaluar` la ve como "hechos cambiados" y `reprocess --impacted` (o `run` entero) pone
       la de la norma. La de contingencia queda en el historial con vigente=0.
  C4 · Se ve: su Motivo `contingencia.C1` es el único con ok=False, así que `package` escribe
       `"regla":"contingencia.C1"` en la línea; hay un evento `decide` con `"contingencia": true`; y la auditoría
       de entrega la enseña en ÁMBAR.

Uso:
    uv run python scripts/contingencia.py --lote 2                        # EN SECO: qué quedaría y por qué
    uv run python scripts/contingencia.py --lote 2 --aplicar --motivo "LLM caído desde las 06:40; reintentado …"
Salida: 0 si no queda nada sin decisión (o se aplicó a todo); 1 si queda algo; 2 si faltan argumentos.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from albertitos.core import db  # noqa: E402
from albertitos.core.contracts import (  # noqa: E402
    ContextoDecision,
    Decision,
    EstadoEvento,
    Etapa,
    Event,
    Motivo,
    Resultado,
)
from albertitos.core.versions import NORMA_VERSION_POR_DEFECTO  # noqa: E402
from albertitos.rules import REGISTRO  # noqa: E402
from albertitos.sources import chaos, snapshot  # noqa: E402

REGLA = "contingencia.C1"
SIN_HECHOS = "sin-hechos"
# Fallos que no son un intento de extracción: el proveedor ni siquiera se llegó a llamar.
NO_ES_INTENTO = {"LLM-CIRCUIT-OPEN", "LLM-PRESUPUESTO", "LLM-CONFIG"}
# Lo que un fallo simulado lleva en el detalle del evento (`extract/llm.py`: "caos: proveedor caído"…).
MARCA_CAOS = "caos:"
PORQUE = {
    "LLM-DOWN": "el proveedor del LLM no responde",
    "LLM-RED": "no hay conexión con el proveedor del LLM",
    "LLM-TIMEOUT": "el proveedor del LLM no contestó a tiempo",
    "LLM-429": "el proveedor del LLM limita las peticiones (429)",
    "LLM-INVALID": "el LLM devolvió una respuesta inválida",
    "LLM-CIRCUIT-OPEN": "el breaker estaba abierto: no se llegó a llamar al proveedor",
    "LLM-CONFIG": "falta la configuración del LLM (la key): no se llegó a llamar",
    "LLM-PRESUPUESTO": "presupuesto agotado: no se llegó a llamar",
}


@dataclass
class Intento:
    ts: str
    estado: str
    codigo: str
    detalle: str

    @property
    def simulado(self) -> bool:
        return MARCA_CAOS in self.detalle

    @property
    def real(self) -> bool:
        """Un intento real: con el caos apagado y llegando (o intentando llegar) al proveedor o al PDF."""
        return not self.simulado and self.codigo not in NO_ES_INTENTO


@dataclass
class Pendiente:
    """Un fichero del lote sin decisión vigente, con su historia de extracción."""

    file_id: str
    sha256: str
    lote: int
    tiene_texto: bool
    intentos: list[Intento] = field(default_factory=list)
    ultimo_evento: str = "ningún evento"

    @property
    def reales(self) -> list[Intento]:
        return [i for i in self.intentos if i.real]

    @property
    def ultimo_error(self) -> str:
        return self.intentos[-1].codigo if self.intentos else "SIN-INTENTOS"

    def porque(self) -> str:
        if not self.intentos:
            return "nunca se intentó extraer"
        codigo = self.ultimo_error
        texto = PORQUE.get(codigo) or (
            "el PDF no se pudo leer" if codigo.startswith("EXTRACT-") else codigo
        )
        return texto + (" (simulado: caos)" if self.intentos[-1].simulado else "")


def pendientes(conn: sqlite3.Connection, lote: int) -> list[Pendiente]:
    filas = conn.execute(
        """SELECT f.file_id, f.sha256, f.lote, f.tiene_texto FROM ficheros f
           LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
           WHERE d.id IS NULL AND f.lote = ? ORDER BY f.file_id""",
        (lote,),
    ).fetchall()
    out = []
    for f in filas:
        p = Pendiente(f["file_id"], f["sha256"], int(f["lote"]), bool(f["tiene_texto"]))
        for e in conn.execute(
            """SELECT ts, estado, coalesce(error_codigo, '') codigo, coalesce(detalle, '') detalle
               FROM eventos WHERE (sha256 = ? OR file_id = ?) AND etapa = 'extract'
                 AND estado IN ('pendiente', 'error') ORDER BY id""",
            (f["sha256"], f["file_id"]),
        ):
            p.intentos.append(Intento(e["ts"], e["estado"], e["codigo"], e["detalle"]))
        ultimo = conn.execute(
            "SELECT etapa, estado, error_codigo, ts FROM eventos WHERE sha256 = ? OR file_id = ?"
            " ORDER BY id DESC LIMIT 1",
            (f["sha256"], f["file_id"]),
        ).fetchone()
        if ultimo is not None:
            p.ultimo_evento = (
                f"{ultimo['etapa']} {ultimo['estado']} {ultimo['error_codigo'] or ''} {ultimo['ts'][:16]}"
            ).replace("  ", " ")
        out.append(p)
    return out


def contexto(
    conn: sqlite3.Connection, norma: str, erp: str | None, fecha_corte: date
) -> ContextoDecision:
    """Los mismos que usa `albertitos decide`: el último maestro, el ERP indicado (o el último), la norma y el
    corte que se pasan. Nunca la fecha de hoy."""
    if norma not in REGISTRO:
        raise SystemExit(f"la norma {norma!r} no está registrada ({sorted(REGISTRO)})")
    return ContextoDecision(
        norma_version=norma,
        fecha_corte=fecha_corte,
        maestro_version=snapshot.cargar_maestro_bd(conn).version,
        erp_version=snapshot.cargar_erp_bd(conn, erp).version,
    )


def decision_de_contingencia(p: Pendiente, ctx: ContextoDecision, motivo: str) -> Decision:
    ultimo = p.intentos[-1] if p.intentos else None
    return Decision(
        file_id=p.file_id,
        sha256=p.sha256,
        resultado=Resultado.ESCALAR,  # C2: nunca otro
        motivos=[
            Motivo(
                regla_id=REGLA,
                ok=False,  # C4: la única que falla, así package la pone en "regla"
                detalle=f"sin hechos validados a la hora de entregar ({p.ultimo_error}): lo revisa una persona",
                evidencia={
                    "ultimo_error": p.ultimo_error,
                    "ultimo_intento": ultimo.ts if ultimo else None,
                    "intentos_reales": len(p.reales),
                    "motivo": motivo,
                    "adr": "ADR-0009",
                },
            )
        ],
        norma_version=ctx.norma_version,
        fecha_corte=ctx.fecha_corte,
        hechos_hash=SIN_HECHOS,  # C3: cualquier hecho real tiene otro hash → linaje la recalcula
        maestro_version=ctx.maestro_version,
        erp_version=ctx.erp_version,
    )


def aplicar(
    conn: sqlite3.Connection, lista: list[Pendiente], ctx: ContextoDecision, motivo: str
) -> int:
    """Una decisión ESCALAR y un evento decide por fichero, todo en una transacción."""
    try:
        for p in lista:
            d = decision_de_contingencia(p, ctx, motivo)
            db.guardar_decision(conn, d)
            db.registrar_evento(
                conn,
                Event(
                    file_id=p.file_id,
                    sha256=p.sha256,
                    etapa=Etapa.DECIDE,
                    estado=EstadoEvento.OK,
                    version=ctx.norma_version,
                    detalle=json.dumps(
                        {
                            "contingencia": True,
                            "resultado": d.resultado.value,
                            "reglas_ko": [REGLA],
                            "motivo": motivo,
                            "ultimo_error": p.ultimo_error,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(lista)


def _respaldo_configurado(p: Pendiente) -> str:
    variable = (
        "ALBERTITOS_MODELO_TEXTO_FALLBACK" if p.tiene_texto else "ALBERTITOS_MODELO_VISION_FALLBACK"
    )
    return os.environ.get(variable, "").strip() or "ninguno"


def describir(p: Pendiente) -> list[str]:
    lineas = [f"  {p.file_id}  · último evento: {p.ultimo_evento} · {p.porque()}"]
    if not p.intentos:
        lineas.append("     intentos de extract: 0")
        return lineas
    codigos = Counter(
        f"{i.codigo or i.estado}{' (caos)' if i.simulado else ''}" for i in p.intentos
    )
    reales = p.reales
    lineas.append(
        f"     intentos de extract: {len(p.intentos)} · reales {len(reales)} · simulados "
        f"{sum(i.simulado for i in p.intentos)} · primero {p.intentos[0].ts[:16]} · último "
        f"{p.intentos[-1].ts[:16]} · " + ", ".join(f"{c}×{n}" for c, n in codigos.items())
    )
    # extract/llm.py pone delante del detalle "[modelo X · sin respaldo…]" o "[respaldo Y tras … del principal X]"
    # (desde el 19/09 09:40). Los eventos anteriores no lo llevan: se dice, no se supone.
    contextos = [
        m.group(1)
        for i in reales
        if (m := re.search(r"\[([^\]]*(?:modelo|respaldo)[^\]]*)\]", i.detalle))
    ]
    if contextos:
        lineas.append(f"     modelo y respaldo (último intento real): {contextos[-1]}")
    else:
        lineas.append(
            "     modelo y respaldo: estos eventos no lo dicen (son anteriores a que llm.py lo anote)"
            f" · respaldo configurado para este camino: {_respaldo_configurado(p)}"
        )
    return lineas


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # la misma BD, corte y modelos que la CLI (el entorno explícito manda sobre .env)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--db", type=Path, default=Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    ap.add_argument("--lote", type=int, choices=[1, 2], required=True)
    ap.add_argument("--aplicar", action="store_true", help="escribe (sin esto, en seco)")
    ap.add_argument(
        "--motivo", default="", help="obligatorio con --aplicar; queda en la decisión y el evento"
    )
    ap.add_argument("--norma", default=NORMA_VERSION_POR_DEFECTO)
    ap.add_argument(
        "--erp", default=None, help="versión del ERP (por defecto la última, como decide)"
    )
    ap.add_argument("--fecha-corte", default=os.environ.get("ALBERTITOS_FECHA_CORTE"))
    a = ap.parse_args(argv)

    if not a.db.is_file():
        print(f"no existe la BD {a.db}")
        return 2
    os.environ["ALBERTITOS_DB"] = str(a.db)  # el caos es por BD: que se mire el de ésta
    modo_caos = chaos.modo()
    conn = db.conectar(a.db, solo_lectura=not a.aplicar)
    try:
        lista = pendientes(conn, a.lote)
        print(
            f"Contingencia · {a.db} · lote {a.lote} · "
            + ("APLICAR" if a.aplicar else "EN SECO (no escribe nada)")
        )
        print(f"caos en esta BD: {modo_caos or 'apagado'}")
        if a.lote == 1:
            # C2: en el lote 1 no se aplica nunca. Si falta alguna decisión, es otro problema.
            if lista:
                print(f"\nROJO  {len(lista)} ficheros del lote 1 sin decisión vigente:")
                for p in lista:
                    print("\n".join(describir(p)))
                print(
                    "El lote 1 no admite contingencia (ADR-0009, C2): eso no es un imprevisto de la hora de "
                    "entregar. Mira `albertitos status` y `albertitos trace <file_id>` y extrae o decide de verdad."
                )
                return 1
            if a.aplicar:
                print(
                    "ROJO  en el lote 1 no se aplica nunca la contingencia (ADR-0009, C2). Nada que hacer."
                )
                return 1
            print("OK    lote 1: ningún fichero sin decisión vigente. Nada que aplicar.")
            return 0

        if not lista:
            print(f"OK    lote {a.lote}: ningún fichero sin decisión vigente. Nada que aplicar.")
            return 0
        print(f"\n{len(lista)} ficheros del lote {a.lote} sin decisión vigente:")
        for p in lista:
            print("\n".join(describir(p)))
        sin_intento_real = [p for p in lista if not p.reales]
        aptos = [p for p in lista if p.reales]
        extraer = (
            f"ALBERTITOS_DB={a.db} uv run albertitos chaos --off && "
            f"ALBERTITOS_DB={a.db} uv run albertitos extract --workers 4"
        )

        if not a.aplicar:
            if sin_intento_real:
                print(
                    f"\n{len(sin_intento_real)} sin ningún intento real (sólo simulados o ninguno): la "
                    f"contingencia no se les aplicaría. Antes: {extraer}"
                )
            print(
                "\nÚltimo recurso (ADR-0009), después de reintentar de verdad (caos apagado, extract de los "
                "pendientes, modelo de respaldo):\n"
                f'  uv run python scripts/contingencia.py --lote {a.lote} --aplicar --motivo "<por qué>"'
                " --fecha-corte <AAAA-MM-DD>"
            )
            return 1

        # --- aplicar: las comprobaciones de C1 van antes de escribir nada
        if not a.motivo.strip():
            print(
                'ROJO  --aplicar exige --motivo "…": el porqué queda en la decisión y en el evento.'
            )
            return 2
        if modo_caos:
            print(
                f"ROJO  el caos está encendido en esta BD ({modo_caos}): los fallos son simulados. "
                f"Apágalo (`ALBERTITOS_DB={a.db} uv run albertitos chaos --off`), reintenta el extract y vuelve."
            )
            return 1
        if not a.fecha_corte:
            print(
                "ROJO  falta la fecha de corte: --fecha-corte AAAA-MM-DD o ALBERTITOS_FECHA_CORTE. Nunca la de hoy."
            )
            return 2
        ctx = contexto(conn, a.norma, a.erp, date.fromisoformat(a.fecha_corte))
        for p in sin_intento_real:
            print(
                f"NO    {p.file_id}: sin ningún intento real de extracción; no se le aplica. Antes: {extraer}"
            )
        if aptos:
            n = aplicar(conn, aptos, ctx, a.motivo.strip())
            print(
                f"OK    {n} decisiones ESCALAR de contingencia ({REGLA}) · norma {ctx.norma_version} · "
                f"maestro {ctx.maestro_version} · erp {ctx.erp_version} · corte {ctx.fecha_corte}"
            )
            print(
                "      Se deshacen solas: cuando lleguen los hechos, `albertitos reprocess --impacted` "
                "(o `run`) pone la decisión de la norma. Ahora: auditoría y `make publicar` en seco."
            )
        return 1 if sin_intento_real else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
