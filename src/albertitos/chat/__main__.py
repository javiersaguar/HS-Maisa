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
    parser.add_argument(
        "--puerto", type=int, default=None, help="por defecto ALBERTITOS_CHAT_PUERTO o 8001"
    )
    parser.add_argument(
        "--salud", action="store_true", help="la salud v2 (¿hay modelo y por qué no?), sin llamarlo"
    )
    args = parser.parse_args()
    if args.salud:
        from albertitos.chat.agente import Gateway
        from albertitos.chat.api import salud

        sys.stdout.write(json.dumps(salud(args.db, Gateway()), ensure_ascii=False, indent=2) + "\n")
    elif args.servidor:
        from albertitos.chat.api import PuertoOcupado, puerto_defecto, servir

        puerto = args.puerto or puerto_defecto()
        sys.stdout.write(f"Chat sólo lectura en http://127.0.0.1:{puerto}\n")
        sys.stdout.flush()
        try:
            servir(args.db, puerto)
        except PuertoOcupado as exc:
            sys.stderr.write(f"Chat: {exc}\n")
            raise SystemExit(1) from None
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
