"""El catálogo y el detector no deben dejar volver cifras de una sola lectura."""

import importlib.util
import json
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "scripts/cifras_check.py"
spec = importlib.util.spec_from_file_location("cifras_check", RUTA)
cifras = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cifras)


@pytest.fixture
def catalogo(tmp_path):
    p = tmp_path / "docs/CIFRAS.md"
    p.parent.mkdir()
    p.write_text(
        "<!-- cifras-obsoletas\n"
        + json.dumps(
            [
                {
                    "formas": ["0,22 ficheros/s"],
                    "vigente": "0,065–0,106 ficheros/s (doble lectura)",
                    "fuente": "docs/agentes/ESCALA-10K.md §4",
                }
            ]
        )
        + "\n-->\n"
    )
    for nombre in cifras.OBJETIVOS:
        ruta = tmp_path / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("Sólo 0,065–0,106 ficheros/s.\n")
    return p


@pytest.mark.parametrize(
    "vieja", ["0,22 ficheros/s", "**0.22**  ficheros/s", "antes 0,22 ficheros/s; ya corregido"]
)
def test_cifra_obsoleta_con_linea_y_sustitucion_sin_escribir(tmp_path, catalogo, vieja, capsys):
    plan = tmp_path / cifras.OBJETIVOS[0]
    plan.write_text("# Plan\n" + vieja + "\n")
    antes = plan.read_bytes()
    assert cifras.main(["--raiz", str(tmp_path)]) == 1
    salida = capsys.readouterr().out
    assert "docs/plan/albertitos_plan.md:2:" in salida
    assert "0,065–0,106" in salida and "ESCALA-10K.md §4" in salida
    assert plan.read_bytes() == antes


def test_vigentes_y_numero_distinto_no_fallan(tmp_path, catalogo):
    (tmp_path / cifras.OBJETIVOS[0]).write_text(
        "10,22 ficheros/s no es 0,22 ni una afirmación sobre visión.\n"
    )
    assert cifras.main(["--raiz", str(tmp_path)]) == 0


def test_documento_ausente_no_da_falso_verde(tmp_path, catalogo):
    (tmp_path / cifras.OBJETIVOS[1]).unlink()
    assert cifras.main(["--raiz", str(tmp_path)]) == 2


def test_catalogo_malformado_no_da_falso_verde(tmp_path, catalogo):
    catalogo.write_text("<!-- cifras-obsoletas\n[]\n-->\n")
    assert cifras.main(["--raiz", str(tmp_path)]) == 2


def test_catalogo_real_incluye_forma_de_regresion():
    reglas = cifras.cargar_reglas(RUTA.parents[1] / "docs/CIFRAS.md")
    assert any("0,22 ficheros/s" in r["formas"] for r in reglas)


def test_mencion_historica_declarada_no_cuenta_pero_otra_linea_si(tmp_path):
    """La frase que explica por qué se abandonó una cifra no es un error; la misma cifra en otra línea, sí."""
    catalogo = tmp_path / "CIFRAS.md"
    reglas = [
        {
            "formas": ["0,22 ficheros/s"],
            "vigente": "0,065",
            "fuente": "ESCALA-10K §4",
            "historicas": [
                {"fichero": "docs/benchmark.md", "contiene": "La cifra que usábamos antes"}
            ],
        }
    ]
    catalogo.write_text(
        "<!-- cifras-obsoletas\n" + json.dumps(reglas, ensure_ascii=False) + "\n-->\n",
        encoding="utf-8",
    )
    doc = tmp_path / "docs" / "benchmark.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "La cifra que usábamos antes, 0,22 ficheros/s, era de una lectura.\n"
        "La visión va a 0,22 ficheros/s.\n",
        encoding="utf-8",
    )
    hallazgos = cifras.comprobar(tmp_path, catalogo, archivos=("docs/benchmark.md",))
    assert [h["linea"] for h in hallazgos] == [2]
