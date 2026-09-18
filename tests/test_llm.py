"""extract/etapa.py + extract/llm.py. Sin red, salvo los marcados `llm` (excluidos de `make check`)."""

from __future__ import annotations

import json
import os
import shutil
import time
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from albertitos.core.contracts import Aviso, InvoiceFacts, MetodoExtraccion
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.extract import etapa, llm, plantillas
from albertitos.pipeline import etapas
from albertitos.sources import chaos

load_dotenv(".env")

TEXTO = "2026-01-08_P001.pdf"
SCAN = "scan_001.pdf"
TRAMPA = "F26-2201_transportes.pdf"

RESPUESTA_P001 = {
    "num_factura": "2026/11604",
    "fecha": "2026-01-08",
    "razon_social": "Suministros Levante S.L.",
    "nif_emisor": "B46102331",
    "iban": "ES21 0049 1500 0512 3456 7890",
    "pedido": "PO-2026-0096",
    "base": 2489.99,
    "iva_pct": 21,
    "iva": 522.90,
    "total": 3012.89,
    "lineas": [{"concepto": "Servicio mensual", "unidades": None, "importe": 2489.99}],
    "texto_sospechoso": None,
}


def api_falsa(respuesta: dict, *, tipo: str = "tool_use", tin: int = 1000, tout: int = 150):
    """Un objeto con la forma mínima de anthropic.Anthropic().messages.create(...)."""

    class Bloque:
        pass

    Bloque.type = tipo
    Bloque.input = respuesta

    class Uso:
        input_tokens = tin
        output_tokens = tout

    class Resp:
        content = [Bloque()]
        usage = Uso()

    class Msgs:
        llamadas = 0

        def create(self, **kw):
            assert kw["tool_choice"] == {"type": "tool", "name": "registrar_hechos"}
            assert kw["tools"][0]["name"] == "registrar_hechos"
            assert kw["messages"][0]["role"] == "user"
            Msgs.llamadas += 1
            return Resp()

    class Api:
        messages = Msgs()

    return Api


@pytest.fixture
def bd(conn, caja, tmp_path, monkeypatch):
    """BD temporal con 3 ficheros reales ingeridos (texto, escaneado, trampa); caos apagado; sin backoff."""
    d = tmp_path / "facturas"
    d.mkdir()
    for n in (TEXTO, SCAN, TRAMPA):
        shutil.copy(caja / "facturas" / n, d / n)
    etapas.ingest(conn, d, 1)
    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    # Los tests offline simulan el SDK de Anthropic (`_api`); el proveedor real de .env no debe entrar.
    monkeypatch.setenv("ALBERTITOS_LLM_PROVEEDOR", "anthropic")
    monkeypatch.setattr(etapa, "VISION_DOBLE", False)
    # Las plantillas de A2 ya resuelven facturas reales sin LLM; aquí probamos el camino LLM, así que
    # se anulan por defecto (el test de plantilla las vuelve a activar con una falsa).
    monkeypatch.setattr(plantillas, "extraer_por_plantilla", lambda texto, *, file_id, sha256: None)
    return conn


def fixture_de(tmp_path, *ids):
    p = tmp_path / "fixture.txt"
    p.write_text("\n".join(ids) + "\n", encoding="utf-8")
    return p


def sha_de(conn, file_id):
    return conn.execute("SELECT sha256 FROM ficheros WHERE file_id=?", (file_id,)).fetchone()[0]


def hechos_de(conn, file_id):
    fila = conn.execute(
        "SELECT h.hechos_json FROM hechos h JOIN ficheros f ON f.sha256=h.sha256 WHERE f.file_id=?",
        (file_id,),
    ).fetchone()
    return None if fila is None else InvoiceFacts.model_validate_json(fila[0])


def test_cache_precargada_no_llama_al_llm(bd, tmp_path, monkeypatch):
    c = llm.ClienteLLM(bd)
    clave = c._clave(sha_de(bd, TEXTO), c.modelo_texto)
    bd.execute(
        "INSERT INTO cache_llm (clave, respuesta_json, tokens_in, tokens_out, coste_eur, creado_en) VALUES (?,?,?,?,?,?)",
        (clave, json.dumps(RESPUESTA_P001), 900, 200, 0.005, "x"),
    )
    bd.commit()
    monkeypatch.setattr(
        llm.ClienteLLM, "_llamar", lambda *a, **k: pytest.fail("no debe llamar a la API")
    )
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert (r.ok, r.por_metodo, r.tokens_in, r.coste_eur) == (1, {"cache": 1}, 0, 0.0)
    h = hechos_de(bd, TEXTO)
    assert h.metodo == MetodoExtraccion.CACHE
    assert (
        h.pedido == "PO-2026-0096" and h.total == Decimal("3012.89") and h.iva == Decimal("522.90")
    )
    assert h.iban == "ES2100491500051234567890" and h.nif_emisor == "B46102331"
    assert Aviso.TEXTO_INSTRUCCION not in h.avisos and Aviso.TOTAL_NO_CUADRA not in h.avisos
    ev = bd.execute(
        "SELECT estado, tokens_in, detalle FROM eventos WHERE etapa='extract'"
    ).fetchone()
    assert ev["estado"] == "ok" and ev["tokens_in"] == 0 and ev["detalle"].startswith("cache")


