from decimal import Decimal

from albertitos.sources.excel import cargar_maestro, leer_norma


def test_maestro_real(caja):
    m = cargar_maestro(caja / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    assert len(m.proveedores) == 11
    assert len(m.pedidos) == 516
    assert m.proveedores["P003"].razon_social == "Ofimática Cieza S.L."  # sin espacios sobrantes
    assert m.proveedores["P001"].iban == "ES2100491500051234567890"
    assert m.proveedores["P001"].condiciones_dias == 60
    assert m.pedidos["PO-2026-0001"].importe_total == Decimal("9221.75")
    assert any("P007 duplicado" in a for a in m.avisos_calidad)
    assert any("NUNCA pagar sin cruzar" in a for a in m.avisos_calidad)
    assert (
        sum(1 for a in m.avisos_calidad if "sin NIF en el Excel" in a) == 20
    )  # PO-2026-0538..0557
    assert m.proveedor_por_nif("b-46102331").id == "P001"
    assert len(m.version) == 12


def test_norma_v3_tiene_seis_reglas(caja):
    lineas = leer_norma(caja / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    assert sum(1 for x in lineas if x[:2] in {f"{i}." for i in range(1, 7)}) == 6
