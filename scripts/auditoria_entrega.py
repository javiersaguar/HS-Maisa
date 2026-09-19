"""Auditoría de entrega (CLI). Sólo LEE la BD, los PDF y los JSONL: no decide, no corrige, no escribe nada.

La lógica está en `albertitos.pipeline.auditoria`, que `package` ejecuta antes de sustituir la entrega. Este
script es para mirarla a mano, para `make publicar` y para la skill /lote2: además compara con los JSONL que hay
en disco (`--entrega`). Sale con código 1 si hay algo ROJO.

Uso:
    uv run python scripts/auditoria_entrega.py                      # BD de ALBERTITOS_DB, los dos lotes
    uv run python scripts/auditoria_entrega.py --lote 1 --json      # para engancharla a otro script
    uv run python scripts/auditoria_entrega.py --db dist/ensayo/ensayo.db \\
        --dir-lote2 data/fixtures/lote2_sim/facturas --entrega dist/ensayo/entrega
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from albertitos.core import db  # noqa: E402
from albertitos.pipeline.auditoria import AMBAR, OK, ROJO, Informe, auditar, texto  # noqa: E402

__all__ = ["AMBAR", "OK", "ROJO", "Informe", "auditar", "main", "texto"]


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # la misma BD y los mismos directorios que la CLI (el entorno explícito manda)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    ap.add_argument("--lote", choices=["1", "2", "ambos"], default="ambos")
    ap.add_argument(
        "--dir-lote1",
        type=Path,
        default=Path(os.environ.get("ALBERTITOS_DIR_CAJA", "data/caja/facturas")),
    )
    ap.add_argument(
        "--dir-lote2",
        type=Path,
        default=Path(os.environ.get("ALBERTITOS_DIR_LOTE2", "data/lote2/facturas")),
    )
    ap.add_argument("--entrega", type=Path, default=Path("dist/entrega"))
    ap.add_argument("--json", action="store_true", help="salida JSON para otro script")
    args = ap.parse_args(argv)

    if not Path(args.db).is_file():
        print(f"no existe la BD {args.db}", file=sys.stderr)
        return 2
    lotes = [1, 2] if args.lote == "ambos" else [int(args.lote)]
    conn = db.conectar(args.db, solo_lectura=True)
    try:
        informe = auditar(
            conn,
            {1: args.dir_lote1, 2: args.dir_lote2},
            lotes=lotes,
            entrega=args.entrega,
            ruta_db=str(args.db),
        )
    finally:
        conn.close()
    if args.json:
        print(json.dumps(informe.como_dict(), ensure_ascii=False, indent=1))
    else:
        print(texto(informe))
    return 0 if informe.ok else 1


if __name__ == "__main__":
    sys.exit(main())
