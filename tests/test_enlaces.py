"""El comprobador de enlaces relativos: uno bueno, uno roto, uno http y uno dentro de código."""

import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "scripts/enlaces_check.py"
spec = importlib.util.spec_from_file_location("enlaces_check", RUTA)
enlaces = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enlaces)


def test_destinos_ignora_http_y_ancla_sola():
    assert enlaces.destinos("[ok](../foo.md)") == ["../foo.md"]
    assert enlaces.destinos("[web](https://example.com/x.md)") == []
    assert enlaces.destinos("[mail](mailto:a@b.c)") == []
    assert enlaces.destinos("[aquí](#seccion)") == []
    assert enlaces.destinos("![img](foto.png)") == []
    assert enlaces.destinos('rutas()["/bonus/calendario"](conn, {"proveedor": ["P001"]})') == []


def test_lineas_fuera_de_codigo_saltan_el_fence():
    texto = "fuera [a](a.md)\n```\ndentro [b](b.md)\n```\nfuego [c](c.md)\n"
    pares = list(enlaces.lineas_fuera_de_codigo(texto))
    assert [n for n, _ in pares] == [1, 5]
    assert "b.md" not in "".join(linea for _, linea in pares)


def test_arbol_temporal_bueno_roto_http_y_codigo(tmp_path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "existe.md").write_text("# hay\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        "\n".join(
            [
                "[bueno](docs/existe.md)",
                "[roto](docs/no-existe.md#ancla)",
                "[web](https://example.com/no.md)",
                "```",
                "[dentro](docs/tampoco.md)",
                "```",
                "[mail](mailto:x@y.z)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rotos = enlaces.comprobar(tmp_path)
    assert rotos == [("CLAUDE.md", 2, "docs/no-existe.md#ancla")]
    assert enlaces.main(["--raiz", str(tmp_path)]) == 1
    salida = capsys.readouterr().out
    assert "CLAUDE.md:2 → docs/no-existe.md#ancla" in salida
    assert "https://" not in salida
    assert "tampoco.md" not in salida
    assert (docs / "existe.md").read_text(encoding="utf-8") == "# hay\n"


def test_arbol_sin_rotos_sale_cero(tmp_path, capsys):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("[sigue](b.md#x)\n", encoding="utf-8")
    (tmp_path / "docs" / "b.md").write_text("ok\n", encoding="utf-8")
    assert enlaces.main(["--raiz", str(tmp_path)]) == 0
    assert "OK: ningún enlace relativo roto." in capsys.readouterr().out


def test_codigo_en_linea_no_es_un_enlace(tmp_path):
    """Un resumen que CITA un enlace roto entre comillas invertidas no es un enlace roto."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(
        "El fallo era `[x](no-existe.md)`, ya corregido.\n", encoding="utf-8"
    )
    assert enlaces.comprobar(tmp_path) == []
