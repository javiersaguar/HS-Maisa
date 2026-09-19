"""Maestro del lote 2: Excel + proveedores_nuevos.csv + pedidos_nuevos.csv (sources/lote2.py)."""

from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.sources import excel, lote2

RAIZ = Path(__file__).resolve().parents[1]
XLSX = RAIZ / "data/caja/FINAL_v7_DEFINITIVO_ahorasi.xlsx"
LOTE2 = RAIZ / "data/lote2"

PROV = "ID,Razon Social,NIF,IBAN,Ciudad,Condiciones\n"
PED = "pedido,proveedor_id,nif,importe_total,estado,fecha_pedido\n"


@pytest.fixture(scope="module")
def base():
    return excel.cargar_maestro(XLSX)


@pytest.mark.skipif(not (LOTE2 / "pedidos_nuevos.csv").exists(), reason="sin material del lote 2")
def test_maestro_real_del_lote2(base):
    m = lote2.cargar_maestro_lote2(XLSX, LOTE2)
    assert (len(m.proveedores), len(m.pedidos)) == (15, 555)
    assert m.version != base.version
    assert m.proveedores["P015"].nif == "5010401075570"
    assert m.pedidos["PO-2026-1309"].importe_total == Decimal("5244.50")
    assert m.pedidos["PO-2026-0071"] == base.pedidos["PO-2026-0071"]  # lo del Excel no cambia
    avisos = " | ".join(m.avisos_calidad)
    assert "P015" in avisos and "Japón no usa IBAN" in avisos
    assert "P012" not in avisos  # el IBAN alemán es válido


def test_lo_del_excel_no_se_pisa_y_se_avisa(tmp_path, base):
    (tmp_path / "proveedores_nuevos.csv").write_text(
        PROV
        + "P001,Suministros Levante S.L.,B46102331,ES99 0000 0000 0000 0000 0000,Valencia,60 dias\n"
        + "P099,Nuevo SL,B12345678,DE89 3704 0044 0532 0130 00,Madrid,30 dias\n",
        encoding="utf-8",
    )
    (tmp_path / "pedidos_nuevos.csv").write_text(
        PED
        + "PO-2026-0071,P010,B98455101,1.00,ABIERTO,2026-09-14\n"
        + "PO-2026-9001,P099,B12345678,100.50,ABIERTO,2026-09-14\n"
        + "PO-2026-9002,P777,X0000000,5.00,ABIERTO,2026-09-14\n",
        encoding="utf-8",
    )
    m = lote2.cargar_maestro_lote2(XLSX, tmp_path)
    assert m.proveedores["P001"] == base.proveedores["P001"]
    assert m.pedidos["PO-2026-0071"] == base.pedidos["PO-2026-0071"]
    assert m.proveedores["P099"].condiciones_dias == 30
    assert m.pedidos["PO-2026-9001"].importe_total == Decimal("100.50")
    avisos = " | ".join(m.avisos_calidad)
    assert "P001 ya está en el Excel CON DATOS DISTINTOS" in avisos
    assert "PO-2026-0071 ya está en el Excel CON DATOS DISTINTOS" in avisos
    assert "PO-2026-9002 referencia un proveedor que no está en el maestro (P777)" in avisos


def test_mismo_contenido_misma_version(tmp_path, base):
    """Un CSV que sólo repite lo del Excel no crea otra versión: el linaje no redecide nada."""
    (tmp_path / "pedidos_nuevos.csv").write_text(
        PED + "PO-2026-0071,P010,B98455101,951.89,ABIERTO,2026-05-24\n", encoding="utf-8"
    )
    assert lote2.cargar_maestro_lote2(XLSX, tmp_path).version == base.version


def test_cabeceras_por_nombre_no_por_posicion(tmp_path):
    (tmp_path / "pedidos_nuevos.csv").write_text(
        "Estado,Importe_Total,Pedido,ProveedorID,NIF,Fecha_Pedido\n"
        "ABIERTO,200.00,PO-2026-9100,P001,B46102331,2026-09-14\n",
        encoding="utf-8",
    )
    m = lote2.cargar_maestro_lote2(XLSX, tmp_path)
    p = m.pedidos["PO-2026-9100"]
    assert (p.proveedor_id, p.importe_total, p.estado) == ("P001", Decimal("200.00"), "ABIERTO")


def test_sin_csv_no_es_un_maestro_del_lote2(tmp_path):
    with pytest.raises(excel.ErrorMaestro, match="no hay"):
        lote2.cargar_maestro_lote2(XLSX, tmp_path)
