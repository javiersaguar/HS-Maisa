"""Todo lo que el sistema ya sabe de cada factura, leído de la BD en sólo lectura.

Un `Expediente` por nombre entregado (copias exactas incluidas): hechos vigentes, decisión vigente, los snapshots
del maestro y del ERP con los que se decidió, las lecturas del LLM guardadas en `cache_llm` (el contraste de las
plantillas y las lecturas de las escaneadas) y el detalle del último evento de extracción.

No importa `rules/` ni `extract/` y no recalcula nada: lee lo que dejaron. Una consulta por tabla, así que puntuar las
500 cuesta lo que cuesta leerlas.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import ErpSnapshot, InvoiceFacts, MasterSnapshot

#: Variantes de la caché que no son lecturas de la factura sino ensayos de velocidad: no cuentan.
_VARIANTES_IGNORADAS = ("bench",)


def nfc(valor: str) -> str:
    return unicodedata.normalize("NFC", valor)


def _nombre_entrega(file_id: str) -> str:
    # P0-5 (rama de Miguel): el PDF que choca con un nombre del lote 1 se guarda como "./X.pdf".
    prefijo = getattr(db, "PREFIJO_INTERNO", None)
    if prefijo and file_id.startswith(prefijo):
        return file_id[len(prefijo) :]
    return file_id


@dataclass
class Expediente:
    file_id: str
    lote: int
    sha256: str
    tiene_texto: bool | None
    decision: dict[str, Any]
    hechos: InvoiceFacts | None = None
    maestro: MasterSnapshot | None = None
    erp: ErpSnapshot | None = None
    #: (variante, respuesta cruda del LLM) — p. ej. ("contraste", {...}) o ("qwen3.6|sup200", {...})
    lecturas: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    detalle_extract: str | None = None
    #: otros nombres entregados con el mismo PDF (copias exactas, P0-1)
    mismo_pdf_que: list[str] = field(default_factory=list)

    @property
    def motivos(self) -> list[dict[str, Any]]:
        return self.decision.get("motivos") or []

    @property
    def resultado(self) -> str:
        return str(self.decision.get("resultado"))


def _tabla(conn: sqlite3.Connection, nombre: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (nombre,)
        ).fetchone()
        is not None
    )


def _decisiones(
    conn: sqlite3.Connection, lote: int | None, file_id: str | None
) -> list[dict[str, Any]]:
    sql = """SELECT d.file_id, d.sha256, d.resultado, d.norma_version, d.fecha_corte, d.maestro_version,
                    d.erp_version, d.motivos_json, f.lote, f.tiene_texto
             FROM decisiones d JOIN ficheros f ON f.sha256 = d.sha256
             WHERE d.vigente = 1"""
    params: list[Any] = []
    if lote is not None:
        sql += " AND f.lote = ?"
        params.append(lote)
    # Uno solo: se filtra en SQL (la consola y el calendario de K1 piden de uno en uno).
    if file_id is not None:
        nombre = nfc(file_id)
        candidatos = [nombre, f"{getattr(db, 'PREFIJO_INTERNO', '')}{nombre}"]
        sql += " AND (d.file_id IN (?, ?)"
        params += candidatos
        if _tabla(conn, "identidades"):
            sql += " OR d.sha256 IN (SELECT sha256 FROM identidades WHERE file_id = ?)"
            params.append(nombre)
        sql += ")"
    filas = [dict(r) for r in conn.execute(sql, params).fetchall()]
    for f in filas:
        f["file_id"] = nfc(_nombre_entrega(f["file_id"]))
        f["motivos"] = json.loads(f.pop("motivos_json") or "[]")

    # Las copias exactas (tabla `identidades`, P0-1) llevan la decisión de su PDF con su propio nombre.
    if _tabla(conn, "identidades"):
        por_sha: dict[str, dict[str, Any]] = {}
        for f in filas:
            por_sha.setdefault(f["sha256"], f)
        sql_i = "SELECT file_id, lote, sha256 FROM identidades"
        params_i: list[Any] = []
        if lote is not None:
            sql_i += " WHERE lote = ?"
            params_i.append(lote)
        ya = {(f["file_id"], f["lote"]) for f in filas}
        extra = []
        for r in conn.execute(sql_i, params_i).fetchall():
            base = por_sha.get(r["sha256"])
            if base is None:  # la decisión es de otro lote: se busca sin filtro
                fila = conn.execute(
                    """SELECT d.file_id, d.sha256, d.resultado, d.norma_version, d.fecha_corte,
                              d.maestro_version, d.erp_version, d.motivos_json, f.tiene_texto
                       FROM decisiones d JOIN ficheros f ON f.sha256 = d.sha256
                       WHERE d.vigente = 1 AND d.sha256 = ?""",
                    (r["sha256"],),
                ).fetchone()
                if fila is None:
                    continue
                base = dict(fila)
                base["motivos"] = json.loads(base.pop("motivos_json") or "[]")
            nombre = nfc(_nombre_entrega(r["file_id"]))
            if (nombre, r["lote"]) in ya:
                continue
            extra.append({**base, "file_id": nombre, "lote": r["lote"]})
        filas.extend(extra)

    if file_id is not None:
        objetivo = nfc(file_id)
        filas = [f for f in filas if f["file_id"] == objetivo]
    return sorted(filas, key=lambda f: (f["lote"], f["file_id"]))


def _en(shas: set[str]) -> tuple[str, list[str]]:
    """Filtro `IN (...)` para pocas sha256; para muchas, sin filtro (una pasada es más barata)."""
    if len(shas) > 50:
        return "", []
    return f" AND sha256 IN ({','.join('?' * len(shas))})", sorted(shas)


def _hechos(conn: sqlite3.Connection, shas: set[str]) -> dict[str, InvoiceFacts]:
    filtro, params = _en(shas)
    filas = conn.execute(
        f"""SELECT h.sha256, h.hechos_json FROM hechos h
           JOIN (SELECT sha256, MAX(creado_en) AS c FROM hechos WHERE 1=1{filtro} GROUP BY sha256) u
             ON u.sha256 = h.sha256 AND u.c = h.creado_en""",
        params,
    ).fetchall()
    return {
        r["sha256"]: InvoiceFacts.model_validate_json(r["hechos_json"])
        for r in filas
        if r["sha256"] in shas
    }


def _lecturas(conn: sqlite3.Connection, shas: set[str]) -> dict[str, list[tuple[str, dict]]]:
    if not _tabla(conn, "cache_llm"):
        return {}
    out: dict[str, list[tuple[str, dict]]] = {}
    filtro, params = _en(shas)
    sql = "SELECT clave, respuesta_json FROM cache_llm"
    if filtro:
        sql += f" WHERE substr(clave, 1, 64) IN ({','.join('?' * len(params))})"
    for clave, respuesta in conn.execute(sql, params):
        sha, _, resto = clave.partition("|")
        if sha not in shas or any(v in resto for v in _VARIANTES_IGNORADAS):
            continue
        partes = resto.split("|")  # prompt_version | modelo [| variante]
        variante = "|".join(partes[1:]) if len(partes) > 1 else resto
        try:
            datos = json.loads(respuesta)
        except json.JSONDecodeError:
            continue
        if isinstance(datos, dict):
            out.setdefault(sha, []).append((variante, datos))
    return out


def _detalles_extract(conn: sqlite3.Connection, shas: set[str]) -> dict[str, str]:
    filtro, params = _en(shas)
    filas = conn.execute(
        f"""SELECT sha256, detalle FROM eventos WHERE id IN (
             SELECT MAX(id) FROM eventos WHERE etapa = 'extract' AND estado = 'ok'{filtro}
             GROUP BY sha256)""",
        params,
    ).fetchall()
    return {r["sha256"]: r["detalle"] or "" for r in filas if r["sha256"] in shas}


#: Maestro y ERP ya validados, por (tipo, versión, creado_en): validarlos es lo más caro de puntuar una factura, y
#: una versión guardada no cambia (si alguien la reescribe, cambia `creado_en` y se vuelve a cargar).
_SNAPSHOTS: dict[tuple[str, str, str], Any] = {}


class _Snapshots:
    """Carga cada versión de maestro/ERP una sola vez (las 500 decisiones comparten dos o tres)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, tipo: str, version: str | None) -> Any:
        if not version:
            return None
        fila = self.conn.execute(
            "SELECT creado_en FROM snapshots WHERE tipo = ? AND version = ?", (tipo, version)
        ).fetchone()
        if fila is None:
            return None
        clave = (tipo, version, fila[0])
        if clave not in _SNAPSHOTS:
            bruto = db.cargar_snapshot(self.conn, tipo, version)
            modelo = MasterSnapshot if tipo == "maestro" else ErpSnapshot
            _SNAPSHOTS[clave] = modelo.model_validate_json(bruto) if bruto else None
        return _SNAPSHOTS[clave]


