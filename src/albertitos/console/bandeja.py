"""La bandeja: facturas sueltas que se sueltan en el panel (lote 99), siempre sobre una BD aparte.

La consola no decide. Aquí sólo se guardan los PDF en `<carpeta de la BD>/inbox/` y se llama a la CLI
por subproceso, como el botón de Streamlit (ADR-0007), con `ALBERTITOS_DB` apuntando a la BD que sirve
el puente:

    ingest --dir <inbox> --lote 99      síncrono: la respuesta del POST ya trae los file_id
    extract --fixture <lista>           en un hilo, un trabajo cada vez
    decide --fixture <lista>            nunca `reprocess`: ése pasa marcar_duplicados por toda la BD

**Nunca contra la BD de la entrega** (`dist/albertitos.db`). Un fichero de lote 99 allí deja la
auditoría de entrega en ROJO (`comprobar_fantasmas`: no está en el directorio de ningún lote, y package
se niega) y el siguiente `run` lo cuenta en `marcar_duplicados`: una factura de prueba con el pedido de
una de la Caja marcaría el original DUPLICADO_SOSPECHOSO. Por eso el puente se arranca con
`--bandeja`, que sirve `dist/bandeja.db` (una copia de la real, como `make demo-caos`).
"""

from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import sys
import threading
import unicodedata
from collections.abc import Callable
from email.parser import BytesParser
from email.policy import default as politica_email
from pathlib import Path
from typing import Any

from albertitos.core import db

logger = logging.getLogger(__name__)

LOTE = 99
BD_ENTREGA = Path("dist/albertitos.db")
BD_BANDEJA = Path("dist/bandeja.db")
MAX_FICHEROS = 20
MAX_BYTES_FICHERO = 10 * 1024 * 1024
MAX_BYTES_PETICION = MAX_FICHEROS * MAX_BYTES_FICHERO
# extract de 20 PDF por el LLM con reintentos; si se pasa, el fichero queda PENDIENTE
TIMEOUT_CLI_S = 900
LINEAS_LOG = 60

EN_CURSO = ("ingiriendo", "extrayendo", "decidiendo")

#: (argumentos de la CLI, BD) → (código de salida, salida). Los tests lo sustituyen: nada de LLM.
Runner = Callable[[list[str], Path], tuple[int, str]]
Respuesta = tuple[int, Any]


class PeticionInvalida(ValueError):
    """El POST no trae PDF válidos: 400 con este mensaje."""


def es_bd_de_entrega(ruta: Path) -> bool:
    return Path(ruta).resolve() == BD_ENTREGA.resolve()


def preparar(origen: Path = BD_ENTREGA, destino: Path = BD_BANDEJA) -> Path:
    """Copia la BD de la entrega en `destino` si aún no existe (maestro, ERP, hechos y caché LLM
    incluidos: un PDF de la Caja no vuelve a cobrar). Si existe, se conserva: para empezar de cero,
    bórrala. Copia con la API de backup de SQLite, segura con el WAL abierto."""
    destino = Path(destino)
    if destino.exists():
        return destino
    if not Path(origen).exists():
        raise FileNotFoundError(
            f"no existe {origen}: sin ella la bandeja no tiene maestro ni ERP con que decidir"
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    src = db.conectar(Path(origen), solo_lectura=True)
    dst = sqlite3.connect(destino)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return destino


def _nombre(bruto: str) -> str:
    """Nombre de fichero seguro y en NFC: sin carpetas, con la tilde tal cual la mandó el navegador."""
    try:  # el parser de email deja los bytes UTF-8 de la cabecera como surrogates
        bruto = bruto.encode("utf-8", "surrogateescape").decode("utf-8")
    except UnicodeError:
        pass
    nombre = unicodedata.normalize("NFC", bruto.replace("\\", "/").rsplit("/", 1)[-1].strip())
    if not nombre.lower().endswith(".pdf") or nombre.lower() == ".pdf" or nombre.startswith("."):
        raise PeticionInvalida(f"{bruto!r} no es un .pdf")
    return nombre


def leer_multipart(cuerpo: bytes, tipo: str | None) -> list[tuple[str, bytes]]:
    """multipart/form-data → [(nombre NFC, bytes)] de cada parte con fichero. Stdlib, sin `cgi`."""
    if not tipo or not tipo.lower().startswith("multipart/form-data"):
        raise PeticionInvalida("se espera multipart/form-data con uno o varios PDF")
    if len(cuerpo) > MAX_BYTES_PETICION:
        raise PeticionInvalida(f"la petición pasa de {MAX_BYTES_PETICION // 1024 // 1024} MB")
    cabecera = f"Content-Type: {tipo}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin-1")
    mensaje = BytesParser(policy=politica_email).parsebytes(cabecera + cuerpo)
    if not mensaje.is_multipart():
        raise PeticionInvalida("multipart vacío o sin boundary")
    ficheros: dict[str, bytes] = {}
    for parte in mensaje.iter_parts():
        bruto = parte.get_filename()
        if not bruto:
            continue
        nombre = _nombre(bruto)
        datos = parte.get_payload(decode=True) or b""
        if not datos.startswith(b"%PDF"):
            raise PeticionInvalida(f"{nombre} no es un PDF (no empieza por %PDF)")
        if len(datos) > MAX_BYTES_FICHERO:
            raise PeticionInvalida(f"{nombre} pasa de {MAX_BYTES_FICHERO // 1024 // 1024} MB")
        ficheros[nombre] = datos
    if not ficheros:
        raise PeticionInvalida("no llega ningún PDF")
    if len(ficheros) > MAX_FICHEROS:
        raise PeticionInvalida(f"como mucho {MAX_FICHEROS} PDF por envío (llegan {len(ficheros)})")
    return sorted(ficheros.items())


