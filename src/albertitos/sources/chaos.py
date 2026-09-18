"""Interruptor de caos para la demo de resiliencia. Lo lee extract/llm.py antes de cada llamada."""

from __future__ import annotations

import json
import os
from pathlib import Path

RUTA = Path(os.environ.get("ALBERTITOS_CHAOS", "dist/chaos.json"))
MODOS = ("llm_down", "llm_429", "llm_invalid")


def activar(modo: str) -> None:
    if modo not in MODOS:
        raise ValueError(f"modo {modo!r}; válidos: {MODOS}")
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    RUTA.write_text(json.dumps({"modo": modo}))


def desactivar() -> None:
    if RUTA.exists():
        RUTA.unlink()


def modo() -> str | None:
    try:
        return json.loads(RUTA.read_text()).get("modo")
    except (OSError, ValueError):
        return None
