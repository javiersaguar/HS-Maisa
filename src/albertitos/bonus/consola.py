"""Rutas GET del bonus para el puente de la consola (`albertitos.console.api`).

Mismo contrato que las rutas de Alejandro: `(conn, query) -> (status, body)`, con `conn` en sólo lectura y
`body` serializable a JSON. Se registran con una línea en `console/api.py`:

    from albertitos import bonus
    RUTAS.update(bonus.rutas())

Nada de aquí escribe en la BD ni cambia una decisión: recalcula el calendario en cada petición (0,2 s con
las 438 PAGAR de la Caja) a partir de las decisiones vigentes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from albertitos.bonus import Informe, calcular_conn
from albertitos.bonus import tesoreria as tes

Query = dict[str, list[str]]
Respuesta = tuple[int, Any]
Handler = Callable[[sqlite3.Connection, Query], Respuesta]

LIMITE_DEFECTO = 500


class ParametroInvalido(ValueError):
    pass


def _param(query: Query, clave: str) -> str | None:
    valores = query.get(clave) or []
    valor = valores[0].strip() if valores else ""
    return valor or None


def _bool(query: Query, clave: str) -> bool | None:
    valor = _param(query, clave)
    if valor is None:
        return None
    if valor.lower() in ("1", "true", "si", "sí"):
        return True
    if valor.lower() in ("0", "false", "no"):
        return False
    raise ParametroInvalido(f"{clave} tiene que ser true/false, no {valor!r}")


def _int(query: Query, clave: str, defecto: int | None = None) -> int | None:
    valor = _param(query, clave)
    if valor is None:
        return defecto
    try:
        n = int(valor)
    except ValueError:
        raise ParametroInvalido(f"{clave} tiene que ser un número entero, no {valor!r}") from None
    if n < 0:
        raise ParametroInvalido(f"{clave} no puede ser negativo")
    return n


def _informe(conn: sqlite3.Connection, query: Query) -> Informe:
    return calcular_conn(conn, estricto=bool(_bool(query, "estricto")))


def _pagos(pagos, query: Query) -> dict:
    limite = _int(query, "limite", LIMITE_DEFECTO)
    lista = [p.model_dump(mode="json") for p in pagos]
    return {"total": len(lista), "mostrados": min(len(lista), limite), "pagos": lista[:limite]}


def _envolver(fn: Callable[[sqlite3.Connection, Query], Any]) -> Handler:
    def handler(conn: sqlite3.Connection, query: Query) -> Respuesta:
        try:
            return 200, fn(conn, query)
        except ParametroInvalido as e:
            return 400, {"error": str(e)}
        except ValueError as e:  # BD sin decisiones, o con cortes distintos
            return 409, {"error": str(e)}

    return handler


def resumen(conn: sqlite3.Connection, query: Query) -> dict:
    informe = _informe(conn, query)
    t = tes.tesoreria(informe)
    return {
        **informe.resumen(),
        "vencido_importe_eur": t["vencido_importe_eur"],
        "en_plazo_importe_eur": t["en_plazo_importe_eur"],
        "semana_corte": t["semana_corte"],
        "lotes": sorted({p.lote for p in informe.calendario}),
        "proveedores": len({p.proveedor_id for p in informe.calendario}),
    }


def calendario(conn: sqlite3.Connection, query: Query) -> dict:
    informe = _informe(conn, query)
    semana, proveedor = _param(query, "semana"), _param(query, "proveedor")
    lote, vencido = _int(query, "lote"), _bool(query, "vencido")
    pagos = [
        p
        for p in informe.calendario
        if (semana is None or p.semana == semana)
        and (proveedor is None or proveedor in (p.proveedor_id, p.beneficiario))
        and (lote is None or p.lote == lote)
        and (vencido is None or p.vencido == vencido)
    ]
    filtros = {"semana": semana, "proveedor": proveedor, "lote": lote, "vencido": vencido}
    return {"filtros": filtros, **_pagos(pagos, query)}


def proveedores(conn: sqlite3.Connection, query: Query) -> dict:
    return {"proveedores": tes.proveedores(_informe(conn, query))}


def remesa(conn: sqlite3.Connection, query: Query) -> dict:
    informe = _informe(conn, query)
    return {
        "tipo": "BORRADOR: no es una orden bancaria ni acredita pagos ejecutados",
        "iban_sin_control": sum(not p.iban_control_ok for p in informe.remesa),
        **_pagos(informe.remesa, query),
    }


def avisos(conn: sqlite3.Connection, query: Query) -> dict:
    informe = _informe(conn, query)
    return {"total": len(informe.avisos), "avisos": [a.model_dump() for a in informe.avisos]}


def tesoreria(conn: sqlite3.Connection, query: Query) -> dict:
    informe = _informe(conn, query)
    out = tes.tesoreria(informe)
    tope = _param(query, "tope")
    if tope is not None:
        try:
            valor = Decimal(tope.replace(",", "."))
        except InvalidOperation:
            raise ParametroInvalido(f"tope tiene que ser un importe, no {tope!r}") from None
        if not valor.is_finite() or valor <= 0:
            raise ParametroInvalido("tope tiene que ser un importe positivo")
        out["programa"] = tes.programa(informe, valor)
    return out


def rutas() -> dict[str, Handler]:
    return {
        "/bonus/resumen": _envolver(resumen),
        "/bonus/calendario": _envolver(calendario),
        "/bonus/proveedores": _envolver(proveedores),
        "/bonus/remesa": _envolver(remesa),
        "/bonus/avisos": _envolver(avisos),
        "/bonus/tesoreria": _envolver(tesoreria),
    }
