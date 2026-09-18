"""PostToolUse(Edit|Write|MultiEdit): ruff format + ruff check --fix sobre el .py tocado.

No decide nada: formatea siempre. Si quedan errores que ruff no arregla solo, sale con 2 para que
el agente los vea y los corrija (PostToolUse no bloquea, pero el stderr llega al modelo).
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from _common import leer_entrada, raiz_proyecto, ruta_relativa

datos = leer_entrada()
entrada = datos.get("tool_input") or {}
ruta = entrada.get("file_path") or ""
if not ruta.endswith(".py"):
    raise SystemExit(0)
raiz = raiz_proyecto(datos)
rel = ruta_relativa(ruta, raiz)
if rel.startswith(("data/", "dist/", ".venv/")):
    raise SystemExit(0)

uv = shutil.which("uv")
if not uv:
    print(
        "format_py: no encuentro `uv`. Ejecuta ./bootstrap.sh (instala uv y ruff).", file=sys.stderr
    )
    raise SystemExit(2)

subprocess.run([uv, "run", "--quiet", "ruff", "format", "--quiet", ruta], cwd=raiz, timeout=50)
res = subprocess.run(
    [uv, "run", "--quiet", "ruff", "check", "--fix", "--quiet", ruta],
    cwd=raiz,
    capture_output=True,
    text=True,
    timeout=50,
)
if res.returncode != 0:
    print(
        f"ruff deja errores en {rel} que no arregla solo. Corrígelos:\n{res.stdout}{res.stderr}",
        file=sys.stderr,
    )
    raise SystemExit(2)
raise SystemExit(0)
