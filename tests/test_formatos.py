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
