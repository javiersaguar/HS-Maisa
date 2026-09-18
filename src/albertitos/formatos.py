"""Formatos españoles compartidos: importes, fechas (numéricas y en letra), IBAN y NIF.

Se convierte una vez aquí; aguas abajo sólo circulan Decimal / date / strings normalizados.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}  # fmt: skip

_FECHA_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_FECHA_NUM = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})")
_FECHA_LETRA = re.compile(
    r"(\d{1,2})\s+(?:de\s+)?([a-záéíóúA-ZÁÉÍÓÚ]+)\.?\s+(?:de\s+|del\s+)?(\d{4})"
)


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def parse_importe_es(texto: str | float | Decimal | None) -> Decimal | None:
    """'12.874,40' → 12874.40 · 'EUR 1705.37' → 1705.37 · '943,80 €' → 943.80 · '1.705' → 1705."""
    if texto is None:
        return None
    if isinstance(texto, (int, float, Decimal)):
        return Decimal(str(texto)).quantize(CENT, rounding=ROUND_HALF_UP)
    s = re.sub(r"(?i)eur|€", "", str(texto)).strip()
    negativo = s.startswith("-") or s.startswith("(")
    s = re.sub(r"[^\d,.]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        s = (
            s.replace(".", "").replace(",", ".")
            if s.rfind(",") > s.rfind(".")
            else s.replace(",", "")
        )
    elif "," in s:
        ent, _, dec = s.rpartition(",")
        s = ent.replace(",", "") + "." + dec if len(dec) <= 2 else s.replace(",", "")
    elif "." in s:
        ent, _, dec = s.rpartition(".")
        s = s.replace(".", "") if len(dec) == 3 else ent.replace(".", "") + "." + dec
    try:
        v = Decimal(s).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    return -v if negativo else v


def parse_fecha_es(texto: str | date | None) -> date | None:
    """'08/01/2026', '2026-01-08', '15 de enero de 2026', '8 ene 2026' → date. None si no se puede."""
    if texto is None:
        return None
    if isinstance(texto, date):
        return texto
    s = str(texto).strip()
    if m := _FECHA_ISO.search(s):
        y, mo, d = (int(x) for x in m.groups())
        return _fecha_segura(y, mo, d)
    if m := _FECHA_NUM.search(s):
        d, mo, y = (int(x) for x in m.groups())
        return _fecha_segura(y, mo, d)
    if m := _FECHA_LETRA.search(s):
        mes = MESES.get(sin_tildes(m.group(2)).lower())
        if mes:
            return _fecha_segura(int(m.group(3)), mes, int(m.group(1)))
    return None


def fecha_en_letra(texto: str) -> bool:
    return bool(_FECHA_LETRA.search(texto)) and not _FECHA_NUM.search(texto)


def _fecha_segura(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def normalizar_iban(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def iban_valido(s: str) -> bool:
    """mod-97 (ISO 13616). Los IBAN sintéticos de la Caja pueden no pasarlo: es un Aviso, no una regla."""
    s = normalizar_iban(s)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", s):
        return False
    if s.startswith("ES") and len(s) != 24:
        return False
    reordenado = s[4:] + s[:4]
    numerico = "".join(str(int(c, 36)) for c in reordenado)
    return int(numerico) % 97 == 1


def normalizar_nif(s: str) -> str:
    return re.sub(r"[\s\-.]", "", s).upper()


def normalizar_pedido(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()
