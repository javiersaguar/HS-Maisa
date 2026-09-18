"""Acceso a la SQLite: WAL, SQL a mano, sin ORM. Única fuente de verdad del sistema."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from albertitos.core.contracts import Decision, Event, InvoiceFacts

RUTA_POR_DEFECTO = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
_SCHEMA = Path(__file__).with_name("schema.sql")


def ahora_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def conectar(ruta: Path | str | None = None, solo_lectura: bool = False) -> sqlite3.Connection:
    ruta = Path(ruta or RUTA_POR_DEFECTO)
    if solo_lectura:
        conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=5)
    else:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(ruta, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


# ----------------------------------------------------------------------------- escrituras


def guardar_fichero(
    conn: sqlite3.Connection,
    *,
    sha256: str,
    file_id: str,
    lote: int,
    bytes_: int,
    paginas: int | None,
    tiene_texto: bool | None,
) -> None:
    conn.execute(
        """INSERT INTO ficheros (sha256, file_id, lote, bytes, paginas, tiene_texto, ingerido_en)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(sha256) DO UPDATE SET file_id=excluded.file_id, lote=excluded.lote,
             paginas=excluded.paginas, tiene_texto=excluded.tiene_texto""",
        (
            sha256,
            file_id,
            lote,
            bytes_,
            paginas,
            None if tiene_texto is None else int(tiene_texto),
            ahora_iso(),
        ),
    )


def guardar_hechos(conn: sqlite3.Connection, hechos: InvoiceFacts) -> None:
    conn.execute(
        """INSERT INTO hechos (sha256, extractor_version, metodo, hechos_json, hechos_hash, creado_en)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(sha256, extractor_version) DO UPDATE SET metodo=excluded.metodo,
             hechos_json=excluded.hechos_json, hechos_hash=excluded.hechos_hash, creado_en=excluded.creado_en""",
        (
            hechos.sha256,
            hechos.extractor_version,
            hechos.metodo.value,
            hechos.model_dump_json(),
            hechos.hash(),
            ahora_iso(),
        ),
    )


def guardar_decision(conn: sqlite3.Connection, d: Decision) -> None:
    """Idempotente por linaje: la decisión nueva pasa a vigente y las anteriores del fichero a 0.
    `decidido_en` se sella aquí si no viene: el reloj es de la BD, no de la norma."""
    conn.execute("UPDATE decisiones SET vigente=0 WHERE sha256=? AND vigente=1", (d.sha256,))
    conn.execute(
        """INSERT INTO decisiones (sha256, file_id, resultado, norma_version, fecha_corte, hechos_hash,
             maestro_version, erp_version, motivos_json, decidido_en, vigente)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            d.sha256,
            d.file_id,
            d.resultado.value,
            d.norma_version,
            d.fecha_corte.isoformat(),
            d.hechos_hash,
            d.maestro_version,
            d.erp_version,
            json.dumps([m.model_dump(mode="json") for m in d.motivos], ensure_ascii=False),
            d.decidido_en.isoformat() if d.decidido_en else ahora_iso(),
        ),
    )


