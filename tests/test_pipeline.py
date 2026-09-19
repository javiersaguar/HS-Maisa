"""`run` de principio a fin sin LLM: hechos ya en la BD → duplicados → decide → package.

Tres PDFs reales de la Caja (uno con tilde) copiados a una Caja temporal; ERP del fixture en memoria.
"""

import json
import shutil
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import Decision, InvoiceFacts, MetodoExtraccion, Motivo, Resultado
from albertitos.core.hashing import sha256_fichero
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, package
from albertitos.pipeline.run import MAESTRO_XLSX, correr
from albertitos.pipeline.validar import listar_pdfs, validar_jsonl
from albertitos.sources import snapshot

MUESTRA = ["2026-01-08_P001.pdf", "FA-4290_mensajería.pdf", "F26-2201_transportes.pdf"]
PEDIDOS = {MUESTRA[0]: "PO-2026-0001", MUESTRA[1]: "PO-2026-0001", MUESTRA[2]: "PO-2026-0002"}


def _preparar(conn, caja: Path, tmp_path: Path, erp, nombres: list[str]) -> Path:
    """Caja temporal con `nombres`, ingerida, con hechos a mano y el ERP del fixture."""
    caja_tmp = tmp_path / "caja"
    (caja_tmp / "facturas").mkdir(parents=True)
    for n in nombres:
        shutil.copy(caja / "facturas" / n, caja_tmp / "facturas" / n)
    etapas.ingest(conn, caja_tmp / "facturas", 1)
    snapshot.guardar_erp(conn, erp)  # sin ERP vivo: run usa el último snapshot
    for n in nombres:
        db.guardar_hechos(
            conn,
            InvoiceFacts(
                file_id=n,
                sha256=sha256_fichero(caja_tmp / "facturas" / n),
                pedido=PEDIDOS[n],
                total=Decimal("3012.89"),
                metodo=MetodoExtraccion.PLANTILLA,
                extractor_version=EXTRACTOR_VERSION,
            ),
        )
    conn.commit()
    return caja_tmp


def _correr(conn, caja_tmp: Path, caja: Path, entrega: Path, **kw):
    return correr(
        conn,
        caja=caja_tmp,
        lote2=None,
        entrega=entrega,
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        maestro_xlsx=caja / MAESTRO_XLSX,
        **{"extraer": False, **kw},
    )


