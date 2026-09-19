"""El guardián de Bash tiene que decidir igual en los cuatro portátiles.

Estos tests simulan un portátil cualquiera (sin `.claude/dueno.local`, es decir, nadie es dueño del
merge) y otro el de Miguel, y comprueban las prohibiciones que de verdad nos pueden costar la entrega.
El caso que motivó el fichero: el runbook de entrega hace push a `main` del repo HS-Maisa-Entrega, y
la regla "a main sólo Miguel" —que habla de ESTE repo— lo bloqueaba en el portátil de quien entregase.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "guard_bash.py"


def entorno(raiz: Path, **extra: str) -> dict[str, str]:
    """El entorno del sistema (PATH con git, SYSTEMROOT en Windows) sin nada que cambie la decisión del hook:
    ni el marcador de dueño por variable ni el proyecto real. Antes se pasaba un PATH de Unix fijo y en
    Windows el hook no encontraba git: 5 tests fallaban en el portátil de Miguel."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("ALBERTITOS_", "CLAUDE_")) and k != "PYTHONPATH"
    }
    env.update(CLAUDE_PROJECT_DIR=str(raiz), PYTHONUTF8="1", **extra)
    return env


def decidir(comando: str, raiz: Path) -> str:
    """Lanza el hook como lo lanza Claude Code y devuelve deny/ask/allow, o 'pasa' si no dice nada."""
    entrada = json.dumps({"cwd": str(raiz), "tool_input": {"command": comando}})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        env=entorno(raiz),
    )
    assert proc.returncode == 0, proc.stderr
    salida = proc.stdout.strip()
    if not salida:
        return "pasa"
    return json.loads(salida)["hookSpecificOutput"]["permissionDecision"]


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def portatil(tmp_path: Path) -> Path:
    """Un clon de trabajo cualquiera: repo git en main, sin marcador de dueño."""
    raiz = tmp_path / "HS-Maisa"
    (raiz / ".claude").mkdir(parents=True)
    git("init", "-q", "-b", "main", str(raiz), cwd=tmp_path)
    # Sin un commit, `git rev-parse --abbrev-ref HEAD` no dice "main" y la regla no se activaría.
    (raiz / "README.md").write_text("x", encoding="utf-8")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", "README.md", cwd=raiz)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "inicial", cwd=raiz)
    git("switch", "-q", "-c", "javier/ingesta", cwd=raiz)
    return raiz


def marcar_dueno(raiz: Path) -> Path:
    (raiz / ".claude" / "dueno.local").write_text("merge\ncontratos\n", encoding="utf-8")
    return raiz


@pytest.fixture
def portatil_de_miguel(portatil: Path) -> Path:
    return marcar_dueno(portatil)


@pytest.fixture
def portatil_en_main(portatil: Path) -> Path:
    git("switch", "-q", "main", cwd=portatil)
    return portatil


@pytest.fixture
def repo_entrega(tmp_path: Path) -> Path:
    destino = tmp_path / "HS-Maisa-Entrega"
    destino.mkdir()
    git("init", "-q", "-b", "main", str(destino), cwd=tmp_path)
    return destino


# --------------------------------------------------------------------------- main es de Miguel


def test_push_a_main_bloqueado_para_el_resto(portatil: Path) -> None:
    assert decidir("git push -u origin HEAD:main", portatil) == "deny"


def test_push_de_tu_rama_permitido(portatil: Path) -> None:
    assert decidir("git push -u origin javier/ingesta", portatil) == "pasa"


def test_commit_en_main_bloqueado_para_el_resto(portatil_en_main: Path) -> None:
    assert decidir("git commit -m 'sources: algo'", portatil_en_main) == "deny"


def test_commit_en_tu_rama_permitido(portatil: Path) -> None:
    assert decidir("git commit -m 'sources: algo'", portatil) == "pasa"


def test_miguel_si_puede(portatil_de_miguel: Path) -> None:
    git("switch", "-q", "main", cwd=portatil_de_miguel)
    assert decidir("git push origin main", portatil_de_miguel) == "pasa"


# --------------------------------------------------------------------------- repo de entrega


