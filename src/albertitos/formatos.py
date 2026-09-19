"""Formatos compartidos: importes, fechas (numéricas y en letra), IBAN y NIF españoles, e identificadores
extranjeros (IBAN por país, IVA europeo, CNPJ, número corporativo japonés) desde el lote 2.

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


#: Longitud del IBAN por país (registro IBAN de SWIFT, ISO 13616). Japón, EE. UU. o México no usan IBAN: un
#: «IBAN» japonés (lote 2, P015) no está aquí y sale mal formado, no con un error.
LONGITUD_IBAN = {
    "AD": 24, "AT": 20, "BE": 16, "BR": 29, "CH": 21, "CZ": 24, "DE": 22, "DK": 18, "ES": 24, "FI": 18,
    "FR": 27, "GB": 22, "GR": 27, "IE": 22, "IT": 27, "LU": 20, "MC": 27, "NL": 18, "NO": 15, "PL": 28,
    "PT": 25, "SE": 24,
}  # fmt: skip


def iban_bien_formado(s: str) -> bool:
    """Forma del IBAN por país: país del registro, longitud exacta, dos dígitos de control y sólo letras y
    cifras (el brasileño acaba en letra + cifra, «…493C1»). Sin mod-97: los IBAN sintéticos de la Caja y de
    los proveedores nuevos no lo pasan, y eso no delata un error de extracción."""
    s = normalizar_iban(s)
    return s.isascii() and s.isalnum() and LONGITUD_IBAN.get(s[:2]) == len(s) and s[2:4].isdigit()


def iban_valido(s: str) -> bool:
    """Forma por país + mod-97 (ISO 13616). Nunca lanza: un IBAN de un país sin IBAN (JP) da False. Los IBAN
    sintéticos de la Caja no lo pasan: es un Aviso, no una regla."""
    if not iban_bien_formado(s):
        return False
    s = normalizar_iban(s)
    reordenado = s[4:] + s[:4]
    numerico = "".join(str(int(c, 36)) for c in reordenado)
    return int(numerico) % 97 == 1


def normalizar_nif(s: str) -> str:
    """Sin espacios, guiones, puntos ni barras, en mayúsculas. La barra es del CNPJ brasileño
    («12.345.678/0001-95» → «12345678000195»), para que el PDF y el maestro casen escriban como escriban."""
    return re.sub(r"[\s\-./]", "", s).upper()


#: Identificadores fiscales extranjeros, por su forma (sin espacios ni puntuación). No se validan como NIF
#: español: un DE…, un FR…, un CNPJ o un número corporativo japonés no son un «NIF inválido».
_VAT_UE = re.compile(
    r"DE\d{9}|FR[0-9A-HJ-NP-Z]{2}\d{9}|GB(?:\d{9}|\d{12}|GD\d{3}|HA\d{3})|IT\d{11}|PT\d{9}|NL\d{9}B\d{2}"
    r"|BE[01]\d{9}|ATU\d{8}|LU\d{8}|DK\d{8}|FI\d{8}|SE\d{12}|PL\d{10}|EL\d{9}|IE\d{7}[A-W][A-I]?"
    r"|CHE\d{9}(?:MWST|TVA|IVA)?"
)
_CNPJ = re.compile(r"\d{14}")
_CORPORATIVO_JP = re.compile(r"T?\d{13}")


def tipo_identificador_extranjero(s: str) -> str | None:
    """'vat_ue' (IVA europeo, GB y CH incluidos), 'cnpj' (Brasil), 'jp' (número corporativo, 13 cifras) o
    None si no tiene la forma de ninguno. Sólo forma: los dígitos de control del CNPJ los da `cnpj_valido`."""
    n = normalizar_nif(s)
    if _VAT_UE.fullmatch(n):
        return "vat_ue"
    if _CNPJ.fullmatch(n):
        return "cnpj"
    if _CORPORATIVO_JP.fullmatch(n):
        return "jp"
    return None


def identificador_extranjero(s: str) -> bool:
    return tipo_identificador_extranjero(s) is not None


def cnpj_valido(s: str) -> bool:
    """Dígitos de control del CNPJ (módulo 11, pesos 5-4-3-2-9-8-7-6-5-4-3-2 y 6-5-…)."""
    d = [int(c) for c in normalizar_nif(s) if c.isdigit()]
    if len(d) != 14 or len(set(d)) == 1:
        return False

    def dv(n: list[int], pesos: list[int]) -> int:
        r = sum(a * b for a, b in zip(n, pesos, strict=True)) % 11
        return 0 if r < 2 else 11 - r

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return d[12] == dv(d[:12], p1) and d[13] == dv(d[:13], [6, *p1])


def normalizar_pedido(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()
