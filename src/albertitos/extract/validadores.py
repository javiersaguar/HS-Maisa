"""Validadores deterministas sobre InvoiceFacts. Mandan sobre lo que diga el LLM."""

from __future__ import annotations

from decimal import Decimal

from albertitos.core.contracts import Aviso, InvoiceFacts
from albertitos.formatos import CENT, iban_valido

IVA_GENERAL = Decimal("21")
OBLIGATORIOS = ("nif_emisor", "iban", "pedido", "fecha", "total")


def validar(h: InvoiceFacts) -> list[Aviso]:
    """Devuelve los avisos de h más los que se deducen de sus campos, sin duplicados y en orden."""
    avisos = list(h.avisos)
    for campo in OBLIGATORIOS:
        if getattr(h, campo) is None:
            avisos.append(Aviso.CAMPO_AUSENTE)
            break
    if (
        h.base is not None
        and h.iva is not None
        and h.total is not None
        and abs(h.base + h.iva - h.total) > CENT
    ):
        avisos.append(Aviso.TOTAL_NO_CUADRA)
    if h.base is not None and h.iva is not None and h.base != 0:
        if abs(h.iva - (h.base * IVA_GENERAL / 100).quantize(CENT)) > CENT:
            avisos.append(Aviso.IVA_NO_ESTANDAR)
    if h.iva_pct is not None and h.iva_pct != IVA_GENERAL:
        avisos.append(Aviso.IVA_NO_ESTANDAR)
    if h.iban and not iban_valido(h.iban):
        avisos.append(Aviso.IBAN_INVALIDO)
    vistos: list[Aviso] = []
    for a in avisos:
        if a not in vistos:
            vistos.append(a)
    return vistos


CAMPOS_CLAVE = ("num_factura", "fecha", "nif_emisor", "iban", "pedido", "base", "iva", "total")


def discrepancias(a: InvoiceFacts, b: InvoiceFacts) -> dict[str, tuple[object, object]]:
    """Campos clave en los que dos extractores (p. ej. plantilla y LLM) no coinciden. Vacío = de acuerdo."""
    out: dict[str, tuple[object, object]] = {}
    for campo in CAMPOS_CLAVE:
        x, y = getattr(a, campo), getattr(b, campo)
        if x != y:
            out[campo] = (x, y)
    return out
