from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from albertitos.core.contracts import (
    Aviso,
    Decision,
    InvoiceFacts,
    MetodoExtraccion,
    Motivo,
    Outcome,
    Resultado,
)


def hechos(**kw) -> InvoiceFacts:
    base = dict(
        file_id="f.pdf",
        sha256="x" * 64,
        metodo=MetodoExtraccion.LLM_TEXTO,
        extractor_version="ext-0.1",
        total=Decimal("10.00"),
    )
    base.update(kw)
    return InvoiceFacts(**base)


def test_outcome_rechaza_nfd():
    nfd = "FA-4290_mensajería.pdf"
    with pytest.raises(ValidationError, match="NFC"):
        Outcome(file_id=nfd, result=Resultado.PAGAR)
    assert (
        Outcome(file_id="FA-4290_mensajería.pdf", result="PAGAR").linea()
        == '{"file_id":"FA-4290_mensajería.pdf","result":"PAGAR"}'
    )


def test_outcome_rechaza_campos_extra_y_rutas():
    with pytest.raises(ValidationError):
        Outcome(file_id="a.pdf", result="PAGAR", sha256="abc")
    with pytest.raises(ValidationError):
        Outcome(file_id="data/caja/a.pdf", result="PAGAR")
    with pytest.raises(ValidationError):
        Outcome(file_id="a.pdf", result="PAGAR_YA")


def test_invoice_facts_no_admite_decision():
    with pytest.raises(ValidationError):
        hechos(resultado="PAGAR")
    with pytest.raises(ValidationError):
        hechos(decision="ESCALAR")


def test_invoice_facts_normaliza_file_id_a_nfc():
    h = hechos(file_id="FA-1_ofimática.pdf")
    assert h.file_id == "FA-1_ofimática.pdf"


def test_hash_ignora_metodo_y_confianza_pero_no_los_hechos():
    a = hechos(metodo=MetodoExtraccion.LLM_TEXTO, confianza=0.9)
    b = hechos(metodo=MetodoExtraccion.CACHE, confianza=0.1)
    c = hechos(total=Decimal("10.01"))
    assert a.hash() == b.hash()
    assert a.hash() != c.hash()


def test_decision_motivo_principal():
    d = Decision(
        file_id="f.pdf",
        sha256="x" * 64,
        resultado=Resultado.ESCALAR,
        motivos=[
            Motivo(regla_id="v3.R1", ok=True, detalle="ok"),
            Motivo(regla_id="v3.R2", ok=False, detalle="pedido no existe"),
        ],
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        hechos_hash="h",
        maestro_version="m",
        erp_version="e",
        decidido_en=datetime.now(UTC),
    )
    assert d.motivo_principal == "v3.R2: pedido no existe"
    assert d.reglas_incumplidas == ["v3.R2"]


def test_contratos_v1_compatibles_hacia_atras():
    # hechos guardados antes de NIF_INVALIDO siguen cargando; el aviso nuevo cambia el hash (linaje)
    antiguo = hechos(avisos=[Aviso.IBAN_INVALIDO])
    recargado = InvoiceFacts.model_validate_json(antiguo.model_dump_json())
    assert recargado.hash() == antiguo.hash()
    nuevo = hechos(avisos=[Aviso.IBAN_INVALIDO, Aviso.NIF_INVALIDO])
    assert nuevo.hash() != antiguo.hash()
    superpuesto = hechos(avisos=[Aviso.SIN_TEXTO, Aviso.DOCUMENTO_SUPERPUESTO])
    assert InvoiceFacts.model_validate_json(superpuesto.model_dump_json()) == superpuesto
    assert Aviso("documento_superpuesto") is Aviso.DOCUMENTO_SUPERPUESTO
    # decidido_en ya no es obligatorio: la norma no lo pone, lo sella core.db
    d = Decision(
        file_id="f.pdf",
        sha256="x" * 64,
        resultado=Resultado.PAGAR,
        motivos=[],
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        hechos_hash="h",
        maestro_version="m",
        erp_version="e",
    )
    assert d.decidido_en is None
