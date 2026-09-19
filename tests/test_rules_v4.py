"""Norma v4 (lote 2, ADR-0022): la v3 más R7, la moneda. Sin la regla publicada, la divisa escala con su motivo."""

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
from albertitos.rules import REGISTRO, norma_v3, norma_v4


def hechos(**kw) -> InvoiceFacts:
    """La factura perfecta de test_rules.py (P001, PO-2026-0001, 3.012,89 €)."""
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


CTX = ContextoDecision(
    norma_version="v4",
    fecha_corte=date(2026, 9, 18),
    maestro_version="m-test",
    erp_version="e-test",
)
# 3.274,88 USD × 0,92 = 3.012,89 EUR: el pedido PO-2026-0001 y su asiento del ERP de conftest.
EN_USD = dict(
    moneda="USD", base=Decimal("2706.51"), iva=Decimal("568.37"), total=Decimal("3274.88")
)


def test_registro():
    assert REGISTRO["v4"] is norma_v4


@pytest.mark.parametrize("moneda", [None, "EUR"])
def test_en_euros_decide_igual_que_la_v3(maestro, erp, moneda):
    h = hechos(moneda=moneda)
    d3, d4 = norma_v3.decidir(h, maestro, erp, CTX), norma_v4.decidir(h, maestro, erp, CTX)
    assert d4.resultado == d3.resultado == Resultado.PAGAR
    assert all(m.regla_id.startswith("v4.") for m in d4.motivos)
    assert [m.regla_id for m in d4.motivos] == [f"v4.R{n}" for n in (1, 7, 2, 3, 4, 5, 6)]


def test_en_divisa_sin_tipo_escala_por_la_moneda(maestro, erp):
    """e02: 2.450 USD contra un pedido en EUR. El motivo es la divisa, no «el total no coincide»."""
    d = norma_v4.decidir(hechos(**EN_USD), maestro, erp, CTX)
    assert d.resultado == Resultado.ESCALAR
    assert d.motivo_principal.startswith(
        "v4.R7: factura en USD (el pedido PO-2026-0001 está en EUR"
    )
    r7 = next(m for m in d.motivos if m.regla_id == "v4.R7")
    assert r7.evidencia["tipo_implicito"] == "0.92000"


def test_en_divisa_con_tipo_se_compara_convertida(maestro, erp, monkeypatch):
    monkeypatch.setattr(norma_v4, "TIPOS_CAMBIO", {"USD": Decimal("0.92")})
    d = norma_v4.decidir(hechos(**EN_USD), maestro, erp, CTX)
    assert d.resultado == Resultado.PAGAR, d.motivo_principal


def test_el_redondeo_del_tipo_no_escala_pero_un_importe_distinto_si(maestro, erp, monkeypatch):
    """El redondeo del tipo mueve céntimos (BRL: 15.500 × 0,1613 = 2.500,15 frente a 2.500,00): R2 lo admite
    dentro de la tolerancia relativa; un importe que no es el del pedido, no."""
    monkeypatch.setattr(norma_v4, "TIPOS_CAMBIO", {"USD": Decimal("0.9201")})  # 3.013,22 €: +0,33
    r2 = next(
        m
        for m in norma_v4.decidir(hechos(**EN_USD), maestro, erp, CTX).motivos
        if m.regla_id == "v4.R2"
    )
    assert r2.ok, r2.detalle
    assert norma_v4.decidir(hechos(**EN_USD), maestro, erp, CTX).resultado == Resultado.PAGAR
    monkeypatch.setattr(
        norma_v4, "TIPOS_CAMBIO", {"USD": Decimal("1.00")}
    )  # 3.274,88 €: otro importe
    d = norma_v4.decidir(hechos(**EN_USD), maestro, erp, CTX)
    assert d.resultado == Resultado.ESCALAR and "v4.R2" in d.reglas_incumplidas


def test_la_v4_mantiene_lo_de_la_v3(maestro, erp):
    """Anotación a mano (e18) y pedido ya pagado (2026-08-22_P010) deciden como en la v3."""
    assert norma_v4.decidir(
        hechos(avisos=[Aviso.ANOTACION_A_MANO]), maestro, erp, CTX
    ).resultado == (Resultado.ESCALAR)
    pagada = hechos(
        pedido="PO-2026-0009", total=Decimal("100.00"), base=Decimal("82.64"), iva=Decimal("17.36")
    )
    assert norma_v4.decidir(pagada, maestro, erp, CTX).resultado == Resultado.NO_PAGAR
