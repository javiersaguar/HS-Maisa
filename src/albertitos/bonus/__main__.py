"""Entrada independiente: python -m albertitos.bonus."""

import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from albertitos.bonus import calcular, exportar


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calendario y borrador CSV de los PAGAR; sólo lectura."
    )
    parser.add_argument(
        "--db", type=Path, default=Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    parser.add_argument("--salida", type=Path, default=Path("dist/bonus"))
    parser.add_argument(
        "--fecha-corte",
        type=date.fromisoformat,
        help="Por defecto, el corte guardado en las decisiones.",
    )
    args = parser.parse_args()
    try:
        informe = calcular(args.db, args.fecha_corte)
        exportar(informe, args.salida, ruta_bd=args.db)
    except (ValueError, OSError, sqlite3.Error) as exc:
        sys.stderr.write(f"Bonus: {exc}\n")
        return 1
    sys.stdout.write(json.dumps(informe.resumen(), ensure_ascii=False, indent=2) + "\n")
    sys.stdout.write(f"Calendario: {args.salida / 'calendario.html'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
