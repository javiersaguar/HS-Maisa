"""Validadores deterministas sobre InvoiceFacts. Mandan sobre lo que diga el LLM.

Un aviso sólo vale si separa. Dos comprobaciones clásicas se dejan deliberadamente SIN emitir aviso
porque sobre esta Caja marcarían casi todo (medido el 18/09 sobre las 468 facturas que salen por
plantilla) y dejarían la traza inservible:

- **dígito de control del IBAN (mod-97): 0 de 468 lo pasan.** Los IBAN de la Caja y los 11 del
  maestro son sintéticos. `IBAN_INVALIDO` se emite sólo si el IBAN está mal FORMADO (país, longitud,
  alfabeto), que es lo que delata un error de extracción de verdad.
- **letra de control del NIF: 46 de 468 la pasan** (sólo B46102331). Mismo motivo: se comprueba la
  forma, no la letra. Las funciones `iban_checksum_ok` / `nif_letra_control_ok` siguen aquí para la
  consola y para el lote 2, por si esos datos sí son reales.

Lo que sí separa en esta Caja: el total que no cuadra, la cuota de IVA que no sale del porcentaje
impreso, y las líneas que no suman la base.
"""

from __future__ import annotations

import re
from decimal import Decimal

from albertitos.core.contracts import Aviso, InvoiceFacts
from albertitos.formatos import (
    CENT,
    iban_valido,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
)

IVA_GENERAL = Decimal("21")
OBLIGATORIOS = ("nif_emisor", "iban", "pedido", "fecha", "total")
RECOMENDADOS = (
    "num_factura",
    "base",
    "iva",
)  # su ausencia no impide decidir, pero deja cojo el cruce

_IBAN_FORMA = re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}")
_NIF_FORMA = re.compile(r"(?:[A-HJ-NP-SUVW]\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])")
_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def iban_bien_formado(s: str) -> bool:
    """Forma esperada en esta Caja: `ES` + 2 dígitos de control + 20 cifras, 24 caracteres.

    Se exige España a propósito: los 11 proveedores del maestro son españoles, así que un IBAN de
    otro país es casi seguro un error de extracción (o un cambio de cuenta que hay que mirar). Si
    el lote 2 trae un proveedor extranjero saltará el aviso y alguien lo revisará, que es el lado
    seguro por el que equivocarse.
    """
    s = normalizar_iban(s)
    return bool(_IBAN_FORMA.fullmatch(s)) and s.startswith("ES") and len(s) == 24


def iban_checksum_ok(s: str) -> bool:
    """mod-97 (ISO 13616). NO se emite aviso con esto: 0 de 468 lo pasan en esta Caja."""
    return iban_valido(s)


def nif_bien_formado(s: str) -> bool:
    """Forma del NIF/CIF español, sin letra de control."""
    return bool(_NIF_FORMA.fullmatch(normalizar_nif(s)))


def nif_letra_control_ok(s: str) -> bool:
    """Letra/dígito de control real (DNI mod-23, CIF suma ponderada). 46 de 468 en esta Caja."""
    n = normalizar_nif(s)
    if len(n) != 9:
        return False
    if n[0].isdigit():  # DNI: 8 cifras + letra
        return n[:8].isdigit() and n[8] == _LETRAS_DNI[int(n[:8]) % 23]
    cuerpo = n[1:8]
    if not cuerpo.isdigit():
        return False
    pares = sum(int(c) for c in cuerpo[1::2])
    impares = sum(sum(divmod(int(c) * 2, 10)) for c in cuerpo[0::2])
    digito = (10 - (pares + impares) % 10) % 10
    return n[8] == str(digito) or n[8] == "JABCDEFGHI"[digito]


def suma_lineas(h: InvoiceFacts) -> Decimal | None:
    """Suma de los importes de línea, o None si no hay líneas o alguna no trae importe."""
    if not h.lineas:
        return None
    total = Decimal("0")
    for linea in h.lineas:
        if linea.importe is None:
            return None
        total += linea.importe
    return total.quantize(CENT)


