"""Trazabilidad (20 pts): la traza legible nombra a la pareja del duplicado, cada decisión de `run`
dice por qué se tomó, `status` enseña lo que pasa ahora y `erp pull` sin ERP cabe en una línea."""

import json

import pytest
from typer.testing import CliRunner

from albertitos import cli
from albertitos.core import db
from albertitos.core.contracts import EstadoEvento, Etapa, Event
from albertitos.pipeline import traza
from test_pipeline import MUESTRA, _correr, _preparar

runner = CliRunner()


def test_la_traza_legible_sigue_el_camino_y_nombra_a_la_pareja(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    assert _correr(conn, caja_tmp, caja, tmp_path / "entrega").ok

    texto = traza.legible(conn, MUESTRA[0])
    pasos = [ln.split()[1] for ln in texto.splitlines() if ln[:1].isdigit() and ln[1] == " "]
    assert pasos == ["HECHOS", "MAESTRO", "ERP", "DUPLICADO", "REGLAS", "RESULTADO"]
    # MUESTRA[0] y [1] comparten PO-2026-0001: cada una dice con quién, sin evento validate
    assert f"comparte pedido PO-2026-0001 con {MUESTRA[1]}" in texto
    assert f"comparte pedido PO-2026-0001 con {MUESTRA[0]}" in traza.legible(conn, MUESTRA[1])
    assert "4 DUPLICADO" not in traza.legible(conn, MUESTRA[2])
    assert "run: sin decisión" in texto  # el porqué del linaje, también en run
    assert "entregado" in texto and "outcomes.jsonl" in texto
    assert traza.legible(conn, "no-existe.pdf") is None


def test_cada_decision_de_run_lleva_su_porque(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[2:])
    assert _correr(conn, caja_tmp, caja, tmp_path / "e1").ok
    assert _correr(conn, caja_tmp, caja, tmp_path / "e2").ok  # nada cambió: redecide igual
    t = db.traza(conn, MUESTRA[2])
    por = traza.porques(t["decisiones"], t["eventos"])
    primera, segunda = sorted(d["id"] for d in t["decisiones"])
    assert por[primera] == "run: sin decisión"
    assert por[segunda].startswith("run: ninguna entrada cambió")
    assert "historial: 2 decisiones" in traza.legible(conn, MUESTRA[2])


def test_run_con_erp_explicito_no_lo_sustituye_por_otro(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[2:])
    with pytest.raises(LookupError, match="v9"):
        _correr(conn, caja_tmp, caja, tmp_path / "e", erp_version="v9")
    r = _correr(conn, caja_tmp, caja, tmp_path / "e", erp_version=erp.version)
    assert r.ok and r.erp_version == erp.version


def test_estado_actual_no_cuenta_fallos_ya_resueltos(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[2:])
    fid = MUESTRA[2]
    for estado in (EstadoEvento.PENDIENTE, EstadoEvento.OK):  # LLM caído y luego bien
        db.registrar_evento(conn, Event(file_id=fid, etapa=Etapa.EXTRACT, estado=estado))
    db.registrar_evento(conn, Event(file_id="L2-borrado.pdf", etapa=Etapa.EXTRACT, estado="error"))
    conn.commit()
    actual = {(e["etapa"], e["estado"]): e["n"] for e in db.estado_actual(conn)}
    assert actual[("extract", "ok")] == 1
    assert ("extract", "pendiente") not in actual  # resuelto
    assert ("extract", "error") not in actual  # de un fichero que ya no está
    historico = {(e["etapa"], e["estado"]) for e in db.resumen(conn)["eventos"]}
    assert ("extract", "pendiente") in historico  # el histórico lo sigue teniendo
    assert _correr(conn, caja_tmp, caja, tmp_path / "e").ok


def test_erp_pull_sin_erp_es_una_linea(tmp_path, monkeypatch):
    monkeypatch.setenv("ALBERTITOS_DB", str(tmp_path / "a.db"))
    monkeypatch.setenv("ALBERTITOS_ERP_URL", "http://127.0.0.1:1")

    def caido(self, tag):
        raise cli_erp.ErrorERP("ERP-NO-RESPONDE", "http://127.0.0.1:1/erp/login tras 8 intentos")

    from albertitos.sources import erp as cli_erp

    monkeypatch.setattr(cli_erp.ClienteERP, "descargar_todo", caido)
    r = runner.invoke(cli.app, ["erp", "pull", "--tag", "v1"])
    assert r.exit_code == 1
    assert r.output.strip().splitlines() == [
        "ERP-NO-RESPONDE: http://127.0.0.1:1/erp/login tras 8 intentos"
    ]
    assert "Traceback" not in r.output


def test_trace_json_lleva_pareja_y_erp(conn, caja, erp, tmp_path, monkeypatch):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    assert _correr(conn, caja_tmp, caja, tmp_path / "entrega").ok
    monkeypatch.setenv("ALBERTITOS_DB", str(tmp_path / "test.db"))
    r = runner.invoke(cli.app, ["trace", MUESTRA[0], "--json"])
    assert r.exit_code == 0, r.output
    t = json.loads(r.output)
    assert t["duplicado_con"] == {MUESTRA[1]: "pedido PO-2026-0001"}
    assert t["erp"]["version"] == erp.version
