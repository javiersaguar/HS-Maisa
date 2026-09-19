"""Comprueba que cada fichero cambiado en la rama pertenece a exactamente un agente de docs/agentes/plan.json.

Uso: uv run python scripts/agentes_check.py [--base main]
Sale con 1 si hay ficheros fuera de las listas o repartidos entre dos agentes. Javier lo pasa antes de /handoff.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

PLAN = Path("docs/agentes/plan.json")


def cambiados(base: str) -> set[str]:
    ficheros: set[str] = set()
    for cmd in (
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", f"{base}...HEAD"],
        ["git", "-c", "core.quotepath=false", "status", "--porcelain", "--untracked-files=all"],
    ):
        # Sin core.quotepath=false, git escapa en octal los nombres con «ñ» o tildes
        # ("a\303\261adir_…") y ningún patrón de plan.json casa con ellos.
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        for linea in r.stdout.splitlines():
            ruta = linea[3:] if "status" in cmd else linea
            ruta = ruta.strip().strip('"')
            if " -> " in ruta:
                ruta = ruta.split(" -> ")[1]
            if ruta:
                ficheros.add(ruta)
    return ficheros


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="por defecto, la `base` de plan.json o main")
    args = ap.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    # Cada ciclo arranca de un commit: si main no está al día (Miguel no ha mergeado), comparar con main
    # mezclaría los ficheros de ciclos anteriores con los de éste y los daría por "de NADIE".
    args.base = args.base or plan.get("base") or "main"
    compartidos = set(plan.get("compartidos", []))
    problemas = 0
    print(f"ciclo {plan['ciclo']} · rama {plan['rama']} · base {args.base}")
    for ruta in sorted(cambiados(args.base)):
        if ruta in compartidos or ruta.startswith(".pytest_cache"):
            continue
        duenos = [
            a
            for a, globs in plan["agentes"].items()
            if any(fnmatch.fnmatch(ruta, g) for g in globs)
        ]
        if len(duenos) == 1:
            print(f"  ✓ {duenos[0]}  {ruta}")
        elif not duenos:
            print(f"  ✗ NADIE  {ruta}  ← fuera de todas las listas: ¿quién lo tocó y por qué?")
            problemas += 1
        else:
            print(
                f"  ✗ {'+'.join(duenos)}  {ruta}  ← el plan lo asigna a más de un agente: corrige plan.json"
            )
            problemas += 1
    print("OK: cada fichero tiene un único dueño" if not problemas else f"{problemas} problema(s)")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
