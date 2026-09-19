"""P0-5: mismo file_id que el lote 1, distinto contenido (docs/ESTADO-BACKEND.md).

`ficheros.file_id` es UNIQUE. Si el lote 2 trae un PDF con el nombre de uno del lote 1 y bytes
distintos, la ingesta choca con el UNIQUE: no hay hechos ni línea → NO APTO. `verificar_material`
ya lo marca en ROJO («nombre coincide con lote 1»), así que no llega por sorpresa, pero no tiene
salida hasta que Miguel decida (migración quitando el UNIQUE o id interno distinto del file_id).

Los tests del arreglo deseado llevan xfail ESTRICTO: cuando entre el parche pasarán a XPASS.
El test «hoy» documenta el ROJO del verificador y el UNIQUE en ingest.

Sin red. Fixture: data/fixtures/lote2_nombre_repetido/ (nombre de lote 1 ausente de muestra.txt).
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import ErpSnapshot
from albertitos.pipeline import etapas
from albertitos.sources import chaos, excel, snapshot

CAJA = Path("data/caja")
FIXTURE = Path("data/fixtures/lote2_nombre_repetido/facturas")
MUESTRA = Path("data/fixtures/muestra.txt")

# Nombre de lote 1 que NO está en muestra.txt; contenido = distinto del de la Caja.
NOMBRE = "2026-01-16_P004.pdf"

P0_5 = pytest.mark.xfail(
    strict=True,
    reason="P0-5: espera decisión/parche de Miguel (file_id UNIQUE entre lotes)",
)

pytestmark = pytest.mark.skipif(
    not ((CAJA / "facturas" / NOMBRE).is_file() and (FIXTURE / NOMBRE).is_file()),
    reason="falta la Caja o el fixture lote2_nombre_repetido",
)


def _erp_vacio() -> ErpSnapshot:
    return ErpSnapshot(version="v1", asientos={}, descargado_en=datetime.now(UTC))


@pytest.fixture
def bd(conn, tmp_path, monkeypatch):
    raiz = {1: tmp_path / "caja", 2: tmp_path / "lote2"}
    (raiz[1] / "facturas").mkdir(parents=True)
    (raiz[2] / "facturas").mkdir(parents=True)
    shutil.copy(CAJA / "facturas" / NOMBRE, raiz[1] / "facturas" / NOMBRE)
    shutil.copy(FIXTURE / NOMBRE, raiz[2] / "facturas" / NOMBRE)
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setenv("ALBERTITOS_DB", ruta_db)
    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    maestro = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    erp = _erp_vacio()
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    return {"conn": conn, "raiz": raiz, "maestro": maestro, "erp": erp, "tmp": tmp_path}


def test_fixture_nombre_repetido_es_lo_que_dice():
    """Mismo nombre que lote 1, bytes distintos, y el nombre no está en la muestra etiquetada."""
    caja = (CAJA / "facturas" / NOMBRE).read_bytes()
    l2 = (FIXTURE / NOMBRE).read_bytes()
    assert caja != l2
    assert hashlib.sha256(caja).hexdigest() != hashlib.sha256(l2).hexdigest()
    nombres_muestra = {
        line.strip() for line in MUESTRA.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    assert NOMBRE not in nombres_muestra


def test_hoy_verificar_material_para_por_nombre(tmp_path, conn):
    """Documenta el ROJO actual. Cuando P0-5 tenga salida, este test se reescribe o se borra."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "verificar_material_p05", Path("scripts/verificar_material.py")
    )
    assert spec and spec.loader
    material = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = material
    spec.loader.exec_module(material)

    lote1 = tmp_path / "lote1"
    lote1.mkdir()
    shutil.copy(CAJA / "facturas" / NOMBRE, lote1 / NOMBRE)
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]
    inf = material.verificar(FIXTURE.parent, ruta_db=ruta_db, lote1=lote1)
    assert not inf.ok
    assert "nombre coincide con lote 1" in inf.texto()


def test_hoy_ingest_no_deja_linea_en_lote_2(bd):
    """Documenta el UNIQUE: ingest traga el error (PDF-ILEGIBLE) y el lote 2 queda sin fila."""
    conn = bd["conn"]
    etapas.ingest(conn, bd["raiz"][1] / "facturas", 1)
    assert [f["file_id"] for f in db.ficheros(conn, lote=1)] == [NOMBRE]
    n = etapas.ingest(conn, bd["raiz"][2] / "facturas", 2)
    assert n == 0
    assert list(db.ficheros(conn, lote=2)) == []
    assert [f["file_id"] for f in db.ficheros(conn, lote=1)] == [NOMBRE]


@P0_5
def test_r1_ambos_nombres_quedan_en_su_lote(bd):
    """Tras el parche: lote 1 conserva su fila y lote 2 tiene la suya con el mismo file_id de entrega."""
    conn = bd["conn"]
    etapas.ingest(conn, bd["raiz"][1] / "facturas", 1)
    etapas.ingest(conn, bd["raiz"][2] / "facturas", 2)
    assert [f["file_id"] for f in db.ficheros(conn, lote=1)] == [NOMBRE]
    assert [f["file_id"] for f in db.ficheros(conn, lote=2)] == [NOMBRE]
    assert len(list(db.ficheros(conn))) == 2
