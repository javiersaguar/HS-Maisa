"""Lectura de PDFs con PyMuPDF: texto, nº de páginas, imagen PNG para visión."""

from __future__ import annotations

from pathlib import Path

import pymupdf

UMBRAL_TEXTO = 50  # caracteres no blancos; por debajo, la factura se trata como escaneada
MAX_PAGINAS_VISION = 4  # tope de seguridad: ninguna factura de la Caja pasa de 2 páginas


def texto_de(ruta: Path | str) -> str:
    """Texto de TODAS las páginas concatenadas.

    No es un detalle: las 22 facturas de 2 páginas de la Caja llevan base, IVA y total en la
    página 2 (la 1 termina en `Suma y sigue:`, que no es el total). Leer sólo la primera da un
    importe que parece bueno y no lo es.
    """
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


def imagenes_png(ruta: Path | str, dpi: int = 150, maximo: int = MAX_PAGINAS_VISION) -> list[bytes]:
    """Una imagen por página, en orden. Para mandarle al LLM una escaneada de varias páginas.

    `imagen_png` sigue existiendo y devolviendo sólo la primera: quien no necesite más no cambia.
    """
    with pymupdf.open(ruta) as doc:
        return [doc[i].get_pixmap(dpi=dpi).tobytes("png") for i in range(min(len(doc), maximo))]
