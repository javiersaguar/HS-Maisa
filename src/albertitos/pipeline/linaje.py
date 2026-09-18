"""Linaje: qué ficheros hay que (re)decidir dado el estado actual de versiones y hechos."""

from __future__ import annotations

import sqlite3


def impactados(
    conn: sqlite3.Connection,
    *,
    norma_version: str,
    maestro_version: str,
    erp_version: str,
    extractor_version: str,
    lote: int | None = None,
) -> list[str]:
    """file_id sin decisión vigente, o cuya decisión vigente se tomó con otra norma, otro maestro,
    otro ERP u otros hechos (hash). Es lo que `reprocess --impacted` recalcula: nada más."""
    sql = """
        SELECT f.file_id
        FROM ficheros f
        LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
        LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
        WHERE (? IS NULL OR f.lote = ?)
          AND (d.id IS NULL
               OR d.norma_version <> ?
               OR d.maestro_version <> ?
               OR d.erp_version <> ?
               OR h.hechos_hash IS NULL
               OR d.hechos_hash <> h.hechos_hash)
        ORDER BY f.file_id
    """
    filas = conn.execute(
        sql, (extractor_version, lote, lote, norma_version, maestro_version, erp_version)
    ).fetchall()
    return [str(r["file_id"]) for r in filas]


def diff_decisiones(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Para cada fichero con más de una decisión, la vigente frente a la inmediatamente anterior."""
    filas = conn.execute(
        """
        SELECT a.file_id, a.resultado AS antes, b.resultado AS despues, b.norma_version, b.erp_version
        FROM decisiones b
        JOIN decisiones a ON a.sha256 = b.sha256 AND a.vigente = 0
          AND a.id = (SELECT max(id) FROM decisiones x WHERE x.sha256 = b.sha256 AND x.id < b.id)
        WHERE b.vigente = 1 AND a.resultado <> b.resultado
        ORDER BY a.file_id
        """
    ).fetchall()
    return [dict(r) for r in filas]
