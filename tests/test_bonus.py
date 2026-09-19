"""Remesa sin red, sin escribir decisiones y sin aproximar dinero con float."""

import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.bonus import calcular, exportar, semana_iso
from albertitos.core import db
from albertitos.core.contracts import Decision, InvoiceFacts

IBAN = "ES9121000418450200051332"


@pytest.fixture
def escenario(conn, maestro, tmp_path):
    maestro.proveedores["P001"].iban = IBAN
    maestro.proveedores["P001"].condiciones_dias = 30
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())

    def agregar(nombre="a.pdf", resultado="PAGAR", total="10.10", referencia=None, **campos):
        h = InvoiceFacts(
            file_id=nombre,
            sha256=nombre,
            num_factura=referencia or nombre,
            fecha=date(2026, 8, 19),
            nif_emisor="B46102331",
            iban=IBAN,
            pedido="PO-2026-0001",
            total=Decimal(total),
            metodo="plantilla",
            extractor_version="test",
        )
        h = h.model_copy(update=campos)
        db.guardar_fichero(
            conn, sha256=nombre, file_id=nombre, lote=1, bytes_=1, paginas=1, tiene_texto=True
        )
        db.guardar_hechos(conn, h)
        db.guardar_decision(
            conn,
            Decision(
                file_id=nombre,
                sha256=nombre,
                resultado=resultado,
                motivos=[],
                norma_version="v3",
                fecha_corte=date(2026, 9, 18),
                hechos_hash=h.hash(),
                maestro_version=maestro.version,
                erp_version="v1",
            ),
        )
        conn.commit()
        return h

    return tmp_path / "test.db", agregar


