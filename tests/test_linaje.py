from datetime import UTC, date, datetime
from decimal import Decimal

from albertitos.core import db
from albertitos.core.contracts import Decision, InvoiceFacts, MetodoExtraccion, Motivo, Resultado
from albertitos.pipeline.linaje import impactados


def test_impactados_por_norma_erp_y_hechos(conn):
    db.guardar_fichero(
        conn, sha256="a" * 64, file_id="a.pdf", lote=1, bytes_=1, paginas=1, tiene_texto=True
    )
    db.guardar_fichero(
        conn, sha256="b" * 64, file_id="b.pdf", lote=1, bytes_=1, paginas=1, tiene_texto=True
    )
    h = InvoiceFacts(
        file_id="a.pdf",
        sha256="a" * 64,
        metodo=MetodoExtraccion.CACHE,
        extractor_version="ext-0.1",
        total=Decimal("1.00"),
    )
    db.guardar_hechos(conn, h)
    d = Decision(
        file_id="a.pdf",
        sha256="a" * 64,
        resultado=Resultado.PAGAR,
        motivos=[Motivo(regla_id="v3.R1", ok=True, detalle="")],
        norma_version="v3",
        fecha_corte=date(2026, 9, 18),
        hechos_hash=h.hash(),
        maestro_version="m1",
        erp_version="v1",
        decidido_en=datetime.now(UTC),
    )
    db.guardar_decision(conn, d)
    conn.commit()
    kw = dict(
        norma_version="v3", maestro_version="m1", erp_version="v1", extractor_version="ext-0.1"
    )
    assert impactados(conn, **kw) == ["b.pdf"]  # b no tiene hechos ni decisión
    assert impactados(conn, **{**kw, "norma_version": "v4"}) == ["a.pdf", "b.pdf"]
    assert impactados(conn, **{**kw, "erp_version": "v2"}) == ["a.pdf", "b.pdf"]
    db.guardar_hechos(conn, h.model_copy(update={"total": Decimal("2.00")}))
    assert impactados(conn, **kw) == ["a.pdf", "b.pdf"]  # cambiaron los hechos de a
