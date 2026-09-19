"""El preflight del lote 2: que no se pueda tocar el lote 2 con la BD contaminada.

Todo con BD temporales; ninguna prueba toca `dist/albertitos.db` ni sale a la red (la comprobación
del ERP se sustituye, porque aquí sólo se prueba la lógica de estado).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    Decision,
    InvoiceFacts,
    MetodoExtraccion,
    Motivo,
    Resultado,
)
from albertitos.sources import estado_bd

RUTA_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preflight_lote2.py"


def cargar_script():
    spec = importlib.util.spec_from_file_location("preflight_lote2", RUTA_SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # @dataclass lo busca en sys.modules al ejecutarse
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def preflight(monkeypatch):
    modulo = cargar_script()
    monkeypatch.setattr(modulo, "url_viva", lambda *a, **k: True)  # el ERP no se prueba aquí
    return modulo


def ingerir(conn, file_id: str, lote: int, *, con_hechos=True, con_decision=True) -> str:
    sha = f"{abs(hash(file_id)):064x}"[:64]
    db.guardar_fichero(
        conn, sha256=sha, file_id=file_id, lote=lote, bytes_=10, paginas=1, tiene_texto=True
    )
    if con_hechos:
        db.guardar_hechos(
            conn,
            InvoiceFacts(
                file_id=file_id,
                sha256=sha,
                metodo=MetodoExtraccion.PLANTILLA,
                extractor_version="ext-0.1",
            ),
        )
    if con_decision:
        db.guardar_decision(
            conn,
            Decision(
                file_id=file_id,
                sha256=sha,
                resultado=Resultado.PAGAR,
                motivos=[Motivo(regla_id="v3.R1", ok=True, detalle="ok")],
                norma_version="v3",
                fecha_corte=date(2026, 9, 18),
                hechos_hash="h",
                maestro_version="m",
                erp_version="v1",
                decidido_en=datetime.now(UTC),
            ),
        )
    conn.commit()
    return sha


def montar(tmp_path, conn, *, fantasma=False, erp=("v1",)):
    """Caja de 2 facturas reales; opcionalmente un fichero del lote 2 simulado que ya no existe."""
    caja = tmp_path / "caja"
    caja.mkdir()
    for nombre in ("a.pdf", "b.pdf"):
        (caja / nombre).write_bytes(b"%PDF-1.4")
        ingerir(conn, nombre, 1)
    if fantasma:
        ingerir(conn, "L2-a.pdf", 2)  # ingerido como lote 2, pero no está en ningún directorio
    for i, version in enumerate(
        erp
    ):  # fechas distintas: `ultimo_erp` mira `creado_en`, como core.db
        conn.execute(
            "INSERT INTO snapshots (tipo, version, datos_json, creado_en) VALUES ('erp', ?, '{}', ?)",
            (version, f"2026-09-19T0{i}:00:00.000+00:00"),
        )
    conn.commit()
    fixture = tmp_path / "hechos.jsonl"
    fixture.write_text(
        "".join(json.dumps({"file_id": n}) + "\n" for n in ("a.pdf", "b.pdf")), encoding="utf-8"
    )
    return Namespace(
        db=str(Path(conn.execute("PRAGMA database_list").fetchone()[2])),
        dir_lote1=str(caja),
        dir_lote2=str(tmp_path / "lote2"),
        fixture=str(fixture),
        erp_url="http://127.0.0.1:1",
        erp_lote2="",
        erp_esperado="v1",
        limpiar=False,
        respaldar=False,
    )


def rojos(checks):
    return {c.nombre: c for c in checks if c.nivel == "ROJO"}


def test_bd_limpia_pasa(preflight, tmp_path, conn):
    args = montar(tmp_path, conn)
    assert rojos(preflight.comprobar(args)) == {}


def test_fichero_fantasma_es_rojo_y_dice_cual(preflight, tmp_path, conn):
    """El incidente del 18/09: 10 PDF de un lote 2 simulado que nadie borró."""
    args = montar(tmp_path, conn, fantasma=True)
    malos = rojos(preflight.comprobar(args))
    assert "ficheros fantasma" in malos
    assert "L2-a.pdf" in malos["ficheros fantasma"].detalle
    assert "--limpiar" in malos["ficheros fantasma"].arreglo


def test_limpiar_borra_solo_lo_fantasma(preflight, tmp_path, conn):
    args = montar(tmp_path, conn, fantasma=True)
    antes = conn.execute("SELECT count(*) FROM ficheros").fetchone()[0]
    conn.commit()
    n_f, n_h = preflight.limpiar(Path(args.db), args.dir_lote1, args.dir_lote2)
    assert (n_f, n_h) == (1, 0)
    despues = {r[0] for r in conn.execute("SELECT file_id FROM ficheros")}
    assert antes == 3 and despues == {"a.pdf", "b.pdf"}
    assert conn.execute("SELECT count(*) FROM hechos").fetchone()[0] == 2
    assert estado_bd.hechos_huerfanos(conn) == []
    assert rojos(preflight.comprobar(args)) == {}


def test_snapshot_simulado_mas_reciente_es_rojo(preflight, tmp_path, conn):
    """Si el último snapshot es un `v2-sim`, `decide`/`run` sin --erp decidirían con datos inventados."""
    args = montar(tmp_path, conn, erp=("v1", "v2-sim"))
    malos = rojos(preflight.comprobar(args))
    assert "snapshot del ERP" in malos and "v2-sim" in malos["snapshot del ERP"].detalle
    assert estado_bd.ultimo_erp(conn) == "v2-sim"


def test_fixture_descuadrado_es_rojo(preflight, tmp_path, conn):
    args = montar(tmp_path, conn)
    Path(args.fixture).write_text(json.dumps({"file_id": "a.pdf"}) + "\n", encoding="utf-8")
    malos = rojos(preflight.comprobar(args))
    assert "fixture de hechos" in malos and "faltan 1" in malos["fixture de hechos"].detalle


def test_hechos_huerfanos_se_detectan(preflight, tmp_path, conn):
    """Por la vía normal no pasa (hay clave foránea), pero el `DELETE` que documenta la skill se
    ejecuta con el cliente `sqlite3`, que NO activa las claves foráneas: ahí sí quedan huérfanos."""
    args = montar(tmp_path, conn)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DELETE FROM ficheros WHERE file_id='a.pdf'")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    assert len(estado_bd.hechos_huerfanos(conn)) == 1
    malos = rojos(preflight.comprobar(args))
    assert "hechos huérfanos" in malos


def test_variable_de_ensayo_exportada_es_roja(preflight, tmp_path, conn, monkeypatch):
    """Bajar el umbral del breaker para una demo y olvidarlo puesto cortaría una pasada real a los
    dos fallos, dejando cientos de ficheros PENDIENTE sin que nadie lo note."""
    args = montar(tmp_path, conn)
    monkeypatch.setenv("ALBERTITOS_BREAKER_FALLOS", "2")
    malos = rojos(preflight.comprobar(args))
    assert "entorno" in malos and "ALBERTITOS_BREAKER_FALLOS=2" in malos["entorno"].detalle
    assert "unset" in malos["entorno"].arreglo
    monkeypatch.setenv("ALBERTITOS_BREAKER_FALLOS", "5")  # el valor por defecto no molesta
    assert "entorno" not in rojos(preflight.comprobar(args))


def test_cache_de_otra_version_de_prompt_avisa(preflight, tmp_path, conn):
    """Subir PROMPT_VERSION sin re-etiquetar deja huérfanas las lecturas: releer las 29 escaneadas
    son minutos de visión (pasó al pasar a p-0.2)."""
    args = montar(tmp_path, conn)
    conn.execute(
        "INSERT INTO cache_llm (clave, respuesta_json, creado_en) VALUES (?, '{}', 'x')",
        ("a" * 64 + "|p-0.1|qwen3.6",),
    )
    conn.commit()
    avisos = {c.nombre: c for c in preflight.comprobar(args) if c.nivel == "ÁMBAR"}
    assert "caché del LLM" in avisos and "p-0.1" in avisos["caché del LLM"].detalle


def test_fixture_desfasado_respecto_a_la_bd_avisa(preflight, tmp_path, conn):
    """El caso real del 19/09: `marcar_duplicados` añadió avisos en la BD y el fixture se quedó sin
    reexportar; quien lo importara perdería la detección de duplicados."""
    args = montar(tmp_path, conn)
    sha = conn.execute("SELECT sha256 FROM ficheros WHERE file_id='a.pdf'").fetchone()[0]
    viejo = InvoiceFacts(
        file_id="a.pdf", sha256=sha, metodo=MetodoExtraccion.PLANTILLA, extractor_version="ext-0.1"
    )
    nuevo = viejo.model_copy(update={"avisos": [Aviso.DUPLICADO_SOSPECHOSO]})
    db.guardar_hechos(conn, nuevo)  # la BD avanza...
    conn.commit()
    Path(args.fixture).write_text(
        viejo.model_dump_json() + "\n", encoding="utf-8"
    )  # ...el fixture no
    avisos = {c.nombre: c for c in preflight.comprobar(args) if c.nivel == "ÁMBAR"}
    assert "fixture vs BD" in avisos and "a.pdf" in avisos["fixture vs BD"].detalle
    assert "hechos export" in avisos["fixture vs BD"].arreglo


def test_fixture_ilegible_no_revienta_el_preflight(preflight, tmp_path, conn):
    args = montar(tmp_path, conn)
    Path(args.fixture).write_text(
        '{"file_id": "a.pdf"}\n', encoding="utf-8"
    )  # sin sha256 ni método
    avisos = {c.nombre: c for c in preflight.comprobar(args) if c.nivel != "VERDE"}
    assert "fixture vs BD" in avisos and "ilegibles" in avisos["fixture vs BD"].detalle


def test_llm_sin_clave_avisa_y_con_todo_en_regla_verde(preflight):
    """R1 (PLAN-12): sin .env las escaneadas del lote 2 quedarían PENDIENTE. La clave sólo se mira si existe."""
    chk = preflight.comprobar_llm({})
    assert chk.nivel == preflight.AMBAR and "clave" in chk.detalle
    chk = preflight.comprobar_llm({"ALBERTITOS_LLM_API_KEY": "x"})
    assert chk.nivel == preflight.AMBAR and "402" in chk.detalle  # visión por defecto: claude-*
    base = {"ALBERTITOS_LLM_API_KEY": "x", "ALBERTITOS_MODELO_VISION": "qwen3.6"}
    chk = preflight.comprobar_llm(base)
    assert chk.nivel == preflight.AMBAR and "NINGUNO" in chk.detalle
    chk = preflight.comprobar_llm(
        {**base, "ALBERTITOS_MODELO_VISION_FALLBACK": "deepseek-v4-flash"}
    )
    assert chk.nivel == preflight.VERDE and "deepseek-v4-flash" in chk.detalle
    assert (
        "API_KEY" not in chk.detalle
    )  # nunca se enseña la clave, ni su nombre en el veredicto verde


def test_material_del_manifiesto_no_es_un_intento_anterior(preflight, tmp_path, conn):
    """19/09: el lote 2 llegó como commit y está en data/lote2 con su manifiesto. Eso es VERDE; un PDF
    de más o con otro contenido sigue siendo ÁMBAR (un intento anterior que hay que apartar)."""
    import hashlib

    args = montar(tmp_path, conn)
    d = Path(args.dir_lote2)
    d.mkdir()
    (d / "x.pdf").write_bytes(b"%PDF-lote2")
    manifiesto = tmp_path / "lote2.sha256"
    h = hashlib.sha256(b"%PDF-lote2").hexdigest()
    manifiesto.write_text(
        f"{h}  data/lote2/facturas/x.pdf\n{'0' * 64}  data/lote2/a.csv\n", encoding="utf-8"
    )
    args.manifiesto_lote2 = str(manifiesto)
    nivel = {c.nombre: c.nivel for c in preflight.comprobar(args)}
    assert nivel["data/lote2/facturas"] == "VERDE"
    (d / "x.pdf").write_bytes(b"%PDF-otro")
    nivel = {c.nombre: c.nivel for c in preflight.comprobar(args)}
    assert nivel["data/lote2/facturas"] == "ÁMBAR"
