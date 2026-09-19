"""Servidor local independiente del puente GET de Alejandro."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

from albertitos.chat.agente import Gateway, Peticion, preguntar

ORIGEN = "http://localhost:3000"


def hacer_handler(ruta: Path, gateway=None):
    gateway = gateway or Gateway()
    ocupada = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            logging.getLogger(__name__).info(formato, *args)

        def enviar(self, status, cuerpo):
            contenido = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(contenido)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", ORIGEN)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(contenido)

        def do_OPTIONS(self):  # noqa: N802
            self.enviar(200, {})

        def do_GET(self):  # noqa: N802
            self.enviar(
                200 if self.path == "/chat/salud" else 404,
                {
                    "ok": self.path == "/chat/salud",
                    "solo_lectura": True,
                    "bd_disponible": ruta.is_file(),
                },
            )

        def do_POST(self):  # noqa: N802
            if self.path != "/chat":
                self.enviar(404, {"error": "Ruta inexistente"})
                return
            if self.headers.get("Origin") not in (None, ORIGEN):
                self.enviar(403, {"error": "Origen no permitido"})
                return
            if self.headers.get_content_type() != "application/json":
                self.enviar(415, {"error": "Se requiere application/json"})
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if not 0 < n <= 65536:
                    self.enviar(413, {"error": "Cuerpo vacío o demasiado grande"})
                    return
                self.connection.settimeout(5)
                peticion = Peticion.model_validate_json(self.rfile.read(n))
            except (TimeoutError, ValueError, ValidationError):
                self.enviar(400, {"error": "Mensaje o historial inválidos"})
                return
            if not ocupada.acquire(blocking=False):
                self.enviar(
                    429, {"error": "Hay una consulta en curso; vuelve a intentarlo al terminar."}
                )
                return
            try:
                self.enviar(200, preguntar(peticion, ruta, gateway))
            finally:
                ocupada.release()

    return Handler


def servir(ruta: Path, puerto=8001):
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), hacer_handler(ruta))
    try:
        servidor.serve_forever()
    finally:
        servidor.server_close()
