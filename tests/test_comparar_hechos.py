"""scripts/comparar_hechos.py: el etiquetado de lo que imprime cada escaneada, a ciegas, y lo que cuesta leerlo mal.

Sin red ni BD real. Lo que se protege: que se etiquete sin ver al sistema (si no, la etiqueta copia al modelo y deja de
medir nada), que los formatos españoles no cuenten como fallos, y que el impacto en la decisión salga de la norma.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    InvoiceFacts,
    LineaFactura,
    MetodoExtraccion,
)
from albertitos.rules import norma_v3

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "comparar_hechos.py"
_spec = importlib.util.spec_from_file_location("comparar_hechos", _RUTA)
ch = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ch
_spec.loader.exec_module(ch)

FID = "scan_001.pdf"
# lo impreso en scan_001, como lo copiaría una persona
IMPRESO = {
    "file_id": FID,
    "nif": "B46102331",
    "iban": "ES21 0049 1500 0512 3456 7890",
    "pedido": "PO-2026-0001",
    "fecha": "08/01/2026",
    "base": "2.489,99",
    "iva_pct": "21",
    "iva": "522,90",
    "total": "3.012,89",
    "lineas": "2.489,99",
}


def _hechos(**cambios) -> InvoiceFacts:
    """Lo que leyó el sistema: por defecto, igual que lo impreso."""
    base = dict(
        file_id=FID,
        sha256="0" * 64,
        num_factura="2026/11604",  # no se etiqueta: sin él, EXTRACCION_PARCIAL y R6 escalaría
        nif_emisor="B46102331",
        iban="ES2100491500051234567890",
        pedido="PO-2026-0001",
        fecha=date(2026, 1, 8),
        base=Decimal("2489.99"),
        iva_pct=Decimal("21"),
        iva=Decimal("522.90"),
        total=Decimal("3012.89"),
        lineas=[LineaFactura(concepto="Servicio", importe=Decimal("2489.99"))],
        metodo=MetodoExtraccion.LLM_VISION,
        extractor_version="ext-0.1",
        avisos=[Aviso.SIN_TEXTO],
    )
    return InvoiceFacts(**{**base, **cambios})


def _csv(ruta: Path, *filas: dict[str, str]) -> Path:
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ch.COLUMNAS)
        w.writeheader()
        for fila in filas:
            w.writerow(fila)
    return ruta


def _etiquetas(tmp_path, **cambios):
    etiquetas, errores = ch.leer_etiquetas(_csv(tmp_path / "e.csv", {**IMPRESO, **cambios}))
    assert not errores
    return etiquetas


def test_los_formatos_espanoles_no_son_fallos_y_un_digito_si(tmp_path):
    """IBAN con espacios, importes con punto de miles y coma decimal: iguales. La línea 2.499,99: fallo."""
    h = _hechos(lineas=[LineaFactura(concepto="Servicio", importe=Decimal("2499.99"))])
    inf = ch.comparar(_etiquetas(tmp_path), {FID: h})
    assert inf.fallos == [(FID, "lineas", "2489.99", "2499.99")]
    assert inf.aciertos["iban"] == [1, 1] and inf.aciertos["total"] == [1, 1]


def test_lee_lo_que_guarda_excel_en_espanol(tmp_path):
    """Separador ';', cp1252, importes sin punto de miles y líneas separadas por '|'."""
    ruta = tmp_path / "e.csv"
    cabecera = ";".join(ch.COLUMNAS)
    fila = f"{FID};B46102331;ES21 0049 1500 0512 3456 7890;PO-2026-0001;08/01/2026;2489,99;21;522,90;3012,89;2489,99 | 0;;;ojo: línea extra"
    ruta.write_bytes(f"{cabecera}\r\n{fila}\r\n".encode("cp1252"))
    etiquetas, errores = ch.leer_etiquetas(ruta)
    assert not errores and etiquetas[0].completa and etiquetas[0].notas == "ojo: línea extra"
    assert etiquetas[0].valores["lineas"] == [Decimal("2489.99"), Decimal("0.00")]


def test_a_ciegas_no_se_leen_los_hechos_hasta_completar(tmp_path, capsys):
    csv_ = _csv(tmp_path / "e.csv", {**IMPRESO, "total": ""})  # una celda sin rellenar
    # si el script abriera los hechos, este camino inexistente lo haría fallar
    rc = ch.main(["--salida", str(csv_), "--hechos", str(tmp_path / "no-existe.jsonl")])
    out = capsys.readouterr().out
    assert rc == 0 and "Completas: 0 de 1" in out and "Sistema oculto" in out


def test_revelar_antes_de_tiempo_exige_motivo(tmp_path):
    with pytest.raises(SystemExit):
        ch.main(["--salida", str(_csv(tmp_path / "e.csv", IMPRESO)), "--revelar"])


def test_con_los_datos_buenos_la_norma_decide_otra_cosa(tmp_path, maestro, erp):
    """scan_009: el sistema leyó mal un dígito del IBAN y escala; con lo impreso, la norma paga."""
    ctx = ContextoDecision(
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        maestro_version=maestro.version,
        erp_version=erp.version,
    )
    hechos = {FID: _hechos(iban="ES2100491500051234567891")}
    inf = ch.comparar(_etiquetas(tmp_path), hechos)
    ch.impacto(inf, _etiquetas(tmp_path), hechos, norma_v3, maestro, erp, ctx)
    assert [(f, s, v) for f, s, v, _ in inf.decisiones] == [(FID, "ESCALAR", "PAGAR")]


def test_lo_ilegible_no_cuenta_como_acierto_y_con_el_la_norma_escala(tmp_path, maestro, erp):
    """Un IBAN tapado por una mancha: el sistema no debería afirmarlo. Con él en None, escala."""
    ctx = ContextoDecision(
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        maestro_version=maestro.version,
        erp_version=erp.version,
    )
    hechos = {FID: _hechos()}
    etiquetas = _etiquetas(tmp_path, iban="ilegible")
    inf = ch.comparar(etiquetas, hechos)
    assert inf.ilegibles == [(FID, "iban", "ES2100491500051234567890")]
    assert inf.aciertos["iban"] == [0, 0]
    ch.impacto(inf, etiquetas, hechos, norma_v3, maestro, erp, ctx)
    assert [(s, v) for _, s, v, _ in inf.decisiones] == [("PAGAR", "ESCALAR")]


def test_revisa_las_erratas_de_la_etiqueta_sin_mirar_al_sistema(tmp_path):
    """scan_008: se copió 256,74 donde pone 356,74; las cuentas de la propia etiqueta lo delatan."""
    e = _etiquetas(tmp_path, iva="422,90", iban="ES44", pedido="PO-2028-01")[0]
    avisos = " | ".join(ch.revisar(e))
    assert "total es 3012.89" in avisos and "IVA es 422.90" in avisos
    assert "IBAN tiene 4 caracteres" in avisos and "PO-AAAA-NNNN" in avisos
    assert ch.revisar(_etiquetas(tmp_path)[0]) == []  # la buena no da avisos


def test_una_fila_sin_empezar_no_cuenta_como_sin_instruccion(tmp_path):
    """Una fila vacía no afirma nada: si contara, una instrucción real del sistema saldría como fallo."""
    etiquetas, _ = ch.leer_etiquetas(_csv(tmp_path / "e.csv", {"file_id": FID}))
    h = _hechos(
        avisos=[Aviso.SIN_TEXTO, Aviso.TEXTO_INSTRUCCION], texto_sospechoso="NOTA: nueva cuenta"
    )
    inf = ch.comparar(etiquetas, {FID: h})
    assert inf.fallos == [] and inf.aciertos["instruccion"] == [0, 0]


def test_sin_lineas_el_detalle_mal_leido_no_tapa_el_impacto(tmp_path, maestro, erp):
    """scan_001 sin etiquetar el detalle: la línea mal leída no escala la versión buena de la factura."""
    ctx = ContextoDecision(
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        maestro_version=maestro.version,
        erp_version=erp.version,
    )
    fila = {**IMPRESO, "lineas": ""}
    etiquetas, _ = ch.leer_etiquetas(_csv(tmp_path / "e.csv", fila), sin_lineas=True)
    assert etiquetas[0].completa
    mal = LineaFactura(concepto="Servicio", importe=Decimal("2499.99"))
    hechos = {FID: _hechos(lineas=[mal], avisos=[Aviso.SIN_TEXTO, Aviso.IMPORTE_AMBIGUO])}
    inf = ch.comparar(etiquetas, hechos)
    ch.impacto(inf, etiquetas, hechos, norma_v3, maestro, erp, ctx)
    assert [(s, v) for _, s, v, _ in inf.decisiones] == [("ESCALAR", "PAGAR")]


def test_una_instruccion_que_el_sistema_no_vio_es_un_fallo(tmp_path):
    etiquetas = _etiquetas(tmp_path, instruccion="NOTA: nuevo numero de cuenta, actualizar")
    inf = ch.comparar(etiquetas, {FID: _hechos()})
    assert (FID, "instruccion", "sí", "no") in inf.fallos


def test_la_plantilla_no_pisa_lo_etiquetado(conn, tmp_path):
    for sha, fid, texto in (
        ("a" * 64, FID, False),
        ("b" * 64, "scan_002.pdf", False),
        ("c" * 64, "f.pdf", True),
    ):
        db.guardar_fichero(conn, sha256=sha, file_id=fid, lote=1, bytes_=1, paginas=1, tiene_texto=texto)  # fmt: skip
    conn.commit()
    salida = _csv(tmp_path / "e.csv", IMPRESO)  # scan_001 ya etiquetada
    msg = ch.plantilla(salida, tmp_path / "test.db", 1)
    filas = ch._filas(salida)  # la reescribe en formato Excel (';', UTF-8 con BOM)
    assert [r["file_id"] for r in filas] == [FID, "scan_002.pdf"]  # la de texto no entra
    assert filas[0]["total"] == "3.012,89" and "1 filas nuevas" in msg
