"""scripts/dato_en_vivo.py: el tribunal cambia un dato y sólo se recalcula lo que ese dato toca.

Sin red, sin LLM y sin tocar `dist/albertitos.db`: BD temporal y los snapshots de `conftest`. Lo que
se comprueba es lo que se enseña en la sala: el cambio entra como un snapshot nuevo, el linaje ve
qué facturas dependen de él, y las demás no se mueven.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import InvoiceFacts, MetodoExtraccion
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, linaje
from albertitos.pipeline.run import MAESTRO_XLSX, reprocesar
from albertitos.sources import excel, snapshot

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "dato_en_vivo.py"
_spec = importlib.util.spec_from_file_location("dato_en_vivo", _RUTA)
vivo = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = vivo
_spec.loader.exec_module(vivo)

CAJA = Path("data/caja")
CORTE = date(2026, 9, 18)
P001 = dict(nif_emisor="B46102331", iban="ES2100491500051234567890")
P002 = dict(nif_emisor="A41220987", iban="ES7621000813610123456789")
OTRO_IBAN = "ES7621000813610123456789"


def _factura(conn, fid: str, **kw) -> InvoiceFacts:
    sha = fid[0] * 64
    db.guardar_fichero(conn, sha256=sha, file_id=fid, lote=1, bytes_=1, paginas=1, tiene_texto=True)
    h = InvoiceFacts(
        file_id=fid,
        sha256=sha,
        metodo=MetodoExtraccion.PLANTILLA,
        extractor_version=EXTRACTOR_VERSION,
        fecha=date(2026, 1, 8),
        **kw,
    )
    db.guardar_hechos(conn, h)
    return h


def _vigentes(conn) -> dict[str, str]:
    return {r["file_id"]: r["resultado"] for r in db.decisiones_vigentes(conn)}


@pytest.fixture
def decidida(conn, maestro, erp):
    """a.pdf (PO-2026-0001, P001) y b.pdf (PO-2026-0002, P002), las dos PAGAR."""
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    _factura(
        conn,
        "a.pdf",
        pedido="PO-2026-0001",
        base=Decimal("2489.99"),
        iva=Decimal("522.90"),
        total=Decimal("3012.89"),
        **P001,
    )
    _factura(
        conn,
        "b.pdf",
        pedido="PO-2026-0002",
        base=Decimal("780.00"),
        iva=Decimal("163.80"),
        total=Decimal("943.80"),
        **P002,
    )
    etapas.decide(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    assert _vigentes(conn) == {"a.pdf": "PAGAR", "b.pdf": "PAGAR"}
    return conn


# ----------------------------------------------------------------------------- el escenario


def test_el_pedido_pagado_en_el_erp_deja_de_pagarse(decidida, maestro, erp):
    """Lo que se enseña: un dato del ERP cambia y esa factura deja de pagarse; la otra, intacta."""
    nuevo, cambios = vivo.erp_con_cambios(erp, tag="vivo", pagadas=["PO-2026-0001"])
    assert cambios == ["ERP · AS-00001 (PO-2026-0001): estado PENDIENTE → PAGADA"]
    snapshot.guardar_erp(decidida, nuevo)

    r = reprocesar(decidida, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=nuevo)

    assert list(r.impactados) == ["a.pdf"]  # b.pdf ni se recalcula: el diff no la toca
    assert [(c["file_id"], c["antes"], c["despues"]) for c in r.cambios] == [
        ("a.pdf", "PAGAR", "NO_PAGAR")
    ]
    assert _vigentes(decidida)["b.pdf"] == "PAGAR"


def test_cambiar_el_iban_solo_toca_a_las_facturas_de_ese_proveedor(decidida, maestro, erp):
    nuevo_m, cambios = vivo.maestro_con_cambios(maestro, ibanes={"P001": OTRO_IBAN})
    assert len(cambios) == 1 and "IBAN" in cambios[0]
    lin = linaje.evaluar(
        decidida,
        norma_version="v3",
        fecha_corte=CORTE,
        maestro=nuevo_m,
        erp=erp,
        extractor_version=EXTRACTOR_VERSION,
    )
    assert "a.pdf" in lin.impactados  # su NIF es el del proveedor que ha cambiado
    assert "b.pdf" not in lin.impactados
    assert [s["file_id"] for s in lin.sin_impacto] == ["b.pdf"]


def test_cambiar_el_estado_del_pedido_impacta_a_su_factura(decidida, maestro, erp):
    nuevo_m, cambios = vivo.maestro_con_cambios(maestro, estados={"PO-2026-0002": "anulado"})
    assert cambios == ["maestro · PO-2026-0002: estado ABIERTO → ANULADO"]
    lin = linaje.evaluar(
        decidida,
        norma_version="v3",
        fecha_corte=CORTE,
        maestro=nuevo_m,
        erp=erp,
        extractor_version=EXTRACTOR_VERSION,
    )
    assert "b.pdf" in lin.impactados
    assert "a.pdf" not in lin.impactados


# ----------------------------------------------------------------------------- el ERP derivado


def test_el_snapshot_derivado_no_toca_el_original_ni_finge_una_descarga(erp):
    nuevo, _ = vivo.erp_con_cambios(erp, tag="vivo", pagadas=["PO-2026-0001"])
    assert erp.asientos["AS-00001"].estado == "PENDIENTE"  # el original, intacto
    assert nuevo.asientos["AS-00001"].estado == "PAGADA"
    assert nuevo.version == "vivo"
    assert (nuevo.consultas, nuevo.reintentos) == (0, 0)  # no es una descarga: no las inventa


def test_el_diff_del_erp_apunta_al_pedido_que_ha_cambiado(erp):
    nuevo, _ = vivo.erp_con_cambios(erp, tag="vivo", pagadas=["PO-2026-0001"])
    d = snapshot.diff_erp(erp, nuevo)
    assert d["pedidos_afectados"] == ["PO-2026-0001"]
    assert list(d["cambiados"]) == ["AS-00001"]


def test_cambiar_el_importe_esperado_sale_en_el_diff(erp):
    nuevo, cambios = vivo.erp_con_cambios(
        erp, tag="vivo", importes={"PO-2026-0002": Decimal("1000.00")}
    )
    assert cambios == [
        "ERP · AS-00002 (PO-2026-0002): importe esperado 943.80 → 1000.00",
    ]
    assert snapshot.diff_erp(erp, nuevo)["pedidos_afectados"] == ["PO-2026-0002"]


def test_un_pedido_que_el_erp_no_conoce_se_dice_y_no_se_inventa(erp):
    with pytest.raises(ValueError, match="PO-2026-9999"):
        vivo.erp_con_cambios(erp, tag="vivo", pagadas=["PO-2026-9999"])


def test_un_proveedor_que_el_maestro_no_conoce_se_dice(maestro):
    with pytest.raises(ValueError, match="P999"):
        vivo.maestro_con_cambios(maestro, ibanes={"P999": OTRO_IBAN})


# ----------------------------------------------------------------------------- la versión


def test_la_version_del_maestro_cambia_con_el_dato_y_es_estable(maestro):
    uno, _ = vivo.maestro_con_cambios(maestro, ibanes={"P001": OTRO_IBAN})
    otro, _ = vivo.maestro_con_cambios(maestro, ibanes={"P001": OTRO_IBAN})
    assert uno.version == otro.version  # el mismo cambio da la misma versión
    assert uno.version != maestro.version


@pytest.mark.skipif(not (CAJA / MAESTRO_XLSX).is_file(), reason="no está el Excel de la Caja")
def test_la_version_del_maestro_es_la_que_calcula_excel():
    """Si alguien cambia cómo se versiona el maestro en `sources/excel.py`, esto salta."""
    m = excel.cargar_maestro(CAJA / MAESTRO_XLSX)
    assert vivo.version_maestro(m) == m.version


# ----------------------------------------------------------------------------- la línea de órdenes


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("PO-2026-0007=1234,56", ("PO-2026-0007", "1234,56")),
        (" P003 = ES91 2100 ", ("P003", "ES91 2100")),
    ],
)
def test_parsear_asignacion(texto, esperado):
    assert vivo.parsear_asignacion(texto, "--importe") == esperado


@pytest.mark.parametrize("texto", ["PO-2026-0007", "=1234", "PO-2026-0007="])
def test_parsear_asignacion_mal_escrita(texto):
    with pytest.raises(ValueError, match="CLAVE=VALOR"):
        vivo.parsear_asignacion(texto, "--importe")
