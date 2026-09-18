"""`run` de principio a fin sin LLM: hechos ya en la BD → duplicados → decide → package.

Tres PDFs reales de la Caja (uno con tilde) copiados a una Caja temporal; ERP del fixture en memoria.
"""

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

from albertitos.core import db
from albertitos.core.contracts import InvoiceFacts, MetodoExtraccion
from albertitos.core.hashing import sha256_fichero
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas
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