def cli(args: list[str], ruta: Path) -> tuple[int, str]:
    """La CLI de verdad, en un subproceso que hereda el .env (fecha de corte, key del LLM)."""
    env = {**os.environ, "ALBERTITOS_DB": str(ruta), "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(
            [sys.executable, "-m", "albertitos.cli", *args],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_CLI_S,
        )
    except subprocess.TimeoutExpired:
        return 124, f"albertitos {args[0]}: más de {TIMEOUT_CLI_S} s, cortado"
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class Bandeja:
    """Un trabajo cada vez: estado en memoria del puente (la verdad sigue en la BD)."""

    def __init__(self, ruta_bd: Path, runner: Runner | None = None) -> None:
        self.ruta = Path(ruta_bd)
        self.carpeta = self.ruta.parent / "inbox"
        self.runner = runner or cli
        self._lock = threading.Lock()
        self._hilo: threading.Thread | None = None
        self._estado: dict[str, Any] = {"estado": "idle", "file_ids": [], "log": [], "error": None}

    @property
    def disponible(self) -> bool:
        return not es_bd_de_entrega(self.ruta)

    def estado(self) -> dict[str, Any]:
        with self._lock:
            out = {**self._estado, "log": list(self._estado["log"][-LINEAS_LOG:])}
        return out | {"lote": LOTE, "disponible": self.disponible, "bd": str(self.ruta)}

    def _poner(self, **cambios: Any) -> None:
        with self._lock:
            self._estado.update(cambios)

    def _paso(self, nombre: str, args: list[str]) -> bool:
        codigo, salida = self.runner(args, self.ruta)
        lineas = [f"$ albertitos {' '.join(args)}", *salida.strip().splitlines()]
        with self._lock:
            self._estado["log"].extend(lineas)
        if codigo != 0:
            logger.warning("bandeja: %s salió con %s", nombre, codigo)
            self._poner(estado="error", error=f"{nombre} salió con código {codigo}")
            return False
        return True

    def recibir(self, cuerpo: bytes, tipo: str | None) -> Respuesta:
        if not self.disponible:
            return 409, {
                "error": f"el puente sirve la BD de la entrega ({self.ruta}): la bandeja no escribe "
                "ahí. Páralo y arráncalo con `uv run python -m albertitos.console.api --bandeja`."
            }
        if not self.ruta.exists():
            return 503, {"error": f"no existe {self.ruta}", "bd": None}
        try:
            ficheros = leer_multipart(cuerpo, tipo)
        except PeticionInvalida as e:
            return 400, {"error": str(e)}
        with self._lock:
            if self._estado["estado"] in EN_CURSO:
                return 409, {"error": "ya hay facturas de la bandeja en curso; espera a que acaben"}
            file_ids = [nombre for nombre, _ in ficheros]
            self._estado = {"estado": "ingiriendo", "file_ids": file_ids, "log": [], "error": None}

        self.carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, datos in ficheros:
            (self.carpeta / nombre).write_bytes(datos)
        lista = self.ruta.parent / "inbox.lista.txt"
        lista.write_text("\n".join(file_ids) + "\n", encoding="utf-8")

        if not self._paso("ingest", ["ingest", "--dir", str(self.carpeta), "--lote", str(LOTE)]):
            fallo = self.estado()
            return 500, {"error": fallo["error"], "log": fallo["log"]}
        self._poner(estado="extrayendo")
        self._hilo = threading.Thread(target=self._fondo, args=(lista,), daemon=True)
        self._hilo.start()
        return 202, {"file_ids": file_ids, "lote": LOTE, "estado": "extrayendo"}

    def _fondo(self, lista: Path) -> None:
        try:
            if not self._paso("extract", ["extract", "--fixture", str(lista)]):
                return
            self._poner(estado="decidiendo")
            if not self._paso("decide", ["decide", "--fixture", str(lista)]):
                return
            self._poner(estado="listo")
        except Exception as exc:  # noqa: BLE001 — el hilo no puede morir callado: el panel hace poll
            logger.exception("bandeja: fallo en segundo plano")
            self._poner(estado="error", error=f"{type(exc).__name__}: {exc}")

    def esperar(self, timeout: float | None = None) -> None:
        """Para los tests: espera a que acabe el hilo de extract + decide."""
        if self._hilo is not None:
            self._hilo.join(timeout)
