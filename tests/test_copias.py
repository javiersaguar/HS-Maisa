"""P0-1: un PDF idéntico byte a byte con otro nombre, repetido del lote 1 o dos veces en el lote 2.

Antes, la ingesta reasignaba el file_id y el lote del original (el lote 1 perdía su línea: NO APTO), y
como hechos y decisiones van por sha256, las dos copias salían PAGAR: pagar dos veces la misma factura.
Ahora cada nombre tiene su línea en su lote, el original no se toca y ninguna de las dos se paga.
PDFs reales de la Caja copiados con otro nombre; maestro y ERP del fixture; sin LLM.
"""

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import InvoiceFacts, MetodoExtraccion
from albertitos.core.hashing import sha256_fichero
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline import etapas, package, traza
from albertitos.pipeline.validar import listar_pdfs, validar_jsonl
from albertitos.sources import snapshot

CORTE = date(2026, 9, 18)
X, Y, Z = "2026-01-08_P001.pdf", "F26-2201_transportes.pdf", "FA-4290_mensajería.pdf"
PAGABLE = {  # con el maestro y el ERP del fixture, sola sale PAGAR
    X: dict(
        pedido="PO-2026-0001",
        nif_emisor="B46102331",
        iban="ES2100491500051234567890",
        base=Decimal("2489.99"),
        iva=Decimal("522.90"),
        total=Decimal("3012.89"),
    ),
    Y: dict(
        pedido="PO-2026-0002",
        nif_emisor="A41220987",
        iban="ES7621000813610123456789",
        base=Decimal("780.00"),
        iva=Decimal("163.80"),
        total=Decimal("943.80"),
    ),
}


def _lote(tmp_path: Path, nombre: str, pdfs: dict[str, str], caja: Path) -> Path:
    """Carpeta de lote con `pdfs` = {nombre en el lote: PDF de la Caja del que es copia}."""
    raiz = tmp_path / nombre
    (raiz / "facturas").mkdir(parents=True)
    for destino, origen in pdfs.items():
        shutil.copy(caja / "facturas" / origen, raiz / "facturas" / destino)
    return raiz


def _hechos(conn, raiz: Path, pdfs: dict[str, str]) -> None:
    for nombre, origen in pdfs.items():
        sha = sha256_fichero(raiz / "facturas" / nombre)
        if conn.execute("SELECT 1 FROM hechos WHERE sha256=?", (sha,)).fetchone():
            continue  # una copia: los hechos van por contenido
        db.guardar_hechos(
            conn,
            InvoiceFacts(
                file_id=nombre,
                sha256=sha,
                fecha=date(2026, 1, 8),
                metodo=MetodoExtraccion.PLANTILLA,
                extractor_version=EXTRACTOR_VERSION,
                **PAGABLE.get(origen, {"pedido": "PO-2026-0009", "total": Decimal("100.00")}),
            ),
        )
    conn.commit()


