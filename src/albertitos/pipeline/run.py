"""`albertitos run` de principio a fin: ingest → maestro → ERP → extract → duplicados → decide → package.

Sin extract disponible (o con `extraer=False`) decide con los hechos que ya hay en la BD
(`albertitos hechos import`); los ficheros sin hechos se quedan sin decisión y `package` se niega.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from albertitos.core.contracts import ErpSnapshot, MasterSnapshot
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, linaje, package
from albertitos.pipeline.validar import InformeValidacion

log = logging.getLogger(__name__)

MAESTRO_XLSX = "FINAL_v7_DEFINITIVO_ahorasi.xlsx"


@dataclass
class ResumenRun:
    ingeridos: int = 0  # nuevos o cambiados: lo ya registrado no se vuelve a abrir
    ficheros: int = 0
    segundos: float = 0.0
    maestro_version: str = ""
    erp_version: str = ""
    extraidos: int | None = None  # None = extract no corrió (saltado o no implementado)
    extract_nota: str = ""
    sin_hechos: list[str] = field(default_factory=list)
    duplicados: int = 0
    duplicados_quitados: int = 0
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
            f"ingest: {self.ingeridos} nuevos de {self.ficheros} · maestro {self.maestro_version} · erp {self.erp_version}",
            f"extract: {extract} · sin hechos: {len(self.sin_hechos)}"
            + (
                f" → {self.sin_hechos[:5]}{' …' if len(self.sin_hechos) > 5 else ''}"
                if self.sin_hechos
                else ""
            ),
            f"duplicados: +{self.duplicados} −{self.duplicados_quitados} · decisiones: {self.decididas}",
        ]
        for ruta, inf in self.entregas:
            lineas.append(f"{inf.texto()} → {ruta}")
        if self.rechazo is not None:
            lineas.append(
                f"NO se escribe la entrega (la anterior, si había, sigue intacta):\n{self.rechazo.texto()}"
            )
        fps = self.ficheros / self.segundos if self.segundos else 0.0
        lineas.append(
            f"tiempo: {self.segundos:.1f} s · {self.ficheros} ficheros · {fps:.1f} ficheros/s"
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

    t0 = time.perf_counter()
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

    r.duplicados, r.duplicados_quitados = etapas.marcar_duplicados(conn)
    r.decididas = etapas.decide(
        conn, norma_version=norma_version, fecha_corte=fecha_corte, maestro=m, erp=e
    )
    try:
        r.entregas = package.empaquetar(conn, entrega, caja, lote2, con_traza=con_traza)
    except package.EntregaInvalida as ex:
        r.rechazo = ex.informe
    r.ficheros = conn.execute("SELECT count(*) n FROM ficheros").fetchone()["n"]
    r.segundos = time.perf_counter() - t0
    return r


@dataclass
class ResumenReproceso:
    destino: str = ""  # "norma v3 · corte 2026-09-18 · maestro … · erp …"
    total: int = 0
    impactados: dict[str, str] = field(default_factory=dict)
    recalculadas: int = 0
    sin_impacto: int = 0  # decididas con otra versión de maestro/ERP que el diff no toca
    pendientes: list[str] = field(default_factory=list)
    duplicados: tuple[int, int] = (0, 0)
    cambios: list[dict[str, str]] = field(default_factory=list)
    segundos: float = 0.0

    def texto(self, max_cambios: int = 30) -> str:
        lineas = [
            f"destino: {self.destino}",
            f"duplicados: +{self.duplicados[0]} −{self.duplicados[1]}"
            f" · sin impacto por diff: {self.sin_impacto}"
            f" · pendientes sin hechos: {len(self.pendientes)}",
            f"{self.recalculadas} de {self.total} recalculadas · {len(self.cambios)} cambian"
            f" · {self.segundos:.2f} s",
        ]
        for c in self.cambios[:max_cambios]:
            por = self.impactados.get(c["file_id"], "")
            lineas.append(f"  {c['file_id']}: {c['antes']} → {c['despues']}  ({por})")
        if len(self.cambios) > max_cambios:
            lineas.append(f"  … y {len(self.cambios) - max_cambios} más")
        return "\n".join(lineas)


def reprocesar(
    conn: sqlite3.Connection,
    *,
    norma_version: str,
    fecha_corte: date,
    maestro: MasterSnapshot,
    erp: ErpSnapshot,
    lote: int | None = None,
    todo: bool = False,
) -> ResumenReproceso:
    """`reprocess --impacted`: duplicados → linaje → decide sólo lo impactado → diff de esta pasada.
    Las no impactadas no se tocan; las decididas con otra versión que el diff no toca dejan un evento."""
    t0 = time.perf_counter()
    r = ResumenReproceso(
        destino=f"norma {norma_version} · corte {fecha_corte} · maestro {maestro.version} · erp {erp.version}"
    )
    r.duplicados = etapas.marcar_duplicados(conn)
    lin = linaje.evaluar(
        conn,
        norma_version=norma_version,
        fecha_corte=fecha_corte,
        maestro=maestro,
        erp=erp,
        extractor_version=EXTRACTOR_VERSION,
        lote=lote,
        todo=todo,
    )
    r.total, r.impactados, r.pendientes = lin.total, lin.impactados, lin.pendientes
    desde = linaje.ultima_decision(conn)
    r.recalculadas = etapas.decide(
        conn,
        norma_version=norma_version,
        fecha_corte=fecha_corte,
        maestro=maestro,
        erp=erp,
        solo=list(lin.impactados),
        por=lin.impactados,
    )
    linaje.registrar_sin_impacto(conn, lin, norma_version)
    r.sin_impacto = len(lin.sin_impacto)
    r.cambios = linaje.diff_decisiones(conn, desde_id=desde)
    r.segundos = time.perf_counter() - t0
    return r
