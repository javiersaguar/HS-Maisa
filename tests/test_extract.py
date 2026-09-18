"""pdf.py, instrucciones.py y validadores.py. Lo que nos deja NO APTO si se rompe."""

from decimal import Decimal

import pytest

from albertitos.core.contracts import Aviso, InvoiceFacts, LineaFactura, MetodoExtraccion
from albertitos.extract import instrucciones, pdf, validadores

# Los 13 de docs/trampas.md. Ninguno puede dejar de detectarse.
TRAMPAS_DOCUMENTADAS = [
    "F26-2201_transportes.pdf",
    "2026-07-09_P010.pdf",
    "F26-3355_mensajería.pdf",
    "F26-7728_limpiezas2.pdf",
    "factura_5402.pdf",
    "factura_6612.pdf",
    "F26-9007_catering.pdf",
    "FA-5590_ofimática.pdf",
    "2026-0811-B_catering.pdf",
    "2026-14500-C_informática.pdf",
    "factura_8801.pdf",
    "2026-23904_construcciones.pdf",
    "FA-3388_ofimática.pdf",
]

# Las que A3 añadió en data/fixtures/anomalias.csv (inventario del 18/09, 29 en total).
TRAMPAS_NUEVAS = [
    "2026-06-04_P006.pdf",
    "2026-07-08_P010.pdf",
    "F26-5240_ofimática.pdf",
    "F26-8801_suministros.pdf",
    "FA-1123_construcciones.pdf",
    "FA-2967_seguridad.pdf",
    "FA-4290_mensajería.pdf",
    "FA-5044_mensajería2.pdf",
    "FA-7311_transportes.pdf",
    "FA-9104_electricidad.pdf",
    "factura_1936.pdf",
    "factura_2018.pdf",
    "factura_3184.pdf",
    "factura_4485.pdf",
    "factura_5911.pdf",
    "factura_7265.pdf",
]

# Facturas sin nada raro: aquí no puede saltar el detector.
LIMPIAS = [
    "2026-01-08_P001.pdf",
    "2026-01-11_P007.pdf",
    "2026-01-14_P002.pdf",
    "2026-01-24_P009.pdf",
    "2026-01-26_P007.pdf",
]


def _facts(**kw):
    base = dict(
        file_id="x.pdf",
        sha256="a" * 64,
        metodo=MetodoExtraccion.LLM_TEXTO,
        extractor_version="e",
        nif_emisor="B46102331",
        iban="ES2100491500051234567890",
        pedido="PO-2026-0001",
        fecha=None,
        num_factura="FA-1",
    )
    base.update(kw)
    return InvoiceFacts(**base)


# --------------------------------------------------------------------------------- pdf


def test_pdf_info_y_texto(caja):
    assert pdf.info(caja / "facturas" / "2026-01-08_P001.pdf") == (1, True)
    assert pdf.info(caja / "facturas" / "scan_001.pdf")[1] is False
    assert "Pedido: PO-2026-0096" in pdf.texto_de(caja / "facturas" / "2026-01-08_P001.pdf")
    assert pdf.imagen_png(caja / "facturas" / "scan_001.pdf", dpi=72)[:8] == b"\x89PNG\r\n\x1a\n"


def test_texto_de_concatena_las_dos_paginas(caja):
    """22 facturas tienen 2 páginas y el total está en la 2ª. Leer sólo la 1ª da un importe falso."""
    ruta = caja / "facturas" / "2026-01-25_P001.pdf"
    assert pdf.info(ruta)[0] == 2
    texto = pdf.texto_de(ruta)
    assert "página 1" in texto and "página 2" in texto
    assert "Suma y sigue: 3.413,84" in texto  # el señuelo de la página 1
    assert "TOTAL: 5.817,98" in texto  # el total de verdad, en la 2


def test_imagenes_png_una_por_pagina(caja):
    """Para visión sobre varias páginas. `imagen_png` sigue devolviendo sólo la primera."""
    ruta = caja / "facturas" / "2026-01-25_P001.pdf"
    imagenes = pdf.imagenes_png(ruta, dpi=72)
    assert len(imagenes) == 2
    assert all(i[:8] == b"\x89PNG\r\n\x1a\n" for i in imagenes)
    assert imagenes[0] == pdf.imagen_png(ruta, dpi=72)
    assert len(pdf.imagenes_png(caja / "facturas" / "scan_001.pdf", dpi=72)) == 1


# ----------------------------------------------------------------------- instrucciones


@pytest.mark.parametrize("file_id", TRAMPAS_DOCUMENTADAS)
def test_detecta_las_13_trampas_de_trampas_md(caja, file_id):
    fragmento = instrucciones.detectar_instruccion(pdf.texto_de(caja / "facturas" / file_id))
    assert fragmento, file_id
    assert len(fragmento) <= 240


