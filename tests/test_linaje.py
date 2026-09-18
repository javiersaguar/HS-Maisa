"""Linaje granular: sólo se recalcula lo que el cambio toca, y las no afectadas no salen impactadas siempre."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    ErpEntry,
    ErpSnapshot,
    InvoiceFacts,
    MasterSnapshot,
    MetodoExtraccion,
    Pedido,
    Proveedor,
)
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, linaje
from albertitos.pipeline.run import MAESTRO_XLSX, reprocesar
from albertitos.rules import REGISTRO
from albertitos.sources import excel, snapshot

CORTE = date(2026, 9, 18)
P001 = dict(nif_emisor="B46102331", iban="ES2100491500051234567890")
P002 = dict(nif_emisor="A41220987", iban="ES7621000813610123456789")


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


def _evaluar(conn, maestro, erp, **kw) -> linaje.Linaje:
    args = dict(
        norma_version="v3",
        fecha_corte=CORTE,
        maestro=maestro,
        erp=erp,
        extractor_version=EXTRACTOR_VERSION,
    )
    return linaje.evaluar(conn, **{**args, **kw})


def _reprocesar(conn, maestro, erp):
    return reprocesar(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)


def _vigentes(conn, campo: str = "resultado") -> dict[str, str]:
    return {r["file_id"]: r[campo] for r in db.decisiones_vigentes(conn)}


@pytest.fixture
def base(conn, maestro, erp):
    """a PAGAR (PO-0001, P001) · b PAGAR (PO-0002, P002) · c NO_PAGAR (PO-0009 ya PAGADA, P001) ·
    d sin hechos. Todo decidido con maestro m-test y ERP e-test."""
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
    _factura(
        conn,
        "c.pdf",
        pedido="PO-2026-0009",
        base=Decimal("82.64"),
        iva=Decimal("17.36"),
        total=Decimal("100.00"),
        **P001,
    )
    db.guardar_fichero(
        conn, sha256="d" * 64, file_id="d.pdf", lote=1, bytes_=1, paginas=1, tiene_texto=False
    )
    etapas.decide(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    assert _vigentes(conn) == {"a.pdf": "PAGAR", "b.pdf": "PAGAR", "c.pdf": "NO_PAGAR"}


def test_sin_cambios_no_hay_nada_que_recalcular(conn, base, maestro, erp):
    lin = _evaluar(conn, maestro, erp)
    assert lin.impactados == {}
    assert lin.sin_impacto == []
    assert lin.pendientes == ["d.pdf"]  # sin hechos: no se puede decidir
    assert lin.total == 4


def test_erp_solo_recalcula_el_pedido_que_cambia_y_vuelve(conn, base, maestro, erp):
    erp2 = erp.model_copy(deep=True, update={"version": "e2"})
    erp2.asientos["AS-00001"].estado = "PAGADA"
    snapshot.guardar_erp(conn, erp2)

    r = _reprocesar(conn, maestro, erp2)
    assert r.impactados == {"a.pdf": "erp e-test→e2: PO-2026-0001"}
    assert (r.recalculadas, r.sin_impacto, r.total) == (1, 2, 4)
    assert [(c["file_id"], c["antes"], c["despues"]) for c in r.cambios] == [
        ("a.pdf", "PAGAR", "NO_PAGAR")
    ]
    # las no afectadas conservan la versión con la que se decidieron y no vuelven a salir
    assert _vigentes(conn, "erp_version") == {"a.pdf": "e2", "b.pdf": "e-test", "c.pdf": "e-test"}
    r2 = _reprocesar(conn, maestro, erp2)
    assert r2.impactados == {} and r2.cambios == []  # el diff es de esta pasada, no global

    r3 = _reprocesar(conn, maestro, erp)  # volver al ERP anterior: sólo a
    assert r3.impactados == {"a.pdf": "erp e2→e-test: PO-2026-0001"}
    assert [(c["file_id"], c["despues"]) for c in r3.cambios] == [("a.pdf", "PAGAR")]


def test_maestro_impacta_por_nif_y_por_pedido(conn, base, maestro, erp):
    m2 = maestro.model_copy(deep=True, update={"version": "m2"})
    m2.proveedores["P002"].iban = "ES9100000000000000000000"
    m2.pedidos["PO-2026-0009"].importe_total = Decimal("101.00")
    snapshot.guardar_maestro(conn, m2)
    lin = _evaluar(conn, m2, erp)
    assert lin.impactados == {
        "b.pdf": "maestro m-test→m2: NIF A41220987",
        "c.pdf": "maestro m-test→m2: PO-2026-0009",
    }
    assert [s["file_id"] for s in lin.sin_impacto] == ["a.pdf"]
    assert lin.sin_impacto[0]["maestro"] == "m-test→m2"


@pytest.mark.parametrize(
    ("cambio", "motivo"),
    [
        ({"norma_version": "v4"}, "norma v3→v4"),
        ({"fecha_corte": date(2026, 9, 19)}, "fecha de corte 2026-09-18→2026-09-19"),
        ({"todo": True}, "recálculo completo (--todo)"),
    ],
)
def test_norma_corte_y_todo_recalculan_todo(conn, base, maestro, erp, cambio, motivo):
    lin = _evaluar(conn, maestro, erp, **cambio)
    assert lin.impactados == {f: motivo for f in ("a.pdf", "b.pdf", "c.pdf")}


def test_hechos_cambiados_y_fichero_nuevo(conn, base, maestro, erp):
    a = InvoiceFacts.model_validate_json(
        conn.execute("SELECT hechos_json FROM hechos WHERE sha256=?", ("a" * 64,)).fetchone()[0]
    )
    db.guardar_hechos(conn, a.model_copy(update={"total": Decimal("3012.90")}))
    _factura(conn, "e.pdf", pedido="PO-2026-0002", **P002)
    assert _evaluar(conn, maestro, erp).impactados == {
        "a.pdf": "hechos cambiados",
        "e.pdf": "sin decisión",
    }


def test_sin_snapshot_de_origen_recalcula_por_prudencia(conn, base, maestro, erp):
    erp2 = erp.model_copy(update={"version": "e2"})
    conn.execute("DELETE FROM snapshots WHERE tipo='erp' AND version='e-test'")
    lin = _evaluar(conn, maestro, erp2)
    assert set(lin.impactados) == {"a.pdf", "b.pdf", "c.pdf"}
    assert lin.impactados["b.pdf"] == "erp e-test→e2: no está el snapshot e-test"


def test_sin_impacto_deja_un_evento_una_sola_vez(conn, base, maestro, erp):
    erp2 = erp.model_copy(deep=True, update={"version": "e2"})
    erp2.asientos["AS-00001"].estado = "PAGADA"
    snapshot.guardar_erp(conn, erp2)
    _reprocesar(conn, maestro, erp2)
    _reprocesar(conn, maestro, erp2)
    skips = conn.execute(
        "SELECT file_id, detalle FROM eventos WHERE etapa='decide' AND estado='skip' ORDER BY file_id"
    ).fetchall()
    assert [s["file_id"] for s in skips] == ["b.pdf", "c.pdf"]
    assert '"erp": "e-test→e2"' in skips[0]["detalle"]
    por = conn.execute(
        "SELECT detalle FROM eventos WHERE etapa='decide' AND estado='ok' AND file_id='a.pdf' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()["detalle"]
    assert "erp e-test→e2: PO-2026-0001" in por  # la traza dice por qué se recalculó


def test_duplicados_se_ponen_y_se_quitan(conn, base, maestro, erp):
    """El ensayo del lote 2: una copia del mismo pedido escala las dos; al borrarla, a vuelve a PAGAR."""
    _factura(conn, "e.pdf", pedido="PO-2026-0001", total=Decimal("3012.89"), **P001)
    r = _reprocesar(conn, maestro, erp)
    assert r.duplicados == (2, 0)
    assert r.impactados == {"a.pdf": "hechos cambiados", "e.pdf": "sin decisión"}
    assert _vigentes(conn)["a.pdf"] == "ESCALAR"

    for tabla in ("eventos", "decisiones", "hechos", "ficheros"):
        conn.execute(f"DELETE FROM {tabla} WHERE sha256=?", ("e" * 64,))
    r = _reprocesar(conn, maestro, erp)
    assert r.duplicados == (0, 1)
    assert [(c["file_id"], c["despues"]) for c in r.cambios] == [("a.pdf", "PAGAR")]
    h = conn.execute("SELECT hechos_json FROM hechos WHERE sha256=?", ("a" * 64,)).fetchone()[0]
    assert Aviso.DUPLICADO_SOSPECHOSO.value not in h


# ----------------------------------------------------------------------------- la suposición del linaje


def _perturbar(
    m: MasterSnapshot, e: ErpSnapshot, pedido: str | None, nif: str | None
) -> tuple[MasterSnapshot, ErpSnapshot]:
    """Cambia todo lo del maestro y del ERP que NO es el pedido ni el NIF de la factura."""
    m2, e2 = m.model_copy(deep=True), e.model_copy(deep=True)
    for k, p in m2.pedidos.items():
        if k != pedido:
            p.importe_total += 1
            p.estado = "CERRADO"
    m2.pedidos["PO-9999-9999"] = Pedido(
        pedido="PO-9999-9999",
        proveedor_id="P999",
        nif="X0000000T",
        importe_total=Decimal(1),
        estado="ABIERTO",
    )
    for p in m2.proveedores.values():
        if linaje.clave_nif(p.nif) != nif:
            p.iban, p.razon_social, p.condiciones_dias = "ES9100000000000000000000", "Otra", 1
    m2.proveedores["P999"] = Proveedor(
        id="P999", razon_social="Nueva", nif="X0000000T", iban="ES9100000000000000000000"
    )
    for a in e2.asientos.values():
        if a.pedido != pedido:
            a.importe_esperado += 1
            a.estado = "PAGADA" if a.estado == "PENDIENTE" else "PENDIENTE"
    e2.asientos["AS-99999"] = ErpEntry(
        asiento_id="AS-99999",
        fecha_registro=date(2026, 1, 1),
        proveedor_id="P999",
        nif="X0000000T",
        pedido="PO-9999-9999",
        importe_esperado=Decimal(1),
        estado="PAGADA",
    )
    return m2, e2


@pytest.mark.parametrize("norma", sorted(REGISTRO))
def test_la_norma_solo_lee_su_pedido_y_su_nif(caja, norma):
    """El linaje granular es correcto sólo si esto se cumple. Si la v4 lee algo más (acumulados por
    proveedor, otros pedidos...), este test falla: ampliar las claves en linaje.py o usar --todo."""
    maestro = excel.cargar_maestro(caja / MAESTRO_XLSX)
    asientos = {
        f"AS-{i:05d}": ErpEntry(
            asiento_id=f"AS-{i:05d}",
            fecha_registro=date(2026, 1, 1),
            proveedor_id=p.proveedor_id,
            nif=p.nif,
            pedido=p.pedido,
            importe_esperado=p.importe_total,
            estado="PAGADA" if i % 7 == 0 else "PENDIENTE",
        )
        for i, p in enumerate(maestro.pedidos.values())
    }
    erp = ErpSnapshot(version="e", asientos=asientos, descargado_en=maestro.cargado_en)
    ctx = ContextoDecision(
        norma_version=norma, fecha_corte=CORTE, maestro_version=maestro.version, erp_version="e"
    )
    decidir = REGISTRO[norma].decidir
    lineas = Path("data/fixtures/hechos_muestra.jsonl").read_text(encoding="utf-8").splitlines()
    assert lineas
    for linea in lineas:
        h = InvoiceFacts.model_validate_json(linea)
        m2, e2 = _perturbar(maestro, erp, h.pedido, linaje.clave_nif(h.nif_emisor))
        antes, despues = decidir(h, maestro, erp, ctx), decidir(h, m2, e2, ctx)
        assert (despues.resultado, despues.motivos) == (antes.resultado, antes.motivos), h.file_id
