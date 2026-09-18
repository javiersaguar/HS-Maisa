from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from albertitos.sources.excel import cargar_maestro, leer_norma


def test_maestro_real(caja):
    m = cargar_maestro(caja / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    assert len(m.proveedores) == 11
    assert len(m.pedidos) == 516
    assert m.proveedores["P003"].razon_social == "Ofimática Cieza S.L."  # sin espacios sobrantes
    assert m.proveedores["P001"].iban == "ES2100491500051234567890"
    assert m.proveedores["P001"].condiciones_dias == 60
    assert m.pedidos["PO-2026-0001"].importe_total == Decimal("9221.75")
    assert "Proveedores: P007 duplicado (filas idénticas; se ignora la segunda)" in m.avisos_calidad
    assert any("P003 tiene espacios sobrantes" in a for a in m.avisos_calidad)
    assert "pendiente_revisar: PO-2026-0007" in m.avisos_calidad
    assert "pendiente_revisar: PO-2026-0141" in m.avisos_calidad
    assert {n for n, p in m.pedidos.items() if not p.nif} == {
        f"PO-2026-{n:04d}" for n in range(538, 558)
    }
    assert any("NUNCA pagar sin cruzar" in a for a in m.avisos_calidad)
    assert (
        sum(1 for a in m.avisos_calidad if "sin NIF en el Excel" in a) == 20
    )  # PO-2026-0538..0557
    assert m.proveedor_por_nif("b-46102331").id == "P001"
    assert len(m.version) == 12


def test_norma_v3_tiene_seis_reglas(caja):
    lineas = leer_norma(caja / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    assert sum(1 for x in lineas if x[:2] in {f"{i}." for i in range(1, 7)}) == 6


PROVEEDOR = ["P001", "Proveedor uno", "B46102331", "ES2100491500051234567890", "Murcia", "60 dias"]
PEDIDO = ["PO-2026-0001", "P001", "B46102331", "1.234,56", "ABIERTO", "18/09/2026"]


def _crear_excel(tmp_path, *, proveedores=None, pedidos=None):
    ruta = tmp_path / "maestro.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Proveedores"
    wb.active.append(["id", "razon", "nif", "iban", "ciudad", "condiciones"])
    for fila in proveedores if proveedores is not None else [PROVEEDOR]:
        wb.active.append(fila)
    hoja = wb.create_sheet("Pedidos_2026")
    hoja.append(["pedido", "proveedor", "nif", "importe", "estado", "fecha"])
    for fila in pedidos if pedidos is not None else [PEDIDO]:
        hoja.append(fila)
    wb.create_sheet("Norma_Pagos_v3").append(["1. Una regla de prueba"])
    wb.save(ruta)
    wb.close()
    return ruta


def test_normaliza_maestro_sin_completar_nif_ausente(tmp_path):
    proveedor = [
        " p001 ",
        " Proveedor uno ",
        " b-46102331 ",
        " es21 0049 1500 0512 3456 7890 ",
        " Murcia ",
        " 60 dias ",
    ]
    pedido = [" po-2026- 0001 ", " p001 ", None, " 1.234,56 EUR ", " abierto ", date(2026, 9, 18)]
    m = cargar_maestro(_crear_excel(tmp_path, proveedores=[proveedor], pedidos=[pedido]))
    assert m.proveedores["P001"].nif == "B46102331"
    assert m.proveedores["P001"].iban == "ES2100491500051234567890"
    assert m.proveedores["P001"].razon_social == "Proveedor uno"
    assert m.proveedores["P001"].condiciones_dias == 60
    p = m.pedidos["PO-2026-0001"]
    assert p.proveedor_id == "P001"
    assert p.nif == ""
    assert p.importe_total == Decimal("1234.56")
    assert p.fecha_pedido == date(2026, 9, 18)
    assert p.estado == "ABIERTO"
    assert any("sin NIF" in a and "B46102331" in a for a in m.avisos_calidad)


@pytest.mark.parametrize("distinto", [False, True])
def test_proveedor_duplicado_conserva_primero_y_explica_conflicto(tmp_path, distinto):
    segundo = PROVEEDOR.copy()
    if distinto:
        segundo[2] = "B99999999"
    m = cargar_maestro(_crear_excel(tmp_path, proveedores=[PROVEEDOR, segundo]))
    assert len(m.proveedores) == 1
    assert m.proveedores["P001"].nif == "B46102331"
    aviso = next(a for a in m.avisos_calidad if "P001 duplicado" in a)
    assert ("CON DATOS DISTINTOS" if distinto else "filas idénticas") in aviso
    if distinto:
        assert "B46102331" in aviso and "B99999999" in aviso


@pytest.mark.parametrize("distinto", [False, True])
def test_pedido_duplicado_conserva_primero_y_explica_conflicto(tmp_path, distinto):
    segundo = PEDIDO.copy()
    if distinto:
        segundo[3] = "9.999,99"
    m = cargar_maestro(_crear_excel(tmp_path, pedidos=[PEDIDO, segundo]))
    assert len(m.pedidos) == 1
    assert m.pedidos["PO-2026-0001"].importe_total == Decimal("1234.56")
    aviso = next(a for a in m.avisos_calidad if "PO-2026-0001 duplicado" in a)
    assert ("CON DATOS DISTINTOS" if distinto else "filas idénticas") in aviso
    if distinto:
        assert "1234.56" in aviso and "9999.99" in aviso


def test_pedido_sin_proveedor_ni_nif_revela_ambas_carencias(tmp_path):
    pedido = PEDIDO.copy()
    pedido[1:3] = ["P999", None]
    m = cargar_maestro(_crear_excel(tmp_path, pedidos=[pedido]))
    assert any("sin NIF" in a for a in m.avisos_calidad)
    assert any("proveedor que no está" in a and "P999" in a for a in m.avisos_calidad)


@pytest.mark.parametrize("lector", [cargar_maestro, leer_norma])
@pytest.mark.parametrize("con_error", [False, True])
def test_cierra_excel_incluso_si_falta_hoja(tmp_path, monkeypatch, lector, con_error):
    ruta = _crear_excel(tmp_path)
    if con_error:
        wb = openpyxl.load_workbook(ruta)
        del wb["Proveedores" if lector is cargar_maestro else "Norma_Pagos_v3"]
        wb.save(ruta)
        wb.close()
    abrir = openpyxl.load_workbook
    libros = []

    def abrir_y_registrar(*args, **kwargs):
        wb = abrir(*args, **kwargs)
        libros.append(wb)
        return wb

    monkeypatch.setattr(openpyxl, "load_workbook", abrir_y_registrar)
    try:
        if con_error:
            with pytest.raises(KeyError):
                lector(ruta)
        else:
            lector(ruta)
        assert libros[0]._archive.fp is None
    finally:
        for wb in libros:
            wb.close()