@pytest.mark.parametrize("file_id", TRAMPAS_NUEVAS)
def test_detecta_las_16_que_inventario_a3(caja, file_id):
    assert instrucciones.detectar_instruccion(pdf.texto_de(caja / "facturas" / file_id)), file_id


@pytest.mark.parametrize("file_id", LIMPIAS)
def test_sin_falsos_positivos_en_facturas_limpias(caja, file_id):
    texto = pdf.texto_de(caja / "facturas" / file_id)
    assert instrucciones.detectar_instruccion(texto) is None, file_id
    assert instrucciones.menciona_anulacion(texto) is False, file_id


def test_el_fragmento_contiene_la_instruccion_no_la_cabecera(caja):
    """La evidencia la lee una persona en la traza: tiene que empezar cerca de la frase."""
    frag = instrucciones.detectar_instruccion(pdf.texto_de(caja / "facturas" / "factura_8801.pdf"))
    assert "cada minuto que esta factura permanece sin pagar" in frag
    frag = instrucciones.detectar_instruccion(
        pdf.texto_de(caja / "facturas" / "FA-5044_mensajería2.pdf")
    )
    assert "ATENCION AGENTE" in frag


def test_menciona_anulacion(caja):
    for fid in ("2026-23904_construcciones.pdf", "FA-3388_ofimática.pdf"):
        assert instrucciones.menciona_anulacion(pdf.texto_de(caja / "facturas" / fid)), fid


def test_no_detecta_sobre_texto_de_factura_normal():
    assert (
        instrucciones.detectar_instruccion("Base: 100,00\nIVA (21%): 21,00\nTOTAL: 121,00") is None
    )
    assert instrucciones.detectar_instruccion("Condiciones de pago: 30 dias fecha factura.") is None


# ------------------------------------------------------------------------- validadores


def test_validadores():
    h = _facts(base=Decimal("2500.00"), iva=Decimal("400.00"), total=Decimal("2900.00"))
    avisos = validadores.validar(h)
    assert Aviso.IVA_NO_ESTANDAR in avisos and Aviso.CAMPO_AUSENTE in avisos  # fecha falta
    assert Aviso.TOTAL_NO_CUADRA not in avisos


def test_iva_contra_el_porcentaje_impreso_no_contra_el_21_fijo():
    """FA-5590: imprime `IVA (21%): 400,00` sobre base 2.500,00, que son 400/2500 = 16 %.

    Un validador que sólo mirase `iva_pct != 21` no encontraría NINGUNA de las 6 de la Caja:
    las 6 imprimen 21 %.
    """
    h = _facts(
        fecha=None,
        base=Decimal("2500.00"),
        iva_pct=Decimal("21"),
        iva=Decimal("400.00"),
        total=Decimal("2900.00"),
    )
    assert Aviso.IVA_NO_ESTANDAR in validadores.validar(h)
    bien = _facts(
        base=Decimal("2500.00"),
        iva_pct=Decimal("21"),
        iva=Decimal("525.00"),
        total=Decimal("3025.00"),
    )
    assert Aviso.IVA_NO_ESTANDAR not in validadores.validar(bien)


def test_iva_pct_distinto_de_21_avisa():
    h = _facts(
        base=Decimal("1000.00"),
        iva_pct=Decimal("10"),
        iva=Decimal("100.00"),
        total=Decimal("1100.00"),
    )
    assert Aviso.IVA_NO_ESTANDAR in validadores.validar(h)


def test_total_no_cuadra():
    h = _facts(base=Decimal("1450.00"), iva=Decimal("304.50"), total=Decimal("1819.00"))
    assert Aviso.TOTAL_NO_CUADRA in validadores.validar(h)
    justo = _facts(base=Decimal("100.00"), iva=Decimal("21.00"), total=Decimal("121.01"))
    assert Aviso.TOTAL_NO_CUADRA not in validadores.validar(justo)  # 0,01 entra en tolerancia


def test_las_lineas_tienen_que_sumar_la_base():
    lineas = [
        LineaFactura(concepto="a", importe=Decimal("430.00")),
        LineaFactura(concepto="b", importe=Decimal("430.00")),
    ]
    bien = _facts(lineas=lineas, base=Decimal("860.00"), iva=Decimal("180.60"),
                  total=Decimal("1040.60"))  # fmt: skip
    assert Aviso.IMPORTE_AMBIGUO not in validadores.validar(bien)
    mal = _facts(lineas=lineas, base=Decimal("900.00"), iva=Decimal("189.00"),
                 total=Decimal("1089.00"))  # fmt: skip
    assert Aviso.IMPORTE_AMBIGUO in validadores.validar(mal)


