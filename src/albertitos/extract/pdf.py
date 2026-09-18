"""Lectura de PDFs con PyMuPDF: texto, nº de páginas, imagen PNG para visión."""

from __future__ import annotations

from pathlib import Path

import pymupdf

UMBRAL_TEXTO = 50  # caracteres no blancos; por debajo, la factura se trata como escaneada


def texto_de(ruta: Path | str) -> str:
    with pymupdf.open(ruta) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def info(ruta: Path | str) -> tuple[int, bool]:
    """(nº de páginas, ¿tiene capa de texto útil?)"""
    with pymupdf.open(ruta) as doc:
        n = len(doc)
        chars = sum(len("".join(page.get_text("text").split())) for page in doc)
    return n, chars >= UMBRAL_TEXTO


def imagen_png(ruta: Path | str, pagina: int = 0, dpi: int = 150) -> bytes:
    with pymupdf.open(ruta) as doc:
        return doc[pagina].get_pixmap(dpi=dpi).tobytes("png")
