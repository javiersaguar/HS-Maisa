"""P0-1: el mismo PDF, byte a byte, con otro nombre (docs/agentes/P0-1-IDENTICOS.md).

`ficheros` tiene la sha256 como clave y los hechos y las decisiones van por sha256. Con una copia exacta
renombrada pasan tres cosas, y las tres nos dejan sin premio o pagan dos veces:
  (a) copia de un PDF del lote 1 que llega en el lote 2: ingest reescribe el file_id y el lote del
      original → el lote 1 pierde su línea → NO APTO;
  (b) dos nombres con el mismo contenido dentro del lote 2: queda uno → falta una línea → NO APTO;
  (c) aunque se guardaran los dos nombres, hay UN hecho para dos facturas: marcar_duplicados no ve grupo
      y las dos salen PAGAR → se paga dos veces.

Los tests de R1-R4 los escribió H1 antes del arreglo, con xfail estricto; pasaron a XPASS con la
implementación de Miguel (`e3b3764`, tabla `identidades`) y se les quitó la marca. Los de control
(renombrar y sin copias) fijan lo que el arreglo no puede romper. Los de Miguel: `tests/test_copias.py`.

Sin red, sin bridge levantado y sin LLM: ERP v1 real leído del bridge, maestro real, hechos por plantilla.
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
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
IDENTICOS = Path("data/fixtures/lote2_identicos/facturas")
BRIDGE = CAJA / "alberto_erp.py"
CORTE = date(2026, 9, 18)

ORIGINAL = "2026-01-08_P001.pdf"  # lote 1
REENVIO = "L2I-reenvio_2026-01-08_P001.pdf"  # lote 2, copia exacta del ORIGINAL
PAREJA = ("L2I-2026-01-14_P002.pdf", "L2I-2026-01-14_P002_copia.pdf")  # lote 2, idénticos entre sí
CONTROL = "L2I-2026-01-15_P003.pdf"  # lote 2, sin copias

pytestmark = pytest.mark.skipif(
    not ((CAJA / "facturas").is_dir() and IDENTICOS.is_dir() and BRIDGE.exists()),
    reason="falta la Caja, el fixture de idénticos o el bridge",
)


# --------------------------------------------------------------------------- montaje


def _erp_v1() -> ErpSnapshot:
    """Los asientos que el bridge sirve como v1, leídos del propio bridge (sin levantarlo)."""
    spec = importlib.util.spec_from_file_location("alberto_erp_identicos", BRIDGE)
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


@pytest.fixture
def bd(conn, tmp_path, monkeypatch):
    """Lote 1 con el ORIGINAL; lote 2 con el fixture entero. Todo ingerido y extraído por plantilla."""
    raiz = {1: tmp_path / "caja", 2: tmp_path / "lote2"}
    (raiz[1] / "facturas").mkdir(parents=True)
    shutil.copy(CAJA / "facturas" / ORIGINAL, raiz[1] / "facturas" / ORIGINAL)
    shutil.copytree(IDENTICOS, raiz[2] / "facturas")
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setenv("ALBERTITOS_DB", ruta_db)
    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    monkeypatch.setattr(etapa, "DIRECTORIOS", {k: v / "facturas" for k, v in raiz.items()})
    maestro = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    erp = _erp_v1()
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    chaos.activar("llm_down")  # garantía de que ningún test sale a la red: todo va por plantilla
    return {"conn": conn, "raiz": raiz, "maestro": maestro, "erp": erp, "tmp": tmp_path}


def ingerir(bd) -> None:
    etapas.ingest(bd["conn"], bd["raiz"][1] / "facturas", 1)
    etapas.ingest(bd["conn"], bd["raiz"][2] / "facturas", 2)


def procesar(bd) -> None:
    """ingest → extract → duplicados → decide (lo que hace `run`, sin package)."""
    ingerir(bd)
    etapa.extraer(bd["conn"])
    etapas.marcar_duplicados(bd["conn"])
    run.reprocesar(
        bd["conn"], norma_version="v3", fecha_corte=CORTE, maestro=bd["maestro"], erp=bd["erp"]
    )


def empaquetar(bd, carpeta: str = "entrega") -> dict[int, dict[str, dict]]:
    """Empaqueta los dos lotes y devuelve {lote: {file_id: línea}}. Falla si package se niega."""
    salida = bd["tmp"] / carpeta
    package.empaquetar(bd["conn"], salida, bd["raiz"][1], bd["raiz"][2], con_traza=True)
    out = {}
    for lote, nombre in ((1, "outcomes.jsonl"), (2, "outcomes_lote2.jsonl")):
        texto = (salida / nombre).read_text(encoding="utf-8")
        out[lote] = {o["file_id"]: o for o in (json.loads(x) for x in io.StringIO(texto))}
    return out


def pdfs(bd, lote: int) -> list[str]:
    return sorted(p.name for p in (bd["raiz"][lote] / "facturas").glob("*.pdf"))


# --------------------------------------------------------------------------- lo que el parche no puede romper


def test_control_el_fixture_es_lo_que_dice():
    """Las copias son copias de verdad; si alguien regenera el fixture, este test lo dice."""
    import hashlib

    def h(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    assert h(IDENTICOS / REENVIO) == h(CAJA / "facturas" / ORIGINAL)
    assert h(IDENTICOS / PAREJA[0]) == h(IDENTICOS / PAREJA[1])
    assert h(IDENTICOS / CONTROL) not in {h(IDENTICOS / REENVIO), h(IDENTICOS / PAREJA[0])}


def test_renombrar_en_el_mismo_lote_sigue_actualizando_el_file_id(bd):
    """Comportamiento que ya existe y hay que conservar: si el nombre viejo YA NO está, es un
    renombrado, no una copia (ingest: "Renombrar actualiza el file_id")."""
    conn, carpeta = bd["conn"], bd["raiz"][1] / "facturas"
    etapas.ingest(conn, carpeta, 1)
    (carpeta / ORIGINAL).rename(carpeta / "2026-01-08_P001_renombrado.pdf")
    etapas.ingest(conn, carpeta, 1)
    assert [f["file_id"] for f in db.ficheros(conn, lote=1)] == ["2026-01-08_P001_renombrado.pdf"]


def test_sin_copias_nada_cambia(bd):
    """R5 en pequeño: sólo el lote 1, sin copias → una línea por PDF y la decisión de la norma."""
    conn = bd["conn"]
    etapas.ingest(conn, bd["raiz"][1] / "facturas", 1)
    etapa.extraer(conn)
    etapas.marcar_duplicados(conn)
    run.reprocesar(
        conn, norma_version="v3", fecha_corte=CORTE, maestro=bd["maestro"], erp=bd["erp"]
    )
    salida = bd["tmp"] / "solo_lote1"
    package.empaquetar(conn, salida, bd["raiz"][1], None, con_traza=True)
    lineas = [json.loads(x) for x in (salida / "outcomes.jsonl").read_text().splitlines()]
    assert [(o["file_id"], o["result"]) for o in lineas] == [(ORIGINAL, "PAGAR")]


# --------------------------------------------------------------------------- R1-R4


def test_r1_la_copia_del_lote_2_no_toca_al_original_del_lote_1(bd):
    """(a) ON CONFLICT(sha256) reescribe file_id y lote del original."""
    ingerir(bd)
    lote1 = [f["file_id"] for f in db.ficheros(bd["conn"], lote=1)]
    assert lote1 == [ORIGINAL]


def test_r2_cada_pdf_tiene_su_linea_y_los_dos_lotes_son_aptos(bd):
    """(a) y (b): cada nombre recibido, en el JSONL de SU lote, y validate da APTO en los dos."""
    procesar(bd)
    entrega = empaquetar(bd)
    assert sorted(entrega[1]) == pdfs(bd, 1)
    assert sorted(entrega[2]) == pdfs(bd, 2)
    for lote, nombre in ((1, "outcomes.jsonl"), (2, "outcomes_lote2.jsonl")):
        informe = validar_jsonl(bd["tmp"] / "entrega" / nombre, pdfs(bd, lote), lote)
        assert informe.ok, informe.texto()


def test_r3_nunca_se_pagan_las_dos_y_el_motivo_nombra_a_la_otra(bd):
    """(c) Todas las identidades de una sha256 con más de un nombre, ESCALAR, diciendo con cuál."""
    procesar(bd)
    entrega = empaquetar(bd)
    grupos = [(entrega[1][ORIGINAL], entrega[2][REENVIO]), tuple(entrega[2][n] for n in PAREJA)]
    for grupo in grupos:
        assert {o["result"] for o in grupo} == {Resultado.ESCALAR.value}, grupo
        nombres = {o["file_id"] for o in grupo}
        for o in grupo:
            otros = nombres - {o["file_id"]}
            traza = json.dumps(db.traza(bd["conn"], o["file_id"]), ensure_ascii=False, default=str)
            assert all(n in traza for n in otros), f"la traza de {o['file_id']} no nombra a {otros}"
    assert entrega[2][CONTROL]["result"] == Resultado.PAGAR.value  # el control no se contagia


def test_r4_repetir_no_duplica_ni_pierde_identidades(bd):
    procesar(bd)
    primera = empaquetar(bd, "primera")
    ingerir(bd)  # repetir ingest
    run.reprocesar(
        bd["conn"], norma_version="v3", fecha_corte=CORTE, maestro=bd["maestro"], erp=bd["erp"]
    )
    segunda = empaquetar(bd, "segunda")
    assert segunda == primera


def test_r4_la_traza_de_una_copia_encuentra_su_fichero(bd):
    """Las dos identidades se trazan. (Hoy la copia "se encuentra" sólo porque ha robado el nombre al
    original, que es justo el fallo: por eso se comprueban las dos.)"""
    ingerir(bd)
    for nombre in (ORIGINAL, REENVIO, *PAREJA):
        assert db.traza(bd["conn"], nombre)["fichero"] is not None, f"trace {nombre}: sin fichero"