def validar(h: InvoiceFacts) -> list[Aviso]:
    """Devuelve los avisos de h más los que se deducen de sus campos, sin duplicados y en orden."""
    avisos = list(h.avisos)

    if any(getattr(h, campo) is None for campo in OBLIGATORIOS):
        avisos.append(Aviso.CAMPO_AUSENTE)
    if any(getattr(h, campo) is None for campo in RECOMENDADOS):
        avisos.append(Aviso.EXTRACCION_PARCIAL)

    # base + IVA = total (±0,01)
    if h.base is not None and h.iva is not None and h.total is not None:
        if abs(h.base + h.iva - h.total) > CENT:
            avisos.append(Aviso.TOTAL_NO_CUADRA)

    # las líneas tienen que sumar la BASE, no el total: medido 468/468 al céntimo en la Caja
    suma = suma_lineas(h)
    referencia = h.base if h.base is not None else h.total
    if suma is not None and referencia is not None and abs(suma - referencia) > CENT:
        avisos.append(Aviso.IMPORTE_AMBIGUO)

    # la cuota de IVA tiene que salir del porcentaje IMPRESO en la propia factura.
    # FA-5590 imprime "IVA (21%): 400,00" sobre una base de 2.500,00 → son 400/2500 = 16 %.
    if h.base is not None and h.iva is not None and h.base != 0:
        pct = h.iva_pct if h.iva_pct is not None else IVA_GENERAL
        if abs(h.iva - (h.base * pct / 100).quantize(CENT)) > CENT:
            avisos.append(Aviso.IVA_NO_ESTANDAR)
    if h.iva_pct is not None and h.iva_pct != IVA_GENERAL:
        avisos.append(Aviso.IVA_NO_ESTANDAR)

    if h.iban and not iban_bien_formado(h.iban):
        avisos.append(Aviso.IBAN_INVALIDO)
    # TODO(Miguel, core/): falta un Aviso.NIF_INVALIDO. Mientras no exista, un NIF con forma
    # imposible se marca como EXTRACCION_PARCIAL (propuesto a Javier en la bitácora del 18/09).
    if h.nif_emisor and not nif_bien_formado(h.nif_emisor):
        avisos.append(Aviso.EXTRACCION_PARCIAL)

    vistos: list[Aviso] = []
    for a in avisos:
        if a not in vistos:
            vistos.append(a)
    return vistos


CAMPOS_CLAVE = ("num_factura", "fecha", "nif_emisor", "iban", "pedido", "base", "iva", "total")
_IMPORTES = {"base", "iva", "total"}
_NORMALIZADORES = {
    "nif_emisor": normalizar_nif,
    "iban": normalizar_iban,
    "pedido": normalizar_pedido,
    "num_factura": lambda s: re.sub(r"\s+", "", s).upper(),
}


def discrepancias(a: InvoiceFacts, b: InvoiceFacts) -> dict[str, tuple[object, object]]:
    """Campos clave en los que dos extractores (p. ej. plantilla y LLM) no coinciden. Vacío = de acuerdo.

    Los importes se comparan con la tolerancia de la casa (0,01) y los identificadores normalizados,
    para que `ES21 0049 …` vs `ES210049…` o `po-2026-0096` vs `PO-2026-0096` no cuenten como
    desacuerdo: si no, la discrepancia real se pierde entre el ruido de formato.
    """
    out: dict[str, tuple[object, object]] = {}
    for campo in CAMPOS_CLAVE:
        x, y = getattr(a, campo), getattr(b, campo)
        if x is None and y is None:
            continue
        if x is None or y is None:
            out[campo] = (x, y)
            continue
        if campo in _IMPORTES:
            if abs(Decimal(x) - Decimal(y)) > CENT:
                out[campo] = (x, y)
        elif campo in _NORMALIZADORES:
            norm = _NORMALIZADORES[campo]
            if norm(str(x)) != norm(str(y)):
                out[campo] = (x, y)
        elif x != y:
            out[campo] = (x, y)
    return out
