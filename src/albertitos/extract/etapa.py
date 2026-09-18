"""Etapa extract: ficheros pendientes → InvoiceFacts en la BD, con eventos. Dueño: Javier (agente A1).

Firma CONGELADA (la llaman pipeline/etapas.py y cli.py):

    extraer(conn, *, solo_pendientes=True, fixture=None, workers=1) -> ResumenExtraccion

Por fichero: texto (o imagen si es escaneado) → plantilla determinista si A2 la reconoce (coste 0) →
si no, LLM (texto o visión, con caché por sha256) → validadores → hechos en BD + evento EXTRACT.
Si el LLM falla (caído, 429 agotado, respuesta inválida, presupuesto, caos): evento PENDIENTE con
error_codigo y se sigue con el siguiente. Nada revienta el lote; sin hechos no hay decisión.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import Aviso, EstadoEvento, Etapa, Event, InvoiceFacts
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.extract import pdf, plantillas, validadores
from albertitos.extract.llm import ClienteLLM, ErrorLLM, EstadoLLM

log = logging.getLogger(__name__)

DIRECTORIOS = {1: Path("data/caja/facturas"), 2: Path("data/lote2/facturas")}
DPI_VISION = int(os.environ.get("ALBERTITOS_DPI_VISION", "150"))
# Segunda lectura de cada escaneada: recorte de la parte superior (identificadores) a más resolución.
# Medido el 18/09: a 130 dpi la segunda lectura era PEOR que la primera (B99 por B98, 51,27 por 61,27) y
# generaba discrepancias falsas; a 200 dpi la página entera dispara los tokens y qwen se pierde. El recorte
# superior a 200 dpi cuesta lo mismo que la página a 150 y lee mejor NIF/IBAN/pedido.
DPI_VISION_2 = int(os.environ.get("ALBERTITOS_DPI_VISION_2", "200"))
FRACCION_SUPERIOR_2 = float(os.environ.get("ALBERTITOS_FRACCION_SUPERIOR_2", "0.55"))
VISION_DOBLE = os.environ.get("ALBERTITOS_VISION_DOBLE", "1") != "0"
# Sólo se comparan los campos de identidad (los importes ya los cruzan validadores, maestro y ERP).
CAMPOS_SEGUNDA_LECTURA = (
    "nif_emisor",
    "iban",
    "pedido",
)  # num_factura no decide nada: no se compara
# Ante desacuerdo entre las dos lecturas de un identificador, se elige la que coincide con el maestro
# Y con el proveedor del pedido (dos evidencias independientes); queda en el evento y baja `confianza`.
# Sin esa evidencia, el desacuerdo se queda como DISCREPANCIA_EXTRACTORES (la norma escala).
RECONCILIAR_MAESTRO = os.environ.get("ALBERTITOS_RECONCILIAR_MAESTRO", "1") != "0"
CONFIANZA_RECONCILIADA = 0.6


@dataclass
class ResumenExtraccion:
    candidatos: int = 0
    ok: int = 0
    pendientes: int = 0
    errores_pdf: int = 0
    por_metodo: dict[str, int] = field(
        default_factory=dict
    )  # plantilla | llm_texto | llm_vision | cache
    errores: dict[str, int] = field(default_factory=dict)  # error_codigo → n
    tokens_in: int = 0
    tokens_out: int = 0
    coste_eur: float = 0.0
    segundos: float = 0.0

    def texto(self) -> str:
        fps = self.candidatos / self.segundos if self.segundos else 0.0
        return (
            f"extract: {self.ok}/{self.candidatos} ok · {self.pendientes} pendientes · {self.errores_pdf} pdf ilegibles · "
            f"métodos {self.por_metodo} · errores {self.errores} · tokens {self.tokens_in}/{self.tokens_out} · "
            f"{self.coste_eur:.4f} EUR · {self.segundos:.1f} s ({fps:.2f} ficheros/s)"
        )


def ruta_pdf(file_id: str, lote: int) -> Path:
    """El PDF por su file_id: primero el directorio del lote, después el otro (por si se movió)."""
    for directorio in (DIRECTORIOS.get(lote), *DIRECTORIOS.values()):
        if directorio is not None and (directorio / file_id).exists():
            return directorio / file_id
    raise FileNotFoundError(f"{file_id} no está en {list(DIRECTORIOS.values())}")


def candidatos(
    conn: sqlite3.Connection, *, solo_pendientes: bool = True, fixture: Path | None = None
) -> list[dict[str, Any]]:
    filas = conn.execute(
        """SELECT f.file_id, f.sha256, f.lote, f.tiene_texto
           FROM ficheros f LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
           WHERE (? = 0 OR h.sha256 IS NULL) ORDER BY f.file_id""",
        (EXTRACTOR_VERSION, 1 if solo_pendientes else 0),
    ).fetchall()
    quiero: set[str] | None = None
    if fixture is not None:
        quiero = {
            unicodedata.normalize("NFC", x.strip())
            for x in Path(fixture).read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.startswith("#")
        }
    return [dict(f) for f in filas if quiero is None or f["file_id"] in quiero]


def _extraer_uno(
    conn: sqlite3.Connection, fila: dict[str, Any], llm: ClienteLLM
) -> tuple[str, str, dict[str, Any]]:
    """(estado, metodo|error_codigo, uso). Escribe hechos + evento en `conn` y hace commit."""
    file_id, sha, lote = fila["file_id"], fila["sha256"], int(fila["lote"] or 1)
    t0 = time.perf_counter()
    uso: dict[str, Any] = {"tokens_in": 0, "tokens_out": 0, "coste_eur": 0, "intento": 1}
    try:
        ruta = ruta_pdf(file_id, lote)
        texto: str | None = None
        png: bytes | None = None
        if fila["tiene_texto"]:
            texto = pdf.texto_de(ruta)
        else:
            png = pdf.imagen_png(ruta, dpi=DPI_VISION)
        hechos: InvoiceFacts | None = None
        if texto is not None:
            hechos = plantillas.extraer_por_plantilla(texto, file_id=file_id, sha256=sha)
        if hechos is None:
            hechos, uso = llm.extraer(sha256=sha, file_id=file_id, texto=texto, png=png)
            if png is not None and VISION_DOBLE:
                uso = _segunda_lectura(hechos, uso, llm, ruta, sha, file_id)
        hechos.avisos = validadores.validar(hechos)
        db.guardar_hechos(conn, hechos)
        db.registrar_evento(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.OK,
                intento=int(uso.get("intento", 1)),
                latencia_ms=_ms(t0),
                tokens_in=int(uso.get("tokens_in", 0)),
                tokens_out=int(uso.get("tokens_out", 0)),
                coste_eur=uso.get("coste_eur", 0),
                version=EXTRACTOR_VERSION,
                detalle=f"{hechos.metodo.value} avisos={[a.value for a in hechos.avisos]}"
                + (f" discrepancias={uso['discrepancias']}" if uso.get("discrepancias") else "")
                + (f" reconciliado={uso['reconciliado']}" if uso.get("reconciliado") else ""),
            ),
        )
        conn.commit()
        return "ok", hechos.metodo.value, uso
    except ErrorLLM as e:
        _evento_seguro(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.PENDIENTE,
                latencia_ms=_ms(t0),
                error_codigo=e.codigo,
                detalle=str(e)[:200],
                version=EXTRACTOR_VERSION,
            ),
        )
        return "pendiente", e.codigo, {}
    except Exception as e:  # PDF ilegible, fichero movido, BD bloqueada...: se registra y se sigue
        codigo = f"EXTRACT-{type(e).__name__}"
        log.warning("%s: %s", file_id, e)
        _evento_seguro(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.ERROR,
                latencia_ms=_ms(t0),
                error_codigo=codigo,
                detalle=str(e)[:200],
                version=EXTRACTOR_VERSION,
            ),
        )
        return "error", codigo, {}


def _recorte_superior_png(ruta: Path, *, dpi: int, fraccion: float) -> bytes:
    import pymupdf

    with pymupdf.open(ruta) as doc:
        pagina = doc[0]
        r = pagina.rect
        clip = pymupdf.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * fraccion)
        return pagina.get_pixmap(dpi=dpi, clip=clip).tobytes("png")


def _segunda_lectura(
    hechos: InvoiceFacts, uso: dict[str, Any], llm: ClienteLLM, ruta: Path, sha: str, file_id: str
) -> dict[str, Any]:
    """Escaneadas: segunda pasada sobre el recorte superior a más resolución. Si los identificadores
    no coinciden, se marca DISCREPANCIA_EXTRACTORES (la norma escala) y queda la evidencia en el uso."""
    try:
        png2 = _recorte_superior_png(ruta, dpi=DPI_VISION_2, fraccion=FRACCION_SUPERIOR_2)
        otra, uso2 = llm.extraer(
            sha256=sha, file_id=file_id, png=png2, variante=f"sup{DPI_VISION_2}"
        )
    except ErrorLLM as e:  # la segunda lectura es opcional: sin ella, se sigue con la primera
        log.warning("%s: segunda lectura no disponible (%s)", file_id, e.codigo)
        return uso
    difs = {
        k: v
        for k, v in validadores.discrepancias(hechos, otra).items()
        if k in CAMPOS_SEGUNDA_LECTURA and getattr(otra, k) is not None
    }
    uso = dict(uso)
    for k in ("tokens_in", "tokens_out"):
        uso[k] = int(uso.get(k, 0)) + int(uso2.get(k, 0))
    uso["coste_eur"] = Decimal(str(uso.get("coste_eur", 0))) + Decimal(
        str(uso2.get("coste_eur", 0))
    )
    if not difs:
        return uso
    reconciliados = (
        _reconciliar_con_maestro(llm.conn, hechos, otra, difs) if RECONCILIAR_MAESTRO else {}
    )
    if reconciliados:
        uso["reconciliado"] = reconciliados
        hechos.confianza = CONFIANZA_RECONCILIADA
    restantes = {k: v for k, v in difs.items() if k not in reconciliados}
    if restantes:
        if Aviso.DISCREPANCIA_EXTRACTORES not in hechos.avisos:
            hechos.avisos.append(Aviso.DISCREPANCIA_EXTRACTORES)
        uso["discrepancias"] = {k: (str(a), str(b)) for k, (a, b) in restantes.items()}
    return uso


def _reconciliar_con_maestro(
    conn: sqlite3.Connection, hechos: InvoiceFacts, otra: InvoiceFacts, difs: dict[str, Any]
) -> dict[str, Any]:
    """Para cada identificador en desacuerdo, elige la lectura respaldada por el maestro y el pedido.

    NIF: la lectura que es el NIF del proveedor al que pertenece el pedido (según el Excel).
    IBAN: la lectura que es el IBAN de ese mismo proveedor.
    Pedido: la lectura que existe en el Excel y cuyo proveedor tiene el NIF leído.
    Devuelve {campo: {"lecturas": [a, b], "elegido": x, "evidencia": "..."}} y muta `hechos`."""
    from albertitos.sources import snapshot

    try:
        maestro = snapshot.cargar_maestro_bd(conn)
    except LookupError:
        return {}
    out: dict[str, Any] = {}
    candidatos_pedido = [x for x in (hechos.pedido, otra.pedido) if x]
    pedido = next((maestro.pedidos[x] for x in candidatos_pedido if x in maestro.pedidos), None)
    if "pedido" in difs and pedido is not None:
        validos = [x for x in candidatos_pedido if x in maestro.pedidos]
        if len(validos) == 1:
            out["pedido"] = {
                "lecturas": [hechos.pedido, otra.pedido],
                "elegido": validos[0],
                "evidencia": "único que existe en el Excel",
            }
            hechos.pedido = validos[0]
            pedido = maestro.pedidos[validos[0]]
    proveedor = maestro.proveedores.get(pedido.proveedor_id) if pedido is not None else None
    if "nif_emisor" in difs and proveedor is not None:
        lecturas = [hechos.nif_emisor, otra.nif_emisor]
        if lecturas.count(proveedor.nif) == 1:
            out["nif_emisor"] = {
                "lecturas": lecturas,
                "elegido": proveedor.nif,
                "evidencia": f"NIF de {proveedor.id}, proveedor del pedido {pedido.pedido}",
            }
            hechos.nif_emisor = proveedor.nif
    if "iban" in difs and proveedor is not None and hechos.nif_emisor == proveedor.nif:
        lecturas = [hechos.iban, otra.iban]
        if lecturas.count(proveedor.iban) == 1:
            out["iban"] = {
                "lecturas": lecturas,
                "elegido": proveedor.iban,
                "evidencia": f"IBAN de {proveedor.id} en el maestro",
            }
            hechos.iban = proveedor.iban
    return out


def contrastar(
    conn: sqlite3.Connection, *, n: int = 40, workers: int = 4, semilla: int = 7
) -> dict[str, Any]:
    """Pasa el LLM (texto) por `n` facturas que salieron por plantilla y compara con `discrepancias`.

    No toca `hechos`: sólo devuelve el informe (y deja las lecturas en caché con variante 'contraste').
    Es la única forma de descartar que un parser se equivoque en bloque sobre cientos de facturas."""
    import random
    from concurrent.futures import ThreadPoolExecutor as _Pool

    filas = conn.execute(
        """SELECT f.file_id, f.sha256, f.lote, h.hechos_json FROM hechos h JOIN ficheros f ON f.sha256 = h.sha256
           WHERE h.extractor_version = ? AND h.metodo = 'plantilla' ORDER BY f.file_id""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    rng = random.Random(semilla)
    muestra = rng.sample([dict(f) for f in filas], min(n, len(filas)))
    estado = EstadoLLM()
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]

    def uno(fila: dict[str, Any]) -> dict[str, Any]:
        c = db.conectar(ruta_db)
        try:
            base = InvoiceFacts.model_validate_json(fila["hechos_json"])
            texto = pdf.texto_de(ruta_pdf(fila["file_id"], int(fila["lote"] or 1)))
            cli = ClienteLLM(c, estado=estado)
            otra, uso = cli.extraer(
                sha256=fila["sha256"], file_id=fila["file_id"], texto=texto, variante="contraste"
            )
            difs = validadores.discrepancias(base, otra)
            return {
                "file_id": fila["file_id"],
                "ok": not difs,
                "discrepancias": {k: (str(a), str(b)) for k, (a, b) in difs.items()},
                "tokens": int(uso.get("tokens_in", 0)) + int(uso.get("tokens_out", 0)),
            }
        except ErrorLLM as e:
            return {"file_id": fila["file_id"], "ok": None, "error": e.codigo}
        finally:
            c.close()

    with _Pool(max_workers=workers) as pool:
        resultados = list(pool.map(uno, muestra))
    coinciden = sum(1 for r in resultados if r["ok"] is True)
    difieren = [r for r in resultados if r["ok"] is False]
    fallos = [r for r in resultados if r["ok"] is None]
    return {
        "n": len(resultados),
        "coinciden": coinciden,
        "difieren": difieren,
        "fallos": fallos,
        "tokens": sum(r.get("tokens", 0) for r in resultados),
        "plantillas_en_bd": len(filas),
    }


