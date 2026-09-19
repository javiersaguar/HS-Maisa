from datetime import date
from decimal import Decimal

import pytest

from albertitos.formatos import (
    fecha_en_letra,
    iban_valido,
    normalizar_iban,
    normalizar_nif,
    parse_fecha_es,
    parse_importe_es,
)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("12.874,40", "12874.40"),
        ("2.489,99", "2489.99"),
        ("943,80 €", "943.80"),
        ("EUR 1705.37", "1705.37"),
        ("1705.37", "1705.37"),
        ("1.705", "1705.00"),
        ("390,00", "390.00"),
        ("0,00", "0.00"),
        ("1.234.567,89", "1234567.89"),
        ("12,874.40", "12874.40"),
        (3012.89, "3012.89"),
        ("", None),
        ("n/a", None),
        (None, None),
    ],
)
def test_parse_importe_es(texto, esperado):
    v = parse_importe_es(texto)
    assert v == (None if esperado is None else Decimal(esperado))


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("08/01/2026", date(2026, 1, 8)),
        ("Fecha: 07/03/2026   Pedido", date(2026, 3, 7)),
        ("2026-01-08", date(2026, 1, 8)),
        ("15 de enero de 2026", date(2026, 1, 15)),
        ("15 de Enero del 2026", date(2026, 1, 15)),
        ("8 ene 2026", date(2026, 1, 8)),
        ("3 de septiembre de 2026", date(2026, 9, 3)),
        ("31/02/2026", None),
        ("ayer", None),
        (None, None),
    ],
)
def test_parse_fecha_es(texto, esperado):
    assert parse_fecha_es(texto) == esperado


def test_fecha_en_letra():
    assert fecha_en_letra("Fecha de emisión: 15 de enero de 2026")
    assert not fecha_en_letra("Fecha: 15/01/2026")


def test_iban():
    assert normalizar_iban("es21 0049 1500 0512 3456 7890") == "ES2100491500051234567890"
    assert iban_valido("GB82 WEST 1234 5698 7654 32")
    assert not iban_valido("ES21 0049 1500 0512 3456 789")  # 23 caracteres
    assert not iban_valido("XX00")


def test_nif():
    assert normalizar_nif(" b-46.102 331 ") == "B46102331"


# --------------------------------------------------------------------------- lote 2: identificadores extranjeros
# Proveedores nuevos del lote 2 (proveedores_nuevos.csv, commit f831e34): P012 DE, P013 FR, P014 BR, P015 JP.


@pytest.mark.parametrize(
    "iban, forma, mod97",
    [
        ("DE89 3704 0044 0532 0130 00", True, True),  # P012: forma y control buenos
        ("GB29 NWBK 6016 1331 9268 19", True, True),  # el de ejemplo del registro
        ("FR76 3000 4000 3000 0000 1234 567", True, False),  # P013: forma buena, control sintético
        ("BR97 0036 0305 0000 1000 9795 493C1", True, False),  # P014: acaba en letra + cifra
        (
            "BR97 0036 0305 0000 1000 9795 493P1",
            True,
            True,
        ),  # el del registro: alfanumérico y válido
        ("ES21 0049 1500 0512 3456 7890", True, False),  # la Caja: sintético, igual que antes
        ("JP01 0001 2331 2345 6789 012", False, False),  # P015: Japón no usa IBAN
        ("DE89 3704 0044 0532 0130 0", False, False),  # un carácter menos
        ("XX00 1234 5678 9012 3456", False, False),
        ("ES21 0049 1500 0512 3456 78!0", False, False),
    ],
)
def test_iban_por_pais_longitud_y_mod97(iban, forma, mod97):
    from albertitos.formatos import iban_bien_formado

    assert iban_bien_formado(iban) is forma
    assert iban_valido(iban) is mod97  # nunca lanza, tampoco con un país sin IBAN


@pytest.mark.parametrize(
    "nif, tipo",
    [
        ("DE812345678", "vat_ue"),  # P012
        ("FR40303265045", "vat_ue"),  # P013
        ("GB 123 4567 89", "vat_ue"),
        ("12.345.678/0001-95", "cnpj"),  # P014
        ("5010401075570", "jp"),  # P015
        ("T5010401075570", "jp"),  # con la T del registro de facturas japonés
        ("B46102331", None),  # español: no es extranjero
        ("B4610233", None),  # español roto: tampoco (sigue siendo NIF_INVALIDO)
        ("DE81234567", None),  # alemán con una cifra menos
    ],
)
def test_identificador_extranjero(nif, tipo):
    from albertitos.formatos import identificador_extranjero, tipo_identificador_extranjero

    assert tipo_identificador_extranjero(nif) == tipo
    assert identificador_extranjero(nif) is (tipo is not None)


def test_cnpj_y_su_barra():
    from albertitos.formatos import cnpj_valido

    assert normalizar_nif("12.345.678/0001-95") == "12345678000195"  # PDF y maestro casan
    assert cnpj_valido("12.345.678/0001-95")
    assert not cnpj_valido("12.345.678/0001-96")
    assert not cnpj_valido("11.111.111/1111-11")  # todos iguales: no vale aunque cuadre el módulo


def test_un_nif_extranjero_no_es_un_nif_invalido():
    """Sin esto, NIF_INVALIDO (anomalía que escala, R6) haría escalar una factura extranjera que cuadra en todo."""
    from albertitos.core.contracts import Aviso, InvoiceFacts, MetodoExtraccion
    from albertitos.extract import validadores

    def avisos(**campos):
        h = InvoiceFacts(
            file_id="x.pdf",
            sha256="0" * 64,
            metodo=MetodoExtraccion.LLM_TEXTO,
            extractor_version="t",
            **campos,
        )
        return validadores.validar(h)

    for nif in ("DE812345678", "FR40303265045", "12345678000195", "5010401075570"):
        assert Aviso.NIF_INVALIDO not in avisos(nif_emisor=nif), nif
    assert Aviso.NIF_INVALIDO in avisos(nif_emisor="B4610233")  # el español roto sigue avisando
    assert Aviso.IBAN_INVALIDO not in avisos(iban="DE89370400440532013000")
    assert Aviso.IBAN_INVALIDO not in avisos(iban="BR9700360305000010009795493C1")
    assert Aviso.IBAN_INVALIDO in avisos(iban="JP0100012331234567890 12")  # Japón no usa IBAN
