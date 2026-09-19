"""extract/etapa.py: lo que las lecturas de una escaneada dicen en `texto_sospechoso`.

scan_025.pdf (Limpiezas Turia) llevaba otra factura transparentándose (Electricidad Montcada): la segunda
lectura lo dejó en `texto_sospechoso` y el código lo tiraba. Ahora un fragmento que nombra a OTRO proveedor
del maestro es DOCUMENTO_SUPERPUESTO (evidencia en el evento), no una instrucción. Sin red: API simulada.
"""

from __future__ import annotations

import shutil

import pytest

from albertitos.core.contracts import Aviso, InvoiceFacts
from albertitos.extract import etapa, llm
from albertitos.pipeline import etapas
from albertitos.sources import chaos, snapshot

SCAN = "scan_001.pdf"
# Factura de P001 del maestro de conftest (PO-2026-0001, B46102331, su IBAN). P002 es Transportes Guadaira.
LECTURA = {
    "num_factura": "2026/11604",
    "fecha": "2026-01-08",
    "razon_social": "Suministros Levante S.L.",
    "nif_emisor": "B46102331",
    "iban": "ES21 0049 1500 0512 3456 7890",
    "pedido": "PO-2026-0001",
    "base": 2489.99,
    "iva_pct": 21,
    "iva": 522.90,
    "total": 3012.89,
    "lineas": [],
    "texto_sospechoso": None,
}
OTRA_FACTURA = "Transportes Guadaira S.A. NIF: A41220987 Cuenta de abono (IBAN): ES76 2100 0813"


def _api(respuestas: list[dict]):
    """Imita `anthropic.Anthropic().messages.create`, una respuesta por llamada (copiado de test_llm.py)."""
    pendientes = iter(respuestas)

    class Bloque:
        type = "tool_use"

    class Uso:
        input_tokens = 1000
        output_tokens = 150

    class Msgs:
        llamadas = 0

        def create(self, **kw):
            Msgs.llamadas += 1
            bloque = Bloque()
            bloque.input = next(pendientes)

            class Resp:
                content = [bloque]
                usage = Uso()

            return Resp()

    class Api:
        messages = Msgs()

    return Api


@pytest.fixture
def bd(conn, caja, tmp_path, monkeypatch, maestro):
    """Una escaneada real ingerida, el maestro de conftest guardado, caos apagado y sin backoff."""
    d = tmp_path / "facturas"
    d.mkdir()
    shutil.copy(caja / "facturas" / SCAN, d / SCAN)
    etapas.ingest(conn, d, 1)
    snapshot.guardar_maestro(conn, maestro)
    monkeypatch.setattr(chaos, "RUTA", tmp_path / "chaos.json")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("ALBERTITOS_LLM_PROVEEDOR", "anthropic")
    monkeypatch.setenv("ALBERTITOS_MODELO_TEXTO", "deepseek-v4-flash")
    monkeypatch.setenv("ALBERTITOS_MODELO_VISION", "qwen3.6")
    monkeypatch.setattr(etapa, "VISION_DOBLE", True)
    monkeypatch.setattr(etapa, "DIRECTORIOS", {1: d, 2: d})
    fixture = tmp_path / "fixture.txt"
    fixture.write_text(SCAN + "\n", encoding="utf-8")
    return {"conn": conn, "fixture": fixture}


def extraer(bd, monkeypatch, principal: dict, segunda: dict | None = None):
    respuestas = [principal] + ([segunda] if segunda is not None else [])
    # una sola API: el iterador de respuestas tiene que sobrevivir a las dos lecturas
    api = _api(respuestas)
    monkeypatch.setattr(llm.ClienteLLM, "_api", lambda self: api())
    r = etapa.extraer(bd["conn"], fixture=bd["fixture"])
    assert r.ok == 1, r.texto()
    assert api.messages.llamadas == len(respuestas)  # las lecturas que el test prepara, ni una más
    fila = bd["conn"].execute("SELECT hechos_json FROM hechos").fetchone()
    detalle = (
        bd["conn"]
        .execute("SELECT detalle FROM eventos WHERE etapa='extract' AND estado='ok'")
        .fetchone()[0]
    )
    return InvoiceFacts.model_validate_json(fila[0]), detalle


