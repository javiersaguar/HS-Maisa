"""Snapshots versionados del maestro y del ERP en la BD, y diff entre versiones del ERP."""

from __future__ import annotations

import sqlite3
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import ErpSnapshot, MasterSnapshot


def guardar_maestro(conn: sqlite3.Connection, m: MasterSnapshot) -> None:
    db.guardar_snapshot(conn, "maestro", m.version, m.model_dump_json())
    conn.commit()


def cargar_maestro_bd(conn: sqlite3.Connection, version: str | None = None) -> MasterSnapshot:
    datos = (
        db.cargar_snapshot(conn, "maestro", version)
        if version
        else (db.ultimo_snapshot(conn, "maestro") or (None, None))[1]
    )
    if datos is None:
        raise LookupError("no hay snapshot del maestro: `albertitos maestro`")
    return MasterSnapshot.model_validate_json(datos)


def guardar_erp(conn: sqlite3.Connection, s: ErpSnapshot) -> None:
    db.guardar_snapshot(conn, "erp", s.version, s.model_dump_json())
    conn.commit()


def cargar_erp_bd(conn: sqlite3.Connection, version: str | None = None) -> ErpSnapshot:
    datos = (
        db.cargar_snapshot(conn, "erp", version)
        if version
        else (db.ultimo_snapshot(conn, "erp") or (None, None))[1]
    )
    if datos is None:
        raise LookupError(
            f"no hay snapshot del ERP{' ' + version if version else ''}: `albertitos erp pull --tag v1`"
        )
    return ErpSnapshot.model_validate_json(datos)


def diff_erp(a: ErpSnapshot, b: ErpSnapshot) -> dict[str, Any]:
    """Diferencias contables, con todos los pedidos cuyo contexto ha cambiado."""
    nuevos = sorted(set(b.asientos) - set(a.asientos))
    eliminados = sorted(set(a.asientos) - set(b.asientos))
    cambiados: dict[str, dict[str, tuple[Any, Any]]] = {}
    for k in sorted(set(a.asientos) & set(b.asientos)):
        x, y = a.asientos[k].model_dump(mode="json"), b.asientos[k].model_dump(mode="json")
        delta = {campo: (x[campo], y[campo]) for campo in x if x[campo] != y[campo]}
        if delta:
            cambiados[k] = delta
    pedidos_afectados = sorted(
        {b.asientos[k].pedido for k in nuevos}
        | {a.asientos[k].pedido for k in eliminados}
        | {a.asientos[k].pedido for k in cambiados}
        | {b.asientos[k].pedido for k in cambiados}
    )
    return {
        "de": a.version,
        "a": b.version,
        "nuevos": nuevos,
        "eliminados": eliminados,
        "cambiados": cambiados,
        "pedidos_afectados": pedidos_afectados,
    }
