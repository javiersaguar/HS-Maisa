"""Pruebas de despliegue sin red, gateway ni BD de entrega."""

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from albertitos.console import bandeja
from albertitos.core import db

spec = importlib.util.spec_from_file_location(
    "iniciar_puente", Path(__file__).with_name("iniciar_puente.py")
)
inicio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inicio)


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    for nombre in ("ALBERTITOS_CLAVE_DEMO", "ALBERTITOS_BANDEJA_MAX", "ALBERTITOS_BANDEJA_EFIMERA"):
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture
def origen(tmp_path):
    ruta = tmp_path / "demo.db"
    with sqlite3.connect(ruta) as conn:
        conn.execute("CREATE TABLE prueba (valor TEXT)")
        conn.execute("INSERT INTO prueba VALUES ('original')")
    return ruta


def test_sin_clave_no_copia_ni_abre_subidas(origen, monkeypatch):
    monkeypatch.setattr(inicio.tempfile, "mkdtemp", lambda **kw: pytest.fail("no debe copiar"))
    assert inicio.comando(origen)[-2:] == ["--db", str(origen)]
    assert "--bandeja" not in inicio.comando(origen)


def test_con_clave_copia_nueva_en_cada_arranque(origen, monkeypatch, tmp_path):
    monkeypatch.setenv("ALBERTITOS_CLAVE_DEMO", "clave-de-prueba")
    carpetas = iter([tmp_path / "arranque1", tmp_path / "arranque2"])
    monkeypatch.setattr(inicio.tempfile, "mkdtemp", lambda **kw: str(next(carpetas)))
    antes = origen.read_bytes()
    primera = inicio.comando(origen)
    assert primera[-1] == "--bandeja"
    copia1 = Path(primera[-2])
    with sqlite3.connect(copia1) as conn:
        conn.execute("UPDATE prueba SET valor = 'subida'")
    copia2 = Path(inicio.comando(origen)[-2])
    assert copia1 != copia2
    with sqlite3.connect(copia2) as conn:
        assert conn.execute("SELECT valor FROM prueba").fetchone()[0] == "original"
    assert origen.read_bytes() == antes
    assert bandeja.Bandeja(copia2, activa=True).estado()["efimera"] is True


def test_con_clave_sin_puerta_no_arranca(origen, monkeypatch):
    monkeypatch.setenv("ALBERTITOS_CLAVE_DEMO", "clave-de-prueba")
    monkeypatch.delattr(inicio.api, "clave_ok", raising=False)
    with pytest.raises(RuntimeError, match="puerta del backend"):
        inicio.comando(origen)


def test_efimera_sin_clave_rechaza_subidas(origen, monkeypatch):
    monkeypatch.setenv("ALBERTITOS_BANDEJA_EFIMERA", "1")
    b = bandeja.Bandeja(origen, activa=True)
    assert b.recibir(b"", None)[0] == 409
    assert not b.disponible


@pytest.mark.parametrize("valor", ["-1", "no-entero", "1.5"])
def test_limite_invalido_falla_cerrado(tmp_path, monkeypatch, valor):
    monkeypatch.setenv("ALBERTITOS_BANDEJA_MAX", valor)
    with pytest.raises(ValueError, match="entero no negativo"):
        bandeja.Bandeja(tmp_path / "demo.db", activa=True)


def test_limite_defecto_40(tmp_path):
    assert bandeja.Bandeja(tmp_path / "demo.db").estado()["restantes_arranque"] == 40


@pytest.mark.parametrize("limite", [0, 2])
def test_cupo_rechaza_sin_escribir_ni_ejecutar(tmp_path, monkeypatch, limite):
    monkeypatch.setenv("ALBERTITOS_BANDEJA_MAX", str(limite))
    ruta = tmp_path / "demo.db"
    conn = db.conectar(ruta)
    db.init_schema(conn)
    conn.close()
    llamadas = []

    def runner(args, ruta):
        llamadas.append(args)
        return 1, "fallo simulado"

    b = bandeja.Bandeja(ruta, runner=runner, activa=True)
    monkeypatch.setattr(bandeja, "leer_multipart", lambda *args: [("a.pdf", b"%PDF-prueba")])
    for _ in range(limite):
        assert b.recibir(b"", None)[0] == 500
    monkeypatch.setattr(
        bandeja, "leer_multipart", lambda *args: [("rechazado.pdf", b"%PDF-prueba")]
    )
    estado, cuerpo = b.recibir(b"", None)
    assert estado == 409 and "Límite" in cuerpo["error"]
    assert len(llamadas) == limite
    assert not (b.carpeta / "rechazado.pdf").exists()
    assert b.estado()["restantes_arranque"] == 0
    assert b.estado()["recibidos_arranque"] == limite