def test_run_sin_llm_entrega_valida_e_idempotente(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    entrega = tmp_path / "entrega"
    salida = entrega / "outcomes.jsonl"

    r1 = _correr(conn, caja_tmp, caja, entrega)
    assert r1.ok, r1.texto()
    assert r1.decididas == 3 and r1.sin_hechos == []
    assert r1.duplicados == 2  # los dos PDFs del mismo pedido
    primera = salida.read_bytes()

    r2 = _correr(conn, caja_tmp, caja, entrega)
    assert r2.ok and r2.duplicados == 0
    assert salida.read_bytes() == primera  # dos run → mismo JSONL, byte a byte
    assert (r2.ingeridos, r2.ficheros) == (0, 3)  # lo ya registrado no se reabre
    n_ingest = conn.execute("SELECT count(*) FROM eventos WHERE etapa='ingest'").fetchone()[0]
    assert n_ingest == 3  # un evento por fichero, no uno por run

    inf = validar_jsonl(salida, listar_pdfs(caja_tmp / "facturas"), 1)
    assert inf.ok and inf.n_lineas == 3, inf.texto()
    lineas = [json.loads(x) for x in primera.decode("utf-8").splitlines()]
    assert {x["file_id"] for x in lineas} == set(MUESTRA)
    assert all(x["norma_version"] == "v3" and x["motivo"] for x in lineas)  # traza por defecto


def test_run_no_entrega_si_falta_una_decision_y_no_pisa_la_anterior(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[:2])
    entrega = tmp_path / "entrega"
    salida = entrega / "outcomes.jsonl"
    assert _correr(conn, caja_tmp, caja, entrega).ok
    anterior = salida.read_bytes()

    # llega un PDF nuevo y no hay hechos para él (LLM caído): sin hechos no hay decisión.
    # Sin traza, el JSONL rechazado difiere del anterior: si se escribiera, se notaría.
    shutil.copy(caja / "facturas" / MUESTRA[2], caja_tmp / "facturas" / MUESTRA[2])
    r = _correr(conn, caja_tmp, caja, entrega, con_traza=False)
    assert not r.ok and r.sin_hechos == [MUESTRA[2]]
    assert any(MUESTRA[2] in e for e in r.rechazo.errores)
    assert salida.read_bytes() == anterior  # la entrega válida anterior sigue intacta
    assert not list(entrega.glob("*.tmp"))


ESCANEADA = "scan_002.pdf"  # sin capa de texto: sólo la lee el LLM (visión)


def test_run_con_llm_caido_deja_pendiente_no_paga_y_reanuda(conn, caja, erp, tmp_path, monkeypatch):
    """G4: con el LLM caído, extract deja PENDIENTE la escaneada, decide se la salta y package se
    niega. Vuelto el LLM, el mismo run entrega. Cada transición deja un evento, sin copias."""
    from albertitos.sources import chaos

    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    chaos.activar("llm_down")
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[:2])
    shutil.copy(caja / "facturas" / ESCANEADA, caja_tmp / "facturas" / ESCANEADA)
    entrega = tmp_path / "entrega"

    for _ in range(2):  # dos run con el LLM caído: mismo estado y ningún evento de estado repetido
        r = _correr(conn, caja_tmp, caja, entrega, extraer=True)
        assert not r.ok and r.sin_hechos == [ESCANEADA]
    assert not (entrega / "outcomes.jsonl").exists()
    n = conn.execute("SELECT count(*) FROM decisiones WHERE file_id=?", (ESCANEADA,)).fetchone()[0]
    assert n == 0  # sin hechos no hay decisión, y sin decisión no hay PAGAR
    ev = [
        (e["etapa"], e["estado"], e["error_codigo"]) for e in db.traza(conn, ESCANEADA)["eventos"]
    ]
    assert ("extract", "pendiente", "LLM-DOWN") in ev
    assert ev.count(("decide", "skip", None)) == 1
    assert ev.count(("emit", "pendiente", None)) == 1
    rechazos = conn.execute(
        "SELECT count(*) FROM eventos WHERE etapa='emit' AND estado='error' AND file_id IS NULL"
    ).fetchone()[0]
    assert rechazos == 2  # uno por intento de entrega

    chaos.desactivar()  # vuelve el LLM; en el test (sin red), sus hechos
    db.guardar_hechos(
        conn,
        InvoiceFacts(
            file_id=ESCANEADA,
            sha256=sha256_fichero(caja_tmp / "facturas" / ESCANEADA),
            pedido="PO-2026-0002",
            total=Decimal("943.80"),
            metodo=MetodoExtraccion.LLM_VISION,
            extractor_version=EXTRACTOR_VERSION,
        ),
    )
    r = _correr(conn, caja_tmp, caja, entrega)
    assert r.ok, r.texto()
    emit = [e["estado"] for e in db.traza(conn, ESCANEADA)["eventos"] if e["etapa"] == "emit"]
    assert emit == ["pendiente", "ok"]
    r = _correr(conn, caja_tmp, caja, entrega)  # otra vez: nada nuevo por fichero en emit
    emit = [e["estado"] for e in db.traza(conn, ESCANEADA)["eventos"] if e["etapa"] == "emit"]
    assert emit == ["pendiente", "ok"]


def test_bench_mide_la_ventana_y_filtra_desde(conn):
    from datetime import UTC, datetime

    from albertitos.core.contracts import EstadoEvento, Etapa, Event
    from albertitos.pipeline import bench

    def ev(fid: str, seg: int, estado=EstadoEvento.OK, **kw):
        ts = datetime(2026, 9, 19, 10, 0, seg, tzinfo=UTC)
        db.registrar_evento(
            conn, Event(file_id=fid, etapa=Etapa.EXTRACT, estado=estado, ts=ts, **kw)
        )

    ev("viejo.pdf", 0, latencia_ms=1)  # de una pasada anterior
    for i, fid in enumerate(["a.pdf", "b.pdf", "c.pdf"]):
        ev(fid, 10 + i, latencia_ms=100 * (i + 1), tokens_in=10, coste_eur=Decimal(0))
    ev("c.pdf", 11, EstadoEvento.RETRY, error_codigo="LLM-429")

    todo = bench.medir(conn)["etapas"]["extract"]
    assert todo["ficheros"] == 4 and todo["fps"] == pytest.approx(4 / 12)
    m = bench.medir(conn, desde="2026-09-19T10:00:05")
    e = m["etapas"]["extract"]
    assert (e["ficheros"], e["p50_ms"], e["tin"], e["eur"]) == (3, 200.0, 30, 0)
    assert e["fps"] == pytest.approx(3 / 2)
    assert m["reintentos"] == {"LLM-429": 1}
    assert "1.5 ficheros/s" in bench.texto(m)


