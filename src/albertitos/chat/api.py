"""Servidor local independiente del puente GET de Alejandro."""

import json
import logging
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

from albertitos.chat.agente import Gateway, Peticion, preguntar

ORIGENES_DEFECTO = "http://localhost:3000,http://127.0.0.1:3000"
API = 2  # versión del contrato de /chat/salud (PLAN-13)


def origenes() -> set[str]:
    """ALBERTITOS_CHAT_ORIGENES (coma). Antes sólo valía http://localhost:3000 y 127.0.0.1:3000 daba 403 (B3)."""
    return {
        o.strip().rstrip("/")
        for o in (os.getenv("ALBERTITOS_CHAT_ORIGENES") or ORIGENES_DEFECTO).split(",")
        if o.strip()
    }


def salud(ruta: Path, gateway) -> dict:
    """/chat/salud v2 (contrato en docs/api/chat.md): sin llamar al modelo."""
    disponible = (
        gateway.salud()
        if hasattr(gateway, "salud")
        else {
            "modelo_disponible": True,
            "motivo": None,
            "modelo": getattr(gateway, "modelo", None),
            "respaldo": getattr(gateway, "respaldo", None),
            "llamadas_restantes": None,
            "ventana": None,
        }
    )
    return {
        "ok": True,
        "api": API,
        "solo_lectura": True,
        "bd_disponible": ruta.is_file(),
        **disponible,
    }


def hacer_handler(ruta: Path, gateway=None):
    gateway = gateway or Gateway()
    ocupada = threading.Lock()
    permitidos = origenes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            logging.getLogger(__name__).info(formato, *args)

        def enviar(self, status, cuerpo):
            contenido = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(contenido)))
            self.send_header("Cache-Control", "no-store")
            origen = (self.headers.get("Origin") or "").rstrip("/")
            if origen in permitidos:  # nunca "*": sólo el origen que pide, si está en la lista
                self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(contenido)

        def do_OPTIONS(self):  # noqa: N802
            self.enviar(200, {})

        def do_GET(self):  # noqa: N802
            if self.path.split("?", 1)[0] != "/chat/salud":
                self.enviar(404, {"ok": False, "error": "Ruta inexistente"})
                return
            self.enviar(200, salud(ruta, gateway))

        def do_POST(self):  # noqa: N802
            if self.path != "/chat":
                self.enviar(404, {"error": "Ruta inexistente"})
                return
            if self.headers.get("Origin") is not None and (
                self.headers.get("Origin").rstrip("/") not in permitidos
            ):
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


PUERTO_DEFECTO = 8001


def puerto_defecto() -> int:
    try:
        return int(os.getenv("ALBERTITOS_CHAT_PUERTO") or PUERTO_DEFECTO)
    except ValueError:
        return PUERTO_DEFECTO


class PuertoOcupado(RuntimeError):
    pass


def puerto_libre(ocupado: int, intentos: int = 50) -> int | None:
    """El primer puerto por encima de `ocupado` en el que se puede escuchar ahora mismo (para sugerirlo)."""
    for candidato in range(ocupado + 1, ocupado + 1 + intentos):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", candidato))
            except OSError:
                continue
            return candidato
    return None


def servir(ruta: Path, puerto: int | None = None):
    puerto = puerto or puerto_defecto()
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", puerto), hacer_handler(ruta))
    except OSError as exc:
        # dirección en uso: macOS, Linux, Windows. En Windows, un puerto ocupado (o reservado por el sistema)
        # también puede dar WinError 10013 "acceso denegado"; el remedio es el mismo: otro puerto.
        if exc.errno in (48, 98, 10048) or getattr(exc, "winerror", None) in (10048, 10013):
            otro = puerto_libre(puerto) or puerto + 100  # uno libre de verdad, nunca el ocupado
            raise PuertoOcupado(
                f"el puerto {puerto} ya lo usa otro proceso (¿otro chat abierto en otra terminal?). "
                f"Páralo con Ctrl+C o arranca el chat en otro: ALBERTITOS_CHAT_PUERTO={otro} make chat, "
                f"y en la consola NEXT_PUBLIC_CHAT_URL=http://127.0.0.1:{otro}"
            ) from None
        raise
    try:
        servidor.serve_forever()
    finally:
        servidor.server_close()
