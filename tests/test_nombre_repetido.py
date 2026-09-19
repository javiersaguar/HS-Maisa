"""P0-5: el lote 2 trae un PDF con el nombre exacto de uno del lote 1 y otro contenido.

`ficheros.file_id` es UNIQUE: sin arreglo, la ingesta choca, ese PDF no tiene hechos ni línea → NO APTO.
El arreglo está en la rama `miguel/p0-5-nombre-repetido` (el que choca se guarda con un nombre interno,
`db.PREFIJO_INTERNO`, y el de entrega va a `identidades`). Miguel lo mergea sólo si el lote 2 lo trae.

Estos tests valen con el arreglo y sin él: se detecta por `db.PREFIJO_INTERNO`. El requisito se comprueba
donde importa, en la línea entregada de cada lote y en `validate`, no en cómo se guarda por dentro. Sin el
arreglo, el requisito es xfail estricto y el «hoy» documenta el fallo; con él, al revés.

Sin red: ERP v1 real leído del propio bridge (sin levantarlo) y hechos por plantilla, con el caos puesto.
Fixture: data/fixtures/lote2_nombre_repetido/ (nombre de lote 1 ausente de muestra.txt).
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import ErpEntry, ErpSnapshot, Resultado
from albertitos.extract import etapa
from albertitos.pipeline import etapas, package, run
from albertitos.pipeline.validar import validar_jsonl
from albertitos.sources import chaos, excel, snapshot

CAJA = Path("data/caja")
FIXTURE = Path("data/fixtures/lote2_nombre_repetido/facturas")
MUESTRA = Path("data/fixtures/muestra.txt")
BRIDGE = CAJA / "alberto_erp.py"
CORTE = date(2026, 9, 18)

# Nombre de lote 1 que NO está en muestra.txt; el contenido del fixture es otra factura.
NOMBRE = "2026-01-16_P004.pdf"

P0_5_DISPONIBLE = hasattr(db, "PREFIJO_INTERNO")

pytestmark = pytest.mark.skipif(
    not (
        (CAJA / "facturas" / NOMBRE).is_file() and (FIXTURE / NOMBRE).is_file() and BRIDGE.exists()
    ),
    reason="falta la Caja, el fixture lote2_nombre_repetido o el bridge",
)


def _erp_v1() -> ErpSnapshot:
    """Los asientos que el bridge sirve como v1, leídos del propio bridge (sin levantarlo)."""
    spec = importlib.util.spec_from_file_location("alberto_erp_nombre_repetido", BRIDGE)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    asientos = {
        f["asiento_id"]: ErpEntry(
            asiento_id=f["asiento_id"],
            fecha_registro=date.fromisoformat(f["fecha_registro"]),
            proveedor_id=f["proveedor_id"],
            nif=f["nif"],
            pedido=f["pedido"],
            importe_esperado=Decimal(f["importe_esperado"]),
            estado=f["estado"],
        )
        for f in modulo._cargar_asientos_embebidos()
    }
    return ErpSnapshot(version="v1", asientos=asientos, descargado_en=datetime.now(UTC))


def _verificador():
    spec = importlib.util.spec_from_file_location(
        "verificar_material_p05", Path("scripts/verificar_material.py")
    )
    assert spec and spec.loader
    material = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = material
    spec.loader.exec_module(material)
    return material


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
    monkeypatch.setattr(etapa, "DIRECTORIOS", {k: v / "facturas" for k, v in raiz.items()})
    maestro = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    erp = _erp_v1()
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    chaos.activar("llm_down")  # ningún test sale a la red: todo va por plantilla
    return {"conn": conn, "raiz": raiz, "maestro": maestro, "erp": erp, "tmp": tmp_path}


def test_fixture_nombre_repetido_es_lo_que_dice():
    """Mismo nombre que lote 1, bytes distintos, y el nombre no está en la muestra etiquetada."""
    caja = (CAJA / "facturas" / NOMBRE).read_bytes()
    l2 = (FIXTURE / NOMBRE).read_bytes()
    assert hashlib.sha256(caja).hexdigest() != hashlib.sha256(l2).hexdigest()
    nombres_muestra = {
        line.strip() for line in MUESTRA.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    assert NOMBRE not in nombres_muestra


def _verificar(tmp_path, conn):
    lote1 = tmp_path / "lote1"
    lote1.mkdir()
    shutil.copy(CAJA / "facturas" / NOMBRE, lote1 / NOMBRE)
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]
    return _verificador().verificar(FIXTURE.parent, ruta_db=ruta_db, lote1=lote1)


def test_verificador_sin_p0_5_para(tmp_path, conn, monkeypatch):
    monkeypatch.delattr(db, "PREFIJO_INTERNO", raising=False)
    inf = _verificar(tmp_path, conn)
    assert not inf.ok
    assert any("nombre coincide con lote 1" in e for e in inf.errores)


def test_verificador_con_p0_5_avisa_y_no_para(tmp_path, conn, monkeypatch):
    monkeypatch.setattr(db, "PREFIJO_INTERNO", "./", raising=False)
    inf = _verificar(tmp_path, conn)
    assert not any("nombre coincide con lote 1" in e for e in inf.errores), inf.errores
    assert any("nombre coincide con lote 1 y el contenido es otro" in a for a in inf.avisos)


@pytest.mark.skipif(P0_5_DISPONIBLE, reason="con P0-5 la ingesta ya deja la línea del lote 2")
def test_sin_p0_5_la_ingesta_no_deja_linea_en_el_lote_2(bd):
    """El fallo de hoy: el UNIQUE hace que el lote 2 se quede sin fila (y sin línea)."""
    conn = bd["conn"]
    etapas.ingest(conn, bd["raiz"][1] / "facturas", 1)
    assert etapas.ingest(conn, bd["raiz"][2] / "facturas", 2) == 0
    assert list(db.ficheros(conn, lote=2)) == []
    assert [f["file_id"] for f in db.ficheros(conn, lote=1)] == [NOMBRE]


@pytest.mark.xfail(
    not P0_5_DISPONIBLE, strict=True, reason="P0-5: rama miguel/p0-5-nombre-repetido sin mergear"
)
def test_cada_lote_tiene_su_linea_con_ese_nombre_y_los_dos_son_aptos(bd):
    conn = bd["conn"]
    etapas.ingest(conn, bd["raiz"][1] / "facturas", 1)
    etapas.ingest(conn, bd["raiz"][2] / "facturas", 2)
    etapa.extraer(conn)
    etapas.marcar_duplicados(conn)
    run.reprocesar(
        conn, norma_version="v3", fecha_corte=CORTE, maestro=bd["maestro"], erp=bd["erp"]
    )
    salida = bd["tmp"] / "entrega"
    package.empaquetar(conn, salida, bd["raiz"][1], bd["raiz"][2], con_traza=True)
    lineas = {}
    for lote, fichero in ((1, "outcomes.jsonl"), (2, "outcomes_lote2.jsonl")):
        ruta = salida / fichero
        informe = validar_jsonl(ruta, [NOMBRE], lote)
        assert informe.ok, informe.texto()
        lineas[lote] = [json.loads(x) for x in io.StringIO(ruta.read_text(encoding="utf-8"))]
        assert [o["file_id"] for o in lineas[lote]] == [NOMBRE]
    # Son dos facturas distintas del mismo pedido: nunca se pagan las dos.
    assert {lineas[1][0]["result"], lineas[2][0]["result"]} != {Resultado.PAGAR.value}
