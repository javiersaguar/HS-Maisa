"""Puente HTTP de la consola: lecturas sobre una BD de fixture, sin rules/ ni extract/."""

from __future__ import annotations

import ast
import hashlib
import unicodedata
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

from albertitos.console import api, bandeja, lecturas
from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    Decision,
    EstadoEvento,
    Etapa,
    Event,
    InvoiceFacts,
    MetodoExtraccion,
    Motivo,
    Resultado,
)

CORTE = date(2026, 9, 18)
TILDE = "FA-5590_ofimática.pdf"


def _sha(file_id: str) -> str:
    return hashlib.sha256(file_id.encode()).hexdigest()


def _hechos(file_id: str, **kw) -> InvoiceFacts:
    base = dict(
        file_id=file_id,
        sha256=_sha(file_id),
        num_factura="F-1",
        fecha=date(2026, 1, 8),
        razon_social="Suministros Levante S.L.",
        nif_emisor="B46102331",
        iban="ES2100491500051234567890",
        pedido="PO-2026-0001",
        total=Decimal("3012.89"),
        metodo=MetodoExtraccion.PLANTILLA,
        extractor_version="ext-0.1",
    )
    base.update(kw)
    return InvoiceFacts(**base)


def _alta(
    conn,
    file_id: str,
    *,
    lote: int = 1,
    resultado: Resultado | None = Resultado.PAGAR,
    motivos: list[Motivo] | None = None,
    hechos: InvoiceFacts | None = None,
    ts: datetime | None = None,
):
    h = hechos or _hechos(file_id)
    db.guardar_fichero(
        conn,
        sha256=h.sha256,
        file_id=h.file_id,
        lote=lote,
        bytes_=10,
        paginas=1,
        tiene_texto=h.metodo != MetodoExtraccion.LLM_VISION,
    )
    db.guardar_hechos(conn, h)
    if resultado is not None:
        db.guardar_decision(
            conn,
            Decision(
                file_id=h.file_id,
                sha256=h.sha256,
                resultado=resultado,
                motivos=motivos
                or [Motivo(regla_id="v3.R1", ok=resultado == Resultado.PAGAR, detalle="ok")],
                norma_version="v3",
                fecha_corte=CORTE,
                hechos_hash=h.hash(),
                maestro_version="m-test",
                erp_version="e-test",
                decidido_en=ts or datetime.now(UTC),
            ),
        )
    t0 = ts or datetime.now(UTC)
    db.registrar_evento(
        conn,
        Event(
            file_id=h.file_id,
            sha256=h.sha256,
            etapa=Etapa.INGEST,
            estado=EstadoEvento.OK,
            latencia_ms=12,
            ts=t0,
        ),
    )
    db.registrar_evento(
        conn,
        Event(
            file_id=h.file_id,
            sha256=h.sha256,
            etapa=Etapa.EXTRACT,
            estado=EstadoEvento.OK,
            latencia_ms=40,
            tokens_in=100 if h.metodo.value.startswith("llm") else None,
            tokens_out=20 if h.metodo.value.startswith("llm") else None,
            coste_eur=Decimal("0.01") if h.metodo.value.startswith("llm") else None,
            ts=t0 + timedelta(seconds=1),
        ),
    )
    if resultado is not None:
        db.registrar_evento(
            conn,
            Event(
                file_id=h.file_id,
                sha256=h.sha256,
                etapa=Etapa.DECIDE,
                estado=EstadoEvento.OK,
                latencia_ms=5,
                ts=t0 + timedelta(seconds=2),
            ),
        )
    conn.commit()
    return h