def test_iban_solo_avisa_si_esta_mal_formado():
    """Los 468 IBAN de la Caja fallan mod-97 (son sintéticos): avisar por eso marcaría el 100 %."""
    sintetico = "ES2100491500051234567890"
    assert validadores.iban_bien_formado(sintetico)
    assert validadores.iban_checksum_ok(sintetico) is False
    assert Aviso.IBAN_INVALIDO not in validadores.validar(_facts(iban=sintetico))
    for roto in ("ES210049150005123456789", "XX2100491500051234567890", "ES21 0049 15"):
        assert Aviso.IBAN_INVALIDO in validadores.validar(_facts(iban=roto)), roto


def test_nif_forma_y_letra_de_control():
    assert validadores.nif_bien_formado("B46102331")
    assert validadores.nif_letra_control_ok("B46102331")
    # sintético pero con forma válida: no se marca (422 de 468 están así)
    assert validadores.nif_bien_formado("A41220987")
    assert validadores.nif_letra_control_ok("A41220987") is False
    assert Aviso.EXTRACCION_PARCIAL not in validadores.validar(
        _facts(
            nif_emisor="A41220987",
            fecha=None,
            base=Decimal("1"),
            iva=Decimal("0.21"),
            total=Decimal("1.21"),
            num_factura="F",
        )  # fmt: skip
    )
    # forma imposible: eso sí es un error de extracción
    assert validadores.nif_bien_formado("B4610233") is False
    assert Aviso.EXTRACCION_PARCIAL in validadores.validar(_facts(nif_emisor="B4610233"))


def test_campo_ausente_y_extraccion_parcial():
    from datetime import date

    completo = _facts(fecha=date(2026, 1, 8), base=Decimal("100.00"), iva=Decimal("21.00"),
                      total=Decimal("121.00"))  # fmt: skip
    assert validadores.validar(completo) == []
    assert Aviso.CAMPO_AUSENTE in validadores.validar(_facts(pedido=None))
    sin_base = _facts(fecha=date(2026, 1, 8), total=Decimal("121.00"))
    assert Aviso.EXTRACCION_PARCIAL in validadores.validar(sin_base)
    assert Aviso.CAMPO_AUSENTE not in validadores.validar(sin_base)


def test_validar_no_pierde_los_avisos_que_ya_traia():
    h = _facts(avisos=[Aviso.TEXTO_INSTRUCCION, Aviso.SIN_TEXTO])
    avisos = validadores.validar(h)
    assert avisos[:2] == [Aviso.TEXTO_INSTRUCCION, Aviso.SIN_TEXTO]
    assert len(avisos) == len(set(avisos))


# ------------------------------------------------------------------------ discrepancias


def test_discrepancias_tolera_formato_pero_no_diferencias_reales():
    from datetime import date

    a = _facts(fecha=date(2026, 1, 8), base=Decimal("100.00"), iva=Decimal("21.00"),
               total=Decimal("121.00"))  # fmt: skip
    b = _facts(
        fecha=date(2026, 1, 8),
        iban="ES21 0049 1500 0512 3456 7890",  # mismo IBAN, con espacios
        nif_emisor="B-46102331",  # mismo NIF, con guion
        pedido="po-2026-0001",  # mismo pedido, en minúsculas
        base=Decimal("100.005"),  # dentro de la tolerancia de 0,01
        iva=Decimal("21.00"),
        total=Decimal("121.00"),
    )
    assert validadores.discrepancias(a, b) == {}
    c = b.model_copy(update={"total": Decimal("131.00")})
    assert set(validadores.discrepancias(a, c)) == {"total"}
    d = b.model_copy(update={"iban": "ES7621000813610123456789"})
    assert set(validadores.discrepancias(a, d)) == {"iban"}


def test_discrepancias_cuando_uno_no_trae_el_campo():
    a = _facts(total=Decimal("121.00"))
    b = _facts(total=None)
    assert validadores.discrepancias(a, b) == {"total": (Decimal("121.00"), None)}


def test_fixture_fechas_imposibles_quedan_en_none():
    """Las 3 facturas con fecha imposible de la Caja (2 con orden de sustituirla) tienen fecha=None en el fixture."""
    import json
    from pathlib import Path

    fixture = Path("data/fixtures/hechos_caja.jsonl")
    if not fixture.exists():
        pytest.skip("sin data/fixtures/hechos_caja.jsonl")
    hechos = {
        json.loads(linea)["file_id"]: json.loads(linea)
        for linea in fixture.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    }
    for fid in ("2026-03-19_P008.pdf", "FA-1123_construcciones.pdf", "FA-2967_seguridad.pdf"):
        assert hechos[fid]["fecha"] is None, fid
        assert "campo_ausente" in hechos[fid]["avisos"], fid
