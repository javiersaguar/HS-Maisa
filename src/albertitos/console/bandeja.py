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

import hashlib
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import unicodedata
from collections.abc import Callable
from contextlib import closing
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
# Windows no deja crear estos nombres: mejor un 400 que un fichero a medias
PROHIBIDOS_EN_NOMBRE = set('<>:"|?*') | {chr(i) for i in range(32)}

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
    if PROHIBIDOS_EN_NOMBRE & set(nombre) or nombre.endswith((" ", ".")):
        raise PeticionInvalida(f"{nombre!r} no vale como nombre de fichero")
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


def carpeta_de(ruta_bd: Path) -> Path:
    """Donde la bandeja guarda los PDF de la BD `ruta_bd` (extract los busca ahí como lote 99)."""
    return Path(ruta_bd).parent / "inbox"


def norma_de(ruta_bd: Path) -> str | None:
    """La norma **más nueva** de las que decidieron algo en esa BD, o None si no hay ninguna.

    Una factura que se sube hoy se decide con la norma de hoy. No vale coger la de la última decisión: en la BD de
    la entrega, lo último que se reprocesó fue el lote 1 (norma v3, ADR-0017), así que una factura en divisa
    subida por la consola habría salido por "el total no coincide con el pedido" en vez de por su moneda (v4.R7).
    `ALBERTITOS_BANDEJA_NORMA` la fija a mano si hiciera falta otra cosa.
    """
    try:
        with closing(db.conectar(Path(ruta_bd), solo_lectura=True)) as conn:
            versiones = [
                str(f["norma_version"])
                for f in conn.execute(
                    "SELECT DISTINCT norma_version FROM decisiones WHERE vigente = 1"
                )
            ]
    except sqlite3.Error:
        logger.exception(
            "bandeja: no se pudo leer la norma vigente; decide con su valor por defecto"
        )
        return None
    # "v10" es más nueva que "v9": se ordena por los números que trae, no por el texto.
    return max(versiones, key=_orden_norma, default=None) or None


def _orden_norma(version: str) -> tuple:
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"(\d+)", version))


