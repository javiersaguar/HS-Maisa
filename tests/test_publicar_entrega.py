"""Publicación offline: Git real contra un bare local; pipeline/auditoría de pega.

Sólo main(comandos=..., raiz=..., ahora=...) permite inyectar esos scripts.
No hay flags de producción que permitan sustituir la auditoría.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from test_hooks import decidir

RUTA = Path(__file__).resolve().parents[1] / "scripts/publicar_entrega.py"
spec = importlib.util.spec_from_file_location("publicar_entrega", RUTA)
pub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pub
spec.loader.exec_module(pub)
AHORA = datetime(2026, 9, 19, 17, 30, tzinfo=pub.MADRID)


def git(ruta, *args):
    return subprocess.run(
        ["git", "-C", str(ruta), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def caso(tmp_path, monkeypatch):
    # Identidad sólo de estos subprocesos, ni configuración global ni red.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    raiz = tmp_path / "solucion"
    raiz.mkdir()
    git(raiz, "init", "-q", "-b", "javier/ingesta")
    git(raiz, "config", "user.name", "Prueba")
    git(raiz, "config", "user.email", "prueba@example.test")
    remoto = tmp_path / "remoto.git"
    git(tmp_path, "init", "--bare", "-q", "-b", "main", str(remoto))
    destino = tmp_path / "HS-Maisa-Entrega"
    git(tmp_path, "clone", str(remoto), str(destino))
    git(destino, "config", "user.name", "Prueba")
    git(destino, "config", "user.email", "prueba@example.test")
    monkeypatch.setenv("ENTREGA_REPO", str(remoto))
    (raiz / "dist/entrega").mkdir(parents=True)
    (raiz / "dist/entrega/albertitos_plan.pdf").write_bytes(b"%PDF-plan-prueba")
    (raiz / "docs").mkdir()
    (raiz / "docs/entregas.log").write_text("# registro\n")
    bd = raiz / "dist/albertitos.db"
    with sqlite3.connect(bd) as c:
        c.executescript(
            "CREATE TABLE ficheros(sha256 TEXT,file_id TEXT,lote INTEGER); CREATE TABLE decisiones(sha256 TEXT,resultado TEXT,norma_version TEXT,erp_version TEXT,vigente INTEGER);"
        )
        c.execute("INSERT INTO ficheros VALUES ('sha','a.pdf',1)")
        c.execute("INSERT INTO decisiones VALUES ('sha','PAGAR','v3','v1',1)")
    doble = raiz / "doble.py"
    doble.write_text("""import json,sys
from pathlib import Path
args=sys.argv[1:]
raiz=Path.cwd()
with (raiz/'llamadas.txt').open('a') as f: f.write(json.dumps(args)+'\\n')
if args[0]=='package':
    p=Path(args[args.index('--salida')+1]);p.mkdir()
    (p/'outcomes.jsonl').write_text(json.dumps({'file_id':'a.pdf','result':'PAGAR'})+'\\n')
    if (raiz/'generar-lote2').exists(): (p/'outcomes_lote2.jsonl').write_text(json.dumps({'file_id':'b.pdf','result':'ESCALAR'})+'\\n')
elif args[0]=='validate':
    if (raiz/'validacion-falla').exists(): sys.exit(1)
elif args[0]=='audit':
    if (raiz/'audit-crash').exists(): sys.exit(2)
    if (raiz/'rojo').exists():
        print('scan_025.pdf: evidencia None\\nVEREDICTO: ROJO');sys.exit(1)
    print('VEREDICTO: VERDE')