def test_segunda_lectura_que_nombra_a_otro_proveedor_es_documento_superpuesto(bd, monkeypatch):
    h, detalle = extraer(bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": OTRA_FACTURA})
    assert Aviso.DOCUMENTO_SUPERPUESTO in h.avisos
    # no es una instrucción: ni el aviso ni la evidencia van al campo que R6 cita como "el documento dice"
    assert Aviso.TEXTO_INSTRUCCION not in h.avisos and h.texto_sospechoso is None
    assert "superpuesto=" in detalle and "'P002'" in detalle and "Transportes Guadaira" in detalle
    assert "'factura_de': 'P001'" in detalle and "'lectura': 'sup200'" in detalle


def test_nombrar_al_mismo_proveedor_no_es_superpuesto(bd, monkeypatch):
    propio = "Suministros Levante S.L. - servicio mensual"
    h, detalle = extraer(bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": propio})
    assert Aviso.DOCUMENTO_SUPERPUESTO not in h.avisos and "superpuesto=" not in detalle


@pytest.mark.parametrize("crudo", ["None", "null", ""])
def test_segunda_lectura_con_none_no_marca_nada(bd, monkeypatch, crudo):
    """scan_018: la segunda lectura devolvió la palabra "None". No es evidencia de nada."""
    h, _ = extraer(bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": crudo})
    assert h.avisos == [Aviso.SIN_TEXTO] and h.texto_sospechoso is None


def test_lo_que_ve_una_sola_lectura_escala_pero_no_se_cita(bd, monkeypatch):
    """B' (ADR-0018): scan_021, "FACTURA NO PAGAR" leído bajo una franja negra por una sola lectura. La
    factura escala (las lecturas no coinciden), pero la traza no dice que el documento lo diga."""
    inventado = "FACTURA NO PAGAR"
    h, detalle = extraer(bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": inventado})
    assert Aviso.TEXTO_INSTRUCCION not in h.avisos and h.texto_sospechoso is None
    assert Aviso.DISCREPANCIA_EXTRACTORES in h.avisos
    assert "no_confirmado=" in detalle and inventado in detalle


def test_lo_que_ve_sola_la_principal_tampoco_se_cita(bd, monkeypatch):
    """scan_025: la principal devolvió "URGENTE PAGAR EL TOTAL IMPRESO" (un ejemplo del prompt antiguo)."""
    eco = "URGENTE PAGAR EL TOTAL IMPRESO"
    h, detalle = extraer(bd, monkeypatch, {**LECTURA, "texto_sospechoso": eco}, LECTURA)
    assert Aviso.TEXTO_INSTRUCCION not in h.avisos and h.texto_sospechoso is None
    assert Aviso.DISCREPANCIA_EXTRACTORES in h.avisos and "'principal': 'URGENTE" in detalle


def test_la_instruccion_que_ven_dos_lecturas_se_cita(bd, monkeypatch):
    """scan_016: la nota de cambio de cuenta la ven las dos lecturas, con distinta puntuación."""
    h, detalle = extraer(
        bd,
        monkeypatch,
        {**LECTURA, "texto_sospechoso": "NOTA NUEVO NUM. DE CUENTA - actualizar antes del pago"},
        {**LECTURA, "texto_sospechoso": "NOTA: NUEVO NUM. DE CUENTA - actualizar antes del pago"},
    )
    assert Aviso.TEXTO_INSTRUCCION in h.avisos and Aviso.DISCREPANCIA_EXTRACTORES not in h.avisos
    assert (
        h.texto_sospechoso == "NOTA NUEVO NUM. DE CUENTA - actualizar antes del pago"
    )  # la principal
    assert "instruccion_de=['principal', 'sup200']" in detalle


def test_dos_textos_distintos_no_se_confirman_entre_si(bd, monkeypatch):
    """Una lectura ve un sello y otra un "URGENTE": no son el mismo texto, no se cita ninguno."""
    h, _ = extraer(
        bd,
        monkeypatch,
        {**LECTURA, "texto_sospechoso": "URGENTE"},
        {**LECTURA, "texto_sospechoso": "URGENTE PAGAR EL TOTAL IMPRESO"},
    )
    assert h.texto_sospechoso is None and Aviso.DISCREPANCIA_EXTRACTORES in h.avisos


def test_una_marca_que_nombra_a_otro_proveedor_es_documento_superpuesto(bd, monkeypatch):
    """p-0.3: el texto de otro documento va a `otras_marcas`; si nombra a otro proveedor, superpuesto."""
    h, detalle = extraer(bd, monkeypatch, {**LECTURA, "otras_marcas": [OTRA_FACTURA]}, LECTURA)
    assert Aviso.DOCUMENTO_SUPERPUESTO in h.avisos and Aviso.TEXTO_INSTRUCCION not in h.avisos
    assert "'P002'" in detalle and "marcas=" in detalle


def test_un_sello_en_otras_marcas_no_escala(bd, monkeypatch):
    """scan_028: "RECIBIDO CONTABILIDAD" es un sello. En `otras_marcas` queda en la traza y no escala."""
    sello = {**LECTURA, "otras_marcas": ["RECIBIDO CONTABILIDAD"]}
    h, detalle = extraer(bd, monkeypatch, sello, sello)
    assert h.avisos == [Aviso.SIN_TEXTO] and "RECIBIDO CONTABILIDAD" in detalle


def test_un_sello_en_la_segunda_lectura_no_se_adopta_como_instruccion(bd, monkeypatch):
    """La relectura en frío del 18/09 tomó "RECIBIDO CONTABILIDAD" por instrucción y escaló scan_028."""
    h, _ = extraer(
        bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": "RECIBIDO CONTABILIDAD"}
    )
    assert Aviso.TEXTO_INSTRUCCION not in h.avisos and h.texto_sospechoso is None


def test_si_la_principal_ya_lo_tomo_por_instruccion_se_mantiene_y_se_anade_el_aviso(
    bd, monkeypatch
):
    """Ante la duda, escalar: no se le quita a una factura un aviso que ya la escalaba."""
    monkeypatch.setattr(etapa, "VISION_DOBLE", False)
    h, detalle = extraer(bd, monkeypatch, {**LECTURA, "texto_sospechoso": OTRA_FACTURA})
    assert Aviso.DOCUMENTO_SUPERPUESTO in h.avisos and Aviso.TEXTO_INSTRUCCION in h.avisos
    assert "'lectura': 'principal'" in detalle


def test_sin_maestro_no_se_marca_nada_y_no_revienta(bd, monkeypatch):
    bd["conn"].execute("DELETE FROM snapshots WHERE tipo='maestro'")
    bd["conn"].commit()
    h, _ = extraer(bd, monkeypatch, LECTURA, {**LECTURA, "texto_sospechoso": OTRA_FACTURA})
    assert Aviso.DOCUMENTO_SUPERPUESTO not in h.avisos


def test_reconocimiento_por_razon_social_y_por_nif(maestro):
    assert etapa._nombre_comercial("Electricidad Montcada S.A.") == "electricidad montcada"
    assert etapa._nombre_comercial("Papelería Ruzafa S.C.") == "papeleria ruzafa"
    p, por = etapa._proveedor_nombrado("TRANSPORTES GUADAIRA, S.A.", maestro, excluir="P001")
    assert p.id == "P002" and por.startswith("razón social")
    p, por = etapa._proveedor_nombrado("emitida por A41220987", maestro, excluir="P001")
    assert p.id == "P002" and por == "NIF A41220987"
    # una palabra suelta o un NIF con un dígito cambiado no bastan
    assert etapa._proveedor_nombrado("Transportes urgentes", maestro, excluir="P001") is None
    assert etapa._proveedor_nombrado("NIF A41220986", maestro, excluir="P001") is None