# --------------------------------------------------------------------- auditoría de entrega (E2)


@dataclass
class _Informe:
    rojos: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return not any(self.rojos.values())

    def texto(self) -> str:
        return "ROJO · " + "; ".join(f"{c}: {f}" for c, f in self.rojos.items() if f)


def _auditor_doble(llamadas: list[dict[int, Path]]):
    """Doble de UNA comprobación de la auditoría de E2, para probar el enganche en `empaquetar`."""

    def auditar(conn, lotes: dict[int, Path]) -> _Informe:
        llamadas.append(lotes)
        malas = [
            f["file_id"]
            for f in db.decisiones_vigentes(conn)
            if f["resultado"] == "PAGAR" and any(not m["ok"] for m in json.loads(f["motivos_json"]))
        ]
        return _Informe({"PAGAR con una regla incumplida": malas})

    return auditar


def _forzar_pagar(conn, file_id: str, motivos: list[Motivo]) -> None:
    """Una decisión que la norma nunca daría: PAGAR pese a lo que digan sus motivos."""
    f = next(x for x in db.decisiones_vigentes(conn) if x["file_id"] == file_id)
    db.guardar_decision(
        conn,
        Decision(
            file_id=file_id,
            sha256=f["sha256"],
            resultado=Resultado.PAGAR,
            motivos=motivos,
            norma_version="v3",
            fecha_corte=date(2026, 9, 18),
            hechos_hash=f["hechos_hash"],
            maestro_version=f["maestro_version"],
            erp_version=f["erp_version"],
        ),
    )
    conn.commit()


def _emit(conn, estado: str) -> list[dict]:
    filas = conn.execute(
        "SELECT file_id, error_codigo, detalle FROM eventos WHERE etapa='emit' AND estado=? ORDER BY id",
        (estado,),
    ).fetchall()
    return [dict(f) for f in filas]


