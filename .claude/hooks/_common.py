"""Utilidades compartidas por los hooks. Sólo stdlib: tiene que correr en cualquier portátil."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def leer_entrada() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def raiz_proyecto(datos: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or os.getcwd()).resolve()


def decidir(decision: str, motivo: str) -> None:
    """Emite la decisión en el formato oficial de PreToolUse y termina.

    decision: "deny" | "ask" | "allow". El motivo lo lee el agente: di qué hacer en su lugar.
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": motivo,
                }
            }
        )
    )
    sys.exit(0)


def rama_actual(cwd: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        return "?"


def es_dueno(variable: str, rol: str, raiz: Path | None = None) -> bool:
    """Un dueño (Miguel) se identifica de dos formas equivalentes:

    - variable de entorno = 1 (p. ej. en .claude/settings.local.json → "env"), o
    - una línea con el rol ("merge", "contratos") en el fichero gitignored .claude/dueno.local.
    """
    if os.environ.get(variable, "").strip() == "1":
        return True
    if raiz is None:
        return False
    marcador = raiz / ".claude" / "dueno.local"
    try:
        roles = {linea.strip().lower() for linea in marcador.read_text().splitlines()}
    except OSError:
        return False
    return rol in roles


def ruta_relativa(ruta: str, raiz: Path) -> str:
    try:
        return str(Path(ruta).resolve().relative_to(raiz)).replace(os.sep, "/")
    except Exception:
        return ruta.replace(os.sep, "/")
