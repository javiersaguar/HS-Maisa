"""scripts/kit_demo.py: la BD viaja entera y comprobada, y al instalar no se pisa nada sin querer.

BD temporales construidas a mano. Sin red, sin la BD real y sin `albertitos status` (con_status=False).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from albertitos.core import db

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "kit_demo.py"
_spec = importlib.util.spec_from_file_location("kit_demo", _RUTA)
kit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = kit
_spec.loader.exec_module(kit)

AHORA = datetime(2026, 9, 19, 7, 30, tzinfo=UTC)


def bd_con(ruta: Path, ficheros: int, *, resultado: str = "PAGAR") -> Path:
    """Una BD con `ficheros` facturas, cada una con hechos, una decisión vigente y una fila de caché."""
    conn = db.conectar(ruta)
    db.init_schema(conn)
    for i in range(ficheros):
        sha = f"sha{i:03d}-{ruta.stem}"
        conn.execute(
            "INSERT INTO ficheros (sha256, file_id, lote, ingerido_en) VALUES (?, ?, 1, 'x')",
            (sha, f"f{i:03d}.pdf"),
        )
        conn.execute(
            "INSERT INTO hechos VALUES (?, 'ext-0.1', 'plantilla', '{}', 'h', 'x')", (sha,)
        )
        conn.execute(
            "INSERT INTO decisiones (sha256, file_id, resultado, norma_version, fecha_corte, hechos_hash,"
            " maestro_version, erp_version, motivos_json, decidido_en) VALUES"
            " (?, ?, ?, 'v3', '2026-09-18', 'h', 'm1', 'v1', '[]', 'x')",
            (sha, f"f{i:03d}.pdf", resultado),
        )
        conn.execute("INSERT INTO cache_llm VALUES (?, '{}', 1, 1, 0, 'x')", (f"{sha}|p|m",))
    conn.commit()
    conn.close()  # deja el WAL como lo dejaría la CLI
    return ruta


@pytest.fixture
def origen(tmp_path):
    return bd_con(tmp_path / "origen" / "albertitos.db", 3)


def empaquetar(origen: Path, tmp_path: Path) -> Path:
    entrega = tmp_path / "entrega"
    entrega.mkdir(exist_ok=True)
    (entrega / "outcomes.jsonl").write_text('{"file_id":"f000.pdf","result":"PAGAR"}\n')
    return kit.empaquetar(origen, tmp_path / "kit", entrega, ahora=AHORA)


def test_ida_y_vuelta_con_los_mismos_recuentos(origen, tmp_path, capsys):
    tar = empaquetar(origen, tmp_path)
    assert tar.name == "albertitos-kit-20260919-0930.tar.gz"  # hora de Madrid en el nombre
    with tarfile.open(tar) as t:
        assert sorted(t.getnames()) == ["MANIFIESTO.json", "albertitos.db"]
        man = json.load(t.extractfile("MANIFIESTO.json"))
    assert man["recuentos"] == {
        "ficheros_por_lote": {"1": 3},
        "decisiones": {"PAGAR": 3},
        "hechos": 3,
        "cache_llm": 3,
    }
    assert man["versiones_vigentes"][0]["norma"] == "v3" and man["entrega"]["outcomes.jsonl"]
    destino = tmp_path / "alfonso" / "dist" / "albertitos.db"
    assert kit.instalar(tar, destino, con_status=False) == 0
    assert kit.recuentos(destino) == man["recuentos"]
    assert "VEREDICTO: instalado" in capsys.readouterr().out


def test_la_copia_no_depende_del_wal_del_origen(origen, tmp_path):
    """Con otra conexión escribiendo en el origen (WAL a medias), el kit sale coherente."""
    abierta = sqlite3.connect(origen)
    abierta.execute("PRAGMA journal_mode=WAL")
    abierta.execute("INSERT INTO cache_llm VALUES ('nueva', '{}', 1, 1, 0, 'x')")
    abierta.commit()  # queda en el -wal: una copia con cp del .db no la vería
    tar = empaquetar(origen, tmp_path)
    abierta.close()
    with tarfile.open(tar) as t:
        man = json.load(t.extractfile("MANIFIESTO.json"))
    assert man["recuentos"]["cache_llm"] == 4


def test_una_bd_modificada_no_pasa_el_manifiesto(origen, tmp_path, capsys):
    tar = empaquetar(origen, tmp_path)
    trucado = tmp_path / "trucado.tar.gz"
    with tarfile.open(tar) as t, tarfile.open(trucado, "w:gz") as nuevo:
        man = t.extractfile("MANIFIESTO.json").read()
        bd = bytearray(t.extractfile("albertitos.db").read())
        bd[-1] ^= 0xFF  # un byte distinto
        for nombre, datos in (("MANIFIESTO.json", man), ("albertitos.db", bytes(bd))):
            info = tarfile.TarInfo(nombre)
            info.size = len(datos)
            nuevo.addfile(info, io.BytesIO(datos))
    destino = tmp_path / "alfonso" / "albertitos.db"
    assert kit.instalar(trucado, destino, con_status=False) == 1
    assert "sha256 distinto" in capsys.readouterr().out and not destino.exists()


def test_un_kit_con_otros_ficheros_o_rutas_se_rechaza(tmp_path, capsys):
    malo = tmp_path / "malo.tar.gz"
    with tarfile.open(malo, "w:gz") as t:
        for nombre in ("MANIFIESTO.json", "../albertitos.db"):
            info = tarfile.TarInfo(nombre)
            info.size = 2
            t.addfile(info, io.BytesIO(b"{}"))
    assert kit.instalar(malo, tmp_path / "d" / "albertitos.db", con_status=False) == 1
    assert "exactamente" in capsys.readouterr().out
    assert (
        not (tmp_path / "d" / "albertitos.db").exists()
        and not (tmp_path / "albertitos.db").exists()
    )


def test_sin_forzar_no_pisa_una_bd_con_datos(origen, tmp_path, capsys):
    tar = empaquetar(origen, tmp_path)
    destino = bd_con(tmp_path / "alfonso" / "albertitos.db", 7, resultado="ESCALAR")
    antes = kit.sha256_de(destino)
    assert kit.instalar(tar, destino, con_status=False) == 1
    assert "No la piso" in capsys.readouterr().out
    assert kit.sha256_de(destino) == antes
    assert not destino.with_name("albertitos.db.antes-del-kit").exists()


def test_con_forzar_deja_la_copia_antes_del_kit_y_no_pisa_una_copia_anterior(origen, tmp_path):
    tar = empaquetar(origen, tmp_path)
    destino = bd_con(tmp_path / "alfonso" / "albertitos.db", 7, resultado="ESCALAR")
    # restos del WAL de la BD anterior: si se quedaran, SQLite los aplicaría a la nueva
    destino.with_name("albertitos.db-wal").write_bytes(b"basura")
    assert kit.instalar(tar, destino, forzar=True, con_status=False) == 0
    copia = destino.with_name("albertitos.db.antes-del-kit")
    assert kit.recuentos(copia)["decisiones"] == {"ESCALAR": 7}
    assert kit.recuentos(destino)["decisiones"] == {"PAGAR": 3}
    assert not destino.with_name("albertitos.db-wal").exists()
    # un segundo --forzar no sobrescribe la primera copia (la única con los datos de antes)
    assert kit.instalar(tar, destino, forzar=True, con_status=False) == 0
    assert kit.recuentos(copia)["decisiones"] == {"ESCALAR": 7}
    assert len(list(destino.parent.glob("albertitos.db.antes-del-kit*"))) == 2


def test_la_bd_vacia_de_bootstrap_se_sustituye_sin_forzar(origen, tmp_path, capsys):
    tar = empaquetar(origen, tmp_path)
    destino = tmp_path / "alfonso" / "albertitos.db"
    destino.parent.mkdir(parents=True)
    conn = db.conectar(destino)
    db.init_schema(conn)  # lo que hace ./bootstrap.sh con `albertitos db init`
    conn.close()
    assert kit.instalar(tar, destino, con_status=False) == 0
    assert "estaba vacía" in capsys.readouterr().out
    assert kit.recuentos(destino)["ficheros_por_lote"] == {"1": 3}


def test_avisa_de_un_caos_encendido_en_destino(origen, tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("ALBERTITOS_CHAOS", raising=False)
    tar = empaquetar(origen, tmp_path)
    destino = tmp_path / "alfonso" / "albertitos.db"
    destino.parent.mkdir(parents=True)
    destino.with_name("albertitos.db.chaos.json").write_text('{"modo": "llm_down"}')
    assert kit.instalar(tar, destino, con_status=False) == 0
    salida = capsys.readouterr().out
    assert "caos encendido" in salida and "con avisos" in salida


def test_codigo_mas_viejo_que_el_kit(tmp_path):
    assert kit.estado_del_codigo("0" * 40)[0] == "ÁMBAR"
    cabeza = kit.git("rev-parse", "HEAD").stdout.strip()
    assert kit.estado_del_codigo(cabeza) == (
        "OK",
        f"el código contiene el commit del kit ({cabeza[:9]})",
    )