def test_sumas_csv_semanas_y_solo_pagar(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    agregar("b.pdf", total="0.20", fecha=date(2026, 8, 18))
    agregar("c.pdf", resultado="ESCALAR")
    agregar("d.pdf", resultado="NO_PAGAR")
    informe = calcular(ruta)
    assert informe.resumen()["remesa_total_eur"] == "10.30"
    assert informe.resumen()["decisiones_pagar"] == 2
    assert informe.resumen()["vencidos"] == 1
    assert informe.resumen()["vencen_semana_corte"] == 2
    assert informe.resumen()["semanas"] == {"2026-W38": {"numero": 2, "importe_eur": "10.30"}}
    assert all(p.fecha_ejecucion == date(2026, 9, 18) for p in informe.remesa)
    exportar(informe, tmp_path / "salida", ruta_bd=ruta)
    with (tmp_path / "salida/remesa.csv").open() as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    assert {f["file_id"] for f in filas} == {"a.pdf", "b.pdf"}
    assert sum(Decimal(f["importe_eur"]) for f in filas) == Decimal("10.30")
    assert semana_iso(date(2027, 1, 1)) == "2026-W53"


@pytest.mark.parametrize(
    "campo,valor,codigo,en_calendario",
    [
        ("iban", "ES000000", "IBAN_INVALIDO", 1),
        ("condiciones_dias", None, "SIN_CONDICIONES", 0),
        ("condiciones_dias", -1, "SIN_CONDICIONES", 0),
    ],
)
def test_exclusiones_maestro(escenario, conn, maestro, campo, valor, codigo, en_calendario):
    ruta, agregar = escenario
    agregar()
    setattr(maestro.proveedores["P001"], campo, valor)
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert len(informe.calendario) == en_calendario
    assert codigo in {a.codigo for a in informe.avisos}
    assert informe.resumen()["excluidos_remesa"] == 1


def test_usa_maestro_de_la_decision(escenario, conn, maestro):
    ruta, agregar = escenario
    agregar()
    maestro.version = "posterior"
    maestro.proveedores["P001"].iban = "ES00"
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    conn.commit()
    assert calcular(ruta).remesa[0].iban == IBAN


@pytest.mark.parametrize(
    "campos,codigo",
    [
        ({"iban": "ES00"}, "IBAN_DISCREPANTE"),
        ({"nif_emisor": "OTRO"}, "PROVEEDOR_NO_IDENTIFICADO"),
        ({"fecha": None}, "FACTURA_INCOMPLETA"),
        ({"total": Decimal("-1")}, "IMPORTE_INVALIDO"),
        ({"total": Decimal("1.001")}, "IMPORTE_INVALIDO"),
    ],
)
def test_datos_no_pagables(escenario, campos, codigo):
    ruta, agregar = escenario
    agregar(**campos)
    informe = calcular(ruta)
    assert not informe.remesa
    assert informe.avisos[0].codigo == codigo


def test_hechos_cambiados_exigen_reprocesado(escenario, conn):
    ruta, agregar = escenario
    h = agregar()
    h.total = Decimal("999.00")
    db.guardar_hechos(conn, h)
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert informe.avisos[0].codigo == "HECHOS_NO_VIGENTES"


def test_duplicados_no_se_preparan(escenario, conn):
    ruta, agregar = escenario
    agregar(referencia="R1")
    agregar("b.pdf", referencia="R1")
    agregar("c.pdf")
    db.guardar_identidad(conn, file_id="copia.pdf", lote=2, sha256="c.pdf")
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert {a.codigo for a in informe.avisos} == {"REFERENCIA_DUPLICADA", "COPIA_EXACTA"}


def test_cli_solo_lectura_y_repetible(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    salida = tmp_path / "salida"
    cmd = [sys.executable, "-m", "albertitos.bonus", "--db", str(ruta), "--salida", str(salida)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    ficheros = {p.name: p.read_bytes() for p in salida.iterdir()}
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert ficheros == {p.name: p.read_bytes() for p in salida.iterdir()}
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes
    assert json.loads((salida / "resumen.json").read_text())["remesa_numero"] == 1


def test_corte_explicito_si_bd_vacia(escenario):
    ruta, _ = escenario
    with pytest.raises(ValueError, match="fecha-corte"):
        calcular(ruta)
    assert calcular(ruta, date(2026, 9, 18)).resumen()["remesa_total_eur"] == "0.00"


def test_exportacion_no_interpreta_texto(escenario, tmp_path):
    ruta, agregar = escenario
    agregar(referencia="=1+2", razon_social="<script>alert(1)</script>")
    informe = calcular(ruta)
    informe.calendario[0].beneficiario = "<script>alert(1)</script>"
    salida = tmp_path / "salida"
    exportar(informe, salida, ruta_bd=ruta)
    assert "'=1+2" in (salida / "remesa.csv").read_text()
    assert "<script>" not in (salida / "calendario.html").read_text()


def test_no_sobrescribe_bd_ni_entrega(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    informe = calcular(ruta)
    salida = tmp_path / "salida"
    salida.mkdir()
    (salida / "remesa.csv").symlink_to(ruta)
    with pytest.raises(ValueError, match="enlace"):
        exportar(informe, salida, ruta_bd=ruta)
    with pytest.raises(ValueError, match="oficial"):
        exportar(informe, Path("dist/entrega/bonus"), ruta_bd=ruta)


SINTETICO = "ES2100491500051234567890"  # el IBAN de P001 en la Caja: forma de IBAN, mod-97 falla


def _con_iban_sintetico(conn, maestro, agregar):
    maestro.proveedores["P001"].iban = SINTETICO
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    agregar("a.pdf", iban=SINTETICO)
    agregar("b.pdf", iban=SINTETICO)


def test_iban_sintetico_de_la_caja_entra_marcado_y_avisa_una_vez(escenario, conn, maestro):
    """Los 11 IBAN del maestro de la Caja no pasan el mod-97. Excluirlos dejaba la remesa en 0 pagos
    con 438 PAGAR: el bonus no enseñaba nada. Entran marcados, con un aviso por proveedor."""
    ruta, agregar = escenario
    _con_iban_sintetico(conn, maestro, agregar)
    informe = calcular(ruta)
    assert [p.file_id for p in informe.remesa] == ["a.pdf", "b.pdf"]
    assert not any(p.iban_control_ok for p in informe.remesa)
    assert [a.codigo for a in informe.avisos] == ["IBAN_SIN_CONTROL"]
    assert informe.resumen()["remesa_iban_sin_control"] == 2


def test_modo_estricto_excluye_lo_que_un_banco_rechazaria(escenario, conn, maestro):
    ruta, agregar = escenario
    _con_iban_sintetico(conn, maestro, agregar)
    informe = calcular(ruta, estricto=True)
    assert not informe.remesa
    assert {a.codigo for a in informe.avisos} == {"IBAN_INVALIDO"}