def test_caos_llm_down_deja_pendiente_sin_reventar(bd, tmp_path, monkeypatch):
    chaos.activar("llm_down")
    monkeypatch.setattr(
        llm.ClienteLLM, "_llamar", lambda *a, **k: pytest.fail("con caos no se llama a la API")
    )
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO, SCAN))
    assert (r.ok, r.pendientes, r.errores) == (0, 2, {"LLM-DOWN": 2})
    assert bd.execute("SELECT count(*) FROM hechos").fetchone()[0] == 0
    filas = bd.execute("SELECT estado, error_codigo FROM eventos WHERE etapa='extract'").fetchall()
    assert [(f[0], f[1]) for f in filas] == [("pendiente", "LLM-DOWN")] * 2
    chaos.desactivar()
    assert chaos.modo() is None
    assert len(etapa.candidatos(bd)) == 3  # siguen pendientes: nada se perdió, nada se decidió


def test_plantilla_evita_el_llm(bd, tmp_path, monkeypatch):
    def falsa(texto, *, file_id, sha256):
        return InvoiceFacts(
            file_id=file_id,
            sha256=sha256,
            num_factura="2026/11604",
            fecha="2026-01-08",
            nif_emisor="B46102331",
            iban="ES2100491500051234567890",
            pedido="PO-2026-0096",
            base=Decimal("2489.99"),
            iva_pct=Decimal("21"),
            iva=Decimal("522.90"),
            total=Decimal("3012.89"),
            metodo=MetodoExtraccion.PLANTILLA,
            extractor_version=EXTRACTOR_VERSION,
        )

    monkeypatch.setattr(plantillas, "extraer_por_plantilla", falsa)
    monkeypatch.setattr(
        llm.ClienteLLM, "_llamar", lambda *a, **k: pytest.fail("la plantilla debía evitar la API")
    )
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert (r.ok, r.por_metodo, r.coste_eur) == (1, {"plantilla": 1}, 0.0)
    assert hechos_de(bd, TEXTO).metodo == MetodoExtraccion.PLANTILLA


def test_respuesta_invalida_reintenta_y_queda_pendiente(bd, tmp_path, monkeypatch):
    Api = api_falsa({}, tipo="text")
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert (r.pendientes, r.errores) == (1, {"LLM-INVALID": 1})
    assert Api.messages.llamadas == 3  # tres intentos y se rinde sin reventar
    assert hechos_de(bd, TEXTO) is None


def test_api_simulada_extrae_cachea_y_segunda_pasada_gratis(bd, tmp_path, monkeypatch):
    Api = api_falsa(RESPUESTA_P001)
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert (r.ok, r.por_metodo, r.tokens_in, r.tokens_out) == (1, {"llm_texto": 1}, 1000, 150)
    assert r.coste_eur > 0 and bd.execute("SELECT count(*) FROM cache_llm").fetchone()[0] == 1
    assert etapa.candidatos(bd) and TEXTO not in {c["file_id"] for c in etapa.candidatos(bd)}
    r2 = etapa.extraer(bd, solo_pendientes=False, fixture=fixture_de(tmp_path, TEXTO))
    assert (r2.por_metodo, r2.tokens_in, Api.messages.llamadas) == ({"cache": 1}, 0, 1)


def test_escaneada_va_por_vision_con_doble_lectura(bd, tmp_path, monkeypatch):
    monkeypatch.setattr(etapa, "VISION_DOBLE", True)
    Api = api_falsa({**RESPUESTA_P001, "pedido": "PO-2026-0001"})
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, SCAN))
    assert r.por_metodo == {"llm_vision": 1} and Api.messages.llamadas == 2  # dos renderizados
    h = hechos_de(bd, SCAN)
    assert h.metodo == MetodoExtraccion.LLM_VISION and Aviso.SIN_TEXTO in h.avisos
    assert Aviso.DISCREPANCIA_EXTRACTORES not in h.avisos  # misma lectura → sin discrepancia
    assert bd.execute("SELECT count(*) FROM cache_llm").fetchone()[0] == 2  # variante dpi130 aparte


