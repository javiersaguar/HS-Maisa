"""Interruptor de caos para la demo de resiliencia. Lo lee extract/llm.py antes de cada llamada.

El fichero vive **junto a la BD** (`<db>.chaos.json`), no en una ruta global: si fuera global, ensayar
la caída del proveedor en una BD de pruebas tumbaría cualquier extracción real en curso (le pasó a C1
el 18/09 con una medición en marcha). `ALBERTITOS_CHAOS` sigue mandando si se indica.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MODOS = ("llm_down", "llm_429", "llm_invalid", "llm_timeout")
RUTA: Path | None = None  # sólo para los tests: si se fija, gana sobre el entorno


def ruta() -> Path:
    """Fichero de caos de ESTA base de datos, resuelto en cada llamada (el entorno puede cambiar)."""
    if RUTA is not None:
        return Path(RUTA)
    explicito = os.environ.get("ALBERTITOS_CHAOS")
    if explicito:
        return Path(explicito)
    db = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    return db.with_suffix(db.suffix + ".chaos.json")


def activar(modo: str) -> None:
    if modo not in MODOS:
        raise ValueError(f"modo {modo!r}; válidos: {MODOS}")
    destino = ruta()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"modo": modo}))


def desactivar() -> None:
    destino = ruta()
    if destino.exists():
        destino.unlink()


def modo() -> str | None:
    try:
        return json.loads(ruta().read_text()).get("modo")
    except (OSError, ValueError):
        return None