def cargar(
    conn: sqlite3.Connection, *, lote: int | None = None, file_id: str | None = None
) -> list[Expediente]:
    """Un expediente por nombre entregado con decisión vigente. Sólo lee."""
    decisiones = _decisiones(conn, lote, file_id)
    shas = {d["sha256"] for d in decisiones}
    hechos = _hechos(conn, shas)
    lecturas = _lecturas(conn, shas)
    detalles = _detalles_extract(conn, shas)
    snaps = _Snapshots(conn)
    nombres_por_sha: dict[str, list[str]] = {}
    for d in decisiones:
        nombres_por_sha.setdefault(d["sha256"], []).append(d["file_id"])

    out = []
    for d in decisiones:
        tiene_texto = d.get("tiene_texto")
        out.append(
            Expediente(
                file_id=d["file_id"],
                lote=int(d["lote"]),
                sha256=d["sha256"],
                tiene_texto=None if tiene_texto is None else bool(tiene_texto),
                decision=d,
                hechos=hechos.get(d["sha256"]),
                maestro=snaps.get("maestro", d.get("maestro_version")),
                erp=snaps.get("erp", d.get("erp_version")),
                lecturas=lecturas.get(d["sha256"], []),
                detalle_extract=detalles.get(d["sha256"]),
                mismo_pdf_que=[n for n in nombres_por_sha[d["sha256"]] if n != d["file_id"]],
            )
        )
    return out
