"""Rutas GET para el puente de la consola (`console/api.py`), con su misma firma: `(conn, query) -> (status, body)`.

Alejandro las registra con una línea: `RUTAS.update(confianza.rutas())`. La conexión la abre el puente en sólo lectura.

    GET /confianza/resumen?lote=                               bandas por lote y por resultado
    GET /confianza/ficheros?banda=&resultado=&lote=&limite=&orden=   lista, por defecto las de MENOR confianza primero
    GET /confianza/fichero?file_id=                            puntuación, banda, razones y desglose por fuente
"""

from __future__ import annotations

import sqlite3
import time
import unicodedata
from collections.abc import Callable
from typing import Any

Query = dict[str, list[str]]
Respuesta = tuple[int, Any]
API = 1  # como lecturas.API_VERSION: sube si cambia un nombre o un tipo que la consola ya lee
LIMITE_DEFECTO = 50
LIMITE_MAXIMO = 1000


def _param(query: Query, clave: str) -> str | None:
    valores = query.get(clave) or []
    if not valores or valores[0] in ("", "all"):
        return None
    return valores[0]


def _entero(query: Query, clave: str, defecto: int | None) -> int | None:
    bruto = _param(query, clave)
    if bruto is None:
        return defecto
    try:
        return int(bruto)
    except ValueError:
        return defecto


def _r_resumen(conn: sqlite3.Connection, query: Query) -> Respuesta:
    from albertitos.confianza import puntuar_todas, resumen

    t0 = time.perf_counter()
    cuerpo = resumen(puntuar_todas(conn, lote=_entero(query, "lote", None)))
    cuerpo["api"] = API
    cuerpo["segundos"] = round(time.perf_counter() - t0, 3)
    return 200, cuerpo


def _r_ficheros(conn: sqlite3.Connection, query: Query) -> Respuesta:
    from albertitos.confianza import puntuar_todas

    items = puntuar_todas(conn, lote=_entero(query, "lote", None))
    banda = _param(query, "banda")
    resultado = _param(query, "resultado")
    if banda:
        items = [p for p in items if p["banda"] == banda]
    if resultado:
        items = [p for p in items if p["resultado"] == resultado.upper()]
    descendente = (_param(query, "orden") or "asc") == "desc"
    items.sort(key=lambda p: (p["puntuacion"], p["file_id"]), reverse=descendente)
    limite = max(1, min(_entero(query, "limite", LIMITE_DEFECTO) or LIMITE_DEFECTO, LIMITE_MAXIMO))
    filas = [
        {
            "file_id": p["file_id"],
            "lote": p["lote"],
            "resultado": p["resultado"],
            "regla": p["regla"],
            "puntuacion": p["puntuacion"],
            "banda": p["banda"],
            "razon_principal": p["razones"][0] if p["razones"] else None,
            "razones": p["razones"],
        }
        for p in items[:limite]
    ]
    return 200, {"api": API, "items": filas, "total": len(items), "limite": limite}


def _r_fichero(conn: sqlite3.Connection, query: Query) -> Respuesta:
    from albertitos.confianza import puntuar

    file_id = _param(query, "file_id")
    if not file_id:
        return 400, {"error": "falta ?file_id=<nombre del PDF>"}
    cuerpo = puntuar(conn, unicodedata.normalize("NFC", file_id))
    if cuerpo is None:
        return 404, {"error": f"el fichero {file_id} no existe o no tiene decisión vigente"}
    return 200, {"api": API, **cuerpo}


def rutas() -> dict[str, Callable[[sqlite3.Connection, Query], Respuesta]]:
    """Las rutas GET de la confianza, para `RUTAS.update(confianza.rutas())` en console/api.py."""
    return {
        "/confianza/resumen": _r_resumen,
        "/confianza/ficheros": _r_ficheros,
        "/confianza/fichero": _r_fichero,
    }