""")
    comandos = pub.Comandos((sys.executable, str(doble)), (sys.executable, str(doble), "audit"))
    return raiz, destino, remoto, comandos


def llamar(caso, *opciones, ahora=AHORA):
    raiz, destino, _, comandos = caso
    return pub.main(
        ["--sin-gh", "--destino", str(destino), *opciones],
        raiz=raiz,
        comandos=comandos,
        ahora=ahora,
    )


def test_seco_no_modifica_remoto_destino_bd_ni_registro(caso):
    raiz, destino, remoto, _ = caso
    antes = pub.huella(raiz / "dist/albertitos.db")
    assert llamar(caso) == 0
    assert not git(remoto, "for-each-ref")
    assert {p.name for p in destino.iterdir()} == {".git"}
    assert (raiz / "docs/entregas.log").read_text() == "# registro\n"
    assert pub.huella(raiz / "dist/albertitos.db") == antes


def test_publica_archivos_exactos_y_segunda_vez_no_commit(caso):
    raiz, destino, remoto, _ = caso
    assert llamar(caso, "--publicar") == 0
    commit = git(remoto, "rev-parse", "main")
    assert git(remoto, "ls-tree", "--name-only", "main").splitlines() == [
        "albertitos_plan.pdf",
        "outcomes.jsonl",
    ]
    assert {p.name for p in destino.iterdir()} == {".git", "albertitos_plan.pdf", "outcomes.jsonl"}
    mensaje = git(remoto, "log", "-1", "--format=%B", "main")
    assert "lote1 1 (1/0/0)" in mensaje and "norma v3 · erp v1" in mensaje
    registro = (raiz / "docs/entregas.log").read_text()
    assert commit in registro
    assert llamar(caso, "--publicar") == 0
    assert git(remoto, "rev-parse", "main") == commit
    assert (raiz / "docs/entregas.log").read_text() == registro


def test_rojo_para_y_excepcion_queda_en_commit_y_log(caso, capsys):
    raiz, destino, remoto, _ = caso
    (raiz / "rojo").touch()
    assert llamar(caso, "--publicar") == 1
    assert "scan_025.pdf" in capsys.readouterr().out
    assert not git(remoto, "for-each-ref")
    motivo = "scan_025: ESCALAR correcto; evidencia 'None' pendiente de Mónica"
    assert llamar(caso, "--publicar", "--aceptar-rojo", motivo) == 0
    assert motivo in git(remoto, "log", "-1", "--format=%B", "main")
    assert motivo in (raiz / "docs/entregas.log").read_text()
    # package también audita: el motivo le llega, o su puerta pararía el rojo antes que publicar
    llamadas = [json.loads(x) for x in (raiz / "llamadas.txt").read_text().splitlines()]
    paquetes = [a for a in llamadas if a[0] == "package"]
    assert "--aceptar-rojo" not in paquetes[0]
    assert paquetes[-1][-2:] == ["--aceptar-rojo", motivo]


@pytest.mark.parametrize("fallo", ["README.md", "lote2", "validacion-falla", "audit-crash"])
def test_bloqueos_no_se_saltan_aceptando_rojo(caso, fallo):
    raiz, destino, remoto, _ = caso
    if fallo == "README.md":
        (destino / fallo).write_text("conservar")
    elif fallo == "lote2":
        (raiz / "data/lote2/facturas").mkdir(parents=True)
        (raiz / "data/lote2/facturas/b.pdf").write_bytes(b"pdf")
    else:
        (raiz / fallo).touch()
    assert llamar(caso, "--publicar", "--aceptar-rojo", "no autoriza fallos técnicos") == 1
    assert not git(remoto, "for-each-ref")
    if fallo == "README.md":
        assert (destino / fallo).read_text() == "conservar"


def test_lote2_se_valida_y_publica(caso):
    raiz, _, remoto, _ = caso
    (raiz / "generar-lote2").touch()
    with sqlite3.connect(raiz / "dist/albertitos.db") as c:
        c.execute("INSERT INTO ficheros VALUES ('sha2','b.pdf',2)")
        c.execute("INSERT INTO decisiones VALUES ('sha2','ESCALAR','v4','v2',1)")
    assert llamar(caso, "--publicar") == 0
    assert "outcomes_lote2.jsonl" in git(remoto, "ls-tree", "--name-only", "main")
    llamadas = [json.loads(x) for x in (raiz / "llamadas.txt").read_text().splitlines()]
    assert any(x[0] == "validate" and x[-1] == "2" for x in llamadas)
    assert "norma v3,v4 · erp v1,v2" in git(remoto, "log", "-1", "--format=%B", "main")


def test_cierre_y_motivo_vacio(caso):
    tarde = datetime(2026, 9, 20, 10, 31, tzinfo=pub.MADRID)
    assert llamar(caso, ahora=tarde) == 1
    assert llamar(caso, "--despues-del-cierre", ahora=tarde) == 0
    assert llamar(caso, "--aceptar-rojo", "  ") == 1


def test_comandos_git_generados_pasan_hook(caso, monkeypatch):
    raiz = caso[0]
    original = pub.ejecutar
    comandos = []

    def observar(args, **kwargs):
        if args[0] == "git":
            comandos.append(list(args))
            assert args[1] == "-C"
            assert decidir(shlex.join(args), raiz) == "pasa"
        return original(args, **kwargs)

    monkeypatch.setattr(pub, "ejecutar", observar)
    assert llamar(caso, "--publicar") == 0
    assert any("HEAD:main" in x for x in comandos)


def test_cambios_locales_no_se_pisan(caso):
    assert llamar(caso, "--publicar") == 0
    (caso[1] / "outcomes.jsonl").write_text("trabajo ajeno")
    assert llamar(caso, "--publicar") == 1
    assert (caso[1] / "outcomes.jsonl").read_text() == "trabajo ajeno"


def test_push_rechazado_no_se_registra_como_publicado(caso):
    raiz, _, remoto, _ = caso
    hook = remoto / "hooks/pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    assert llamar(caso, "--publicar") == 1
    assert not git(remoto, "for-each-ref")
    assert (raiz / "docs/entregas.log").read_text() == "# registro\n"


def test_origin_de_push_distinto_bloquea(caso):
    git(caso[1], "config", "remote.origin.pushurl", str(caso[0] / "otro.git"))
    assert llamar(caso, "--publicar") == 1
    assert not git(caso[2], "for-each-ref")


def test_repo_privado_bloquea_antes_de_copiar(caso, monkeypatch):
    original = pub.ejecutar

    def privado(args, **kwargs):
        if args[0] == "gh":
            return subprocess.CompletedProcess(args, 0, '{"visibility":"PRIVATE"}', "")
        return original(args, **kwargs)

    monkeypatch.setattr(pub, "ejecutar", privado)
    raiz, destino, remoto, comandos = caso
    assert (
        pub.main(
            ["--destino", str(destino), "--publicar"], raiz=raiz, comandos=comandos, ahora=AHORA
        )
        == 1
    )
    assert not git(remoto, "for-each-ref")
    assert {p.name for p in destino.iterdir()} == {".git"}


def test_destino_nuevo_se_clona_solo_al_publicar(caso):
    raiz, destino, remoto, comandos = caso
    nuevo = destino.parent / "entrega nueva"
    otro = raiz, nuevo, remoto, comandos
    assert llamar(otro) == 0
    assert not nuevo.exists()
    assert llamar(otro, "--publicar") == 0
    assert (nuevo / ".git").is_dir()
    assert git(remoto, "rev-parse", "main") == git(nuevo, "rev-parse", "HEAD")
    (raiz / "dist/entrega/albertitos_plan.pdf").write_bytes(b"%PDF-plan-revisado")
    assert llamar(otro, "--publicar") == 0
    assert git(remoto, "rev-list", "--count", "main") == "2"
