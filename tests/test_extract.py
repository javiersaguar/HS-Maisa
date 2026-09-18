from decimal import Decimal

from albertitos.core.contracts import Aviso, InvoiceFacts, MetodoExtraccion
from albertitos.extract import instrucciones, pdf, validadores


def test_pdf_info_y_texto(caja):
    assert pdf.info(caja / "facturas" / "2026-01-08_P001.pdf") == (1, True)
    assert pdf.info(caja / "facturas" / "scan_001.pdf")[1] is False
    assert "Pedido: PO-2026-0096" in pdf.texto_de(caja / "facturas" / "2026-01-08_P001.pdf")
    assert pdf.imagen_png(caja / "facturas" / "scan_001.pdf", dpi=72)[:8] == b"\x89PNG\r\n\x1a\n"


def test_detecta_instrucciones_reales(caja):
    con = [
        "F26-2201_transportes.pdf",
        "2026-07-09_P010.pdf",
        "F26-9007_catering.pdf",
        "FA-5590_ofimática.pdf",
        "2026-0811-B_catering.pdf",
        "factura_8801.pdf",
    ]
    for f in con:
        frag = instrucciones.detectar_instruccion(pdf.texto_de(caja / "facturas" / f))
        assert frag, f
    assert (
        instrucciones.detectar_instruccion(pdf.texto_de(caja / "facturas" / "2026-01-08_P001.pdf"))
        is None
    )
    assert instrucciones.menciona_anulacion(
        pdf.texto_de(caja / "facturas" / "2026-23904_construcciones.pdf")
    )


def test_validadores():
    h = InvoiceFacts(
        file_id="x.pdf",
        sha256="a" * 64,
        metodo=MetodoExtraccion.LLM_TEXTO,
        extractor_version="e",
        nif_emisor="B1",
        iban="ES2100491500051234567890",
        pedido="PO",
        base=Decimal("2500.00"),
        iva=Decimal("400.00"),
        total=Decimal("2900.00"),
    )
    avisos = validadores.validar(h)
    assert Aviso.IVA_NO_ESTANDAR in avisos and Aviso.CAMPO_AUSENTE in avisos  # fecha falta
    assert Aviso.TOTAL_NO_CUADRA not in avisos
