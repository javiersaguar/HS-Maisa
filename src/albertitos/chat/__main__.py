"""CLI de repliegue y arranque del servidor POST."""

import argparse
import json
import os
import sys
from pathlib import Path

from albertitos.chat.agente import Peticion, preguntar


def main():
    parser = argparse.ArgumentParser(description="Chat con Alberto, sólo lectura")
    parser.add_argument("pregunta", nargs="?")
    parser.add_argument(
        "--db", type=Path, default=Path(os.getenv("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    parser.add_argument("--servidor", action="store_true")
    parser.add_argument("--puerto", type=int, default=8001)
    args = parser.parse_args()
    if args.servidor:
        from albertitos.chat.api import servir

        sys.stdout.write(f"Chat sólo lectura en http://127.0.0.1:{args.puerto}\n")
        servir(args.db, args.puerto)
    elif args.pregunta:
        sys.stdout.write(
            json.dumps(
                preguntar(Peticion(mensaje=args.pregunta), args.db), ensure_ascii=False, indent=2
            )
            + "\n"
        )
    else:
        parser.error("Indica una pregunta o --servidor")


if __name__ == "__main__":
    main()
