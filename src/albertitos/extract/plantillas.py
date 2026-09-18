"""Parsers deterministas por plantilla. Optimización de coste medida, no el camino principal.

Viernes: vacío (todo va al LLM con caché). Sábado: las 3-5 plantillas más frecuentes, cada una con
su test sobre facturas reales. Si plantilla y LLM discrepan → Aviso.DISCREPANCIA_EXTRACTORES.
"""

from __future__ import annotations

from collections.abc import Callable

from albertitos.core.contracts import InvoiceFacts

# nombre → (detector, parser). El parser devuelve None si no consigue TODOS los campos obligatorios.
PLANTILLAS: dict[
    str, tuple[Callable[[str], bool], Callable[[str, str, str], InvoiceFacts | None]]
] = {}


def extraer_por_plantilla(texto: str, *, file_id: str, sha256: str) -> InvoiceFacts | None:
    for _nombre, (detecta, parsea) in PLANTILLAS.items():
        if detecta(texto):
            return parsea(texto, file_id, sha256)
    return None
