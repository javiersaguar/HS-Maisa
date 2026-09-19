"""Entrada independiente: python -m albertitos.bonus."""

import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from decimal import Decimal
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
    parser.add_argument(
        "--estricto",
        action="store_true",
        help="excluye de la remesa los IBAN que no pasan el mod-97 (los de la Caja son sintéticos)",
    )
    parser.add_argument(
        "--tope-semanal",
        type=Decimal,
        help="reparte la remesa en semanas sin pasar de este importe (EUR) y dice cuánto se tarda",
    )
    args = parser.parse_args()
    if args.tope_semanal is not None and args.tope_semanal <= 0:
        parser.error("--tope-semanal tiene que ser positivo")
    try:
        informe = calcular(args.db, args.fecha_corte, estricto=args.estricto)
        exportar(informe, args.salida, ruta_bd=args.db, tope_semanal=args.tope_semanal)
    except (ValueError, OSError, sqlite3.Error) as exc:
        sys.stderr.write(f"Bonus: {exc}\n")
        return 1
    sys.stdout.write(json.dumps(informe.resumen(), ensure_ascii=False, indent=2) + "\n")
    sys.stdout.write(f"Calendario: {args.salida / 'calendario.html'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