def registrar_evento(conn: sqlite3.Connection, ev: Event) -> int:
    cur = conn.execute(
        """INSERT INTO eventos (ts, sha256, file_id, etapa, estado, intento, latencia_ms, tokens_in,
             tokens_out, coste_eur, error_codigo, detalle, version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            (ev.ts or datetime.now(UTC)).isoformat(timespec="milliseconds"),
            ev.sha256,
            ev.file_id,
            ev.etapa.value,
            ev.estado.value,
            ev.intento,
            ev.latencia_ms,
            ev.tokens_in,
            ev.tokens_out,
            None if ev.coste_eur is None else float(ev.coste_eur),
            ev.error_codigo,
            ev.detalle,
            ev.version,
        ),
    )
    return int(cur.lastrowid or 0)


def guardar_snapshot(conn: sqlite3.Connection, tipo: str, version: str, datos_json: str) -> None:
    conn.execute(
        """INSERT INTO snapshots (tipo, version, datos_json, creado_en) VALUES (?, ?, ?, ?)
           ON CONFLICT(tipo, version) DO UPDATE SET datos_json=excluded.datos_json, creado_en=excluded.creado_en""",
        (tipo, version, datos_json, ahora_iso()),
    )


# ----------------------------------------------------------------------------- lecturas


def cargar_snapshot(conn: sqlite3.Connection, tipo: str, version: str) -> str | None:
    fila = conn.execute(
        "SELECT datos_json FROM snapshots WHERE tipo=? AND version=?", (tipo, version)
    ).fetchone()
    return None if fila is None else str(fila["datos_json"])


def ultimo_snapshot(conn: sqlite3.Connection, tipo: str) -> tuple[str, str] | None:
    fila = conn.execute(
        "SELECT version, datos_json FROM snapshots WHERE tipo=? ORDER BY creado_en DESC LIMIT 1",
        (tipo,),
    ).fetchone()
    return None if fila is None else (str(fila["version"]), str(fila["datos_json"]))


def decisiones_vigentes(conn: sqlite3.Connection, lote: int | None = None) -> list[sqlite3.Row]:
    sql = """SELECT d.*, f.lote FROM decisiones d JOIN ficheros f ON f.sha256 = d.sha256
             WHERE d.vigente = 1"""
    params: tuple[Any, ...] = ()
    if lote is not None:
        sql += " AND f.lote = ?"
        params = (lote,)
    return list(conn.execute(sql + " ORDER BY d.file_id", params).fetchall())


def ficheros(conn: sqlite3.Connection, lote: int | None = None) -> list[sqlite3.Row]:
    if lote is None:
        return list(conn.execute("SELECT * FROM ficheros ORDER BY file_id").fetchall())
    return list(
        conn.execute("SELECT * FROM ficheros WHERE lote=? ORDER BY file_id", (lote,)).fetchall()
    )


def traza(conn: sqlite3.Connection, file_id: str) -> dict[str, Any]:
    """Todo lo que sabemos de un fichero: para `albertitos trace` y la vista Traza de la consola."""
    fichero = conn.execute("SELECT * FROM ficheros WHERE file_id=?", (file_id,)).fetchone()
    if fichero is None:
        return {"file_id": file_id, "fichero": None}
    sha = fichero["sha256"]
    return {
        "file_id": file_id,
        "fichero": dict(fichero),
        "hechos": [
            dict(r)
            for r in conn.execute("SELECT * FROM hechos WHERE sha256=? ORDER BY creado_en", (sha,))
        ],
        "decisiones": [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM decisiones WHERE sha256=? ORDER BY decidido_en", (sha,)
            )
        ],
        "eventos": [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM eventos WHERE sha256=? OR file_id=? ORDER BY ts", (sha, file_id)
            )
        ],
    }


def resumen(conn: sqlite3.Connection) -> dict[str, Any]:
    """Contadores para `status` y el Panel."""
    out: dict[str, Any] = {}
    out["ficheros"] = {
        r["lote"]: r["n"]
        for r in conn.execute("SELECT lote, count(*) n FROM ficheros GROUP BY lote")
    }
    out["decisiones"] = {
        r["resultado"]: r["n"]
        for r in conn.execute(
            "SELECT resultado, count(*) n FROM decisiones WHERE vigente=1 GROUP BY resultado"
        )
    }
    out["eventos"] = [
        dict(r)
        for r in conn.execute(
            """SELECT etapa, estado, count(*) n, round(avg(latencia_ms)) lat_media_ms,
                      round(coalesce(sum(coste_eur),0), 4) coste_eur, sum(intento>1) reintentos
               FROM eventos GROUP BY etapa, estado ORDER BY etapa, estado"""
        )
    ]
    out["pendientes"] = [
        r["file_id"]
        for r in conn.execute(
            """SELECT f.file_id FROM ficheros f
               LEFT JOIN decisiones d ON d.sha256=f.sha256 AND d.vigente=1
               WHERE d.id IS NULL ORDER BY f.file_id"""
        )
    ]
    out["cache_llm"] = conn.execute("SELECT count(*) n FROM cache_llm").fetchone()["n"]
    return out
