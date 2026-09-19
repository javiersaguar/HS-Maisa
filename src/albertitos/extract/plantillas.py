"""Parsers deterministas por plantilla. Optimización de coste MEDIDA, no el camino principal.

Las 471 facturas con capa de texto de la Caja caen en **6 familias** de maquetación (inventario en la
bitácora del ciclo 1). Cada familia tiene aquí un detector (ancla inequívoca) y un parser de campos
fijos. El parser es deliberadamente conservador: si falta cualquier campo obligatorio devuelve `None`
y el fichero se va al LLM. Un campo mal extraído es peor que no extraer nada, porque la norma decide
con él y nadie lo revisa.

El texto de la factura es un DATO: aquí sólo se leen campos. Las frases que intentan dictar la
decisión se recogen como `Aviso.TEXTO_INSTRUCCION` + `texto_sospechoso` (evidencia), igual que en el
camino del LLM, y decide `rules/`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from albertitos.core.contracts import Aviso, InvoiceFacts, LineaFactura, MetodoExtraccion
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.extract import instrucciones
from albertitos.formatos import (
    CENT,
    fecha_en_letra,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
)

# Caracteres invisibles que algunos PDFs de la Caja intercalan dentro de los importes
# (p. ej. `TOTAL: 3​.​0​1​2​,​8​9​ €` con U+200B entre cada cifra). Se quitan antes de casar.
_INVISIBLES = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)

# Fragmentos reutilizables. `IMP` acepta `2.489,99`, `EUR 1705.37`, `943,80 €`, `-12,00`.
IMP = r"(?:EUR\s*)?(-?\d[\d.,]*)\s*(?:€|EUR)?"
PCT = r"(\d{1,2}(?:[.,]\d+)?)"
NIF = r"([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])"
IBAN = r"(ES[\d\s]{22,30}?)(?:\s*$|\s{2})"
PED = r"(PO-\d{4}-\d{4})"


@dataclass(frozen=True)
class Plantilla:
    """Una familia de maquetación: cómo reconocerla y dónde está cada campo."""

    nombre: str
    ancla: str  # detector: debe casar para intentar el parser
    num_factura: str
    fecha: str
    nif_emisor: str
    iban: str
    pedido: str
    base: str
    iva: str  # dos grupos: (porcentaje, importe)
    total: str
    razon_social: str | None = None
    linea: str | None = None  # tres grupos: (concepto, unidades, importe)

    def compilada(self) -> dict[str, re.Pattern[str]]:
        campos = {
            "ancla": self.ancla,
            "num_factura": self.num_factura,
            "fecha": self.fecha,
            "nif_emisor": self.nif_emisor,
            "iban": self.iban,
            "pedido": self.pedido,
            "base": self.base,
            "iva": self.iva,
            "total": self.total,
        }
        if self.razon_social:
            campos["razon_social"] = self.razon_social
        if self.linea:
            campos["linea"] = self.linea
        return {k: re.compile(v, re.MULTILINE) for k, v in campos.items()}


# --------------------------------------------------------------------------- las 6 familias
# n = facturas de la Caja (de 471 con texto) medidas el 18/09; el ejemplo es un file_id real.

PLANTILLAS_DEF: tuple[Plantilla, ...] = (
    Plantilla(  # n=113 · ej. 2026-01-16_P004.pdf · las 22 de 2 páginas son todas de aquí
        nombre="moderna",
        ancla=r"^FACTURA N[ºo°]:.*\n(?s:.)*^Base imponible:",
        num_factura=r"^FACTURA N[ºo°]:\s*([^\n·]+?)\s*(?:·|$)",
        fecha=r"^Fecha:\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{4})",
        nif_emisor=r"^NIF:\s*" + NIF,
        iban=r"IBAN:\s*" + IBAN,
        pedido=r"Ref\.\s*Pedido:\s*" + PED,
        base=r"^Base imponible:\s*" + IMP,
        iva=r"^IVA\s*\(" + PCT + r"\s*%\):\s*" + IMP,
        total=r"^TOTAL:\s*" + IMP,
        razon_social=r"\A\s*(.+?)\s*$",
        linea=r"^\s{2,}(.+?)\s+x(\d+)\s+\.{2,}\s+" + IMP + r"\s*$",
    ),
    Plantilla(  # n=92 · ej. 2026-01-15_P003.pdf · fecha siempre en letra
        nombre="abono",
        ancla=r"^Cuenta de abono \(IBAN\):.*\n(?s:.)*^Importe base:",
        num_factura=r"^N[ºo°] de factura:\s*(\S+)",
        fecha=r"^Fecha de emisi[oó]n:\s*(.+?)\s*$",
        nif_emisor=r"^.*·\s*NIF\s+" + NIF,
        iban=r"^Cuenta de abono \(IBAN\):\s*" + IBAN,
        pedido=r"^Su pedido:\s*" + PED,
        base=r"^Importe base:\s*" + IMP,
        iva=r"^Cuota IVA\s*\(" + PCT + r"\s*%\):\s*" + IMP,
        total=r"^Total factura:\s*" + IMP,
        razon_social=r"\A\s*(.+?)\s*$",
        linea=r"^\s{2,}(.+?)\s+\((\d+)\)\s+—\s+" + IMP + r"\s*$",
    ),
    Plantilla(  # n=91 · ej. 2026-01-26_P007.pdf · importes en formato inglés ("EUR 1705.37")
        nombre="invoice",
        ancla=r"^Invoice #.*\n(?s:.)*^Subtotal:",
        num_factura=r"^Invoice #\s*(\S+)",
        fecha=r"^Fecha factura:\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{4})",
        nif_emisor=r"^NIF:\s*" + NIF,
        iban=r"^IBAN:\s*" + IBAN,
        pedido=r"\bPO:\s*" + PED,
        base=r"^Subtotal:\s*" + IMP,
        iva=r"^IVA\s*\(" + PCT + r"\s*%\):\s*" + IMP,
        total=r"^TOTAL A PAGAR:\s*" + IMP,
        razon_social=r"\A\s*(.+?)\s*$",
        linea=r"^-\s+(.+?)\s+\((\d+)\s*ud\):\s+" + IMP + r"\s*$",
    ),
    Plantilla(  # n=73 · ej. 2026-01-08_P001.pdf · la "clásica", cabecera FACTURA suelta
        nombre="clasica",
        ancla=r"^FACTURA\s*$\n^Factura:.*\n(?s:.)*^Base:",
        num_factura=r"^Factura:\s*(\S+)",
        fecha=r"^Factura:\s*\S+\s+Fecha:\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{4})",
        nif_emisor=r"^NIF:\s*" + NIF,
        iban=r"^IBAN:\s*" + IBAN,
        pedido=r"^Pedido:\s*" + PED,
        base=r"^Base:\s*" + IMP,
        iva=r"^IVA\s*\(" + PCT + r"\s*%\):\s*" + IMP,
        total=r"^TOTAL:\s*" + IMP,
        razon_social=r"^Pedido:\s*PO-\d{4}-\d{4}\s*\n\s*(.+?)\s*$",
        linea=r"^(\S.*?)\s+\.{3,}\s+" + IMP + r"\s*$",
    ),
    Plantilla(  # n=57 · ej. 2026-01-14_P002.pdf · todo en mayúsculas, importes alineados con puntos
        nombre="mayusculas",
        ancla=r"^REF FACTURA:.*\n(?s:.)*^BASE IMPONIBLE\.{3,}",
        num_factura=r"^REF FACTURA:\s*(\S+)",
        fecha=r"^FECHA:\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{4})",
        nif_emisor=r"^NIF\s+" + NIF,
        iban=r"^CUENTA DE ABONO \(IBAN\):\s*" + IBAN,
        pedido=r"^PEDIDO CLIENTE:\s*" + PED,
        base=r"^BASE IMPONIBLE\.{3,}\s*" + IMP,
        iva=r"^IVA\s*\(" + PCT + r"\s*%\)\.{3,}\s*" + IMP,
        total=r"^TOTAL\.{3,}\s*" + IMP,
        razon_social=r"\A\s*(.+?)\s*$",
        linea=r"^([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ .]*[A-ZÁÉÍÓÚÜÑ])\s{2,}" + IMP + r"\s*$",
    ),
    Plantilla(  # n=45 · ej. 2026-01-24_P009.pdf · "FACTURA SIMPLIFICADA", tabla con Uds
        nombre="simplificada",
        ancla=r"^FACTURA SIMPLIFICADA N[ºo°].*\n(?s:.)*^BASE IMPONIBLE:",
        num_factura=r"^FACTURA SIMPLIFICADA N[ºo°]\s*(\S+)",
        fecha=r"^Fecha:\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{4})",
        nif_emisor=r"^Emisor:.*?·\s*NIF\s+" + NIF,
        iban=r"^IBAN:\s*" + IBAN,
        pedido=r"Pedido asociado:\s*" + PED,
        base=r"^BASE IMPONIBLE:\s*" + IMP,
        iva=r"^I\.V\.A\.\s*\(" + PCT + r"\s*%\):\s*" + IMP,
        total=r"^IMPORTE TOTAL:\s*" + IMP,
        razon_social=r"^Emisor:\s*(.+?)\s*·\s*NIF\s",
        linea=r"^([^\d\n]+?)\s{2,}(\d+)\s{2,}" + IMP + r"\s*$",
    ),
)

_COMPILADAS = {p.nombre: (p, p.compilada()) for p in PLANTILLAS_DEF}


def normalizar_texto(texto: str) -> str:
    """Quita invisibles y NBSP. No toca el contenido: sólo hace casable lo que se ve igual."""
    return texto.translate(_INVISIBLES).replace("\xa0", " ")


def _grupo(rx: re.Pattern[str], texto: str, n: int = 1) -> str | None:
    m = rx.search(texto)
    return m.group(n).strip() if m else None


def _lineas(rx: re.Pattern[str] | None, texto: str) -> list[LineaFactura]:
    if rx is None:
        return []
    out: list[LineaFactura] = []
    for m in rx.finditer(texto):
        grupos = m.groups()
        concepto = grupos[0].strip()
        if len(grupos) == 3:
            unidades, importe = parse_importe_es(grupos[1]), parse_importe_es(grupos[2])
        else:
            unidades, importe = None, parse_importe_es(grupos[1])
        if importe is None:
            return []  # línea ilegible: mejor sin líneas que con una mal
        out.append(LineaFactura(concepto=concepto, unidades=unidades, importe=importe))
    return out


def _parsear(p: Plantilla, rx: dict[str, re.Pattern[str]], texto: str, file_id: str, sha: str):
    num = _grupo(rx["num_factura"], texto)
    fecha_txt = _grupo(rx["fecha"], texto)
    nif = _grupo(rx["nif_emisor"], texto)
    iban = _grupo(rx["iban"], texto)
    pedido = _grupo(rx["pedido"], texto)
    base = parse_importe_es(_grupo(rx["base"], texto))
    total = parse_importe_es(_grupo(rx["total"], texto))
    m_iva = rx["iva"].search(texto)
    iva_pct = parse_importe_es(m_iva.group(1)) if m_iva else None
    iva = parse_importe_es(m_iva.group(2)) if m_iva else None
    fecha = parse_fecha_es(fecha_txt) if fecha_txt else None

    obligatorios = (num, fecha, nif, iban, pedido, base, iva_pct, iva, total)
    if any(v is None for v in obligatorios):
        return None  # incompleto → que lo mire el LLM

    lineas = _lineas(rx.get("linea"), texto)
    avisos: list[Aviso] = []
    fragmento = instrucciones.detectar_instruccion(texto)
    if fragmento:
        avisos.append(Aviso.TEXTO_INSTRUCCION)
    if instrucciones.menciona_anulacion(texto):
        avisos.append(Aviso.PEDIDO_ANULADO_SEGUN_PDF)
    if fecha_txt and fecha_en_letra(fecha_txt):
        avisos.append(Aviso.FECHA_EN_LETRA)

    return InvoiceFacts(
        file_id=file_id,
        sha256=sha,
        num_factura=num,
        fecha=fecha,
        razon_social=_grupo(rx["razon_social"], texto) if "razon_social" in rx else None,
        nif_emisor=normalizar_nif(nif),
        iban=normalizar_iban(iban),
        pedido=normalizar_pedido(pedido),
        base=base,
        iva_pct=iva_pct,
        iva=iva,
        total=total,
        moneda="EUR",  # las 6 familias imprimen € o EUR
        lineas=lineas,
        metodo=MetodoExtraccion.PLANTILLA,
        extractor_version=EXTRACTOR_VERSION,
        avisos=avisos,
        texto_sospechoso=fragmento,
        confianza=1.0,
    )


def detectar_plantilla(texto: str) -> str | None:
    """Nombre de la familia de maquetación, o None. Sólo para medir cobertura y para los tests."""
    plano = normalizar_texto(texto)
    for nombre, (_p, rx) in _COMPILADAS.items():
        if rx["ancla"].search(plano):
            return nombre
    return None


# nombre → (detector, parser). El parser devuelve None si no consigue TODOS los campos obligatorios.
PLANTILLAS: dict[
    str, tuple[Callable[[str], bool], Callable[[str, str, str], InvoiceFacts | None]]
] = {
    nombre: (
        (lambda t, _rx=rx: bool(_rx["ancla"].search(t))),
        (lambda t, f, s, _p=p, _rx=rx: _parsear(_p, _rx, t, f, s)),
    )
    for nombre, (p, rx) in _COMPILADAS.items()
}


def extraer_por_plantilla(texto: str, *, file_id: str, sha256: str) -> InvoiceFacts | None:
    plano = normalizar_texto(texto)
    for _nombre, (detecta, parsea) in PLANTILLAS.items():
        if detecta(plano):
            return parsea(plano, file_id, sha256)
    return None


def suma_lineas(h: InvoiceFacts) -> Decimal | None:
    """Suma de los importes de línea, o None si alguna línea no lo trae. Lo usa `validadores`."""
    if not h.lineas:
        return None
    total = Decimal("0")
    for linea in h.lineas:
        if linea.importe is None:
            return None
        total += linea.importe
    return total.quantize(CENT)