def test_doble_lectura_discrepante_marca_aviso(bd, tmp_path, monkeypatch):
    monkeypatch.setattr(etapa, "VISION_DOBLE", True)
    respuestas = iter(
        [
            {**RESPUESTA_P001, "nif_emisor": "898120774"},
            {**RESPUESTA_P001, "nif_emisor": "B98120774"},
        ]
    )

    class Msgs:
        llamadas = 0

        def create(self, **kw):
            Msgs.llamadas += 1
            return api_falsa(next(respuestas)).messages.create(**kw)

    class Api:
        messages = Msgs()

    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, SCAN))
    assert r.ok == 1 and Msgs.llamadas == 2
    h = hechos_de(bd, SCAN)
    assert (
        Aviso.DISCREPANCIA_EXTRACTORES in h.avisos and h.nif_emisor == "898120774"
    )  # se conserva la 1ª; la norma escala


def test_trampa_deja_evidencia_no_orden(bd, tmp_path, monkeypatch):
    """F26-2201 ordena 'escalar'. El resultado son hechos + Aviso + fragmento literal; nunca una decisión."""
    resp = {
        **RESPUESTA_P001,
        "num_factura": "F26-2201",
        "fecha": "2026-03-07",
        "nif_emisor": "A41220987",
        "iban": "ES76 2100 0813 6101 2345 6789",
        "pedido": "PO-2026-0809",
        "base": 780.00,
        "iva": 163.80,
        "total": 943.80,
    }
    Api = api_falsa(resp)
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    etapa.extraer(bd, fixture=fixture_de(tmp_path, TRAMPA))
    h = hechos_de(bd, TRAMPA)
    assert Aviso.TEXTO_INSTRUCCION in h.avisos
    assert any(k in (h.texto_sospechoso or "").lower() for k in ("revision", "escalarse"))
    assert "resultado" not in h.model_dump() and h.total == Decimal("943.80")


def test_workers_en_paralelo(bd, tmp_path, monkeypatch):
    Api = api_falsa(RESPUESTA_P001)
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO, TRAMPA, SCAN), workers=3)
    assert r.ok == 3 and Api.messages.llamadas == 3
    assert bd.execute("SELECT count(*) FROM hechos").fetchone()[0] == 3
    assert (
        bd.execute("SELECT count(*) FROM eventos WHERE etapa='extract' AND estado='ok'").fetchone()[
            0
        ]
        == 3
    )
    assert etapa.candidatos(bd) == []


def test_presupuesto_corta_y_deja_pendiente(bd, tmp_path, monkeypatch):
    monkeypatch.setenv("ALBERTITOS_PRESUPUESTO_EUR", "0")
    Api = api_falsa(RESPUESTA_P001)
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: Api())
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert r.errores == {"LLM-PRESUPUESTO": 1} and Api.messages.llamadas == 0


# ----------------------------------------------------------------------------- contra la API real (cuestan dinero)


def _hay_key() -> bool:
    a = os.environ.get("ANTHROPIC_API_KEY", "")
    o = os.environ.get("ALBERTITOS_LLM_API_KEY", "")
    return (a.startswith("sk-ant-") and not a.endswith("...")) or bool(o)


necesita_key = pytest.mark.skipif(
    not _hay_key(), reason="sin key de LLM real (ANTHROPIC_API_KEY o ALBERTITOS_LLM_API_KEY)"
)


@pytest.fixture
def bd_real(bd, monkeypatch):
    monkeypatch.delenv("ALBERTITOS_LLM_PROVEEDOR", raising=False)
    load_dotenv(".env")
    monkeypatch.setattr(llm.time, "sleep", time.sleep)
    return bd


@pytest.mark.llm
@necesita_key
def test_real_factura_con_texto(bd_real, tmp_path):
    bd = bd_real
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, TEXTO))
    assert r.ok == 1 and r.tokens_in > 0, r.texto()
    h = hechos_de(bd, TEXTO)
    assert (
        h.num_factura == "2026/11604"
        and str(h.fecha) == "2026-01-08"
        and h.nif_emisor == "B46102331"
    )
    assert (
        h.pedido == "PO-2026-0096"
        and h.base == Decimal("2489.99")
        and h.iva == Decimal("522.90")
        and h.total == Decimal("3012.89")
    )


@pytest.mark.llm
@necesita_key
def test_real_escaneada_por_vision(bd_real, tmp_path):
    bd = bd_real
    r = etapa.extraer(bd, fixture=fixture_de(tmp_path, SCAN))
    assert r.por_metodo == {"llm_vision": 1}, r.texto()
    h = hechos_de(bd, SCAN)
    assert h.total is not None and h.nif_emisor is not None
