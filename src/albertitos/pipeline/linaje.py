"""Linaje: qué ficheros hay que (re)decidir, por qué, y cuáles siguen valiendo con otras versiones.

Una decisión depende de sus hechos, de la norma y de la fecha de corte; del maestro y del ERP sólo
depende de lo que la norma lee con el pedido y el NIF de la factura (v3: R1 busca el proveedor por NIF,
R2 el pedido, R5 los asientos del pedido; `tests/test_linaje.py` lo comprueba para cada norma del
REGISTRO). Así que:
- hechos, norma o fecha de corte distintos → se recalcula. "Hechos distintos" es `hechos_hash` distinto
  o hechos reescritos después de la decisión: el hash excluye `texto_sospechoso` (R6 lo cita en el
  motivo) y `confianza` (R6 escala `< 1` desde ADR-0011), y unos hechos reimportados o reextraídos que
  sólo cambien eso no se colarían;
- maestro o ERP distintos → se recalcula sólo si el diff entre la versión con la que se decidió y la de
  destino toca su pedido o su NIF. Las demás NO se tocan: conservan la versión con la que se decidieron
  y se deja un evento `decide/skip` que dice que el diff no les afecta.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ErpSnapshot,
    EstadoEvento,
    Etapa,
    Event,
    InvoiceFacts,
    MasterSnapshot,
)
from albertitos.sources import snapshot


def clave_nif(nif: str | None) -> str | None:
    """La misma normalización que `MasterSnapshot.proveedor_por_nif`."""
    return nif.replace(" ", "").replace("-", "").upper() if nif else None


def diff_maestro(a: MasterSnapshot, b: MasterSnapshot) -> dict[str, Any]:
    """Pedidos y NIF (normalizados) cuyo registro aparece, desaparece o cambia entre dos maestros."""
    pedidos = {
        k for k in a.pedidos.keys() | b.pedidos.keys() if a.pedidos.get(k) != b.pedidos.get(k)
    }
    nifs: set[str] = set()
    for k in a.proveedores.keys() | b.proveedores.keys():
        x, y = a.proveedores.get(k), b.proveedores.get(k)
        if x != y:
            nifs |= {n for p in (x, y) if p is not None and (n := clave_nif(p.nif))}
    return {
        "de": a.version,
        "a": b.version,
        "pedidos_afectados": sorted(pedidos),
        "nifs_afectados": sorted(nifs),
    }


@dataclass
class Linaje:
    impactados: dict[str, str] = field(default_factory=dict)  # file_id → por qué se recalcula
    sin_impacto: list[dict[str, Any]] = field(
        default_factory=list
    )  # otras versiones, diff sin efecto
    pendientes: list[str] = field(default_factory=list)  # sin hechos: no se pueden decidir
    total: int = 0


def evaluar(
    conn: sqlite3.Connection,
    *,
    norma_version: str,
    fecha_corte: date,
    maestro: MasterSnapshot,
    erp: ErpSnapshot,
    extractor_version: str,
    lote: int | None = None,
    todo: bool = False,
) -> Linaje:
    """Clasifica cada fichero frente al destino (norma, corte, maestro, ERP). `todo` recalcula todo."""
    filas = conn.execute(
        """
        SELECT f.file_id, f.sha256, h.hechos_json, h.hechos_hash AS h_hash, h.creado_en AS h_en,
               d.id AS decision, d.hechos_hash AS d_hash, d.decidido_en AS d_en, d.norma_version,
               d.fecha_corte, d.maestro_version, d.erp_version
        FROM ficheros f
        LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
        LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
        WHERE (? IS NULL OR f.lote = ?)
        ORDER BY f.file_id
        """,
        (extractor_version, lote, lote),
    ).fetchall()
    diffs: dict[tuple[str, str], dict[str, Any] | None] = {}

    def diff(tipo: str, origen: str) -> dict[str, Any] | None:
        """Diff origen → destino, una vez por versión de origen. None si el origen ya no está en la BD."""
        if (tipo, origen) not in diffs:
            try:
                if tipo == "maestro":
                    diffs[tipo, origen] = diff_maestro(
                        snapshot.cargar_maestro_bd(conn, origen), maestro
                    )
                else:
                    diffs[tipo, origen] = snapshot.diff_erp(
                        snapshot.cargar_erp_bd(conn, origen), erp
                    )
            except LookupError:
                diffs[tipo, origen] = None
        return diffs[tipo, origen]

    out = Linaje(total=len(filas))
    corte = fecha_corte.isoformat()
    copias = db.nombres_por_sha(conn)
    for f in filas:
        fid = str(f["file_id"])
        if f["h_hash"] is None:
            out.pendientes.append(fid)
            continue
        if todo:
            out.impactados[fid] = "recálculo completo (--todo)"
            continue
        if f["decision"] is None:
            out.impactados[fid] = "sin decisión"
            continue
        if f["d_hash"] != f["h_hash"]:
            out.impactados[fid] = _por_hechos(
                f["hechos_json"], f["d_hash"], copias.get(f["sha256"])
            )
            continue
        if _posterior(f["h_en"], f["d_en"]):
            out.impactados[fid] = "hechos reescritos tras decidir (evidencia o confianza)"
            continue
        if f["norma_version"] != norma_version:
            out.impactados[fid] = f"norma {f['norma_version']}→{norma_version}"
            continue
        if f["fecha_corte"] != corte:
            out.impactados[fid] = f"fecha de corte {f['fecha_corte']}→{corte}"
            continue
        h = json.loads(f["hechos_json"])
        pedido, nif = h.get("pedido"), clave_nif(h.get("nif_emisor"))
        por: list[str] = []
        confirmado: dict[str, str] = {}
        for tipo, origen, destino in (
            ("maestro", f["maestro_version"], maestro.version),
            ("erp", f["erp_version"], erp.version),
        ):
            if origen == destino:
                continue
            d = diff(tipo, origen)
            tramo = f"{tipo} {origen}→{destino}"
            if d is None:
                por.append(f"{tramo}: no está el snapshot {origen}")
            elif pedido and pedido in d["pedidos_afectados"]:
                por.append(f"{tramo}: {pedido}")
            elif nif and nif in d.get("nifs_afectados", ()):
                por.append(f"{tramo}: NIF {nif}")
            else:
                confirmado[tipo] = f"{origen}→{destino}"
        if por:
            out.impactados[fid] = " · ".join(por)
        elif confirmado:
            out.sin_impacto.append(
                {"file_id": fid, "sha256": f["sha256"], "decision": f["decision"], **confirmado}
            )
    return out


def _por_hechos(hechos_json: str, hash_decidido: str, nombres: list[tuple[str, int]] | None) -> str:
    """Por qué cambiaron los hechos, cuando se puede decir: si lo único distinto es la marca de
    duplicado (la pone o la quita `marcar_duplicados`), se dice, y si es por una copia exacta, con
    todos sus nombres. Si no, «hechos cambiados»."""
    h = InvoiceFacts.model_validate_json(hechos_json)
    marcado = Aviso.DUPLICADO_SOSPECHOSO in h.avisos
    h.avisos = (
        [a for a in h.avisos if a != Aviso.DUPLICADO_SOSPECHOSO]
        if marcado
        else [*h.avisos, Aviso.DUPLICADO_SOSPECHOSO]
    )
    if h.hash() != hash_decidido:
        return "hechos cambiados"
    if not marcado:
        return "duplicado quitado: ya no comparte pedido, factura ni PDF con otro"
    if nombres:
        todos = ", ".join(f"{fid} (lote {lote})" for fid, lote in nombres)
        return f"copia exacta: el mismo PDF llega como {todos} → duplicado marcado"
    return "duplicado marcado: comparte pedido o factura con otro PDF"


def _posterior(a: str | None, b: str | None) -> bool:
    """¿El instante ISO `a` es estrictamente posterior a `b`? (distinta precisión: se parsea)"""
    if not a or not b:
        return False
    return datetime.fromisoformat(a) > datetime.fromisoformat(b)


def impactados(conn: sqlite3.Connection, **kw: Any) -> dict[str, str]:
    """file_id → motivo de lo que `reprocess --impacted` recalcula: nada más."""
    return evaluar(conn, **kw).impactados


def registrar_sin_impacto(conn: sqlite3.Connection, lin: Linaje, norma_version: str) -> int:
    """Un evento decide/skip por decisión que sigue valiendo con otra versión de maestro/ERP.
    Idempotente: si ese mismo evento (decisión y tramo) ya está, no se repite."""
    ya = {
        (r["file_id"], r["detalle"])
        for r in conn.execute(
            "SELECT file_id, detalle FROM eventos WHERE etapa=? AND estado=?",
            (Etapa.DECIDE.value, EstadoEvento.SKIP.value),
        )
    }
    n = 0
    for s in lin.sin_impacto:
        detalle = json.dumps(
            {
                "linaje": "sin impacto",
                **{k: s[k] for k in ("decision", "maestro", "erp") if k in s},
            },
            ensure_ascii=False,
        )
        if (s["file_id"], detalle) in ya:
            continue
        db.registrar_evento(
            conn,
            Event(
                file_id=s["file_id"],
                sha256=s["sha256"],
                etapa=Etapa.DECIDE,
                estado=EstadoEvento.SKIP,
                version=norma_version,
                detalle=detalle,
            ),
        )
        n += 1
    conn.commit()
    return n


def ultima_decision(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT coalesce(max(id), 0) m FROM decisiones").fetchone()["m"])


def diff_decisiones(conn: sqlite3.Connection, desde_id: int | None = None) -> list[dict[str, str]]:
    """Para cada fichero con más de una decisión, la vigente frente a la inmediatamente anterior.
    Con `desde_id`, sólo las vigentes creadas después (las de una pasada de `reprocess`)."""
    filas = conn.execute(
        """
        SELECT a.file_id, a.resultado AS antes, b.resultado AS despues, b.norma_version, b.erp_version
        FROM decisiones b
        JOIN decisiones a ON a.sha256 = b.sha256 AND a.vigente = 0
          AND a.id = (SELECT max(id) FROM decisiones x WHERE x.sha256 = b.sha256 AND x.id < b.id)
        WHERE b.vigente = 1 AND a.resultado <> b.resultado AND b.id > ?
        ORDER BY a.file_id
        """,
        (desde_id or 0,),
    ).fetchall()
    return [dict(r) for r in filas]