def test_entrega_a_main_permitida_en_cualquier_portatil(portatil: Path, repo_entrega: Path) -> None:
    """El runbook de entrega usa `git -C`: va a otro repo, así que la regla de main no aplica."""
    assert decidir(f"git -C {repo_entrega} push -u origin HEAD:main", portatil) == "pasa"


def test_push_forzado_prohibido_tambien_en_el_repo_de_entrega(
    portatil: Path, repo_entrega: Path
) -> None:
    """`git -C` no puede ser una puerta trasera para reescribir historia."""
    assert decidir(f"git -C {repo_entrega} push --force origin main", portatil) == "deny"


def test_push_forzado_prohibido_aqui(portatil: Path) -> None:
    assert decidir("git push --force-with-lease origin javier/ingesta", portatil) == "deny"


# --------------------------------------------------------------------------- el resto de las reglas


def test_los_outcomes_no_se_escriben_a_mano(portatil: Path) -> None:
    assert decidir("echo '{}' >> dist/entrega/outcomes.jsonl", portatil) == "deny"


def test_no_se_borra_la_caja(portatil: Path) -> None:
    assert decidir("rm -rf data/caja/facturas", portatil) == "deny"


def test_pip_prohibido(portatil: Path) -> None:
    assert decidir("python -m pip install pandas", portatil) == "deny"


def test_los_contratos_solo_los_toca_miguel(portatil: Path) -> None:
    orden = "sed -i s/x/y/ src/albertitos/core/contracts.py"
    assert decidir(orden, portatil) == "deny"
    assert decidir(orden, marcar_dueno(portatil)) == "pasa"


def test_la_documentacion_puede_hablar_de_comandos_prohibidos(portatil: Path) -> None:
    """Un heredoc es contenido, no comandos: escribir 'git push main' en un doc no puede bloquear."""
    orden = "cat > docs/nota.md <<'EOF'\nNunca hagas git push origin main\nEOF"
    assert decidir(orden, portatil) == "pasa"


@pytest.mark.parametrize("sin_decision", [0, 4])
def test_inicio_cuenta_ficheros_sin_decision_no_eventos_antiguos(portatil, sin_decision):
    ruta = portatil / "dist/albertitos.db"
    ruta.parent.mkdir()
    with sqlite3.connect(ruta) as c:
        c.executescript(
            "CREATE TABLE ficheros(sha256 TEXT, file_id TEXT);"
            "CREATE TABLE decisiones(sha256 TEXT, vigente INTEGER);"
            "CREATE TABLE eventos(estado TEXT);"
            "INSERT INTO ficheros VALUES ('resuelto','resuelto.pdf');"
            "INSERT INTO decisiones VALUES ('resuelto',1);"
        )
        c.executemany("INSERT INTO eventos VALUES (?)", [("pendiente",)] * 7)
        for i in range(sin_decision):
            c.execute("INSERT INTO ficheros VALUES (?,?)", (str(i), f"pendiente_{i}.pdf"))
            c.execute("INSERT INTO decisiones VALUES (?,0)", (str(i),))
    antes = ruta.read_bytes()
    p = subprocess.run(
        [sys.executable, str(HOOK.with_name("session_start.py"))],
        input=json.dumps({"cwd": str(portatil)}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=entorno(portatil, ALBERTITOS_ERP_URL="http://127.0.0.1:1"),
        timeout=10,
    )
    assert p.returncode == 0
    assert f"ficheros sin decisión={sin_decision}" in p.stdout
    assert "eventos pendientes=" not in p.stdout
    if sin_decision:
        assert "pendiente_0.pdf, pendiente_1.pdf, pendiente_2.pdf" in p.stdout
        assert "pendiente_3.pdf" not in p.stdout
    assert ruta.read_bytes() == antes


def test_inicio_bd_ilegible_no_rompe_sesion(portatil):
    ruta = portatil / "dist/albertitos.db"
    ruta.parent.mkdir()
    ruta.write_bytes(b"no es sqlite")
    p = subprocess.run(
        [sys.executable, str(HOOK.with_name("session_start.py"))],
        input=json.dumps({"cwd": str(portatil)}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=entorno(portatil, ALBERTITOS_ERP_URL="http://127.0.0.1:1"),
        timeout=10,
    )
    assert p.returncode == 0 and "existe pero no se lee" in p.stdout
