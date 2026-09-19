"""Qué hay dentro de la base de datos, en funciones puras y sin efectos.

Existe por un incidente real (18/09, 01:30). Para ensayar el runbook del lote 2, B1 dejó 10 PDFs
derivados de la Caja (`L2-*`) ingeridos como `lote=2`. Nadie los borró y dos cosas se torcieron:

1. `marcar_duplicados` los vio como facturas del mismo pedido que sus originales del lote 1 y marcó
   a los originales como duplicados: 20 decisiones se fueron a ESCALAR sin motivo.
2. `pipeline.package` mete en `outcomes_lote2.jsonl` TODO fichero con `lote=2` de la BD. Con los
   simulados dentro, la entrega habría llevado ficheros que no existen en la Caja → NO APTO.

Ninguna de las dos se veía a simple vista: `status` decía "ficheros por lote {1: 500, 2: 10}" y
parecía correcto. De ahí `ficheros_fantasma`: un fichero es fantasma cuando está en la BD pero no
en el directorio del lote al que dice pertenecer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from albertitos.core import db
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline.validar import listar_pdfs


def _pdfs(directorio: Path | str | None) -> set[str]:
    """Nombres (NFC) de los PDF de un directorio; vacío si no existe. Usa `pipeline.validar`."""
    if directorio is None:
        return set()
    ruta = Path(directorio)
    return set(listar_pdfs(ruta)) if ruta.is_dir() else set()


def ficheros_fantasma(
    conn: sqlite3.Connection, dir_lote1: Path | str, dir_lote2: Path | str | None = None
) -> list[tuple[str, int]]:
    """(file_id, lote) que están en la BD pero NO en el directorio real de su lote.

    Son los que contaminan `marcar_duplicados` y la entrega. Si el directorio de un lote no existe,
    todos los ficheros de ese lote son fantasmas: no hay con qué cotejarlos.
    """
    reales = {1: _pdfs(dir_lote1), 2: _pdfs(dir_lote2)}
    fuera = []
    for fila in conn.execute("SELECT file_id, lote FROM ficheros ORDER BY file_id"):
        lote = int(fila["lote"] or 1)
        # un nombre interno de P0-5 (`./X.pdf`) es el PDF X.pdf de su lote: no es un fantasma
        if db.nombre_entrega(fila["file_id"]) not in reales.get(lote, set()):
            fuera.append((str(fila["file_id"]), lote))
    return fuera


def ficheros_sin_hechos(
    conn: sqlite3.Connection, extractor_version: str = EXTRACTOR_VERSION
) -> list[str]:
    """Ficheros ingeridos de los que no se extrajo nada: sin hechos no hay decisión posible."""
    return [
        str(r["file_id"])
        for r in conn.execute(
            """SELECT f.file_id FROM ficheros f
               LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
               WHERE h.sha256 IS NULL ORDER BY f.file_id""",
            (extractor_version,),
        )
    ]


def ficheros_sin_decision(conn: sqlite3.Connection) -> list[str]:
    """Ficheros sin decisión vigente. `package` se niega a escribir la entrega si hay alguno."""
    return [
        str(r["file_id"])
        for r in conn.execute(
            """SELECT f.file_id FROM ficheros f
               LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
               WHERE d.id IS NULL ORDER BY f.file_id"""
        )
    ]


def hechos_huerfanos(conn: sqlite3.Connection) -> list[str]:
    """Hechos cuyo `sha256` ya no está en `ficheros`: restos de un borrado a medias.

    Pasó al limpiar los `L2-*` a mano: si se borra de `ficheros` sin borrar de `hechos`, la próxima
    extracción cree que ese contenido ya está resuelto.
    """
    return [
        str(r["sha256"])
        for r in conn.execute(
            """SELECT h.sha256 FROM hechos h
               LEFT JOIN ficheros f ON f.sha256 = h.sha256
               WHERE f.sha256 IS NULL ORDER BY h.sha256"""
        )
    ]


def ultimo_erp(conn: sqlite3.Connection) -> str | None:
    """Versión del snapshot del ERP que usarían `run`, `decide` y `reprocess` SIN `--erp`.

    `core.db.ultimo_snapshot` devuelve el más reciente por `creado_en`. Si alguien ensayó el lote 2
    y dejó un `v2-sim` detrás, ese es el que se usaría: decidiríamos el lote 1 contra un ERP
    inventado sin enterarnos.
    """
    fila = conn.execute(
        "SELECT version FROM snapshots WHERE tipo='erp' ORDER BY creado_en DESC LIMIT 1"
    ).fetchone()
    return None if fila is None else str(fila["version"])


@dataclass
class EstadoBD:
    """Foto de la BD para decidir en 10 segundos si se puede tocar el lote 2."""

    ficheros_por_lote: dict[int, int] = field(default_factory=dict)
    decisiones_por_resultado: dict[str, int] = field(default_factory=dict)
    hechos_por_metodo: dict[str, int] = field(default_factory=dict)
    fantasmas: list[tuple[str, int]] = field(default_factory=list)
    sin_hechos: list[str] = field(default_factory=list)
    sin_decision: list[str] = field(default_factory=list)
    huerfanos: list[str] = field(default_factory=list)
    erp_en_uso: str | None = None
    lecturas_en_cache: int = 0

    @property
    def total_ficheros(self) -> int:
        return sum(self.ficheros_por_lote.values())


def resumen_estado(
    conn: sqlite3.Connection, dir_lote1: Path | str, dir_lote2: Path | str | None = None
) -> EstadoBD:
    """Todo lo anterior de una vez, para imprimirlo en una tabla."""
    return EstadoBD(
        ficheros_por_lote={
            int(r[0] or 1): int(r[1])
            for r in conn.execute("SELECT lote, count(*) FROM ficheros GROUP BY lote")
        },
        decisiones_por_resultado={
            str(r[0]): int(r[1])
            for r in conn.execute(
                "SELECT resultado, count(*) FROM decisiones WHERE vigente=1 GROUP BY resultado"
            )
        },
        hechos_por_metodo={
            str(r[0]): int(r[1])
            for r in conn.execute("SELECT metodo, count(*) FROM hechos GROUP BY metodo")
        },
        fantasmas=ficheros_fantasma(conn, dir_lote1, dir_lote2),
        sin_hechos=ficheros_sin_hechos(conn),
        sin_decision=ficheros_sin_decision(conn),
        huerfanos=hechos_huerfanos(conn),
        erp_en_uso=ultimo_erp(conn),
        lecturas_en_cache=int(conn.execute("SELECT count(*) FROM cache_llm").fetchone()[0]),
    )
