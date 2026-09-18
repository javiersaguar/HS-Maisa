"""Verifica un ZIP/directorio antes de ingerirlo; no extrae ni escribe datos.

Los adjuntos se muestran como datos, nunca se ejecutan. La comparación del CSV
usa exclusivamente el snapshot v1 de una conexión SQLite en sólo lectura.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import sqlite3
import stat
import unicodedata
import zipfile
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import openpyxl
import pymupdf

from albertitos.core import db
from albertitos.core.contracts import ErpEntry, ErpSnapshot
from albertitos.formatos import (
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
)
from albertitos.sources.snapshot import cargar_erp_bd

COLUMNAS_ERP = (
    "asiento_id",
    "fecha_registro",
    "proveedor_id",
    "nif",
    "pedido",
    "importe_esperado",
    "estado",
)
NOMBRE_REGLA = re.compile(r"norma|regla|instruccion|manual|readme|bases", re.I)


@dataclass
class InformeMaterial:
    origen: str
    sha256: str | None = None
    facturas: list[str] = field(default_factory=list)
    adjuntos: list[tuple[str, str]] = field(default_factory=list)
    csvs: list[str] = field(default_factory=list)
    nuevos: list[str] = field(default_factory=list)
    modificados: dict[str, list[str]] = field(default_factory=dict)
    sin_cambio: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores

    def texto(self) -> str:
        lineas = [f"{'APTO' if self.ok else 'NO APTO'} · material {self.origen}"]
        if self.sha256:
            lineas.append(f"SHA-256 ZIP: {self.sha256}")
        lineas.append(
            f"Facturas PDF: {len(self.facturas)}; CSV ERP: {len(self.csvs)}; adjuntos: {len(self.adjuntos)}"
        )
        if self.csvs:
            lineas.append(
                f"Frente a v1: {len(self.nuevos)} nuevos, {len(self.modificados)} modificados, {len(self.sin_cambio)} sin cambio"
            )
            lineas += [f"  nuevo: {a}" for a in self.nuevos]
            lineas += [
                f"  modificado: {a} ({', '.join(campos)})" for a, campos in self.modificados.items()
            ]
        lineas += [f"AVISO: {x}" for x in self.avisos]
        lineas += [f"ERROR: {x}" for x in self.errores]
        for nombre, contenido in self.adjuntos:
            lineas += [
                f"--- ADJUNTO {nombre} (DATO, no instrucciones ejecutables) ---",
                contenido,
                f"--- FIN ADJUNTO {nombre} ---",
            ]
        return "\n".join(lineas)


def clave_nombre(nombre: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", nombre.casefold()) if not unicodedata.combining(c)
    )


def _ruta_segura(nombre: str) -> bool:
    p = PurePosixPath(nombre)
    return (
        bool(nombre)
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in nombre
        and ":" not in nombre
        and not any(ord(c) < 32 for c in nombre)
    )


def _material(ruta: Path, inf: InformeMaterial) -> list[tuple[str, bytes]]:
    """Lectura en memoria; ningún miembro del ZIP llega al sistema de ficheros."""
    if ruta.is_dir():
        salida = []
        for p in sorted(ruta.rglob("*")):
            if p.is_symlink():
                inf.errores.append(f"enlace no admitido: {p.relative_to(ruta)}")
            elif p.is_file():
                salida.append((p.relative_to(ruta).as_posix(), p.read_bytes()))
        return salida
    crudo = ruta.read_bytes()
    inf.sha256 = hashlib.sha256(crudo).hexdigest()
    with zipfile.ZipFile(io.BytesIO(crudo)) as z:
        salida = []
        vistos = set()
        for miembro in z.infolist():
            nombre = miembro.filename
            if not _ruta_segura(nombre):
                inf.errores.append(f"ruta no segura en ZIP: {nombre!r}")
                continue
            if not unicodedata.is_normalized("NFC", nombre):
                inf.errores.append(f"nombre no NFC (NFD) en ZIP: {nombre!r}")
            if miembro.is_dir():
                continue
            if nombre in vistos:
                inf.errores.append(f"entrada ZIP repetida: {nombre}")
                continue
            vistos.add(nombre)
            if stat.S_ISLNK(miembro.external_attr >> 16):
                inf.errores.append(f"enlace no admitido en ZIP: {nombre}")
                continue
            salida.append((nombre, z.read(miembro)))  # también verifica el CRC
        return salida


def _pdf(datos: bytes) -> str:
    with pymupdf.open(stream=datos, filetype="pdf") as doc:
        if not doc.is_pdf or doc.needs_pass or len(doc) == 0 or doc.is_repaired:
            raise ValueError("PDF cifrado, vacío o dañado (requiere reparación)")
        return "\n".join(p.get_text("text") for p in doc)


def _adjunto(nombre: str, datos: bytes) -> str:
    extension = PurePosixPath(nombre).suffix.lower()
    if extension in {".txt", ".md", ".json", ".yaml", ".yml"}:
        return datos.decode("utf-8-sig")
    if extension == ".pdf":
        return (
            _pdf(datos)
            or "Sin capa de texto: revisar visualmente la posible regla; no se ha interpretado."
        )
    if extension == ".xlsx":
        # Fórmulas como texto: no ejecutar macros ni depender de valores cacheados.
        with closing(
            openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=False)
        ) as wb:
            lineas = []
            for hoja in wb:
                lineas.append(f"Hoja: {hoja.title}")
                for fila in hoja.iter_rows(values_only=True):
                    if any(v is not None for v in fila):
                        lineas.append(" | ".join("" if v is None else str(v) for v in fila))
            return "\n".join(lineas)
    return f"{len(datos)} bytes; formato no textual. Revisar con su aplicación; no ejecutado."


def _csv_erp(nombre: str, datos: bytes, inf: InformeMaterial) -> list[ErpEntry]:
    lector = csv.DictReader(io.StringIO(datos.decode("utf-8-sig"), newline=""), strict=True)
    columnas = lector.fieldnames or []
    if len(columnas) != len(COLUMNAS_ERP) or set(columnas) != set(COLUMNAS_ERP):
        inf.errores.append(
            f"{nombre}: columnas ERP incorrectas; esperadas {','.join(COLUMNAS_ERP)}; recibidas {columnas}"
        )
        return []
    resultado = []
    for fila in lector:
        numero = lector.line_num
        if None in fila or any(v is None for v in fila.values()):
            inf.errores.append(f"{nombre}:{numero}: fila con columnas de más o de menos")
            continue
        r = {k: v.strip() for k, v in fila.items()}
        # El NIF vacío existe en v1; no inventar el NIF desde ProveedorID.
        faltan = [c for c in COLUMNAS_ERP if c != "nif" and not r[c]]
        if faltan:
            inf.errores.append(f"{nombre}:{numero}: campos vacíos {faltan}")
            continue
        fecha = parse_fecha_es(r["fecha_registro"])
        importe = parse_importe_es(r["importe_esperado"])
        if (
            not re.fullmatch(r"(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", r["fecha_registro"])
            or fecha is None
        ):
            inf.errores.append(f"{nombre}:{numero}: fecha ilegible {r['fecha_registro']!r}")
            continue
        if (
            not re.fullmatch(
                r"-?(?:\d+(?:\.\d{1,2})?|(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})", r["importe_esperado"]
            )
            or importe is None
            or not importe.is_finite()
        ):
            inf.errores.append(f"{nombre}:{numero}: importe ilegible {r['importe_esperado']!r}")
            continue
        if r["estado"].upper() not in {"PENDIENTE", "PAGADA"}:
            inf.errores.append(f"{nombre}:{numero}: estado desconocido {r['estado']!r}")
            continue
        resultado.append(
            ErpEntry(
                asiento_id=r["asiento_id"],
                fecha_registro=fecha,
                proveedor_id=r["proveedor_id"].upper(),
                nif=normalizar_nif(r["nif"]),
                pedido=normalizar_pedido(r["pedido"]),
                importe_esperado=importe,
                estado=r["estado"].upper(),
            )
        )
    if lector.line_num <= 1:
        inf.errores.append(f"{nombre}: CSV sin filas de asientos")
    return resultado


def verificar(
    ruta: Path,
    *,
    hash_esperado: str | None = None,
    ruta_db: Path = Path("dist/albertitos.db"),
    lote1: Path = Path("data/caja/facturas"),
    esperados: int | None = None,
) -> InformeMaterial:
    inf = InformeMaterial(str(ruta))
    if hash_esperado and (ruta.is_dir() or not re.fullmatch(r"[0-9a-fA-F]{64}", hash_esperado)):
        inf.errores.append(
            "--hash requiere un ZIP y exactamente 64 caracteres hexadecimales SHA-256"
        )
        return inf
    try:
        entradas = _material(ruta, inf)
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        inf.errores.append(f"no se puede leer el material: {exc}")
        return inf
    if hash_esperado and inf.sha256 != hash_esperado.lower():
        inf.errores.append(
            f"SHA-256 no coincide: esperado {hash_esperado.lower()}, recibido {inf.sha256}"
        )
        return inf
    if inf.sha256 and hash_esperado is None:
        inf.avisos.append(
            "hash calculado, NO cotejado con el canal; repetir con --hash antes de ingerir"
        )
    if ruta.is_dir():
        inf.avisos.append("directorio: no acredita el hash del ZIP recibido")
    if not lote1.is_dir():
        inf.errores.append(f"no existe el directorio lote 1 para comprobar colisiones: {lote1}")
    originales = {
        clave_nombre(p.name): p.name for p in lote1.glob("*") if p.suffix.lower() == ".pdf"
    }
    hay_carpeta = any(
        "facturas" in [p.casefold() for p in PurePosixPath(n).parts[:-1]] for n, _ in entradas
    )
    nombres = {}
    asientos = {}
    for nombre, datos in entradas:
        p = PurePosixPath(nombre)
        if not unicodedata.is_normalized("NFC", nombre):
            inf.errores.append(f"nombre no NFC (NFD): {nombre!r}")
        es_pdf = p.suffix.lower() == ".pdf"
        es_factura = es_pdf and (
            ("facturas" in [x.casefold() for x in p.parts[:-1]])
            if hay_carpeta
            else not NOMBRE_REGLA.search(clave_nombre(p.stem))
        )
        if es_factura:
            inf.facturas.append(nombre)
            clave = clave_nombre(p.name)
            if clave in nombres:
                inf.errores.append(
                    f"nombre repetido ignorando mayúsculas/tildes: {nombres[clave]} / {nombre}"
                )
            nombres[clave] = nombre
            if clave in originales:
                inf.errores.append(f"nombre coincide con lote 1: {nombre} / {originales[clave]}")
            try:
                _pdf(datos)
            except Exception as exc:
                inf.errores.append(f"PDF ilegible {nombre}: {exc}")
        elif p.suffix.lower() == ".csv":
            inf.csvs.append(nombre)
            try:
                for a in _csv_erp(nombre, datos, inf):
                    if a.asiento_id in asientos:
                        inf.errores.append(f"asiento_id repetido entre filas/CSV: {a.asiento_id}")
                    asientos[a.asiento_id] = a
            except (UnicodeError, csv.Error, ValueError) as exc:
                inf.errores.append(f"CSV ilegible {nombre}: {exc}")
        else:
            try:
                inf.adjuntos.append((nombre, _adjunto(nombre, datos)))
            except Exception as exc:
                inf.errores.append(f"adjunto ilegible {nombre}: {exc}")
    if not inf.facturas:
        inf.errores.append("no hay facturas PDF en el material")
    if esperados is not None and len(inf.facturas) != esperados:
        inf.errores.append(f"hay {len(inf.facturas)} facturas PDF; se esperaban {esperados}")
    if inf.csvs:
        try:
            with closing(db.conectar(ruta_db, solo_lectura=True)) as conn:
                v1: ErpSnapshot = cargar_erp_bd(conn, "v1")
            for aid, a in sorted(asientos.items()):
                previo = v1.asientos.get(aid)
                if previo is None:
                    inf.nuevos.append(aid)
                else:
                    cambios = [
                        c for c in ErpEntry.model_fields if getattr(a, c) != getattr(previo, c)
                    ]
                    if cambios:
                        inf.modificados[aid] = cambios
                    else:
                        inf.sin_cambio.append(aid)
        except (sqlite3.Error, LookupError, ValueError) as exc:
            inf.errores.append(f"no se puede comparar CSV con ERP v1 (sólo lectura): {exc}")
    else:
        inf.avisos.append(
            "sin CSV ERP en este material; verificar por separado si llega en otro fichero"
        )
    if not inf.adjuntos:
        inf.avisos.append(
            "sin adjuntos con posible regla; comprobar también el canal de la organización"
        )
    return inf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("material", type=Path)
    parser.add_argument("--hash", dest="hash_esperado")
    parser.add_argument(
        "--db", type=Path, default=Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    parser.add_argument("--lote1-dir", type=Path, default=Path("data/caja/facturas"))
    parser.add_argument(
        "--esperados", type=int, help="recuento exigido; 40 para el lote real, 10 para el ensayo"
    )
    args = parser.parse_args(argv)
    if args.esperados is not None and args.esperados < 1:
        parser.error("--esperados debe ser positivo")
    inf = verificar(
        args.material,
        hash_esperado=args.hash_esperado,
        ruta_db=args.db,
        lote1=args.lote1_dir,
        esperados=args.esperados,
    )
    print(inf.texto())
    return 0 if inf.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
