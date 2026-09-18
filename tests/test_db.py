from datetime import UTC, date, datetime

from albertitos.core import db
from albertitos.core.contracts import Decision, EstadoEvento, Etapa, Event, Motivo, Resultado


def _decision(res: Resultado, norma: str = "v3") -> Decision:
    return Decision(
        file_id="a.pdf",
        sha256="a" * 64,
        resultado=res,
        motivos=[Motivo(regla_id=f"{norma}.R1", ok=res == Resultado.PAGAR, detalle="x")],
        norma_version=norma,
        fecha_corte=date(2026, 9, 18),
        hechos_hash="h",
        maestro_version="m",
        erp_version="e",
        decidido_en=datetime.now(UTC),
    )


def test_decision_nueva_desplaza_a_la_anterior(conn):
    db.guardar_fichero(
        conn, sha256="a" * 64, file_id="a.pdf", lote=1, bytes_=10, paginas=1, tiene_texto=True
    )
    db.guardar_decision(conn, _decision(Resultado.PAGAR))
    db.guardar_decision(conn, _decision(Resultado.ESCALAR, "v4"))
    vigentes = db.decisiones_vigentes(conn)
    assert (
        len(vigentes) == 1
        and vigentes[0]["resultado"] == "ESCALAR"
        and vigentes[0]["norma_version"] == "v4"
    )
    t = db.traza(conn, "a.pdf")
    assert [d["vigente"] for d in t["decisiones"]] == [0, 1]


def test_guardar_decision_sella_decidido_en_si_no_viene(conn):
    db.guardar_fichero(
        conn, sha256="a" * 64, file_id="a.pdf", lote=1, bytes_=10, paginas=1, tiene_texto=True
    )
    db.guardar_decision(conn, _decision(Resultado.PAGAR).model_copy(update={"decidido_en": None}))
    fila = db.decisiones_vigentes(conn)[0]
    assert datetime.fromisoformat(fila["decidido_en"]).tzinfo is not None


def test_eventos_y_resumen(conn):
    db.guardar_fichero(
        conn, sha256="a" * 64, file_id="a.pdf", lote=1, bytes_=10, paginas=1, tiene_texto=True
    )
    db.registrar_evento(
        conn,
        Event(
            file_id="a.pdf",
            sha256="a" * 64,
            etapa=Etapa.EXTRACT,
            estado=EstadoEvento.RETRY,
            intento=2,
            error_codigo="LLM-429",
        ),
    )
    db.registrar_evento(
        conn,
        Event(
            file_id="a.pdf",
            sha256="a" * 64,
            etapa=Etapa.EXTRACT,
            estado=EstadoEvento.OK,
            intento=3,
            latencia_ms=800,
            tokens_in=1000,
            tokens_out=200,
        ),
    )
    r = db.resumen(conn)
    assert r["ficheros"] == {1: 1}
    assert r["pendientes"] == ["a.pdf"]
    ok = next(e for e in r["eventos"] if e["estado"] == "ok")
    assert ok["reintentos"] == 1 and ok["lat_media_ms"] == 800