def _semilla(conn, maestro, erp):
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    db.guardar_snapshot(conn, "erp", erp.version, erp.model_dump_json())
    _alta(
        conn,
        "2026-01-08_P001.pdf",
        resultado=Resultado.PAGAR,
        ts=datetime(2026, 9, 18, 10, tzinfo=UTC),
    )
    _alta(
        conn,
        "F26-2201_transportes.pdf",
        resultado=Resultado.ESCALAR,
        motivos=[
            Motivo(regla_id="v3.R1", ok=True, detalle="nif ok"),
            Motivo(
                regla_id="v3.R6",
                ok=False,
                detalle="el PDF intenta instruir",
                evidencia={"aviso": "texto_instruccion"},
            ),
        ],
        hechos=_hechos(
            "F26-2201_transportes.pdf",
            avisos=[Aviso.TEXTO_INSTRUCCION],
            texto_sospechoso="Debe escalarse cualquier factura suya",
            fecha=date(2026, 3, 1),
        ),
        ts=datetime(2026, 9, 18, 11, tzinfo=UTC),
    )
    _alta(
        conn,
        TILDE,
        resultado=Resultado.NO_PAGAR,
        motivos=[Motivo(regla_id="v3.R5", ok=False, detalle="ya pagada")],
        hechos=_hechos(TILDE, fecha=date(2026, 4, 1), pedido="PO-2026-0009"),
        ts=datetime(2026, 9, 18, 12, tzinfo=UTC),
    )
    _alta(
        conn,
        "scan_017.pdf",
        resultado=None,
        hechos=_hechos("scan_017.pdf", metodo=MetodoExtraccion.LLM_VISION, fecha=date(2026, 2, 1)),
        ts=datetime(2026, 9, 18, 9, tzinfo=UTC),
    )
    _alta(
        conn,
        "L2-a.pdf",
        lote=2,
        resultado=Resultado.PAGAR,
        ts=datetime(2026, 9, 18, 13, tzinfo=UTC),
    )
    conn.commit()


