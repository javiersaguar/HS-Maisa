"""El comprobador de contrato avisa si faltan o sobran claves; no mira valores."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from albertitos.console import api

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "contrato_api_check.py"
_spec = importlib.util.spec_from_file_location("contrato_api_check", _RUTA)
assert _spec and _spec.loader
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def test_claves_anidadas_y_mapa_de_datos():
    a = {
        "total": 1,
        "pagos": [{"file_id": "a.pdf", "importe_eur": "1.00"}],
        "semanas": {
            "2026-W06": {"numero": 1, "importe_eur": "1.00"},
            "2026-W07": {"numero": 2, "importe_eur": "2.00"},
            "2026-W08": {"numero": 3, "importe_eur": "3.00"},
            "2026-W09": {"numero": 4, "importe_eur": "4.00"},
        },
    }
    b = {
        "total": 9,
        "pagos": [{"file_id": "b.pdf", "importe_eur": "9.00", "extra": 1}],
        "semanas": {
            "2026-W10": {"numero": 9, "importe_eur": "9.00"},
            "2026-W11": {"numero": 1, "importe_eur": "1.00"},
            "2026-W12": {"numero": 1, "importe_eur": "1.00"},
            "2026-W13": {"numero": 1, "importe_eur": "1.00"},
        },
    }
    assert "pagos[].file_id" in chk.claves(a)
    assert "semanas.2026-W06" not in chk.claves(a)
    assert "semanas{}.numero" in chk.claves(a)
    assert "pagos[].extra" in chk.claves(b) - chk.claves(a)


def test_parsear_peticion_y_forma_equivalente(tmp_path):
    m, p, q = chk.parsear_peticion("GET /bonus/calendario?vencido=false&limite=3")
    assert (m, p, q) == ("GET", "/bonus/calendario", {"vencido": ["false"], "limite": ["3"]})
    ficha = tmp_path / "confianza-fichero-x.json"
    datos = {"file_id": "scan_006.pdf", "puntuacion": 45}
    parsed = chk.ejemplo_a_peticion(ficha, datos)
    assert parsed is not None
    assert parsed[1] == "/confianza/fichero" and parsed[2] == {"file_id": ["scan_006.pdf"]}


def test_comprobar_detecta_clave_que_falta(tmp_path, monkeypatch):
    ej = tmp_path / "ejemplos"
    ej.mkdir()
    (ej / "bonus-resumen.json").write_text(
        json.dumps(
            {
                "peticion": "GET /bonus/resumen",
                "status": 200,
                "respuesta": {"decisiones_pagar": 1, "calendario_total_eur": "1.00"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "despachar", lambda *_a: (200, {"decisiones_pagar": 1}))
    monkeypatch.setattr(api, "RUTAS", dict(api.RUTAS))
    fallos = chk.comprobar(None, ej)
    assert any("calendario_total_eur" in f and "faltan" in f for f in fallos)


def test_comprobar_ok_si_mismas_claves(tmp_path, monkeypatch):
    ej = tmp_path / "ejemplos"
    ej.mkdir()
    (ej / "bonus-avisos.json").write_text(
        json.dumps(
            {
                "peticion": "GET /bonus/avisos",
                "status": 200,
                "respuesta": {"total": 0, "avisos": []},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "despachar", lambda *_a: (200, {"total": 11, "avisos": []}))
    monkeypatch.setattr(api, "RUTAS", dict(api.RUTAS))
    assert chk.comprobar(None, ej) == []


def test_ignora_nota_del_ejemplo(tmp_path, monkeypatch):
    ej = tmp_path / "ejemplos"
    ej.mkdir()
    (ej / "confianza-ficheros.json").write_text(
        json.dumps(
            {
                "peticion": "GET /confianza/ficheros",
                "status": 200,
                "respuesta": {
                    "api": 1,
                    "items": [],
                    "total": 0,
                    "limite": 50,
                    "nota_del_ejemplo": "x",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        api, "despachar", lambda *_a: (200, {"api": 1, "items": [], "total": 0, "limite": 50})
    )
    monkeypatch.setattr(api, "RUTAS", dict(api.RUTAS))
    assert chk.comprobar(None, ej) == []
