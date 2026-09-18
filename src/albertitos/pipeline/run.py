"""`albertitos run` de principio a fin: ingest → maestro → ERP → extract → duplicados → decide → package.

Sin extract disponible (o con `extraer=False`) decide con los hechos que ya hay en la BD
(`albertitos hechos import`); los ficheros sin hechos se quedan sin decisión y `package` se niega.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, package
from albertitos.pipeline.validar import InformeValidacion

log = logging.getLogger(__name__)

MAESTRO_XLSX = "FINAL_v7_DEFINITIVO_ahorasi.xlsx"


@dataclass
class ResumenRun:
    ingeridos: int = 0
    maestro_version: str = ""
    erp_version: str = ""
    extraidos: int | None = None  # None = extract no corrió (saltado o no implementado)
    extract_nota: str = ""
    sin_hechos: list[str] = field(default_factory=list)
    duplicados: int = 0
    decididas: int = 0
    entregas: list[tuple[Path, InformeValidacion]] = field(default_factory=list)
    rechazo: InformeValidacion | None = None

    @property
    def ok(self) -> bool:
        return self.rechazo is None

    def texto(self) -> str:
        extract = (
            f"{self.extraidos} extraídos"
            if self.extraidos is not None
            else f"no corrió ({self.extract_nota})"
        )
        lineas = [
            f"ingest: {self.ingeridos} · maestro {self.maestro_version} · erp {self.erp_version}",
            f"extract: {extract} · sin hechos: {len(self.sin_hechos)}"
            + (
                f" → {self.sin_hechos[:5]}{' …' if len(self.sin_hechos) > 5 else ''}"
                if self.sin_hechos
                else ""
            ),
            f"duplicados marcados: {self.duplicados} · decisiones: {self.decididas}",
        ]
        for ruta, inf in self.entregas:
            lineas.append(f"{inf.texto()} → {ruta}")
        if self.rechazo is not None:
            lineas.append(
                f"NO se escribe la entrega (la anterior, si había, sigue intacta):\n{self.rechazo.texto()}"
            )
        return "\n".join(lineas)


def sin_hechos(conn: sqlite3.Connection) -> list[str]:
    """Ficheros ingeridos sin hechos para la versión actual del extractor: no se pueden decidir."""
    filas = conn.execute(
        """SELECT f.file_id FROM ficheros f
           LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
           WHERE h.sha256 IS NULL ORDER BY f.file_id""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    return [str(f["file_id"]) for f in filas]


def correr(
    conn: sqlite3.Connection,
    *,
    caja: Path,
    lote2: Path | None,
    entrega: Path,
    norma_version: str,
    fecha_corte: date,
    extraer: bool = True,
    workers: int = 1,
    con_traza: bool = True,
    maestro_xlsx: Path | None = None,
) -> ResumenRun:
    from albertitos.sources import excel, snapshot

    r = ResumenRun()
    r.ingeridos = etapas.ingest(conn, caja / "facturas", 1)
    if lote2 is not None and (lote2 / "facturas").exists():
        r.ingeridos += etapas.ingest(conn, lote2 / "facturas", 2)

    m = excel.cargar_maestro(maestro_xlsx or caja / MAESTRO_XLSX)
    snapshot.guardar_maestro(conn, m)
    try:
        e = snapshot.cargar_erp_bd(conn, None)
    except LookupError:
        from albertitos.sources import erp as erp_mod

        e = erp_mod.ClienteERP(conn=conn).descargar_todo("v1")
        snapshot.guardar_erp(conn, e)
    r.maestro_version, r.erp_version = m.version, e.version

    if not extraer:
        r.extract_nota = "--sin-extraer: sólo hechos ya en la BD"
    else:
        try:
            r.extraidos = etapas.extract(conn, workers=workers)
        except NotImplementedError:
            r.extract_nota = "extract/etapa.py aún no implementado: sólo hechos ya en la BD"
            log.warning(r.extract_nota)
    r.sin_hechos = sin_hechos(conn)

    r.duplicados = etapas.marcar_duplicados(conn)
    r.decididas = etapas.decide(
        conn, norma_version=norma_version, fecha_corte=fecha_corte, maestro=m, erp=e
    )
    try:
        r.entregas = package.empaquetar(conn, entrega, caja, lote2, con_traza=con_traza)
    except package.EntregaInvalida as ex:
        r.rechazo = ex.informe
    return r