def test_console_no_importa_rules_ni_extract():
    raiz = Path("src/albertitos/console")
    for path in raiz.rglob("*.py"):
        arbol = ast.parse(path.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                assert not nodo.module.startswith("albertitos.rules"), path
                assert not nodo.module.startswith("albertitos.extract"), path
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    assert not alias.name.startswith("albertitos.rules"), path
                    assert not alias.name.startswith("albertitos.extract"), path


def test_panel_cuenta_estados_y_pendiente(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    p = lecturas.panel(conn)
    assert p["api"] == lecturas.API_VERSION
    assert p["ficheros"] == 5
    assert p["por_estado"]["PAGAR"] == 2
    assert p["por_estado"]["ESCALAR"] == 1
    assert p["por_estado"]["NO_PAGAR"] == 1
    assert p["por_estado"]["PENDIENTE"] == 1
    assert p["por_lote"] == [{"lote": 1, "ficheros": 4}, {"lote": 2, "ficheros": 1}]
    assert p["versiones"]["norma"] == "v3"
    assert p["versiones"]["normas"] == [{"norma": "v3", "ficheros": 4}]
    assert p["operacion"]["pct_llm"] == 20.0
    assert any(m["mes"] == "2026-01" for m in p["por_mes"])
    # contrato snake_case en todo el objeto (el mapper del frontend lo traduce; no se mezcla)
    etapa = p["etapas"][0]
    assert {"ficheros_ok", "por_estado", "latencia_media_ms", "ultimo_evento_en"} <= etapa.keys()
    assert not any(k for k in etapa if k != k.lower())


def test_panel_no_hardcodea_la_norma_y_reparte_v3_v4(conn, maestro, erp):
    """Cuando conviven v3 y v4 (sábado 18:00), `norma` es la vigente más reciente y `normas` las cuenta."""
    _semilla(conn, maestro, erp)
    h = _hechos("v4.pdf", fecha=date(2026, 5, 1))
    _alta(
        conn,
        "v4.pdf",
        hechos=h,
        resultado=Resultado.ESCALAR,
        ts=datetime(2026, 9, 19, 18, tzinfo=UTC),
    )
    db.guardar_decision(
        conn,
        Decision(
            file_id=h.file_id,
            sha256=h.sha256,
            resultado=Resultado.ESCALAR,
            motivos=[Motivo(regla_id="v4.R6", ok=False, detalle="instrucción")],
            norma_version="v4",
            fecha_corte=CORTE,
            hechos_hash=h.hash(),
            maestro_version="m-test",
            erp_version="e-test",
            decidido_en=datetime(2026, 9, 19, 18, 1, tzinfo=UTC),
        ),
    )
    conn.commit()
    p = lecturas.panel(conn)
    assert p["versiones"]["norma"] == "v4"
    assert {n["norma"]: n["ficheros"] for n in p["versiones"]["normas"]} == {"v3": 4, "v4": 1}


def test_listado_filtra_escalar_regla_lote_y_no_trae_fuentes(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    esc = lecturas.listar_ficheros(conn, estado="ESCALAR")
    assert esc["api"] == lecturas.API_VERSION and esc["page_size"] == lecturas.PAGE_SIZE_DEFECTO
    assert esc["total"] == 1
    assert esc["items"][0]["file_id"] == "F26-2201_transportes.pdf"
    assert esc["items"][0]["fuentes"] is None
    assert all(i["decision"]["resultado"] != "PAGAR" for i in esc["items"])

    r6 = lecturas.listar_ficheros(conn, regla="R6")
    assert r6["total"] == 1 and r6["items"][0]["file_id"] == "F26-2201_transportes.pdf"

    lote2 = lecturas.listar_ficheros(conn, lote=2)
    assert lote2["total"] == 1 and lote2["items"][0]["file_id"] == "L2-a.pdf"

    pend = lecturas.listar_ficheros(conn, estado="PENDIENTE")
    assert pend["total"] == 1 and pend["items"][0]["decision"] is None

    # la exportación CSV pide todos de golpe: la página puede ser mayor que 200
    todos = lecturas.listar_ficheros(conn, page_size=600)
    assert todos["page_size"] == 600 and len(todos["items"]) == 5


def test_filtro_regla_vale_para_v3_y_v4(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    h = _hechos("v4.pdf", fecha=date(2026, 5, 1))
    _alta(
        conn,
        "v4.pdf",
        hechos=h,
        resultado=Resultado.ESCALAR,
        motivos=[Motivo(regla_id="v4.R6", ok=False, detalle="instrucción")],
    )
    r6 = lecturas.listar_ficheros(conn, regla="R6")
    assert {i["file_id"] for i in r6["items"]} == {"F26-2201_transportes.pdf", "v4.pdf"}
    # una regla que sólo se cumple (ok=1) no cuenta como incumplida
    assert lecturas.listar_ficheros(conn, regla="R1")["total"] == 0


def test_detalle_nfc_fuentes_y_404(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    nfd = unicodedata.normalize("NFD", TILDE)
    assert nfd != TILDE
    fila = lecturas.fichero(conn, nfd)
    assert fila is not None and fila["file_id"] == TILDE
    assert fila["fuentes"]["pedido"]["pedido"] == "PO-2026-0009"
    assert fila["fuentes"]["proveedor"]["id"] == "P001"
    assert fila["fuentes"]["asientos"][0]["estado"] == "PAGADA"
    assert lecturas.fichero(conn, "no-existe.pdf") is None


def test_detalle_sin_snapshot_devuelve_fuentes_vacias(conn):
    """Sin snapshots (BD recién ingerida) el detalle no falla: versiones nulas y listas vacías."""
    _alta(conn, "solo.pdf", resultado=None)
    fila = lecturas.fichero(conn, "solo.pdf")
    assert fila is not None
    assert fila["fuentes"] == {
        "maestro_version": None,
        "erp_version": None,
        "proveedor": None,
        "pedido": None,
        "asientos": [],
    }
    assert lecturas.traza_pasos(conn, file_id="solo.pdf") is not None


def test_identidades_es_opcional_y_no_pisa_el_original(conn, maestro, erp):
    """P0-1 de Miguel: un PDF idéntico con dos nombres. Con fila en `identidades`, el segundo nombre
    responde 200 con la decisión del sha256; el original sigue igual. Sin fila (o sin tabla), 404."""
    _semilla(conn, maestro, erp)
    original = "F26-2201_transportes.pdf"
    copia = "F26-2201_transportes (copia).pdf"
    assert lecturas.fichero(conn, copia) is None
    assert lecturas.traza_pasos(conn, file_id=copia) is None

    sha = _sha(original)
    db.guardar_identidad(conn, file_id=copia, lote=2, sha256=sha)
    conn.commit()

    fila = lecturas.fichero(conn, copia)
    assert fila is not None
    assert fila["file_id"] == copia and fila["sha256"] == sha and fila["lote"] == 2
    assert fila["decision"]["resultado"] == "ESCALAR" and fila["decision"]["file_id"] == copia
    assert fila["fuentes"]["proveedor"] is not None

    orig = lecturas.fichero(conn, original)
    assert orig is not None and orig["file_id"] == original and orig["lote"] == 1

    pasos = lecturas.traza_pasos(conn, file_id=copia)
    assert pasos and all(p["file_id"] == copia for p in pasos)
    assert any(p["tipo"] == "motivo" for p in pasos)

    status, body = api.despachar("GET", "/ficheros/" + quote(copia), {}, conn)
    assert status == 200 and body["file_id"] == copia
    assert lecturas.salud(conn)["bd"]["identidades"] is True

    conn.execute("DROP TABLE identidades")
    conn.commit()
    assert lecturas.salud(conn)["bd"]["identidades"] is False
    assert lecturas.fichero(conn, copia) is None
    status, _body = api.despachar("GET", "/ficheros/" + quote(copia), {}, conn)
    assert status == 404


def test_coste_del_panel_es_el_de_la_extraccion_vigente(conn, maestro, erp):
    """El panel no suma el histórico: una reextracción deja atrás lo gastado en la anterior."""
    _semilla(conn, maestro, erp)
    op = lecturas.panel(conn)["operacion"]
    assert op["coste_eur"] == 0.01  # scan_017 (visión) es el único extract con coste
    assert op["coste_eur_historico"] == 0.01
    # la semilla separa cada fichero una hora: la última pasada es sólo L2-a (ingest → extract, 1 s)
    assert op["ventana"]["ficheros"] == 1 and op["ventana"]["segundos"] == 1.0
    assert op["ficheros_s"] == 1.0

    h = _hechos("scan_017.pdf", metodo=MetodoExtraccion.LLM_VISION, fecha=date(2026, 2, 1))
    for intento, estado, coste in ((1, EstadoEvento.RETRY, "0.02"), (2, EstadoEvento.OK, "0.03")):
        db.registrar_evento(
            conn,
            Event(
                file_id=h.file_id,
                sha256=h.sha256,
                etapa=Etapa.EXTRACT,
                estado=estado,
                intento=intento,
                coste_eur=Decimal(coste),
                ts=datetime(2026, 9, 19, 12, 0, intento, tzinfo=UTC),
            ),
        )
    conn.commit()
    op = lecturas.panel(conn)["operacion"]
    assert op["coste_eur"] == 0.05  # sólo la última extracción, con su reintento
    assert op["coste_eur_historico"] == 0.06
    # la última pasada de ingest/extract es la relectura de hoy, no el run de ayer
    assert op["ventana"]["ficheros"] == 1
    assert op["ventana"]["hasta"].startswith("2026-09-19T12:00:02")


def test_salud_responde_sin_bd_y_con_bd(conn, maestro, erp):
    status, body = api.despachar("GET", "/salud", {}, None)
    assert (
        status == 200 and body["ok"] and body["bd"] is None and body["api"] == lecturas.API_VERSION
    )
    status, body = api.despachar("GET", "/panel", {}, None)
    assert status == 503 and "make db" in body["error"]

    _semilla(conn, maestro, erp)
    status, body = api.despachar("GET", "/salud", {}, conn)
    assert status == 200
    assert body["bd"]["ficheros"] == 5 and body["bd"]["decisiones_vigentes"] == 4
    assert body["bd"]["pendientes"] == 1 and body["bd"]["versiones"]["norma"] == "v3"
    status, _ = api.despachar("HEAD", "/panel", {}, conn)
    assert status == 200


def test_traza_inserta_motivos_tras_decide(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    pasos = lecturas.traza_pasos(conn, file_id="F26-2201_transportes.pdf")
    assert pasos is not None
    tipos = [p["tipo"] for p in pasos]
    assert "evento" in tipos and "motivo" in tipos
    decide_idx = next(
        i for i, p in enumerate(pasos) if p["tipo"] == "evento" and p["evento"]["etapa"] == "decide"
    )
    assert pasos[decide_idx + 1]["tipo"] == "motivo"
    assert any(p["tipo"] == "motivo" and not p["motivo"]["ok"] for p in pasos)
    norma = lecturas.traza_pasos(conn, file_id="F26-2201_transportes.pdf", categoria="norma")
    assert norma and all(p["tipo"] == "motivo" for p in norma)
    assert lecturas.traza_pasos(conn, file_id="fantasma.pdf") is None


def test_despachar_rutas_y_tilde(conn, maestro, erp):
    _semilla(conn, maestro, erp)
    status, body = api.despachar("GET", "/panel", {}, conn)
    assert status == 200 and body["ficheros"] == 5

    status, body = api.despachar("GET", "/ficheros", {"estado": ["ESCALAR"]}, conn)
    assert status == 200 and body["total"] == 1

    status, body = api.despachar("GET", f"/ficheros/{TILDE}", {}, conn)
    assert status == 200 and body["file_id"] == TILDE and body["fuentes"]["asientos"]

    status, body = api.despachar("GET", "/ficheros/" + quote(TILDE), {}, conn)
    assert status == 200 and body["file_id"] == TILDE

    status, body = api.despachar("GET", "/ficheros/no.pdf", {}, conn)
    assert status == 404

    status, body = api.despachar("GET", "/traza", {"file_id": ["F26-2201_transportes.pdf"]}, conn)
    assert status == 200 and any(p["tipo"] == "motivo" for p in body)

    status, body = api.despachar("POST", "/panel", {}, conn)
    assert status == 405

    status, body = api.despachar("GET", "/etapas", {}, conn)
    assert status == 200 and len(body["etapas"]) == 6
    assert body["api"] == lecturas.API_VERSION

    nfd = unicodedata.normalize("NFD", TILDE)
    status, body = api.despachar("GET", "/traza", {"file_id": [nfd]}, conn)
    assert status == 200 and body and all(p["file_id"] == TILDE for p in body)

    status, body = api.despachar("GET", "/eventos", {"limit": ["5"]}, conn)
    assert status == 200 and 1 <= len(body) <= 5
    assert {"file_id", "etapa", "estado", "ts"} <= body[0].keys()


def test_console_no_usa_fecha_de_hoy():
    """La consola no decide; fecha_corte llega de la decisión. Nada de date.today()."""
    raiz = Path("src/albertitos/console")
    for path in raiz.rglob("*.py"):
        texto = path.read_text(encoding="utf-8")
        assert "date.today" not in texto, path


# ------------------------------------------------------------------------ bandeja (POST /inbox)
# Lo que se vigila es lo que rompería la entrega o enseñaría una decisión ajena: que la bandeja escriba
# en la BD de la entrega, fuera del lote 99, o que un PDF subido con el nombre de uno de la Caja
# muestre la decisión del original. El runner falso hace la ingest de verdad (sin LLM) y finge el
# resto; `test_inbox_cli_real_*` pasa por la CLI entera con un PDF de texto de la Caja.

CAJA = Path("data/caja/facturas")


def _pdf(texto: str) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), texto)
    try:
        return doc.tobytes()
    finally:
        doc.close()


def _multipart(*ficheros: tuple[str, bytes]) -> tuple[bytes, str]:
    frontera = "----albertitos"
    partes = b""
    for nombre, datos in ficheros:
        partes += (
            (
                f"--{frontera}\r\n"
                f'Content-Disposition: form-data; name="ficheros"; filename="{nombre}"\r\n'
                "Content-Type: application/pdf\r\n\r\n"
            ).encode()
            + datos
            + b"\r\n"
        )
    return partes + f"--{frontera}--\r\n".encode(), f"multipart/form-data; boundary={frontera}"


class _RunnerFalso:
    """`ingest` de verdad sobre la carpeta de la bandeja; extract y decide, fingidos."""

    def __init__(self, codigos: dict[str, int] | None = None):
        self.llamadas: list[list[str]] = []
        self.codigos = codigos or {}

    def __call__(self, args: list[str], ruta: Path) -> tuple[int, str]:
        from albertitos.pipeline import etapas

        self.llamadas.append(args)
        if args[0] == "ingest":
            c = db.conectar(ruta)
            try:
                etapas.ingest(c, Path(args[args.index("--dir") + 1]), lote=bandeja.LOTE)
            finally:
                c.close()
        return self.codigos.get(args[0], 0), f"{args[0]} ok"


def _bandeja(tmp_path: Path, runner=None) -> bandeja.Bandeja:
    return bandeja.Bandeja(tmp_path / "test.db", runner=runner or _RunnerFalso(), activa=True)


def _post(b: bandeja.Bandeja, cuerpo: bytes, tipo: str | None):
    return api.despachar("POST", "/inbox", {}, None, b.ruta, bandeja=b, cuerpo=cuerpo, tipo=tipo)


def _lista(b: bandeja.Bandeja) -> list[str]:
    return (b.ruta.parent / "inbox.lista.txt").read_text(encoding="utf-8").split()


def test_inbox_se_niega_con_la_bd_de_la_entrega():
    b = bandeja.Bandeja(bandeja.BD_ENTREGA, runner=_RunnerFalso(), activa=True)
    status, body = _post(b, *_multipart(("a.pdf", _pdf("a"))))
    assert status == 409 and "--bandeja" in body["error"]
    assert b.runner.llamadas == []


def test_inbox_cerrado_sin_el_flag_aunque_la_bd_no_sea_la_de_la_entrega(conn, tmp_path):
    """Puente arrancado con --db <otra ruta a la BD real> y sin --bandeja: POST 409, nada escrito."""
    b = bandeja.Bandeja(tmp_path / "test.db", runner=_RunnerFalso())
    status, body = _post(b, *_multipart(("a.pdf", _pdf("a"))))
    assert status == 409 and "--bandeja" in body["error"]
    assert b.runner.llamadas == [] and not (tmp_path / "inbox").exists()
    # y el despachar sin bandeja explícita tampoco la abre
    assert api.despachar("POST", "/inbox", {}, None, tmp_path / "test.db", cuerpo=b"")[0] == 409


def test_inbox_400_sin_pdf_o_con_nombre_que_windows_no_acepta(conn, tmp_path):
    b = _bandeja(tmp_path)
    assert _post(b, b"{}", "application/json")[0] == 400
    assert _post(b, *_multipart(("notas.txt", b"hola")))[0] == 400
    assert _post(b, *_multipart(("falso.pdf", b"no soy un pdf")))[0] == 400
    assert _post(b, *_multipart(('fa"ctura?.pdf', _pdf("a"))))[0] == 400
    assert b.runner.llamadas == [] and b.estado()["estado"] == "idle"
    assert api.despachar("POST", "/panel", {}, conn)[0] == 405


def test_inbox_202_lote_99_nfc_y_ciclo_completo(conn, maestro, erp, tmp_path):
    _semilla(conn, maestro, erp)
    b = _bandeja(tmp_path)
    nueva, otra = _pdf("nueva"), _pdf("otra")
    nfd = unicodedata.normalize("NFD", "nueva_ofimática.pdf")
    status, body = _post(b, *_multipart((nfd, nueva), ("../carpeta/otra.pdf", otra)))
    assert status == 202 and body["lote"] == 99
    assert body["file_ids"] == ["nueva_ofimática.pdf", "otra.pdf"]  # NFC y sin carpeta
    assert (tmp_path / "inbox" / "nueva_ofimática.pdf").read_bytes() == nueva
    b.esperar(5)
    assert [a[0] for a in b.runner.llamadas] == ["ingest", "extract", "decide"]
    assert b.runner.llamadas[0][-2:] == ["--lote", "99"]
    assert b.runner.llamadas[1][1] == b.runner.llamadas[2][1] == "--fixture"
    assert _lista(b) == ["nueva_ofimática.pdf", "otra.pdf"]

    # Lo que la CLI habría dejado en la BD: una decidida, la otra PENDIENTE (el LLM no la leyó).
    for fid, datos, res in (
        ("nueva_ofimática.pdf", nueva, Resultado.ESCALAR),
        ("otra.pdf", otra, None),
    ):
        sha = hashlib.sha256(datos).hexdigest()
        _alta(conn, fid, lote=99, resultado=res, hechos=_hechos(fid, sha256=sha))
    conn.commit()
    status, body = api.despachar("GET", "/inbox", {}, conn, b.ruta, bandeja=b)
    assert status == 200 and body["estado"] == "listo" and body["disponible"]
    assert {f["file_id"]: f["estado"] for f in body["ficheros"]} == {
        "nueva_ofimática.pdf": "ESCALAR",
        "otra.pdf": "PENDIENTE",
    }
    assert lecturas.listar_ficheros(conn, lote=99)["total"] == 2


def test_inbox_nombre_de_la_caja_con_otro_contenido_no_hereda_su_decision(
    conn, maestro, erp, tmp_path
):
    """El tribunal coge una factura de la Caja, le cambia un dato y la sube con el mismo nombre: el
    panel no puede enseñar la decisión del original (PAGAR en la semilla)."""
    _semilla(conn, maestro, erp)
    b = _bandeja(tmp_path)
    editada = _pdf("P001 con otro IBAN")
    status, body = _post(b, *_multipart(("2026-01-08_P001.pdf", editada)))
    assert status == 202
    interno = db.PREFIJO_INTERNO + "2026-01-08_P001.pdf"  # P0-5: el nombre ya era del lote 1
    assert body["file_ids"] == [interno]
    b.esperar(5)
    assert _lista(b) == [interno]  # extract y decide van a la subida, no al original

    status, body = api.despachar("GET", "/inbox", {}, conn, b.ruta, bandeja=b)
    assert body["ficheros"] == [
        {"file_id": interno, "nombre": "2026-01-08_P001.pdf", "estado": "PENDIENTE"}
    ]
    assert (
        lecturas.estados(conn, ["2026-01-08_P001.pdf"])[0]["estado"] == "PAGAR"
    )  # el original, intacto


def test_inbox_copia_exacta_no_se_vuelve_a_extraer_y_cuenta_como_el_original(conn, tmp_path):
    b = _bandeja(tmp_path)
    datos = _pdf("original")
    assert _post(b, *_multipart(("original.pdf", datos)))[0] == 202
    b.esperar(5)
    _alta(
        conn,
        "original.pdf",
        lote=99,
        hechos=_hechos("original.pdf", sha256=hashlib.sha256(datos).hexdigest()),
    )
    conn.commit()
    b.runner.llamadas.clear()
    # la misma subida con otro nombre: identidad del original, sin extract ni decide
    status, body = _post(b, *_multipart(("renombrada.pdf", datos)))
    assert status == 202 and body["estado"] == "listo"
    assert [a[0] for a in b.runner.llamadas] == ["ingest"]
    _, body = api.despachar("GET", "/inbox", {}, conn, b.ruta, bandeja=b)
    assert [(f["nombre"], f["estado"]) for f in body["ficheros"]] == [("renombrada.pdf", "PAGAR")]
    # el mismo nombre con otro contenido: se pide renombrar, no se pisa nada
    status, body = _post(b, *_multipart(("original.pdf", _pdf("otra versión"))))
    assert status == 400 and "original.pdf" in body["error"]
    assert (tmp_path / "inbox" / "original.pdf").read_bytes() == datos
    assert b.estado()["estado"] == "idle"


def test_inbox_un_trabajo_cada_vez_y_error_visible(conn, tmp_path):
    import threading

    suelta = threading.Event()

    class Lento(_RunnerFalso):
        def __call__(self, args, ruta):
            if args[0] == "extract":
                suelta.wait(5)
            return super().__call__(args, ruta)

    b = _bandeja(tmp_path, Lento({"decide": 1}))
    assert _post(b, *_multipart(("a.pdf", _pdf("a"))))[0] == 202
    assert _post(b, *_multipart(("b.pdf", _pdf("b"))))[0] == 409
    suelta.set()
    b.esperar(5)
    estado = b.estado()
    assert estado["estado"] == "error" and "decide" in estado["error"]
    assert any(linea.startswith("$ albertitos decide") for linea in estado["log"])


def test_inbox_si_no_se_puede_escribir_el_pdf_no_se_queda_ingiriendo(conn, tmp_path, monkeypatch):
    b = _bandeja(tmp_path)

    def falla(self, datos):
        raise OSError("disco lleno")

    monkeypatch.setattr(Path, "write_bytes", falla)
    status, body = _post(b, *_multipart(("a.pdf", _pdf("a"))))
    assert status == 500 and "disco lleno" in body["error"]
    assert b.estado()["estado"] == "error"
    monkeypatch.undo()
    assert _post(b, *_multipart(("a.pdf", _pdf("a"))))[0] == 202  # no se queda en 409


def test_inbox_cli_real_decide_un_pdf_de_la_caja_editado_sin_llm(
    conn, maestro, erp, tmp_path, monkeypatch
):
    """Sin runner falso: ingest → extract (plantilla, sin LLM) → decide por subproceso, con el PDF en
    la carpeta de la bandeja. Antes extract no lo encontraba y se quedaba PENDIENTE para siempre."""
    _semilla(conn, maestro, erp)
    monkeypatch.setenv("ALBERTITOS_FECHA_CORTE", CORTE.isoformat())
    original = (CAJA / "2026-01-11_P007.pdf").read_bytes()
    editada = original + b"\n%bandeja\n"  # otro sha256, mismo texto: sale por plantilla
    b = bandeja.Bandeja(tmp_path / "test.db", activa=True)
    status, body = _post(b, *_multipart(("2026-01-11_P007_editada.pdf", editada)))
    assert status == 202, body
    b.esperar(120)
    estado = b.estado()
    assert estado["estado"] == "listo", estado["log"]
    log = "\n".join(estado["log"])
    assert "extract: 1/1 ok" in log and "'plantilla': 1" in log and "tokens 0/0" in log, log
    _, body = api.despachar("GET", "/inbox", {}, conn, b.ruta, bandeja=b)
    (fila,) = body["ficheros"]
    assert fila["file_id"] == "2026-01-11_P007_editada.pdf"
    assert fila["estado"] in ("PAGAR", "NO_PAGAR", "ESCALAR"), estado["log"]
    detalle = lecturas.fichero(conn, fila["file_id"])
    assert detalle["lote"] == 99 and detalle["sha256"] == hashlib.sha256(editada).hexdigest()


def test_traza_motivos_una_vez_aunque_se_decida_varias_veces(conn, maestro, erp):
    """Un fichero decidido en dos pasadas: los motivos de la vigente salen una vez, con ids únicos
    (React los usa como key; repetidos, la traza del detalle se descuadra)."""
    _semilla(conn, maestro, erp)
    h = _hechos("2026-01-08_P001.pdf")
    db.registrar_evento(
        conn,
        Event(file_id=h.file_id, sha256=h.sha256, etapa=Etapa.DECIDE, estado=EstadoEvento.OK),
    )
    conn.commit()
    pasos = lecturas.traza_pasos(conn, file_id=h.file_id)
    ids = [p["id"] for p in pasos]
    assert len(ids) == len(set(ids))
    assert sum(p["tipo"] == "motivo" for p in pasos) == 1
    decides = [
        i for i, p in enumerate(pasos) if p["tipo"] == "evento" and p["evento"]["etapa"] == "decide"
    ]
    assert pasos[decides[-1] + 1]["tipo"] == "motivo"