def _decidir(conn, maestro, erp) -> dict[str, str]:
    etapas.marcar_duplicados(conn)
    etapas.decide(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    return {f["file_id"]: f["resultado"] for f in db.decisiones_vigentes(conn)}


def _lineas(ruta: Path) -> dict[str, dict]:
    return {o["file_id"]: o for o in map(json.loads, ruta.read_text(encoding="utf-8").splitlines())}


@pytest.fixture
def lote1(conn, caja, maestro, erp, tmp_path):
    snapshot.guardar_maestro(conn, maestro)
    snapshot.guardar_erp(conn, erp)
    pdfs = {X: X, Y: Y}
    raiz = _lote(tmp_path, "caja", pdfs, caja)
    assert etapas.ingest(conn, raiz / "facturas", 1) == 2
    _hechos(conn, raiz, pdfs)
    assert _decidir(conn, maestro, erp) == {X: "PAGAR", Y: "PAGAR"}
    return raiz


def test_copia_del_lote_1_en_el_lote_2(conn, caja, maestro, erp, tmp_path, lote1):
    antes = dict(
        conn.execute("SELECT file_id, lote FROM ficheros WHERE file_id=?", (X,)).fetchone()
    )
    pdfs2 = {"copia_de_X.pdf": X, "nueva.pdf": Z}
    lote2 = _lote(tmp_path, "lote2", pdfs2, caja)
    assert etapas.ingest(conn, lote2 / "facturas", 2) == 2
    _hechos(conn, lote2, pdfs2)

    # R1: el original sigue siendo del lote 1 con su nombre
    fila = conn.execute("SELECT file_id, lote FROM ficheros WHERE file_id=?", (X,)).fetchone()
    assert dict(fila) == antes == {"file_id": X, "lote": 1}
    # R3: ni el original ni la copia se pagan (antes de la copia, X salía PAGAR)
    resultados = _decidir(conn, maestro, erp)
    assert resultados[X] != "PAGAR" and resultados[Y] == "PAGAR"

    # R2: cada nombre, su línea en su lote, y validate lo acepta
    salida = tmp_path / "entrega"
    auditar = package.auditor_de_entrega()  # la auditoría real también sale verde
    for _ruta, inf in package.empaquetar(
        conn, salida, lote1, lote2, con_traza=True, auditar=auditar
    ):
        assert inf.ok, inf.texto()
    uno, dos = _lineas(salida / "outcomes.jsonl"), _lineas(salida / "outcomes_lote2.jsonl")
    assert set(uno) == {X, Y} and set(dos) == {"copia_de_X.pdf", "nueva.pdf"}
    assert uno[X]["result"] == dos["copia_de_X.pdf"]["result"] == resultados[X]
    assert "el mismo PDF que copia_de_X.pdf (lote 2)" in uno[X]["motivo"]
    assert f"el mismo PDF que {X} (lote 1)" in dos["copia_de_X.pdf"]["motivo"]
    assert validar_jsonl(salida / "outcomes_lote2.jsonl", listar_pdfs(lote2 / "facturas"), 2).ok

    # la traza de la copia lleva a su PDF y nombra al original, y la del original a la copia
    t = traza.legible(conn, "copia_de_X.pdf")
    assert f"copia exacta de {X} (lote 1)" in t and "4 DUPLICADO" in t
    assert f"comparte el mismo PDF (copia exacta, lote 1) con {X}" in t
    assert "entregado" in t and "outcomes_lote2.jsonl" in t
    assert "comparte el mismo PDF (copia exacta, lote 2) con copia_de_X.pdf" in traza.legible(
        conn, X
    )


def test_dos_nombres_con_el_mismo_contenido_dentro_del_lote_2(
    conn, caja, maestro, erp, tmp_path, lote1
):
    pdfs2 = {"dup_a.pdf": Z, "dup_b.pdf": Z, "otra.pdf": Y}  # otra.pdf: copia de Y del lote 1
    lote2 = _lote(tmp_path, "lote2", pdfs2, caja)
    etapas.ingest(conn, lote2 / "facturas", 2)
    _hechos(conn, lote2, pdfs2)
    assert conn.execute("SELECT count(*) FROM identidades").fetchone()[0] == 2  # dup_b, otra
    _decidir(conn, maestro, erp)

    salida = tmp_path / "entrega"
    package.empaquetar(conn, salida, lote1, lote2, con_traza=True)
    dos = _lineas(salida / "outcomes_lote2.jsonl")
    assert set(dos) == set(pdfs2)
    assert "PAGAR" not in {
        dos["otra.pdf"]["result"],
        _lineas(salida / "outcomes.jsonl")[Y]["result"],
    }


def test_idempotente_y_reprocess_no_pierde_ninguna(conn, caja, maestro, erp, tmp_path, lote1):
    pdfs2 = {"copia_de_X.pdf": X}
    lote2 = _lote(tmp_path, "lote2", pdfs2, caja)
    etapas.ingest(conn, lote2 / "facturas", 2)
    _decidir(conn, maestro, erp)
    salida = tmp_path / "entrega"
    package.empaquetar(conn, salida, lote1, lote2, con_traza=True)
    primera = [(salida / n).read_bytes() for n in ("outcomes.jsonl", "outcomes_lote2.jsonl")]

    # R4: reingerir los dos lotes no crea nada; repetir duplicados/decide/package da los mismos bytes
    assert etapas.ingest(conn, lote1 / "facturas", 1) == 0
    assert etapas.ingest(conn, lote2 / "facturas", 2) == 0
    assert conn.execute("SELECT count(*) FROM identidades").fetchone()[0] == 1
    assert etapas.marcar_duplicados(conn) == (0, 0)
    etapas.decide(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    package.empaquetar(conn, salida, lote1, lote2, con_traza=True)
    assert [
        (salida / n).read_bytes() for n in ("outcomes.jsonl", "outcomes_lote2.jsonl")
    ] == primera


def test_sin_marcar_duplicados_la_auditoria_no_deja_pagar_dos_veces(
    conn, caja, maestro, erp, tmp_path, lote1
):
    """Red de seguridad: con pasos sueltos (ingest + decide, sin marcar_duplicados), la copia sale
    PAGAR como el original; la auditoría lo ve como pago doble y package se niega."""
    pytest.importorskip("albertitos.pipeline.auditoria")
    lote2 = _lote(tmp_path, "lote2", {"copia_de_X.pdf": X}, caja)
    etapas.ingest(conn, lote2 / "facturas", 2)
    etapas.decide(conn, norma_version="v3", fecha_corte=CORTE, maestro=maestro, erp=erp)
    auditar = package.auditor_de_entrega()
    with pytest.raises(package.EntregaInvalida) as exc:
        package.empaquetar(conn, tmp_path / "e", lote1, lote2, con_traza=True, auditar=auditar)
    rojos = exc.value.informe.rojos
    assert {X, "copia_de_X.pdf"} <= {f for fids in rojos.values() for f in fids}


def test_renombrar_dentro_del_mismo_lote_sigue_siendo_renombrar(conn, caja, tmp_path):
    raiz = _lote(tmp_path, "caja", {X: X}, caja)
    etapas.ingest(conn, raiz / "facturas", 1)
    (raiz / "facturas" / X).rename(raiz / "facturas" / "renombrada.pdf")
    assert etapas.ingest(conn, raiz / "facturas", 1) == 1
    assert [r["file_id"] for r in db.ficheros(conn)] == ["renombrada.pdf"]
    assert conn.execute("SELECT count(*) FROM identidades").fetchone()[0] == 0


def test_una_bd_anterior_sin_la_tabla_se_lee_igual(conn, caja, maestro, erp, tmp_path, lote1):
    """`status` y `trace` abren en sólo lectura sin init_schema: el kit de la demo tiene el esquema v2."""
    conn.execute("DROP TABLE identidades")
    conn.commit()
    assert db.nombres_por_sha(conn) == {} and db.identidades_vigentes(conn, 2) == []
    assert db.resumen(conn)["copias"] == {}
    assert db.traza(conn, "no-existe.pdf")["fichero"] is None
    assert traza.legible(conn, X).startswith(X)
