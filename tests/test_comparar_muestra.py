"""scripts/comparar_muestra.py: el contraste de la muestra no enseña el sistema (ni al agente) antes de tiempo.

CSV y BD temporales, sin red. Si el script enseñara las decisiones mientras Mónica etiqueta, su columna dejaría de
ser una comprobación de la norma: es lo único que valida `rules/` contra algo que no es `rules/`.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import unicodedata
from pathlib import Path

import pytest

_RUTA = Path(__file__).resolve().parents[1] / "scripts" / "comparar_muestra.py"
_spec = importlib.util.spec_from_file_location("comparar_muestra", _RUTA)
cm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cm
_spec.loader.exec_module(cm)

FICHEROS = ["a.pdf", "FA-5590_ofimática.pdf", "c.pdf"]
CABECERA = [
    "file_id",
    "esperado_monica",
    "esperado_alfonso",
    "acordado",
    "motivo",
    "pregunta_mentor",
]


def _humanos(ruta: Path, filas: dict[str, tuple[str, str, str]]) -> Path:
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CABECERA)
        for fid in FICHEROS:
            m, a, acordado = filas.get(fid, ("", "", ""))
            w.writerow([fid, m, a, acordado, "", ""])
    return ruta


def _agente(ruta: Path, etiquetas: dict[str, str]) -> Path:
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_id", "esperado_agente", "motivo", "comprobado", "confianza", "duda"])
        for fid, e in etiquetas.items():
            w.writerow([fid, e, "m", "c", "media", ""])
    return ruta


def _decision(conn, fid: str, resultado: str, *, vigente: int = 1, falla: str | None = None):
    sha = f"sha-{fid}"  # un reprocesado deja varias decisiones del mismo fichero; sólo una vigente
    conn.execute(
        "INSERT OR IGNORE INTO ficheros (sha256, file_id, lote, ingerido_en) VALUES (?, ?, 1, 't')",
        (sha, fid),
    )
    motivos = [{"regla_id": "v3.R1", "ok": True, "detalle": "NIF e IBAN ok", "evidencia": {}}]
    if falla:
        motivos.append({"regla_id": "v3.R6", "ok": False, "detalle": falla, "evidencia": {}})
    conn.execute(
        """INSERT INTO decisiones (sha256, file_id, resultado, norma_version, fecha_corte, hechos_hash,
           maestro_version, erp_version, motivos_json, decidido_en, vigente)
           VALUES (?, ?, ?, 'v3', '2026-09-18', 'h', 'm', 'v1', ?, 't', ?)""",
        (sha, fid, resultado, json.dumps(motivos), vigente),
    )
    conn.commit()


@pytest.fixture
def bd(conn, tmp_path):
    """BD con decisiones de las tres: la de `c.pdf` tiene una anterior no vigente que no debe salir."""
    _decision(conn, "a.pdf", "PAGAR")
    _decision(conn, "FA-5590_ofimática.pdf", "ESCALAR", falla="iva mal calculado")
    _decision(conn, "c.pdf", "NO_PAGAR", vigente=0)
    _decision(conn, "c.pdf", "PAGAR")
    return tmp_path / "test.db"


def _correr(capsys, *args: str) -> str:
    if "--agente" not in args:  # nunca el CSV real del agente, aunque exista en el árbol
        args = (*args, "--agente", "/nonexistent/esperado_muestra_agente.csv")
    assert cm.main(list(args)) == 0
    return capsys.readouterr().out


def test_sin_cerrar_no_enseña_ni_el_sistema_ni_el_agente_ni_abre_la_bd(tmp_path, capsys):
    muestra = _humanos(tmp_path / "m.csv", {"a.pdf": ("PAGAR", "", "")})
    agente = _agente(tmp_path / "ag.csv", {f: "ESCALAR" for f in FICHEROS})
    no_existe = tmp_path / "no" / "hay.db"  # si la abriera en escritura, crearía la carpeta
    out = _correr(
        capsys, "--muestra", str(muestra), "--agente", str(agente), "--db", str(no_existe)
    )
    assert "Sistema: oculta" in out and "Agente: oculta" in out
    assert "ESCALAR" not in out  # ni la etiqueta del agente ni nada del sistema
    assert "acordado 0/3 · Mónica 1/3 · Alfonso 0/3" in out
    assert not no_existe.parent.exists()


def test_sin_cerrar_la_bd_real_tampoco_sale(tmp_path, capsys, bd):
    muestra = _humanos(tmp_path / "m.csv", {f: ("PAGAR", "PAGAR", "") for f in FICHEROS[:2]})
    out = _correr(capsys, "--muestra", str(muestra), "--db", str(bd))
    assert "iva mal calculado" not in out and "ESCALAR" not in out
    assert "Mónica = Alfonso: 2 de 2" in out


def test_con_acordado_completo_enseña_el_sistema_y_su_motivo_principal(tmp_path, capsys, bd):
    muestra = _humanos(tmp_path / "m.csv", {f: ("PAGAR", "PAGAR", "PAGAR") for f in FICHEROS})
    agente = _agente(tmp_path / "ag.csv", {f: "PAGAR" for f in FICHEROS})
    out = _correr(capsys, "--muestra", str(muestra), "--agente", str(agente), "--db", str(bd))
    assert "oculta" not in out and "REVELADA" not in out
    assert "Acordado = Sistema: 2 de 3" in out
    assert "Agente = Sistema: 2 de 3" in out
    assert "Discrepancias: (1)" in out
    assert "v3.R6: iva mal calculado" in out
    # sólo cuenta la decisión vigente de c.pdf (PAGAR), no la anterior (NO_PAGAR)
    assert "NO_PAGAR" not in out


def test_sin_alfonso_basta_la_columna_de_mónica(tmp_path, capsys, bd):
    muestra = _humanos(tmp_path / "m.csv", {f: ("PAGAR", "", "") for f in FICHEROS})
    out = _correr(capsys, "--muestra", str(muestra), "--db", str(bd))
    assert "sin Alfonso: cuenta la de Mónica" in out
    assert "Mónica = Sistema: 2 de 3" in out
    assert "Alfonso: vacía, no cuenta" in out and "Acordado: vacía, no cuenta" in out


def test_revelar_antes_de_tiempo_exige_motivo(tmp_path, capsys):
    muestra = _humanos(tmp_path / "m.csv", {})
    with pytest.raises(SystemExit) as e:
        cm.main(["--muestra", str(muestra), "--revelar-sistema"])
    assert e.value.code == 2
    assert "--motivo" in capsys.readouterr().err


def test_revelar_con_motivo_lo_dice_arriba(tmp_path, capsys, bd):
    muestra = _humanos(tmp_path / "m.csv", {"a.pdf": ("PAGAR", "", "")})
    out = _correr(
        capsys,
        "--muestra",
        str(muestra),
        "--db",
        str(bd),
        "--revelar-sistema",
        "--motivo",
        "depurar",
    )
    primeras = out.splitlines()[:3]
    assert any(
        "COLUMNA DEL SISTEMA REVELADA ANTES DE CERRAR" in x and "depurar" in x for x in primeras
    )
    assert "iva mal calculado" in out
    assert "Agente: oculta" in out  # revelar el sistema no revela al agente


def test_el_file_id_en_nfd_casa_con_el_de_la_bd(tmp_path, capsys, bd):
    nfd = {unicodedata.normalize("NFD", f): ("ESCALAR", "ESCALAR", "ESCALAR") for f in FICHEROS}
    ruta = tmp_path / "m.csv"
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CABECERA)
        for fid, (m, a, ac) in nfd.items():
            w.writerow([fid, m, a, ac, "", ""])
    out = _correr(capsys, "--muestra", str(ruta), "--db", str(bd))
    assert "sin decisión vigente" not in out
    assert "Acordado = Sistema: 1 de 3" in out  # sólo FA-5590 es ESCALAR en la BD


def test_una_etiqueta_que_no_es_un_resultado_se_rechaza(tmp_path, capsys):
    muestra = _humanos(tmp_path / "m.csv", {"a.pdf": ("PAGAR ", "pagar", "PAGO")})
    assert cm.main(["--muestra", str(muestra)]) == 2
    assert "PAGO" in capsys.readouterr().err


def test_markdown_es_una_tabla_pegable(tmp_path, capsys, bd):
    muestra = _humanos(tmp_path / "m.csv", {f: ("PAGAR", "PAGAR", "PAGAR") for f in FICHEROS})
    out = _correr(capsys, "--muestra", str(muestra), "--db", str(bd), "--markdown")
    tabla = [x for x in out.splitlines() if x.startswith("|")]
    assert tabla[0].startswith("| file_id | Mónica | Alfonso | Acordado | Sistema |")
    assert len(tabla) == 2 + len(FICHEROS)
    assert (
        "- `FA-5590_ofimática.pdf`: Mónica PAGAR · Alfonso PAGAR · Acordado PAGAR · Sistema ESCALAR"
        in out
    )


def test_el_csv_real_de_la_muestra_se_lee():
    """El fichero de Mónica y Alfonso tiene la forma que el script espera (sus 21 filas, sin valores raros)."""
    humanos = cm.leer_humanos(Path("data/fixtures/esperado_muestra.csv"))
    muestra = [
        ln.strip() for ln in Path("data/fixtures/muestra.txt").read_text("utf-8").splitlines()
    ]
    assert sorted(humanos) == sorted(unicodedata.normalize("NFC", m) for m in muestra if m)
