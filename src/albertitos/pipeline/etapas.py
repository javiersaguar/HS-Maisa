"""Etapas del pipeline sobre la BD. Cada etapa es idempotente y emite eventos.

ingest  → PDF → ficheros                       (implementado)
extract → PDF → hechos (plantilla | LLM)        (pendiente: Alfonso, extract/)
decide  → hechos + maestro + ERP → decisiones   (implementado con la norma v3; Mónica valida)
emit    → decisiones → outcomes.jsonl           (pipeline/package.py)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import unicodedata
from datetime import UTC, date, datetime
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
    """Registra cada PDF por sha256. Repetir no duplica; renombrar un PDF actualiza su file_id."""
    from albertitos.extract import pdf  # import tardío: pymupdf tarda en cargar

    n = 0
    for ruta in sorted(Path(directorio).glob("*.pdf")):
        t0 = time.perf_counter()
        file_id = unicodedata.normalize("NFC", ruta.name)
        sha = sha256_fichero(ruta)
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


def marcar_duplicados(conn: sqlite3.Connection) -> int:
    """Segunda pasada sobre los hechos: mismo pedido o mismo (NIF, nº factura) en más de un PDF →
    Aviso.DUPLICADO_SOSPECHOSO en todos ellos. Cambia hechos_hash, así que el linaje los reprocesa."""
    filas = conn.execute(
        "SELECT sha256, hechos_json FROM hechos WHERE extractor_version=?", (EXTRACTOR_VERSION,)
    ).fetchall()
    hechos = [InvoiceFacts.model_validate_json(f["hechos_json"]) for f in filas]
    por_pedido: dict[str, list[InvoiceFacts]] = {}
    por_factura: dict[tuple[str, str], list[InvoiceFacts]] = {}
    for h in hechos:
        if h.pedido:
            por_pedido.setdefault(h.pedido, []).append(h)
        if h.nif_emisor and h.num_factura:
            por_factura.setdefault((h.nif_emisor, h.num_factura), []).append(h)
    marcados = 0
    for grupo in list(por_pedido.values()) + list(por_factura.values()):
        if len(grupo) < 2:
            continue
        for h in grupo:
            if Aviso.DUPLICADO_SOSPECHOSO not in h.avisos:
                h.avisos.append(Aviso.DUPLICADO_SOSPECHOSO)
                db.guardar_hechos(conn, h)
                marcados += 1
    conn.commit()
    return marcados


def decide(
    conn: sqlite3.Connection,
    *,
    norma_version: str,
    fecha_corte: date,
    maestro: MasterSnapshot,
    erp: ErpSnapshot,
    solo: list[str] | None = None,
) -> int:
    """Aplica la norma a los hechos de cada fichero (o sólo a `solo`) y guarda la decisión vigente."""
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
        decision.decidido_en = datetime.now(UTC)
        db.guardar_decision(conn, decision)
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
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        n += 1
    conn.commit()
    return n
