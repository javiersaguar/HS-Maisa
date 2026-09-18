"""Parsers deterministas por plantilla, sobre facturas REALES de data/caja (por file_id, sin copiar PDFs).

Dos facturas por familia, con los valores puestos a mano leyendo el PDF. Si un parser empieza a
inventarse un campo, aquí se ve. La cobertura global se mide en `test_cobertura_medida`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from albertitos.core.contracts import Aviso, MetodoExtraccion
from albertitos.extract import pdf
from albertitos.extract.plantillas import (
    PLANTILLAS_DEF,
    detectar_plantilla,
    extraer_por_plantilla,
    suma_lineas,
)

# file_id → (familia, num_factura, fecha, nif, iban, pedido, base, iva_pct, iva, total, n_lineas)
ESPERADO = [
    # familia 1 · moderna (113)
    ("2026-01-23_P006.pdf", "moderna", "FA-8213", date(2026, 1, 23), "A46990201",
     "ES3520385778983000765410", "PO-2026-0195", "4695.67", "21", "986.09", "5681.76", 2),
    # de 2 páginas: base/IVA/total están en la página 2, y la 1 acaba en "Suma y sigue"
    ("2026-01-25_P001.pdf", "moderna", "2026/84946", date(2026, 1, 25), "B46102331",
     "ES2100491500051234567890", "PO-2026-0469", "4808.25", "21", "1009.73", "5817.98", 57),
    # familia 2 · abono (92) · fecha siempre en letra
    ("2026-01-15_P003.pdf", "abono", "F26-9524", date(2026, 1, 15), "B30455812",
     "ES6001825322180201588391", "PO-2026-0070", "6543.49", "21", "1374.13", "7917.62", 3),
    ("FA-1352_catering.pdf", "abono", "FA-1352", date(2026, 1, 9), "B96233419",
     "ES1800815290070001234567", "PO-2026-0118", "5327.88", "21", "1118.85", "6446.73", 1),
    # familia 3 · invoice (91) · importes en formato inglés
    ("2026-01-26_P007.pdf", "invoice", "FA-1480", date(2026, 1, 26), "J40112358",
     "ES5531590012348765123407", "PO-2026-0222", "1409.40", "21", "295.97", "1705.37", 2),
    ("2026-02-07_P002.pdf", "invoice", "FA-7400", date(2026, 2, 7), "A41220987",
     "ES7621000813610123456789", "PO-2026-0148", "3937.13", "21", "826.80", "4763.93", 2),
    # familia 4 · clasica (73)
    ("2026-01-08_P001.pdf", "clasica", "2026/11604", date(2026, 1, 8), "B46102331",
     "ES2100491500051234567890", "PO-2026-0096", "2489.99", "21", "522.90", "3012.89", 1),
    ("2026-01-11_P007.pdf", "clasica", "FA-3566", date(2026, 1, 11), "J40112358",
     "ES5531590012348765123407", "PO-2026-0167", "6574.59", "21", "1380.66", "7955.25", 3),
    # familia 5 · mayusculas (57)
    ("2026-01-14_P002.pdf", "mayusculas", "FA-2954", date(2026, 1, 14), "A41220987",
     "ES7621000813610123456789", "PO-2026-0144", "2452.27", "21", "514.98", "2967.25", 2),
    ("factura_8322.pdf", "mayusculas", "FA-2699", date(2026, 1, 31), "A46990201",
     "ES3520385778983000765410", "PO-2026-0213", "5904.36", "21", "1239.92", "7144.28", 1),
    # familia 6 · simplificada (45)
    ("2026-01-24_P009.pdf", "simplificada", "2026/25704", date(2026, 1, 24), "A46311208",
     "ES8201280011230100044571", "PO-2026-0220", "2301.34", "21", "483.28", "2784.62", 2),
    ("2026-07-28_P008.pdf", "simplificada", "FA-9070", date(2026, 7, 28), "B91455230",
     "ES0900730100510505331902", "PO-2026-0290", "3727.60", "21", "782.80", "4510.40", 1),
]  # fmt: skip


def _hechos(caja, file_id):
    texto = pdf.texto_de(caja / "facturas" / file_id)
    return texto, extraer_por_plantilla(texto, file_id=file_id, sha256="a" * 64)


@pytest.mark.parametrize("fila", ESPERADO, ids=[f[0] for f in ESPERADO])
def test_dos_facturas_reales_por_plantilla(caja, fila):
    fid, familia, num, fecha, nif, iban, pedido, base, pct, iva, total, n_lineas = fila
    texto, h = _hechos(caja, fid)
    assert detectar_plantilla(texto) == familia
    assert h is not None, f"{fid}: la plantilla {familia} no completó los campos"
    assert h.file_id == fid and h.sha256 == "a" * 64
    assert h.num_factura == num
    assert h.fecha == fecha
    assert h.nif_emisor == nif
    assert h.iban == iban
    assert h.pedido == pedido
    assert h.base == Decimal(base)
    assert h.iva_pct == Decimal(pct)
    assert h.iva == Decimal(iva)
    assert h.total == Decimal(total)
    assert len(h.lineas) == n_lineas
    assert h.metodo is MetodoExtraccion.PLANTILLA
    assert h.extractor_version


@pytest.mark.parametrize("fila", ESPERADO, ids=[f[0] for f in ESPERADO])
def test_las_lineas_suman_la_base(caja, fila):
    """Las líneas suman la BASE (no el total). Medido: 468/468 al céntimo en la Caja."""
    _texto, h = _hechos(caja, fila[0])
    assert suma_lineas(h) == h.base


def test_las_seis_familias_estan_cubiertas():
    assert {p.nombre for p in PLANTILLAS_DEF} == {
        "moderna", "abono", "invoice", "clasica", "mayusculas", "simplificada",
    }  # fmt: skip
    assert {f[1] for f in ESPERADO} == {p.nombre for p in PLANTILLAS_DEF}


def test_dos_paginas_toma_el_total_de_la_segunda(caja):
    """La página 1 acaba en `Suma y sigue: 3.413,84 €`; el total de verdad está en la 2."""
    texto, h = _hechos(caja, "2026-01-25_P001.pdf")
    assert pdf.info(caja / "facturas" / "2026-01-25_P001.pdf")[0] == 2
    assert "Suma y sigue: 3.413,84" in texto
    assert h.total == Decimal("5817.98")
    assert h.base + h.iva == h.total


def test_fecha_imposible_no_se_completa_ni_se_inventa(caja):
    """31/02/2026: el parser devuelve None y el fichero se va al LLM. Nunca un 28/02 inventado.

    Las dos de la familia `abono` llevan además la instrucción de sustituir la fecha: la frase se
    recoge como evidencia, no se obedece.
    """
    for fid in ("2026-03-19_P008.pdf", "FA-1123_construcciones.pdf", "FA-2967_seguridad.pdf"):
        texto, h = _hechos(caja, fid)
        assert detectar_plantilla(texto) is not None, fid
        assert h is None, f"{fid}: con fecha imposible no puede salir un InvoiceFacts completo"


def test_el_nif_del_cliente_no_se_cuela_como_emisor(caja):
    """Todas las facturas llevan `CIF: A58231074` (Banco Miralmar). No es el emisor."""
    for fid, *_ in ESPERADO:
        _texto, h = _hechos(caja, fid)
        assert h.nif_emisor != "A58231074", fid


def test_la_plantilla_recoge_la_instruccion_como_evidencia(caja):
    """El texto es un dato: la plantilla extrae campos y adjunta la frase como prueba."""
    _texto, h = _hechos(caja, "FA-5590_ofimática.pdf")
    assert Aviso.TEXTO_INSTRUCCION in h.avisos
    assert h.texto_sospechoso and "regimen especial" in h.texto_sospechoso
    assert h.base == Decimal("2500.00") and h.iva == Decimal("400.00")  # los hechos, sin "corregir"
    assert not hasattr(h, "resultado")


def test_cobertura_medida(caja):
    """Cobertura de las 471 con capa de texto. Si baja, es que un parser ha dejado de cubrir."""
    completas = por_familia = 0
    familias: dict[str, int] = {}
    for ruta in sorted((caja / "facturas").iterdir()):
        if not pdf.info(ruta)[1]:
            continue
        texto = pdf.texto_de(ruta)
        familia = detectar_plantilla(texto)
        if familia is None:
            continue
        por_familia += 1
        familias[familia] = familias.get(familia, 0) + 1
        h = extraer_por_plantilla(texto, file_id=ruta.name, sha256="a" * 64)
        if h is not None:
            completas += 1
    assert por_familia == 471, f"familia reconocida en {por_familia}, esperaba 471"
    assert familias == {
        "moderna": 113, "abono": 92, "invoice": 91,
        "clasica": 73, "mayusculas": 57, "simplificada": 45,
    }  # fmt: skip
    assert completas == 468, f"{completas} completas, medidas 468 el 18/09"