def extraer(
    conn: sqlite3.Connection,
    *,
    solo_pendientes: bool = True,
    fixture: Path | None = None,
    workers: int = 1,
) -> ResumenExtraccion:
    t0 = time.perf_counter()
    filas = candidatos(conn, solo_pendientes=solo_pendientes, fixture=fixture)
    r = ResumenExtraccion(candidatos=len(filas))
    estado = EstadoLLM()

    def sumar(res: tuple[str, str, dict[str, Any]]) -> None:
        est, clave, uso = res
        if est == "ok":
            r.ok += 1
            r.por_metodo[clave] = r.por_metodo.get(clave, 0) + 1
            r.tokens_in += int(uso.get("tokens_in", 0))
            r.tokens_out += int(uso.get("tokens_out", 0))
            r.coste_eur += float(uso.get("coste_eur", 0))
        elif est == "pendiente":
            r.pendientes += 1
            r.errores[clave] = r.errores.get(clave, 0) + 1
        else:
            r.errores_pdf += 1
            r.errores[clave] = r.errores.get(clave, 0) + 1

    if workers <= 1 or len(filas) <= 1:
        llm = ClienteLLM(conn, estado=estado)
        for fila in filas:
            sumar(_extraer_uno(conn, fila, llm))
    else:
        ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]

        def trabajo(fila: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
            c = db.conectar(
                ruta_db
            )  # una conexión por hilo; WAL aguanta escritores concurrentes cortos
            try:
                return _extraer_uno(c, fila, ClienteLLM(c, estado=estado))
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for res in pool.map(trabajo, filas):
                sumar(res)
    r.segundos = time.perf_counter() - t0
    return r


def _evento_seguro(conn: sqlite3.Connection, ev: Event) -> None:
    """Registrar un evento de error nunca puede tumbar el lote: si la BD no deja, se reintenta y se loguea."""
    for intento in range(3):
        try:
            conn.rollback()
            db.registrar_evento(conn, ev)
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            log.warning("evento no registrado (%s), intento %s: %s", ev.file_id, intento + 1, e)
            time.sleep(0.5 * (intento + 1))


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
