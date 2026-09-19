"""Puente HTTP de sólo lectura sobre dist/albertitos.db: el contrato de la consola (console-web).

Sin dependencias nuevas (stdlib): ocho GET, JSON en snake_case, CORS abierto en localhost. No escribe:
la CLI es quien decide. Si falta la BD responde 503 con el comando que la crea; `/salud` contesta siempre.
El único POST es `/inbox` (la bandeja, `bandeja.py`): guarda PDF y lanza la CLI por subproceso, sólo
si el puente se arrancó con `--bandeja` (que nunca sirve la BD de la entrega) y sólo desde la consola.

Arranque:
    uv run python -m albertitos.console.api                    # http://127.0.0.1:8000
    uv run python -m albertitos.console.api --puerto 8000 --db dist/albertitos.db
    uv run python -m albertitos.console.api --bandeja          # dist/bandeja.db, con POST /inbox

Rutas:
    GET /salud                                   ¿vive el puente? ¿hay BD? contadores y versiones
    GET /panel                                   PanelResumen
    GET /ficheros?q&estado&regla&lote&page&pageSize   { items, total, page, page_size }
    GET /ficheros/:file_id                       Fichero con `fuentes` (maestro + asientos ERP)
    GET /traza?file_id&etapa&categoria           PasoTraza[]
    GET /etapas                                  EtapasResumen
    GET /eventos?etapa&limit                     Event[]
    GET /inbox                                   estado del trabajo de la bandeja + resultado por fichero
    POST /inbox  (multipart, uno o varios PDF)   202 { file_ids, lote: 99 }; 409 con la BD de la entrega

Cada respuesta lleva `X-Albertitos-Api: <versión del contrato>`; las colecciones también `api` en el JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from albertitos.console import bandeja as bandeja_mod
from albertitos.console import lecturas
from albertitos.core import db

logger = logging.getLogger(__name__)

PUERTO_DEFECTO = 8000
RUTA_BD = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
CABECERA_API = "X-Albertitos-Api"

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Accept, Content-Type",
    "Access-Control-Expose-Headers": CABECERA_API,
}
# Un POST multipart no pide preflight: sin esto, cualquier web abierta en el navegador podría subir
# PDF a la bandeja y gastar LLM. Como el chat, sólo la consola Next (o curl, que no manda Origin).
ORIGENES_BANDEJA = ("http://localhost:3000", "http://127.0.0.1:3000")

Query = dict[str, list[str]]
Respuesta = tuple[int, Any]


def _param(query: Query, clave: str, default: str | None = None) -> str | None:
    valores = query.get(clave) or []
    if not valores:
        return default
    valor = valores[0]
    if valor in ("", "all"):
        return default
    return valor


def _int(query: Query, clave: str, default: int) -> int:
    bruto = _param(query, clave)
    if bruto is None:
        return default
    try:
        return int(bruto)
    except ValueError:
        return default


def _sin_bd(ruta: Path) -> Respuesta:
    return 503, {
        "error": f"no existe {ruta}. Ejecuta `make db && uv run albertitos ingest` (o `make run`).",
        "bd": None,
    }


# ------------------------------------------------------------------------------------- rutas


def _r_salud(conn: sqlite3.Connection | None, query: Query) -> Respuesta:
    return 200, lecturas.salud(conn)


def _r_panel(conn: sqlite3.Connection, query: Query) -> Respuesta:
    return 200, lecturas.panel(conn)


def _r_etapas(conn: sqlite3.Connection, query: Query) -> Respuesta:
    return 200, lecturas.etapas(conn)


def _r_eventos(conn: sqlite3.Connection, query: Query) -> Respuesta:
    return 200, lecturas.eventos(conn, etapa=_param(query, "etapa"), limit=_int(query, "limit", 12))


def _r_traza(conn: sqlite3.Connection, query: Query) -> Respuesta:
    pasos = lecturas.traza_pasos(
        conn,
        file_id=_param(query, "file_id"),
        etapa=_param(query, "etapa"),
        categoria=_param(query, "categoria"),
    )
    if pasos is None:
        return 404, {"error": f"el fichero {_param(query, 'file_id')} no existe"}
    return 200, pasos


def _r_ficheros(conn: sqlite3.Connection, query: Query) -> Respuesta:
    lote_bruto = _param(query, "lote")
    lote = None
    if lote_bruto is not None:
        try:
            lote = int(lote_bruto)
        except ValueError:
            lote = None
    return 200, lecturas.listar_ficheros(
        conn,
        q=_param(query, "q"),
        estado=_param(query, "estado"),
        regla=_param(query, "regla"),
        lote=lote,
        page=_int(query, "page", 1),
        page_size=_int(query, "pageSize", _int(query, "page_size", lecturas.PAGE_SIZE_DEFECTO)),
    )


def _r_fichero(conn: sqlite3.Connection, query: Query, file_id: str) -> Respuesta:
    fila = lecturas.fichero(conn, file_id)
    if fila is None:
        return 404, {"error": f"el fichero {file_id} no existe"}
    return 200, fila


def _r_inbox(
    method: str,
    conn: sqlite3.Connection | None,
    bandeja: bandeja_mod.Bandeja,
    cuerpo: bytes | None,
    tipo: str | None,
) -> Respuesta:
    if method == "POST":
        return bandeja.recibir(cuerpo or b"", tipo)
    estado = bandeja.estado()
    estado["ficheros"] = bandeja.resultados(conn) if conn is not None else []
    return 200, estado


#: Rutas exactas → handler. Las que necesitan BD reciben una conexión abierta en sólo lectura.
RUTAS: dict[str, Callable[[sqlite3.Connection, Query], Respuesta]] = {
    "/panel": _r_panel,
    "/etapas": _r_etapas,
    "/eventos": _r_eventos,
    "/traza": _r_traza,
    "/ficheros": _r_ficheros,
}
RUTAS_SIN_BD = ("/", "/salud")


def despachar(
    method: str,
    path: str,
    query: Query,
    conn: sqlite3.Connection | None,
    ruta: Path | None = None,
    *,
    bandeja: bandeja_mod.Bandeja | None = None,
    cuerpo: bytes | None = None,
    tipo: str | None = None,
) -> Respuesta:
    """Enruta una petición. `conn` puede ser None (sin BD): sólo `/salud` responde 200 entonces.
    `/inbox` es la única ruta que acepta POST (`cuerpo` multipart, `tipo` su Content-Type)."""
    if method == "OPTIONS":
        return 204, None
    if path == "/inbox" and method in ("GET", "HEAD", "POST"):
        return _r_inbox(method, conn, bandeja or bandeja_mod.Bandeja(ruta or RUTA_BD), cuerpo, tipo)
    if method not in ("GET", "HEAD"):
        return 405, {"error": "sólo GET (la consola es de sólo lectura; la bandeja es POST /inbox)"}

    if path in RUTAS_SIN_BD:
        return _r_salud(conn, query)
    if conn is None:
        return _sin_bd(ruta or RUTA_BD)

    handler = RUTAS.get(path)
    if handler is not None:
        return handler(conn, query)
    if path.startswith("/ficheros/"):
        file_id = lecturas.nfc(unquote(path[len("/ficheros/") :]))
        return _r_fichero(conn, query, file_id)
    return 404, {"error": f"ruta {path} no existe"}


# ---------------------------------------------------------------------------------- servidor


def _enviar(handler: BaseHTTPRequestHandler, status: int, body: Any) -> None:
    payload = (
        b"" if body is None else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
    )
    handler.send_response(status)
    for clave, valor in _CORS.items():
        handler.send_header(clave, valor)
    handler.send_header(CABECERA_API, str(lecturas.API_VERSION))
    handler.send_header("Cache-Control", "no-store")
    if body is not None:
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    if payload and handler.command != "HEAD":
        handler.wfile.write(payload)


def hacer_handler(ruta: Path, *, bandeja_activa: bool = False) -> type[BaseHTTPRequestHandler]:
    """`bandeja_activa` sólo con `--bandeja`: sin el flag, POST /inbox da 409 sea cual sea la BD."""
    # una por servidor: el estado del trabajo vive aquí
    bandeja = bandeja_mod.Bandeja(ruta, activa=bandeja_activa)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[console-api] {self.address_string()} {fmt % args}")

        def _ruta(self) -> tuple[str, Query]:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            return path, parse_qs(parsed.query)

        def do_OPTIONS(self) -> None:  # noqa: N802
            _enviar(self, 204, None)

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def _no_escritura(self) -> None:
            # BaseHTTPRequestHandler devolvería 501; aquí es 405 con el mismo JSON de despachar.
            _enviar(self, *despachar(self.command, *self._ruta(), None, ruta))

        do_PUT = do_PATCH = do_DELETE = _no_escritura  # noqa: N815

        def do_POST(self) -> None:  # noqa: N802
            path, query = self._ruta()
            if path != "/inbox":
                self._no_escritura()
                return
            origen = self.headers.get("Origin")
            if origen is not None and origen not in ORIGENES_BANDEJA:
                self.close_connection = True
                _enviar(self, 403, {"error": f"origen {origen} no autorizado para subir facturas"})
                return
            try:
                largo = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                largo = -1
            if largo < 0 or largo > bandeja_mod.MAX_BYTES_PETICION:
                self.close_connection = True  # no se lee el cuerpo: la conexión no se reutiliza
                _enviar(
                    self, 413, {"error": "petición sin Content-Length válido o demasiado grande"}
                )
                return
            cuerpo = self.rfile.read(largo)
            try:
                status, body = despachar(
                    "POST",
                    path,
                    query,
                    None,
                    ruta,
                    bandeja=bandeja,
                    cuerpo=cuerpo,
                    tipo=self.headers.get("Content-Type"),
                )
            except Exception as exc:  # noqa: BLE001 — el panel enseña el error, no un socket cerrado
                logger.exception("console-api: fallo en POST %s", path)
                status, body = 500, {"error": f"{type(exc).__name__}: {exc}"}
            _enviar(self, status, body)

        def do_GET(self) -> None:  # noqa: N802
            path, query = self._ruta()
            conn: sqlite3.Connection | None = None
            if ruta.exists():
                try:
                    conn = db.conectar(ruta, solo_lectura=True)
                except sqlite3.Error as exc:
                    _enviar(self, 503, {"error": f"no se pudo abrir {ruta}: {exc}"})
                    return
            try:
                status, body = despachar(self.command, path, query, conn, ruta, bandeja=bandeja)
            except sqlite3.Error as exc:
                status, body = 500, {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001 — un JSON raro en la BD no debe colgar la UI
                logger.exception("console-api: fallo en %s", path)
                status, body = 500, {"error": f"{type(exc).__name__}: {exc}"}
            finally:
                if conn is not None:
                    conn.close()
            _enviar(self, status, body)

    return Handler


def servir(
    ruta: Path | None = None, puerto: int = PUERTO_DEFECTO, *, bandeja: bool = False
) -> None:
    ruta = Path(ruta or RUTA_BD)
    if not ruta.exists():
        print(
            f"Aviso: no existe {ruta}. Sólo /salud responderá hasta que corras "
            "`make db && uv run albertitos ingest` (o `make run`)."
        )
    httpd = ThreadingHTTPServer(("127.0.0.1", puerto), hacer_handler(ruta, bandeja_activa=bandeja))
    modo = (
        "bandeja activa (POST /inbox, lote 99)"
        if bandeja
        else "sólo lectura (POST /inbox desactivado: arranca con --bandeja)"
    )
    print(
        f"Albertitos consola API v{lecturas.API_VERSION} · {modo} · "
        f"http://127.0.0.1:{puerto}  (BD {ruta})"
    )
    print("Rutas: /salud /panel /ficheros /ficheros/:id /traza /etapas /eventos /inbox")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("apagado")
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Puente HTTP de sólo lectura para console-web")
    parser.add_argument("--puerto", type=int, default=PUERTO_DEFECTO)
    parser.add_argument("--db", type=Path, default=None, help="ruta SQLite (defecto ALBERTITOS_DB)")
    parser.add_argument(
        "--bandeja",
        action="store_true",
        help=f"sirve {bandeja_mod.BD_BANDEJA} (copia de la de la entrega si no existe) y "
        "activa POST /inbox; la entrega no se toca",
    )
    args = parser.parse_args()
    ruta = args.db
    if args.bandeja:
        if args.db is not None and bandeja_mod.es_bd_de_entrega(args.db):
            parser.error(
                f"--bandeja no puede servir {args.db}: es la BD de la entrega (quita --db)"
            )
        try:
            ruta = bandeja_mod.preparar(destino=args.db or bandeja_mod.BD_BANDEJA)
        except FileNotFoundError as e:
            parser.error(str(e))
    servir(ruta, args.puerto, bandeja=args.bandeja)


if __name__ == "__main__":
    main()
