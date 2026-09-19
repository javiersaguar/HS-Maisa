"""Avisa si una respuesta de bonus/confianza ya no tiene las claves del contrato (ejemplos JSON).

Repite cada petición de docs/api/ejemplos/bonus-*.json y confianza-*.json contra la BD local
(despachar, sin servidor) y compara las CLAVES a todos los niveles, no los valores. Así Alejandro
se entera si alguien renombra un campo antes de que se le rompa la pantalla.

Uso: uv run python scripts/contrato_api_check.py
     uv run python scripts/contrato_api_check.py --db dist/albertitos.db --ejemplos docs/api/ejemplos
Sale 1 si hay claves que faltan o sobran. Sólo lee la BD.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from albertitos import bonus, confianza
from albertitos.console import api
from albertitos.core import db

RAIZ = Path(__file__).resolve().parents[1]
_MAPA = re.compile(r"\d")


def claves(obj: Any, prefijo: str = "") -> set[str]:
    """Rutas de claves. En un mapa de datos (semanas ISO, ids) no se listan las claves-dato."""
    out: set[str] = set()
    if isinstance(obj, dict):
        if obj and all(_MAPA.search(str(k)) for k in obj) and len(obj) > 3:
            muestra = next(iter(obj.values()))
            marca = f"{prefijo}{{}}" if prefijo else "{}"
            out |= claves(muestra, marca)
            return out
        for k, v in obj.items():
            ruta = f"{prefijo}.{k}" if prefijo else str(k)
            out.add(ruta)
            out |= claves(v, ruta)
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        out |= claves(obj[0], f"{prefijo}[]" if prefijo else "[]")
    return out


def parsear_peticion(texto: str) -> tuple[str, str, dict[str, list[str]]]:
    metodo, _, resto = texto.strip().partition(" ")
    parsed = urlparse(resto)
    return metodo.upper(), parsed.path, parse_qs(parsed.query)


def ejemplo_a_peticion(
    ruta: Path, datos: dict
) -> tuple[str, str, dict[str, list[str]], int, Any] | None:
    if {"peticion", "status", "respuesta"} <= datos.keys():
        metodo, path, query = parsear_peticion(str(datos["peticion"]))
        return metodo, path, query, int(datos["status"]), datos["respuesta"]
    nombre = ruta.stem
    if nombre.startswith("confianza-resumen"):
        return "GET", "/confianza/resumen", {}, 200, datos
    if nombre.startswith("confianza-ficheros"):
        return "GET", "/confianza/ficheros", {"banda": ["baja"]}, 200, datos
    if nombre.startswith("confianza-fichero") and datos.get("file_id"):
        return "GET", "/confianza/fichero", {"file_id": [str(datos["file_id"])]}, 200, datos
    return None


def comprobar(conn, ejemplos: Path) -> list[str]:
    api.RUTAS.update(bonus.rutas())
    api.RUTAS.update(confianza.rutas())
    fallos: list[str] = []
    for fichero in sorted(ejemplos.glob("bonus-*.json")) + sorted(
        ejemplos.glob("confianza-*.json")
    ):
        datos = json.loads(fichero.read_text(encoding="utf-8"))
        parsed = ejemplo_a_peticion(fichero, datos)
        if parsed is None:
            continue
        metodo, path, query, status_esp, cuerpo_esp = parsed
        status, cuerpo = api.despachar(metodo, path, query, conn)
        if status != status_esp:
            fallos.append(f"{fichero.name}: status {status} (ejemplo {status_esp})")

        def _api(ruta: str) -> bool:
            return not ruta.endswith("nota_del_ejemplo") and ruta != "nota_del_ejemplo"

        falta = sorted(k for k in claves(cuerpo_esp) - claves(cuerpo) if _api(k))
        sobra = sorted(k for k in claves(cuerpo) - claves(cuerpo_esp) if _api(k))
        if falta or sobra:
            partes = []
            if falta:
                partes.append("faltan " + ", ".join(falta))
            if sobra:
                partes.append("sobran " + ", ".join(sobra))
            fallos.append(f"{fichero.name}: " + "; ".join(partes))
    return fallos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(RAIZ / "dist/albertitos.db"))
    ap.add_argument("--ejemplos", default=str(RAIZ / "docs/api/ejemplos"))
    args = ap.parse_args()
    conn = db.conectar(args.db, solo_lectura=True)
    try:
        fallos = comprobar(conn, Path(args.ejemplos))
    finally:
        conn.close()
    if not fallos:
        print("OK: claves del contrato intactas")
        return 0
    print("DIFERENCIAS:")
    for linea in fallos:
        print(" ", linea)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