def cli(args: list[str], ruta: Path) -> tuple[int, str]:
    """La CLI de verdad, en un subproceso que hereda el .env (fecha de corte, key del LLM)."""
    env = {
        **os.environ,
        "ALBERTITOS_DB": str(ruta),
        "ALBERTITOS_DIR_BANDEJA": str(carpeta_de(ruta).resolve()),
        "PYTHONIOENCODING": "utf-8",
    }
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
    """Un trabajo cada vez: estado en memoria del puente (la verdad sigue en la BD).

    `activa` sólo es True si el puente se arrancó con `--bandeja`: nunca se deduce de la ruta."""

    def __init__(
        self, ruta_bd: Path, runner: Runner | None = None, *, activa: bool = False
    ) -> None:
        self.ruta = Path(ruta_bd)
        self.activa = activa
        self.carpeta = carpeta_de(self.ruta)
        self.runner = runner or cli
        try:
            self.maximo = int(os.environ.get("ALBERTITOS_BANDEJA_MAX", "40"))
        except ValueError:
            raise ValueError("ALBERTITOS_BANDEJA_MAX debe ser un entero no negativo") from None
        if self.maximo < 0:
            raise ValueError("ALBERTITOS_BANDEJA_MAX debe ser un entero no negativo")
        self._recibidos = 0
        self.efimera = os.environ.get("ALBERTITOS_BANDEJA_EFIMERA") == "1"
        self._lock = threading.Lock()
        self._hilo: threading.Thread | None = None
        self._estado: dict[str, Any] = _estado_vacio()

    @property
    def disponible(self) -> bool:
        return (
            self.activa
            and not es_bd_de_entrega(self.ruta)
            and (not self.efimera or bool(os.environ.get("ALBERTITOS_CLAVE_DEMO", "").strip()))
        )

    def estado(self) -> dict[str, Any]:
        with self._lock:
            out = {
                **self._estado,
                "log": list(self._estado["log"][-LINEAS_LOG:]),
                "subidos": [dict(s) for s in self._estado["subidos"]],
                "limite_arranque": self.maximo,
                "recibidos_arranque": self._recibidos,
                "restantes_arranque": max(0, self.maximo - self._recibidos),
                "efimera": self.efimera,
            }
        return out | {"lote": LOTE, "disponible": self.disponible, "bd": str(self.ruta)}

    def resultados(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        """Resultado de cada PDF subido por el `file_id` que ingest le dio, nunca por el nombre: uno
        subido como `P001.pdf` con otro contenido no es el P001 de la Caja. Sin `file_id` (ingest no
        lo registró: ilegible, o aún no ha pasado) el estado es None."""
        from albertitos.console import lecturas  # import tardío: lecturas no depende de la bandeja

        out = []
        for s in self.estado()["subidos"]:
            fid = s["file_id"]
            estado = lecturas.estados(conn, [fid])[0]["estado"] if fid else None
            out.append({"file_id": fid or s["nombre"], "nombre": s["nombre"], "estado": estado})
        return out

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

    def _ocupados(self, ficheros: list[tuple[str, bytes]]) -> list[str]:
        """Nombres ya subidos a la bandeja con OTRO contenido: ingest no puede darles un segundo
        file_id en el lote 99 (UNIQUE) y el PDF acabaría como ilegible. Se pide renombrarlos."""
        conn = db.conectar(self.ruta, solo_lectura=True)
        try:
            malos = []
            for nombre, datos in ficheros:
                fila = conn.execute(
                    "SELECT sha256 FROM ficheros WHERE lote = ? AND file_id IN (?, ?)",
                    (LOTE, nombre, db.PREFIJO_INTERNO + nombre),
                ).fetchone()
                if fila is not None and fila["sha256"] != hashlib.sha256(datos).hexdigest():
                    malos.append(nombre)
            return malos
        finally:
            conn.close()

    def _subidos(self, ficheros: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
        """Cada PDF subido → el file_id con que ingest lo guardó, buscado por sha256: el nombre tal
        cual si es nuevo, `./<nombre>` si ese nombre ya era de otro lote (P0-5), el del original si
        es copia exacta de uno ya registrado. None si ingest no lo registró."""
        conn = db.conectar(self.ruta, solo_lectura=True)
        try:
            subidos = []
            for nombre, datos in ficheros:
                fila = conn.execute(
                    "SELECT file_id, lote FROM ficheros WHERE sha256 = ?",
                    (hashlib.sha256(datos).hexdigest(),),
                ).fetchone()
                subidos.append(
                    {
                        "nombre": nombre,
                        "file_id": None if fila is None else str(fila["file_id"]),
                        "copia": fila is not None
                        and (
                            int(fila["lote"] or 1) != LOTE
                            or db.nombre_entrega(str(fila["file_id"])) != nombre
                        ),
                    }
                )
            return subidos
        finally:
            conn.close()

    def recibir(self, cuerpo: bytes, tipo: str | None) -> Respuesta:
        if not self.disponible:
            return 409, {
                "error": f"el puente sirve {self.ruta} sin la bandeja: POST /inbox sólo se abre con "
                "`uv run python -m albertitos.console.api --bandeja` (BD aparte, nunca la de la "
                "entrega)."
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
            if self._recibidos + len(ficheros) > self.maximo:
                return 409, {
                    "error": f"Límite de {self.maximo} facturas por arranque alcanzado: "
                    f"quedan {max(0, self.maximo - self._recibidos)} plazas y envías {len(ficheros)}."
                }
            # Reserva bajo el mismo candado que el trabajo. Los fallos también consumen plaza:
            # reintentar una extracción fallida no debe convertir el límite en gasto ilimitado.
            self._recibidos += len(ficheros)
            self._estado = _estado_vacio() | {"estado": "ingiriendo"}

        # Hasta que el hilo arranca, cualquier fallo deja un estado final: si no, todos los POST
        # siguientes darían 409 hasta reiniciar el puente.
        try:
            ocupados = self._ocupados(ficheros)
            if ocupados:
                self._poner(estado="idle")
                return 400, {
                    "error": f"ya subiste {', '.join(ocupados)} con otro contenido: cámbiale el "
                    "nombre para subir la versión nueva"
                }
            self.carpeta.mkdir(parents=True, exist_ok=True)
            for nombre, datos in ficheros:
                (self.carpeta / nombre).write_bytes(datos)
        except (OSError, sqlite3.Error) as exc:
            logger.exception("bandeja: no se pudieron guardar los PDF")
            self._poner(estado="error", error=f"no se pudieron guardar los PDF: {exc}")
            return 500, {"error": f"no se pudieron guardar los PDF: {exc}"}

        if not self._paso("ingest", ["ingest", "--dir", str(self.carpeta), "--lote", str(LOTE)]):
            fallo = self.estado()
            return 500, {"error": fallo["error"], "log": fallo["log"]}
        try:
            subidos = self._subidos(ficheros)
        except sqlite3.Error as exc:
            self._poner(estado="error", error=f"ingest no dejó leer la BD: {exc}")
            return 500, {"error": f"ingest no dejó leer la BD: {exc}"}
        file_ids = [s["file_id"] or s["nombre"] for s in subidos]
        # Sólo lo que entró como fichero nuevo del lote 99: una copia exacta ya tiene su decisión.
        nuevos = [s["file_id"] for s in subidos if s["file_id"] and not s["copia"]]
        self._poner(subidos=subidos, file_ids=file_ids)
        if not nuevos:
            self._poner(estado="listo")
            return 202, {"file_ids": file_ids, "lote": LOTE, "estado": "listo"}
        lista = self.ruta.parent / "inbox.lista.txt"
        lista.write_text("\n".join(nuevos) + "\n", encoding="utf-8")
        self._poner(estado="extrayendo")
        self._hilo = threading.Thread(target=self._fondo, args=(lista,), daemon=True)
        self._hilo.start()
        return 202, {"file_ids": file_ids, "lote": LOTE, "estado": "extrayendo"}

    def _fondo(self, lista: Path) -> None:
        try:
            if not self._paso("extract", ["extract", "--fixture", str(lista)]):
                return
            self._poner(estado="decidiendo")
            # La norma de la BD (la misma que enseña el panel: con el lote 2 dentro, la v4), o la que se
            # fije a mano con ALBERTITOS_BANDEJA_NORMA. Sin ninguna, `decide` aplica su valor por defecto.
            norma = os.environ.get("ALBERTITOS_BANDEJA_NORMA") or norma_de(self.ruta)
            orden = ["decide", "--fixture", str(lista)] + (["--norma", norma] if norma else [])
            if not self._paso("decide", orden):
                return
            self._poner(estado="listo")
        except Exception as exc:  # noqa: BLE001 — el hilo no puede morir callado: el panel hace poll
            logger.exception("bandeja: fallo en segundo plano")
            self._poner(estado="error", error=f"{type(exc).__name__}: {exc}")

    def esperar(self, timeout: float | None = None) -> None:
        """Para los tests: espera a que acabe el hilo de extract + decide."""
        if self._hilo is not None:
            self._hilo.join(timeout)


def _estado_vacio() -> dict[str, Any]:
    return {"estado": "idle", "file_ids": [], "subidos": [], "log": [], "error": None}
