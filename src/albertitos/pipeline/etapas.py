"""Etapas del pipeline sobre la BD. Cada etapa es idempotente y emite eventos.

ingest  → PDF → ficheros                       (implementado)
extract → PDF → hechos (plantilla | LLM)        (extract/etapa.py, Javier)
decide  → hechos + maestro + ERP → decisiones   (implementado con la norma v3; Mónica valida)
emit    → decisiones → outcomes.jsonl           (pipeline/package.py)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import unicodedata
from datetime import date
from pathlib import Path

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    ErpSnapshot,
    EstadoEvento,
    Etapa,
    Event,
    InvoiceFacts,
    MasterSnapshot,
)
from albertitos.core.hashing import sha256_fichero
from albertitos.core.versions import EXTRACTOR_VERSION

log = logging.getLogger(__name__)


def ingest(conn: sqlite3.Connection, directorio: Path, lote: int = 1) -> int:
    """Registra cada PDF por sha256 y devuelve cuántos son nuevos o cambiaron (nombre, lote).
    Repetir no duplica filas ni eventos: lo ya registrado sólo se hashea. Renombrar actualiza el file_id."""
    from albertitos.extract import pdf  # import tardío: pymupdf tarda en cargar

    conocidos = {
        r["sha256"]: (r["file_id"], r["lote"])
        for r in conn.execute("SELECT sha256, file_id, lote FROM ficheros")
    }
    n = 0
    for ruta in sorted(Path(directorio).glob("*.pdf")):
        t0 = time.perf_counter()
        file_id = unicodedata.normalize("NFC", ruta.name)
        sha = sha256_fichero(ruta)
        if conocidos.get(sha) == (file_id, lote):
            continue
        try:
            paginas, tiene_texto = pdf.info(ruta)
            db.guardar_fichero(
                conn,
                sha256=sha,
                file_id=file_id,
                lote=lote,
                bytes_=ruta.stat().st_size,
                paginas=paginas,
                tiene_texto=tiene_texto,
            )
            db.registrar_evento(
                conn,
                Event(
                    file_id=file_id,
                    sha256=sha,
                    etapa=Etapa.INGEST,
                    estado=EstadoEvento.OK,
                    latencia_ms=int((time.perf_counter() - t0) * 1000),
                    detalle=f"lote={lote} paginas={paginas} texto={'si' if tiene_texto else 'no'}",
                ),
            )
            n += 1
        except Exception as e:  # PDF corrupto: se registra y se sigue
            db.registrar_evento(
                conn,
                Event(
                    file_id=file_id,
                    sha256=sha,
                    etapa=Etapa.INGEST,
                    estado=EstadoEvento.ERROR,
                    error_codigo="PDF-ILEGIBLE",
                    detalle=str(e)[:200],
                ),
            )
    conn.commit()
    return n


def extract(
    conn: sqlite3.Connection,
    *,
    solo_pendientes: bool = True,
    fixture: Path | None = None,
    workers: int = 1,
) -> int:
    """PDF → InvoiceFacts. La implementación vive en extract/etapa.py (Javier); aquí sólo se delega."""
    from albertitos.extract.etapa import extraer

    return extraer(conn, solo_pendientes=solo_pendientes, fixture=fixture, workers=workers).ok


def registrar_transicion(conn: sqlite3.Connection, ev: Event) -> bool:
    """Registra `ev` sólo si cambia el estado del fichero en esa etapa (el último evento de ese
    fichero y etapa tiene otro estado o detalle). Repetir un run no llena la traza de copias."""
    ultimo = conn.execute(
        "SELECT estado, detalle FROM eventos WHERE file_id=? AND etapa=? ORDER BY id DESC LIMIT 1",
        (ev.file_id, ev.etapa.value),
    ).fetchone()
    if ultimo is not None and (ultimo["estado"], ultimo["detalle"]) == (
        ev.estado.value,
        ev.detalle,
    ):
        return False
    db.registrar_evento(conn, ev)
    return True


def grupos_duplicados(hechos: list[InvoiceFacts]) -> dict[str, dict[str, str]]:
    """sha256 → {file_id de otro PDF de su grupo: qué comparten}. Grupo = mismo pedido o mismo
    (NIF, nº de factura) en más de un PDF. Lo usan `marcar_duplicados` y la traza."""
    grupos: dict[tuple[str, ...], list[InvoiceFacts]] = {}
    for h in hechos:
        if h.pedido:
            grupos.setdefault(("pedido", h.pedido), []).append(h)
        if h.nif_emisor and h.num_factura:
            grupos.setdefault(("factura", h.nif_emisor, h.num_factura), []).append(h)
    con: dict[str, dict[str, str]] = {}
    for clave, grupo in grupos.items():
        if len(grupo) < 2:
            continue
        que = f"pedido {clave[1]}" if clave[0] == "pedido" else f"factura {clave[2]} de {clave[1]}"
        for h in grupo:
            otros = con.setdefault(h.sha256, {})
            for o in grupo:
                if o is not h:
                    otros[o.file_id] = f"{otros[o.file_id]} y {que}" if o.file_id in otros else que
    return con


def hechos_vigentes(conn: sqlite3.Connection) -> list[InvoiceFacts]:
    filas = conn.execute(
        "SELECT hechos_json FROM hechos WHERE extractor_version=?", (EXTRACTOR_VERSION,)
    ).fetchall()
    return [InvoiceFacts.model_validate_json(f["hechos_json"]) for f in filas]


def marcar_duplicados(conn: sqlite3.Connection) -> tuple[int, int]:
    """Segunda pasada sobre los hechos: mismo pedido o mismo (NIF, nº factura) en más de un PDF →
    Aviso.DUPLICADO_SOSPECHOSO en todos ellos. La marca se recalcula entera: se pone donde hay grupo y
    se quita donde ya no lo hay (p. ej. tras borrar los `L2-*` de un ensayo). Sólo esta función pone
    ese aviso. Cambia hechos_hash, así que el linaje los reprocesa. Devuelve (puestos, quitados)."""
    hechos = hechos_vigentes(conn)
    con = grupos_duplicados(hechos)  # sha256 → los otros PDFs de sus grupos
    puestos = quitados = 0
    for h in hechos:
        marcado = Aviso.DUPLICADO_SOSPECHOSO in h.avisos
        if h.sha256 in con and not marcado:
            h.avisos.append(Aviso.DUPLICADO_SOSPECHOSO)
            puestos, accion = puestos + 1, "puesto"
        elif h.sha256 not in con and marcado:
            h.avisos = [a for a in h.avisos if a != Aviso.DUPLICADO_SOSPECHOSO]
            quitados, accion = quitados + 1, "quitado"
        else:
            continue
        db.guardar_hechos(conn, h)
        db.registrar_evento(
            conn,
            Event(
                file_id=h.file_id,
                sha256=h.sha256,
                etapa=Etapa.VALIDATE,
                estado=EstadoEvento.OK,
                version=EXTRACTOR_VERSION,
                detalle=json.dumps(
                    {
                        "aviso": Aviso.DUPLICADO_SOSPECHOSO.value,
                        "accion": accion,
                        "con": sorted(con.get(h.sha256, ())),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
    conn.commit()
    return puestos, quitados


def decide(
    conn: sqlite3.Connection,
    *,
    norma_version: str,
    fecha_corte: date,
    maestro: MasterSnapshot,
    erp: ErpSnapshot,
    solo: list[str] | None = None,
    por: dict[str, str] | None = None,
    por_defecto: str | None = None,
) -> int:
    """Aplica la norma a los hechos de cada fichero (o sólo a `solo`) y guarda la decisión vigente.
    `por` (file_id → motivo del linaje; `por_defecto` para los demás) va al evento: la traza dice por
    qué se recalculó."""
    from albertitos.rules import REGISTRO

    norma = REGISTRO[norma_version]
    ctx = ContextoDecision(
        norma_version=norma_version,
        fecha_corte=fecha_corte,
        maestro_version=maestro.version,
        erp_version=erp.version,
    )
    sql = "SELECT f.file_id, f.sha256, h.hechos_json FROM ficheros f JOIN hechos h ON h.sha256=f.sha256 AND h.extractor_version=?"
    filas = conn.execute(sql, (EXTRACTOR_VERSION,)).fetchall()
    quiero = set(solo) if solo is not None else None
    n = 0
    for fila in filas:
        if quiero is not None and fila["file_id"] not in quiero:
            continue
        t0 = time.perf_counter()
        hechos = InvoiceFacts.model_validate_json(fila["hechos_json"])
        decision = norma.decidir(hechos, maestro, erp, ctx)
        db.guardar_decision(conn, decision)
        porque = (por or {}).get(fila["file_id"], por_defecto)
        db.registrar_evento(
            conn,
            Event(
                file_id=fila["file_id"],
                sha256=fila["sha256"],
                etapa=Etapa.DECIDE,
                estado=EstadoEvento.OK,
                latencia_ms=int((time.perf_counter() - t0) * 1000),
                version=norma_version,
                detalle=json.dumps(
                    {
                        "resultado": decision.resultado.value,
                        "reglas_ko": decision.reglas_incumplidas,
                    }
                    | ({"por": porque} if porque else {}),
                    ensure_ascii=False,
                ),
            ),
        )
        n += 1
    _registrar_sin_hechos(conn, norma_version)
    conn.commit()
    return n


def _registrar_sin_hechos(conn: sqlite3.Connection, norma_version: str) -> None:
    """decide/skip para cada fichero que decide se salta por no tener hechos (PENDIENTE de extract),
    con el último error de extract. Sin él, la traza de un PENDIENTE acabaría en extract."""
    filas = conn.execute(
        """SELECT f.file_id, f.sha256,
                  (SELECT e.error_codigo FROM eventos e WHERE e.file_id = f.file_id
                     AND e.etapa = 'extract' ORDER BY e.id DESC LIMIT 1) AS error
           FROM ficheros f
           LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
           WHERE h.sha256 IS NULL""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    for f in filas:
        registrar_transicion(
            conn,
            Event(
                file_id=f["file_id"],
                sha256=f["sha256"],
                etapa=Etapa.DECIDE,
                estado=EstadoEvento.SKIP,
                version=norma_version,
                detalle=json.dumps(
                    {"pendiente": "sin hechos: no se decide", "extract": f["error"]},
                    ensure_ascii=False,
                ),
            ),
        )
