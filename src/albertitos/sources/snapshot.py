"""Snapshots versionados del maestro y del ERP en la BD, y diff entre versiones del ERP."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime
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


def resumen_erp(conn: sqlite3.Connection, version: str) -> dict[str, Any]:
    """Resumen sólo lectura: contadores del snapshot y latencias HTTP de su descarga.

    Los pulls nuevos guardan los ids exactos de sus eventos (soporta concurrencia).
    Para el histórico sin vínculo se infiere una ventana sólo si encajan consultas,
    reintentos, páginas consecutivas y estado final junto a descargado_en. Se etiqueta
    como inferencia; si falta evidencia devuelve None, nunca ceros inventados.
    La latencia es la suma HTTP, excluye ritmo, backoff y esperas entre peticiones.
    """
    fila = conn.execute(
        "SELECT datos_json FROM snapshots WHERE tipo='erp' AND version=?", (version,)
    ).fetchone()
    if fila is None:
        raise LookupError(f"no hay snapshot del ERP {version}: `albertitos erp pull --tag v1`")
    s = ErpSnapshot.model_validate_json(fila[0])
    resultado = {
        "version": s.version,
        "descargado_en": s.descargado_en.isoformat(),
        "asientos": len(s.asientos),
        "consultas": s.consultas,
        "reintentos": s.reintentos,
        "errores_por_codigo": None,
        "latencia_total_ms": None,
        "atribucion": "no_disponible",
        "eventos": [],
    }
    # No se cambia row_factory ni se escribe: también funciona con sqlite3 puro.
    cursor = conn.execute(
        "SELECT id,ts,estado,error_codigo,latencia_ms,detalle FROM eventos WHERE etapa='enrich' ORDER BY id"
    )
    filas = [dict(zip([c[0] for c in cursor.description], f, strict=True)) for f in cursor]
    por_id = {f["id"]: f for f in filas}
    vinculados = None
    for f in reversed(filas):
        try:
            d = json.loads(f["detalle"] or "")
        except (ValueError, TypeError):
            continue
        if (
            not isinstance(d, dict)
            or d.get("tipo") != "erp_descarga"
            or d.get("version") != version
        ):
            continue
        if d.get("descargado_en") == s.descargado_en.isoformat():
            ids = d.get("eventos", [])
            if (
                not isinstance(ids, list)
                or any(type(i) is not int for i in ids)
                or len(set(ids)) != len(ids)
            ):
                return resultado
            vinculados = [por_id[i] for i in ids if i in por_id]
            if len(vinculados) != s.consultas or len(ids) != s.consultas:
                return resultado
            resultado["atribucion"] = "explicita"
            break
    if vinculados is None:
        anteriores = []
        for f in filas:
            try:
                ts = datetime.fromisoformat(f["ts"])
                if ts <= s.descargado_en and str(f["detalle"]).startswith(
                    ("GET /erp/", "POST /erp/", "login:")
                ):
                    anteriores.append(f)
            except (TypeError, ValueError):
                continue
        vinculados = anteriores[-s.consultas :] if s.consultas > 0 else []
        if not vinculados or len(vinculados) != s.consultas:
            return resultado
        ultimo = vinculados[-1]
        edad = (s.descargado_en - datetime.fromisoformat(ultimo["ts"])).total_seconds()
        paginas = []
        for f in vinculados:
            if f["estado"] == "ok":
                m = re.fullmatch(r"GET /erp/asientos \{'pagina': '(\d+)'\}", f["detalle"] or "")
                if m:
                    paginas.append(int(m[1]))
        if (
            ultimo["detalle"] != "GET /erp/estado"
            or ultimo["estado"] != "ok"
            or not 0 <= edad < 1
            or not paginas
            or paginas != list(range(1, len(paginas) + 1))
            or sum(f["estado"] == "retry" for f in vinculados) != s.reintentos
            or any(f["estado"] == "error" for f in vinculados)
        ):
            return resultado
        resultado["atribucion"] = "inferida_por_ventana"
    resultado["eventos"] = [f["id"] for f in vinculados]
    resultado["errores_por_codigo"] = dict(
        sorted(Counter(f["error_codigo"] for f in vinculados if f["error_codigo"]).items())
    )
    latencias = [f["latencia_ms"] for f in vinculados]
    resultado["latencia_total_ms"] = (
        sum(latencias) if all(x is not None for x in latencias) else None
    )
    return resultado
