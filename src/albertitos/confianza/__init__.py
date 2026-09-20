"""Confianza por factura: cuánta seguridad hay de que su clasificación (PAGAR / NO_PAGAR / ESCALAR) es la correcta.

Una puntuación 0-100 con su banda (alta / media / baja) y las tres razones que más pesan, construida con lo que el
sistema ya sabe de cada fuente por la que entró la factura: el PDF y sus lecturas, la coherencia de los importes, el
maestro, el ERP, la propia decisión y las políticas de empresa aún no fijadas. Tabla de pesos en `modelo.PESOS`
y en el ADR-0014.

Sólo lee: no cambia decisiones, hechos, avisos ni la entrega. No es una probabilidad calibrada (ver
`scripts/calibrar_confianza.py`).

    from albertitos.confianza import puntuar, puntuar_todas, resumen, rutas
    puntuar(conn, "F26-2201_transportes.pdf")       # dict, o None si no hay decisión vigente
    rutas()                                          # para console/api.py: RUTAS.update(confianza.rutas())
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

from albertitos.confianza.datos import cargar
from albertitos.confianza.modelo import (
    PESOS,
    UMBRAL_ALTA,
    UMBRAL_MEDIA,
    VERSION,
    banda,
    puntuar_expediente,
)
from albertitos.confianza.rutas import rutas

BANDAS = ("alta", "media", "baja")


def puntuar(conn: sqlite3.Connection, file_id: str) -> dict[str, Any] | None:
    """La confianza de un fichero entregado (por su nombre). None si no tiene decisión vigente."""
    expedientes = cargar(conn, file_id=file_id)
    if not expedientes:
        return None
    return puntuar_expediente(expedientes[0])


def puntuar_todas(conn: sqlite3.Connection, lote: int | None = None) -> list[dict[str, Any]]:
    return [puntuar_expediente(e) for e in cargar(conn, lote=lote)]


def resumen(puntuaciones: list[dict[str, Any]]) -> dict[str, Any]:
    """Bandas en total, por resultado y por lote; media de la puntuación."""
    por_resultado: dict[str, Counter] = {}
    por_lote: dict[str, Counter] = {}
    for p in puntuaciones:
        por_resultado.setdefault(p["resultado"], Counter())[p["banda"]] += 1
        por_lote.setdefault(str(p["lote"]), Counter())[p["banda"]] += 1
    total = Counter(p["banda"] for p in puntuaciones)

    def _b(c: Counter) -> dict[str, int]:
        return {b: c.get(b, 0) for b in BANDAS}

    n = len(puntuaciones)
    return {
        "version": VERSION,
        "total": n,
        "bandas": _b(total),
        "por_resultado": {r: _b(c) for r, c in sorted(por_resultado.items())},
        "por_lote": {lo: _b(c) for lo, c in sorted(por_lote.items())},
        "media": round(sum(p["puntuacion"] for p in puntuaciones) / n, 1) if n else None,
        "umbrales": {"alta": UMBRAL_ALTA, "media": UMBRAL_MEDIA},
        "escala": "puntuación ordinal 0-100 (100 = sin dudas conocidas); no es una probabilidad calibrada",
    }


__all__ = ["BANDAS", "PESOS", "VERSION", "banda", "puntuar", "puntuar_todas", "resumen", "rutas"]
