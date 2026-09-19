"""scripts/contingencia.py (ADR-0009) con las cuatro condiciones de Miguel, cada una con su test.

BD temporal con PDF reales: uno del lote 1 (plantilla) y tres del lote 2 simulado (una plantilla y dos
escaneadas). Sin red y sin LLM: el proveedor se sustituye por uno que falla como fallaría de verdad
(`LLM-TIMEOUT`, sin la marca `caos:`) o que contesta. El caos, sólo en un fichero temporal.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.extract import etapa, llm
from albertitos.extract.llm import ErrorLLM
from albertitos.pipeline import etapas, package, run
from albertitos.sources import chaos, excel, snapshot

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "contingencia.py"
_spec = importlib.util.spec_from_file_location("contingencia", _RUTA)
cont = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cont
_spec.loader.exec_module(cont)

CAJA = Path("data/caja")
SIM = Path("data/fixtures/lote2_sim/facturas")
LOTE1 = ["2026-01-08_P001.pdf"]
LOTE2 = ["L2-2026-01-14_P002.pdf", "L2-scan_002.pdf", "L2-scan_004.pdf"]
CORTE = date(2026, 9, 18)
MOTIVO = "LLM caído desde las 06:40; reintentado a las 07:00 y 07:20 con el respaldo"
LECTURA = {  # lo que "contesta" el proveedor cuando vuelve: una lectura cualquiera, válida
    "num_factura": "2026/0001",
    "fecha": "2026-03-02",
    "nif_emisor": "B98120774",
    "iban": "ES4414650100951704302211",
    "pedido": "PO-2026-0001",
    "base": 100.0,
    "iva_pct": 21,
    "iva": 21.0,
    "total": 121.0,
    "lineas": [],
    "texto_sospechoso": None,
}

pytestmark = pytest.mark.skipif(
    not (CAJA / "facturas").is_dir() or not SIM.is_dir(), reason="falta la Caja o el lote simulado"
)


def proveedor(monkeypatch, *, contesta: bool) -> None:
    def falla(self, modelo, **kw):
        raise ErrorLLM("LLM-TIMEOUT", "sin respuesta en 90 s (ReadTimeout)")

    def contesta_(self, modelo, **kw):
        uso = {
            "tokens_in": 10,
            "tokens_out": 5,
            "coste_eur": Decimal("0"),
            "intento": 1,
            "modelo": modelo,
        }
        return {"input": dict(LECTURA), "uso": uso}

    monkeypatch.setattr(llm.ClienteLLM, "_llamar", contesta_ if contesta else falla)


@pytest.fixture
def bd(conn, erp, tmp_path, monkeypatch):
    """Lote 1 decidido; en el lote 2, la plantilla decidida y las dos escaneadas PENDIENTES:
    `L2-scan_002` con un intento real (timeout) y uno simulado; `L2-scan_004` sólo con el simulado."""
    raiz = {1: tmp_path / "caja", 2: tmp_path / "lote2"}
    for lote, origen, nombres in ((1, CAJA / "facturas", LOTE1), (2, SIM, LOTE2)):
        (raiz[lote] / "facturas").mkdir(parents=True)
        for n in nombres:
            shutil.copy(origen / n, raiz[lote] / "facturas" / n)
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setenv("ALBERTITOS_DB", ruta_db)
    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    monkeypatch.setattr(etapa, "DIRECTORIOS", {k: v / "facturas" for k, v in raiz.items()})
    monkeypatch.setattr(etapa, "VISION_DOBLE", False)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("ALBERTITOS_LLM_PROVEEDOR", "anthropic")
    monkeypatch.setenv("ALBERTITOS_MODELO_VISION", "qwen3.6")
    monkeypatch.setenv("ALBERTITOS_MODELO_VISION_FALLBACK", "")
    monkeypatch.setenv("ALBERTITOS_MODELO_TEXTO_FALLBACK", "")
    maestro = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    etapas.ingest(conn, raiz[1] / "facturas", 1)
    etapas.ingest(conn, raiz[2] / "facturas", 2)
    chaos.activar("llm_down")  # 1.º: el proveedor "cae" (simulado) → las dos escaneadas, PENDIENTE
    etapa.extraer(conn)
    chaos.desactivar()
    proveedor(monkeypatch, contesta=False)  # 2.º: un intento de verdad sólo para L2-scan_002
    fixture = tmp_path / "scan_002.txt"
    fixture.write_text("L2-scan_002.pdf\n", encoding="utf-8")
    etapa.extraer(conn, fixture=fixture)
    run.reprocesar(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    return {
        "conn": conn,
        "ruta": ruta_db,
        "raiz": raiz,
        "maestro": maestro,
        "erp": erp,
        "tmp": tmp_path,
    }


def cli(bd, *args: str) -> int:
    return cont.main(["--db", bd["ruta"], "--fecha-corte", str(CORTE), *args])


def vigentes(conn) -> dict[str, tuple[str, list[str]]]:
    return {
        r["file_id"]: (
            r["resultado"],
            [m["regla_id"] for m in json.loads(r["motivos_json"]) if not m["ok"]],
        )
        for r in conn.execute(
            "SELECT file_id, resultado, motivos_json FROM decisiones WHERE vigente=1"
        )
    }


def recuento(conn) -> tuple[int, int]:
    return (
        conn.execute("SELECT count(*) FROM decisiones").fetchone()[0],
        conn.execute("SELECT count(*) FROM eventos").fetchone()[0],
    )


def empaquetar(bd, **kw):
    return package.empaquetar(
        bd["conn"], bd["tmp"] / "entrega", bd["raiz"][1], bd["raiz"][2], con_traza=True, **kw
    )


def test_el_escenario_de_partida(bd):
    v = vigentes(bd["conn"])
    assert set(v) == {"2026-01-08_P001.pdf", "L2-2026-01-14_P002.pdf"}
    assert [p.file_id for p in cont.pendientes(bd["conn"], 2)] == [
        "L2-scan_002.pdf",
        "L2-scan_004.pdf",
    ]


def test_en_seco_no_escribe_nada_y_cuenta_los_intentos(bd, capsys):
    antes = recuento(bd["conn"])
    assert cli(bd, "--lote", "2") == 1
    salida = capsys.readouterr().out
    assert recuento(bd["conn"]) == antes
    assert "EN SECO" in salida and "L2-scan_002.pdf" in salida and "L2-scan_004.pdf" in salida
    assert "reales 1 · simulados 1" in salida  # scan_002: un timeout de verdad y la caída simulada
    assert "reales 0 · simulados 1" in salida  # scan_004: sólo la caída simulada
    assert "--aplicar --motivo" in salida


def test_c1_sin_motivo_se_niega(bd, capsys):
    antes = recuento(bd["conn"])
    assert cli(bd, "--lote", "2", "--aplicar") == 2
    assert "exige --motivo" in capsys.readouterr().out and recuento(bd["conn"]) == antes


def test_c1_con_el_caos_encendido_se_niega(bd, capsys):
    chaos.activar("llm_down")
    antes = recuento(bd["conn"])
    assert cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO) == 1
    assert "caos está encendido" in capsys.readouterr().out and recuento(bd["conn"]) == antes


def test_c1_sin_ningun_intento_real_no_se_toca(bd, capsys):
    assert cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO) == 1  # queda uno sin aplicar
    salida = capsys.readouterr().out
    v = vigentes(bd["conn"])
    assert "L2-scan_004.pdf" not in v  # sólo tuvo el intento simulado
    assert "NO    L2-scan_004.pdf: sin ningún intento real" in salida and "extract" in salida
    assert v["L2-scan_002.pdf"] == ("ESCALAR", ["contingencia.C1"])


def test_c2_solo_escalar_y_solo_a_los_que_no_tienen_decision(bd):
    antes = {
        r["file_id"]: r["id"]
        for r in bd["conn"].execute("SELECT id, file_id FROM decisiones WHERE vigente=1")
    }
    cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO)
    despues = {
        r["file_id"]: r["id"]
        for r in bd["conn"].execute("SELECT id, file_id FROM decisiones WHERE vigente=1")
    }
    assert {k: despues[k] for k in antes} == antes  # las que ya tenían decisión, intactas
    escritas = (
        bd["conn"]
        .execute(
            "SELECT resultado, hechos_hash FROM decisiones WHERE motivos_json LIKE '%contingencia.C1%'"
        )
        .fetchall()
    )
    assert [tuple(r) for r in escritas] == [("ESCALAR", "sin-hechos")]


def test_c2_en_el_lote_1_se_niega_siempre(bd, capsys):
    assert cli(bd, "--lote", "1") == 0  # 1/1 decidido: nada que aplicar
    assert cli(bd, "--lote", "1", "--aplicar", "--motivo", MOTIVO) == 1
    # y con un pendiente de verdad en el lote 1, tampoco: es otro problema
    shutil.copy(CAJA / "facturas" / "scan_001.pdf", bd["raiz"][1] / "facturas" / "scan_001.pdf")
    etapas.ingest(bd["conn"], bd["raiz"][1] / "facturas", 1)
    capsys.readouterr()
    assert cli(bd, "--lote", "1", "--aplicar", "--motivo", MOTIVO) == 1
    assert "ROJO" in capsys.readouterr().out
    assert "scan_001.pdf" not in vigentes(bd["conn"])


def test_idempotente(bd, capsys, monkeypatch):
    cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO)
    tras_la_primera = recuento(bd["conn"])
    cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO)
    assert recuento(bd["conn"]) == tras_la_primera
    # con un intento real también para scan_004, se aplica a ése y ya no queda nada
    fixture = bd["tmp"] / "scan_004.txt"
    fixture.write_text("L2-scan_004.pdf\n", encoding="utf-8")
    proveedor(monkeypatch, contesta=False)
    etapa.extraer(bd["conn"], fixture=fixture)
    assert cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO) == 0
    n = recuento(bd["conn"])[0]
    capsys.readouterr()
    assert cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO) == 0
    assert recuento(bd["conn"])[0] == n and "Nada que aplicar" in capsys.readouterr().out


def aplicar_a_las_dos(bd, monkeypatch) -> None:
    fixture = bd["tmp"] / "scan_004.txt"
    fixture.write_text("L2-scan_004.pdf\n", encoding="utf-8")
    proveedor(monkeypatch, contesta=False)
    etapa.extraer(bd["conn"], fixture=fixture)
    assert cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO) == 0


def test_c4_package_pasa_de_negarse_a_apto_y_la_linea_lo_dice(bd, monkeypatch):
    with pytest.raises(package.EntregaInvalida):
        empaquetar(bd)
    aplicar_a_las_dos(bd, monkeypatch)
    generados = empaquetar(bd)
    assert [inf.ok for _, inf in generados] == [True, True]
    lineas = {
        o["file_id"]: o
        for o in map(
            json.loads, (bd["tmp"] / "entrega" / "outcomes_lote2.jsonl").read_text().splitlines()
        )
    }
    assert lineas["L2-scan_002.pdf"]["result"] == "ESCALAR"
    assert lineas["L2-scan_002.pdf"]["regla"] == "contingencia.C1"
    assert lineas["L2-scan_002.pdf"]["motivo"].startswith(
        "sin hechos validados a la hora de entregar"
    )


def test_c4_el_evento_decide_lo_dice(bd):
    cli(bd, "--lote", "2", "--aplicar", "--motivo", MOTIVO)
    detalle = (
        bd["conn"]
        .execute(
            "SELECT detalle FROM eventos WHERE file_id='L2-scan_002.pdf' AND etapa='decide' ORDER BY id DESC"
        )
        .fetchone()[0]
    )
    d = json.loads(detalle)
    assert (
        d["contingencia"] is True
        and d["motivo"] == MOTIVO
        and d["reglas_ko"] == ["contingencia.C1"]
    )


def _revertida(conn, file_id: str) -> None:
    filas = conn.execute(
        "SELECT vigente, motivos_json FROM decisiones WHERE file_id=? ORDER BY id", (file_id,)
    ).fetchall()
    de_contingencia = [f for f in filas if "contingencia.C1" in f["motivos_json"]]
    assert de_contingencia and all(f["vigente"] == 0 for f in de_contingencia)
    vigente = [f for f in filas if f["vigente"] == 1]
    assert len(vigente) == 1 and "contingencia.C1" not in vigente[0]["motivos_json"]
    assert {m["regla_id"] for m in json.loads(vigente[0]["motivos_json"])} == {
        f"v3.R{i}" for i in range(1, 7)
    }


def test_c3_se_revierte_con_reprocess_impacted(bd, monkeypatch):
    aplicar_a_las_dos(bd, monkeypatch)
    proveedor(monkeypatch, contesta=True)  # vuelve el proveedor
    etapa.extraer(bd["conn"])  # sólo los pendientes de hechos: las dos escaneadas
    r = run.reprocesar(
        bd["conn"], norma_version="v3", fecha_corte=CORTE, maestro=bd["maestro"], erp=bd["erp"]
    )
    assert r.impactados["L2-scan_002.pdf"] == "hechos cambiados"
    for fid in ("L2-scan_002.pdf", "L2-scan_004.pdf"):
        _revertida(bd["conn"], fid)


def test_c3_se_revierte_con_run_entero(bd, monkeypatch):
    aplicar_a_las_dos(bd, monkeypatch)
    proveedor(monkeypatch, contesta=True)
    r = run.correr(
        bd["conn"],
        caja=bd["raiz"][1],
        lote2=bd["raiz"][2],
        entrega=bd["tmp"] / "entrega-run",
        norma_version="v3",
        fecha_corte=CORTE,
        maestro_xlsx=CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx",
    )
    assert r.extraidos == 2 and r.ok, r.texto()
    for fid in ("L2-scan_002.pdf", "L2-scan_004.pdf"):
        _revertida(bd["conn"], fid)


def test_describe_que_modelo_fallo_si_el_evento_lo_dice():
    """Los fallos nuevos llevan "[modelo … · …]" delante (llm.py); los viejos no, y se dice sin suponer."""
    anotado = cont.Pendiente("L2-x.pdf", "a" * 64, 2, True)
    anotado.intentos.append(
        cont.Intento(
            "2026-09-19T18:10:00",
            "pendiente",
            "LLM-HTTP-503",
            "LLM-HTTP-503: [respaldo glm5.3-flash tras LLM-HTTP-503 del principal deepseek-v4-flash] caído",
        )
    )
    texto = "\n".join(cont.describir(anotado))
    assert "respaldo glm5.3-flash tras LLM-HTTP-503 del principal deepseek-v4-flash" in texto

    viejo = cont.Pendiente("L2-y.pdf", "b" * 64, 2, True)
    viejo.intentos.append(
        cont.Intento("2026-09-18T19:07", "pendiente", "LLM-RED", "LLM-RED: sin red")
    )
    assert "estos eventos no lo dicen" in "\n".join(cont.describir(viejo))
