"""Lectura de PDFs con PyMuPDF: texto, nº de páginas, imagen PNG para visión."""

from __future__ import annotations

import re
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


# Letra de mano en un PDF con capa de texto (lote 2, 19/09). Las facturas "del café" (e16-e18) escriben a mano
# con tipografías manuscritas alternadas letra a letra, y e18 además tacha con trazos curvos. El texto impreso
# de e18 cuadra con el ERP: sin esta señal se pagaría sin ver la corrección. Medido: en las 471 del lote 1 no
# hay ninguna tipografía de este tipo ni ningún trazo curvo; en el lote 2, sólo en e16, e17 y e18.
_FUENTE_MANUSCRITA = re.compile(
    r"brush|script|hand|marker|felt|snell|caveat|kalam|comic|chalk|scrawl|cursive", re.IGNORECASE
)


def es_fuente_manuscrita(nombre: str) -> bool:
    return bool(_FUENTE_MANUSCRITA.search(nombre.split("+")[-1]))


def rasgos_manuscritos(ruta: Path | str) -> dict[str, object]:
    """Qué hay escrito o dibujado a mano: {"fuentes": [...], "texto": "...", "trazos": n}. Vacío si nada.

    `texto` recompone lo escrito con tipografías manuscritas (por líneas, de izquierda a derecha) y es
    evidencia para la traza, no un hecho: la factura la tiene que mirar una persona."""
    fuentes: set[str] = set()
    trozos: list[
        tuple[int, float, float, float, float, str]
    ] = []  # página, centro y, alto, x0, x1, texto
    trazos = 0
    with pymupdf.open(ruta) as doc:
        for n, pagina in enumerate(doc):
            for bloque in pagina.get_text("dict")["blocks"]:
                for linea in bloque.get("lines", []):
                    for s in linea["spans"]:
                        if es_fuente_manuscrita(s["font"]) and s["text"].strip():
                            fuentes.add(s["font"].split("+")[-1])
                            x0, y0, x1, y1 = s["bbox"]
                            trozos.append((n, (y0 + y1) / 2, y1 - y0, x0, x1, s["text"]))
            trazos += sum(1 for d in pagina.get_drawings() for item in d["items"] if item[0] == "c")
    if not fuentes and not trazos:
        return {}
    # Cada letra "a mano" baila un poco en vertical: misma línea si su centro cae a menos de medio alto.
    renglones: list[list[tuple[int, float, float, float, float, str]]] = []
    for t in sorted(trozos, key=lambda t: (t[0], t[1])):
        ultimo = renglones[-1] if renglones else None
        if (
            ultimo
            and ultimo[0][0] == t[0]
            and abs(t[1] - ultimo[0][1]) <= 0.5 * max(t[2], ultimo[0][2])
        ):
            ultimo.append(t)
        else:
            renglones.append([t])
    lineas: list[str] = []
    for renglon in renglones:
        texto, fin = "", None
        for _, _, alto, x0, x1, t in sorted(renglon, key=lambda t: t[3]):
            texto += (" " if fin is not None and x0 - fin > 0.25 * alto else "") + t
            fin = x1
        lineas.append(" ".join(texto.split()))
    return {"fuentes": sorted(fuentes), "texto": " / ".join(lineas)[:200], "trazos": trazos}
