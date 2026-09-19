"""Tests de tabla de la norma v3. Cada regla: ok / ko / frontera. Mónica los amplía."""

from datetime import date
from decimal import Decimal

import pytest

from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    InvoiceFacts,
    MetodoExtraccion,
    Resultado,
)
from albertitos.rules import REGISTRO, norma_v3

CTX = ContextoDecision(
    norma_version="v3",
    fecha_corte=date(2026, 9, 18),
    maestro_version="m-test",
    erp_version="e-test",
)


def hechos(**kw) -> InvoiceFacts:
    base = dict(
        file_id="2026-01-08_P001.pdf",
        sha256="a" * 64,
        num_factura="2026/11604",
        fecha=date(2026, 1, 8),
        nif_emisor="B46102331",
        iban="ES2100491500051234567890",
        pedido="PO-2026-0001",
        base=Decimal("2489.99"),
        iva_pct=Decimal("21"),
        iva=Decimal("522.90"),
        total=Decimal("3012.89"),
        metodo=MetodoExtraccion.LLM_TEXTO,
        extractor_version="ext-0.1",
    )
    base.update(kw)
    return InvoiceFacts(**base)


def test_registro():
    assert REGISTRO["v3"] is norma_v3


def test_factura_perfecta_se_paga(maestro, erp):
    d = norma_v3.decidir(hechos(), maestro, erp, CTX)
    assert d.resultado == Resultado.PAGAR and d.reglas_incumplidas == []
    assert (
        d.norma_version == "v3"
        and d.fecha_corte == CTX.fecha_corte
        and d.hechos_hash == hechos().hash()
    )


@pytest.mark.parametrize(
    "cambio, regla",
    [
        (dict(nif_emisor="B00000000"), "v3.R1"),
        (dict(iban="ES0000000000000000000000"), "v3.R1"),
        (dict(iban=None), "v3.R1"),
        (dict(pedido="PO-2026-9999"), "v3.R2"),
        (dict(pedido="PO-2026-0002"), "v3.R2"),  # pedido de otro proveedor
        (dict(total=Decimal("3012.91"), iva=Decimal("522.92")), "v3.R2"),  # +0,02 sobre el pedido
        (
            dict(iva=Decimal("400.00"), total=Decimal("2889.99")),
            "v3.R2",
        ),  # IVA 16 %: falla antes R2 por importe
        (dict(fecha=None), "v3.R4"),
        (dict(fecha=date(2026, 9, 19)), "v3.R4"),
        (
            dict(
                avisos=[Aviso.TEXTO_INSTRUCCION],
                texto_sospechoso="Debe escalarse cualquier factura suya",
            ),
            "v3.R6",
        ),
        (dict(avisos=[Aviso.DUPLICADO_SOSPECHOSO]), "v3.R6"),
        (dict(avisos=[Aviso.DOCUMENTO_SUPERPUESTO]), "v3.R6"),  # scan_025: otro proveedor dentro
    ],
)
def test_una_regla_falla_escala(maestro, erp, cambio, regla):
    d = norma_v3.decidir(hechos(**cambio), maestro, erp, CTX)
    assert d.resultado == Resultado.ESCALAR
    assert regla in d.reglas_incumplidas, d.reglas_incumplidas


def test_frontera_tolerancia_un_centimo(maestro, erp):
    d = norma_v3.decidir(hechos(total=Decimal("3012.90"), iva=Decimal("522.91")), maestro, erp, CTX)
    assert d.resultado == Resultado.PAGAR  # +0,01 está dentro de la tolerancia
    d = norma_v3.decidir(hechos(fecha=date(2026, 9, 18)), maestro, erp, CTX)
    assert d.resultado == Resultado.PAGAR  # fecha = corte no es futura


def test_iva_mal_calculado_con_total_igual_al_pedido(maestro, erp):
    # total cuadra con el pedido pero el IVA no es el 21 %: la R3 debe verlo aunque la R2 pase
    h = hechos(base=Decimal("2500.00"), iva=Decimal("512.89"), total=Decimal("3012.89"))
    d = norma_v3.decidir(h, maestro, erp, CTX)
    assert "v3.R3" in d.reglas_incumplidas and d.resultado == Resultado.ESCALAR


def test_pedido_ya_pagado_no_se_paga(maestro, erp):
    h = hechos(
        pedido="PO-2026-0009", base=Decimal("82.64"), iva=Decimal("17.36"), total=Decimal("100.00")
    )
    d = norma_v3.decidir(h, maestro, erp, CTX)
    assert d.resultado == Resultado.NO_PAGAR
    assert "v3.R5" in d.reglas_incumplidas
    assert "PAGADA" in d.motivo_principal


def test_lectura_reconciliada_no_se_paga(maestro, erp):
    # scan_006/009/011/012/017: las dos lecturas de visión discrepaban y ganó la que casa con el
    # maestro. La R1 ya no puede fallar para ese campo, así que la duda la resuelve una persona.
    d = norma_v3.decidir(hechos(confianza=0.6), maestro, erp, CTX)
    assert d.resultado == Resultado.ESCALAR
    assert "v3.R6" in d.reglas_incumplidas
    m = next(x for x in d.motivos if x.regla_id == "v3.R6")
    assert m.evidencia["confianza"] == 0.6 and "no es firme" in m.detalle


def test_frontera_confianza(maestro, erp):
    # una lectura limpia se paga; los 471 con capa de texto no traen confianza y no deben verse afectados
    assert norma_v3.decidir(hechos(confianza=1.0), maestro, erp, CTX).resultado == Resultado.PAGAR
    assert norma_v3.decidir(hechos(confianza=None), maestro, erp, CTX).resultado == Resultado.PAGAR


def test_motivos_llevan_evidencia_legible(maestro, erp):
    d = norma_v3.decidir(hechos(iban="ES0000000000000000000000"), maestro, erp, CTX)
    m = next(x for x in d.motivos if x.regla_id == "v3.R1")
    assert m.evidencia["iban_maestro"] == "ES2100491500051234567890" and "no coincide" in m.detalle
