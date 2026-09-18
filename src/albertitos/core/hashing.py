"""Hashes: identidad de ficheros (sha256 del PDF) y hash canónico de estructuras (linaje)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_fichero(ruta: Path | str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def hash_canonico(obj: Any) -> str:
    """sha256 del JSON ordenado y sin espacios: mismo contenido → mismo hash, siempre."""
    datos = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()