def test_package_no_entrega_un_pagar_incoherente_y_no_pisa_la_anterior(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    entrega = tmp_path / "entrega"
    salida = entrega / "outcomes.jsonl"
    llamadas: list[dict[int, Path]] = []
    auditar = _auditor_doble(llamadas)

    r = _correr(conn, caja_tmp, caja, entrega, auditar=auditar)  # la norma decide: coherente
    assert r.ok, r.texto()
    assert llamadas == [{1: caja_tmp / "facturas"}]
    assert json.loads(_emit(conn, "ok")[0]["detalle"])["auditoria"] == "verde"
    anterior = salida.read_bytes()

    fallo = Motivo(regla_id="v3.R5", ok=False, detalle="el asiento del ERP ya está PAGADA")
    _forzar_pagar(conn, MUESTRA[2], [fallo])
    with pytest.raises(package.EntregaInvalida) as exc:
        package.empaquetar(conn, entrega, caja_tmp, None, con_traza=True, auditar=auditar)
    assert MUESTRA[2] in str(exc.value)
    assert salida.read_bytes() == anterior  # todo o nada: la entrega válida anterior sigue
    assert not list(entrega.glob("*.tmp"))
    (error,) = _emit(conn, "error")
    assert error["error_codigo"] == "AUDITORIA-ROJA"
    assert json.loads(error["detalle"])["rojos"] == {"PAGAR con una regla incumplida": [MUESTRA[2]]}
    (pendiente,) = _emit(conn, "pendiente")
    assert pendiente["file_id"] == MUESTRA[2]  # la traza del fichero dice por qué no salió

    # sin la auditoría, el JSONL es válido y saldría: por eso va dentro de package
    package.empaquetar(conn, entrega, caja_tmp, None, con_traza=True)
    assert salida.read_bytes() != anterior


def test_package_entrega_un_rojo_aceptado_y_deja_el_motivo(conn, caja, erp, tmp_path):
    """La salida de una puerta roja a las 07:55: se entrega, pero el motivo queda en la traza."""
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    entrega = tmp_path / "entrega"
    auditar = _auditor_doble([])
    assert _correr(conn, caja_tmp, caja, entrega, auditar=auditar).ok
    fallo = Motivo(regla_id="v3.R5", ok=False, detalle="el asiento del ERP ya está PAGADA")
    _forzar_pagar(conn, MUESTRA[2], [fallo])

    with pytest.raises(ValueError, match="motivo"):
        package.empaquetar(conn, entrega, caja_tmp, None, auditar=auditar, aceptar_rojo="  ")
    package.empaquetar(
        conn, entrega, caja_tmp, None, auditar=auditar, aceptar_rojo="lo revisó Mónica"
    )
    lineas = [json.loads(x) for x in (entrega / "outcomes.jsonl").read_text("utf-8").splitlines()]
    assert {"file_id": MUESTRA[2], "result": "PAGAR"} in lineas
    aceptado = next(e for e in _emit(conn, "ok") if e["error_codigo"])
    assert aceptado["error_codigo"] == "AUDITORIA-ROJA-ACEPTADA"
    detalle = json.loads(aceptado["detalle"])
    assert detalle["motivo"] == "lo revisó Mónica"
    assert detalle["rojos"] == {"PAGAR con una regla incumplida": [MUESTRA[2]]}
    por_lote = [e for e in _emit(conn, "ok") if e["file_id"] is None and not e["error_codigo"]]
    assert json.loads(por_lote[-1]["detalle"])["auditoria"] == "roja aceptada: lo revisó Mónica"
    assert not _emit(conn, "error")


def test_package_no_acepta_una_auditoria_que_falla(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[:1])
    assert _correr(conn, caja_tmp, caja, tmp_path / "entrega").ok

    def rota(conn, lotes):
        raise RuntimeError("sin maestro")

    with pytest.raises(package.EntregaInvalida, match="sin maestro"):
        package.empaquetar(
            conn, tmp_path / "otra", caja_tmp, None, auditar=rota, aceptar_rojo="da igual"
        )
    assert not (tmp_path / "otra" / "outcomes.jsonl").exists()


def test_package_se_niega_si_la_auditoria_falla(conn, caja, erp, tmp_path):
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA[:1])
    assert _correr(conn, caja_tmp, caja, tmp_path / "entrega").ok

    def rota(conn, lotes):
        raise RuntimeError("sin maestro")

    with pytest.raises(package.EntregaInvalida, match="sin maestro"):
        package.empaquetar(conn, tmp_path / "otra", caja_tmp, None, auditar=rota)
    assert not (tmp_path / "otra" / "outcomes.jsonl").exists()
    assert [e["error_codigo"] for e in _emit(conn, "error")] == ["AUDITORIA-ERROR"]


def test_auditoria_real_de_e2_caza_un_duplicado_pagado_dos_veces(conn, caja, erp, tmp_path):
    """Contrato con `pipeline.auditoria.auditar` (E2). Se salta hasta que exista; entonces manda."""
    pytest.importorskip("albertitos.pipeline.auditoria")
    auditar = package.auditor_de_entrega()
    caja_tmp = _preparar(conn, caja, tmp_path, erp, MUESTRA)
    entrega = tmp_path / "entrega"
    assert _correr(conn, caja_tmp, caja, entrega, auditar=auditar).ok  # coherente: pasa

    # MUESTRA[0] y [1] comparten PO-2026-0001: como si marcar_duplicados no hubiera corrido
    ok = Motivo(regla_id="v3.R1", ok=True, detalle="ok")
    for fid in MUESTRA[:2]:
        _forzar_pagar(conn, fid, [ok])
    informe = auditar(conn, {1: caja_tmp / "facturas"})
    assert not informe.ok
    assert set(MUESTRA[:2]) <= {f for fids in informe.rojos.values() for f in fids}
    with pytest.raises(package.EntregaInvalida):
        package.empaquetar(conn, entrega, caja_tmp, None, con_traza=True, auditar=auditar)


def test_auditor_de_entrega_se_engancha_solo_cuando_exista(monkeypatch):
    import sys
    import types

    def auditar(conn, lotes):
        return _Informe({})

    monkeypatch.setitem(
        sys.modules, "albertitos.pipeline.auditoria", types.SimpleNamespace(auditar=auditar)
    )
    assert package.auditor_de_entrega() is auditar
    monkeypatch.setitem(sys.modules, "albertitos.pipeline.auditoria", None)  # no existe
    assert package.auditor_de_entrega() is None
