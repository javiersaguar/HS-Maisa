"""Arranque de Render: sin clave sólo lectura; con clave, copia efímera para subidas."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from albertitos.console import api, bandeja


def comando(origen: Path = Path("/app/deploy/demo.db")) -> list[str]:
    orden = [sys.executable, "-m", "albertitos.console.api", "--db", str(origen)]
    if not os.environ.get("ALBERTITOS_CLAVE_DEMO", "").strip():
        return orden
    # No activar las subidas si se despliega A3 antes de integrar la puerta de A1.
    if not callable(getattr(api, "clave_ok", None)):
        raise RuntimeError("Falta la puerta del backend de PLAN-15; no se activan las subidas.")
    carpeta = Path(tempfile.mkdtemp(prefix="albertitos-demo-"))
    copia = bandeja.preparar(origen, carpeta / "bandeja.db")
    os.environ["ALBERTITOS_BANDEJA_EFIMERA"] = "1"
    return [sys.executable, "-m", "albertitos.console.api", "--db", str(copia), "--bandeja"]


def main() -> None:
    orden = comando()
    os.execv(orden[0], orden)


if __name__ == "__main__":
    main()
