"""Prepara, valida y audita una entrega; sólo --publicar modifica el remoto.

Package corre en una copia SQLite y una carpeta temporal incluso al publicar.
No se leen secretos ni se modifican dist/entrega o la BD de origen.
Tests: main(..., raiz=..., comandos=..., ahora=...) inyecta ejecutables Python
de pega y el reloj; esas dependencias no se pueden cambiar desde la CLI.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
RAIZ = Path(__file__).resolve().parents[1]


class Bloqueo(Exception):
    pass


@dataclass
class Comandos:
    cli: tuple[str, ...] = (sys.executable, "-m", "albertitos.cli")
    auditoria: tuple[str, ...] = (sys.executable, str(RAIZ / "scripts/auditoria_entrega.py"))


def ejecutar(args, *, raiz, env, permite_fallo=False):
    print("+ " + shlex.join(map(str, args)), flush=True)
    p = subprocess.run(args, cwd=raiz, env=env, capture_output=True, text=True, timeout=180)
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip())
    if p.returncode and not permite_fallo:
        raise Bloqueo(
            f"Falló ({p.returncode}): {shlex.join(map(str, args))}. Corrige el error mostrado y repite make publicar."
        )
    return p


def git(destino, *args, raiz, env, permite_fallo=False):
    return ejecutar(
        ["git", "-C", str(destino), *args], raiz=raiz, env=env, permite_fallo=permite_fallo
    )


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def origen_normalizado(url, raiz):
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.split(":", 1)[1]
    if url.startswith("https://github.com/"):
        return url.removesuffix(".git").rstrip("/").lower()
    return str((raiz / url).resolve()) if "://" not in url else url.rstrip("/")


def revisar_destino(destino, nombres):
    if not destino.exists():
        return
    extras = {p.name for p in destino.iterdir()} - {".git", *nombres}
    if extras:
        raise Bloqueo(
            f"Destino con ficheros extra: {', '.join(sorted(extras))}. Revísalos y retíralos tú; el script no los borra. Comando: ls -A {shlex.quote(str(destino))}"
        )
    for p in destino.iterdir():
        if p.is_symlink() or (p.name != ".git" and not p.is_file()):
            raise Bloqueo(
                f"Destino no regular: {p}. Conserva su contenido y prepara un clon limpio."
            )


def metadatos(bd):
    with closing(sqlite3.connect(bd.as_uri() + "?mode=ro", uri=True)) as c:
        filas = c.execute(
            "SELECT f.lote,d.resultado,d.norma_version,d.erp_version FROM decisiones d JOIN ficheros f ON f.sha256=d.sha256 WHERE d.vigente=1"
        ).fetchall()
    if not filas:
        raise Bloqueo(
            "No hay decisiones vigentes. Ejecuta albertitos reprocess con norma y ERP explícitos."
        )
    cuentas = {
        lote: {
            r: sum(x[0] == lote and x[1] == r for x in filas)
            for r in ("PAGAR", "ESCALAR", "NO_PAGAR")
        }
        for lote in (1, 2)
    }
    return cuentas, ",".join(sorted({x[2] for x in filas})), ",".join(sorted({x[3] for x in filas}))


def publicar(args, raiz, comandos, ahora):
    if ahora >= datetime(2026, 9, 20, 10, 30, tzinfo=MADRID) and not args.despues_del_cierre:
        raise Bloqueo(
            "Cierre interno superado (domingo 10:30 Madrid). Sólo continuar con --despues-del-cierre explícito."
        )
    if ahora >= datetime(2026, 9, 20, 2, tzinfo=MADRID):
        print("ÁMBAR: periodo de congelación o cierre; revisa la hora antes de publicar.")
    if args.aceptar_rojo is not None and not args.aceptar_rojo.strip():
        raise Bloqueo("--aceptar-rojo exige un motivo no vacío.")
    bd = (raiz / args.db).resolve()
    destino = (raiz / args.destino).resolve()
    if destino == raiz or raiz.is_relative_to(destino):
        raise Bloqueo(
            "El destino no puede ser el repositorio de la solución ni su raíz contenedora."
        )
    if not bd.is_file():
        raise Bloqueo(f"No existe {bd}. Recupera la BD antes de publicar; albertitos status.")
    trabajo = raiz / "dist/ensayo"
    trabajo.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="publicar-", dir=trabajo) as temporal:
        tmp = Path(temporal)
        copia = tmp / "snapshot.db"
        with (
            closing(sqlite3.connect(bd.as_uri() + "?mode=ro", uri=True)) as src,
            closing(sqlite3.connect(copia)) as dst,
        ):
            src.backup(dst)
        salida = tmp / "entrega"
        env = {
            **os.environ,
            "ALBERTITOS_DB": str(copia),
            "ALBERTITOS_DIR_CAJA": str(raiz / "data/caja/facturas"),
            "ALBERTITOS_DIR_LOTE2": str(raiz / "data/lote2/facturas"),
        }
        kw = {"raiz": raiz, "env": env}
        ejecutar([*comandos.cli, "package", "--salida", str(salida)], **kw)
        nombres = ["outcomes.jsonl", "albertitos_plan.pdf"]
        lote2 = salida / "outcomes_lote2.jsonl"
        hay_lote2 = any((raiz / "data/lote2/facturas").glob("*.pdf"))
        if hay_lote2 and not lote2.is_file():
            raise Bloqueo(
                "Hay PDFs de lote 2 pero falta outcomes_lote2.jsonl. Ejecuta albertitos package y revisa las decisiones del lote 2."
            )
        for lote, nombre in ((1, "outcomes.jsonl"), (2, "outcomes_lote2.jsonl")):
            if lote == 2 and not lote2.exists():
                continue
            ejecutar([*comandos.cli, "validate", str(salida / nombre), "--lote", str(lote)], **kw)
        if lote2.exists():
            nombres.append(lote2.name)
        auditoria = ejecutar(
            [
                *comandos.auditoria,
                "--db",
                str(copia),
                "--lote",
                "ambos",
                "--dir-lote1",
                str(raiz / "data/caja/facturas"),
                "--dir-lote2",
                str(raiz / "data/lote2/facturas"),
                "--entrega",
                str(salida),
            ],
            permite_fallo=True,
            **kw,
        )
        if auditoria.returncode:
            # Un crash o fallo de ejecución no es un rojo de dominio que pueda aceptarse.
            if auditoria.returncode != 1 or "VEREDICTO: ROJO" not in auditoria.stdout:
                raise Bloqueo(
                    "La auditoría no pudo completarse; no se puede aceptar un fallo técnico. Ejecuta uv run python scripts/auditoria_entrega.py."
                )
            if args.aceptar_rojo is None:
                raise Bloqueo(
                    "Auditoría ROJA: NO se publica ni se accede al destino. Corrige los casos mostrados y repite make publicar; excepción explícita: --aceptar-rojo '<motivo>'."
                )
            print("ÁMBAR: rojo aceptado expresamente: " + args.aceptar_rojo)
        plan = (raiz / args.plan).resolve()
        if not plan.is_file():
            raise Bloqueo(f"Falta {plan}. Ejecuta make plan-pdf y repite make publicar.")
        shutil.copyfile(plan, salida / "albertitos_plan.pdf")
        cuentas, norma, erp = metadatos(copia)
        repo = os.environ.get("ENTREGA_REPO", "javiersaguar/HS-Maisa-Entrega")
        if not args.sin_gh:
            vis = ejecutar(["gh", "repo", "view", repo, "--json", "visibility"], **kw)
            if json.loads(vis.stdout).get("visibility") != "PUBLIC":
                raise Bloqueo(f"{repo} no es PUBLIC. Corrige su visibilidad antes de publicar.")
            remoto = (
                "https://github.com/"
                + repo.removeprefix("https://github.com/").removesuffix(".git")
                + ".git"
            )
        else:
            remoto = (
                repo
                if "/" in repo and (raiz / repo).exists()
                else (repo if ":" in repo else "https://github.com/" + repo + ".git")
            )
        revisar_destino(destino, nombres)
        if destino.exists():
            if not (destino / ".git").exists():
                raise Bloqueo(
                    "El destino existe pero no es un clon. Elige --destino con un clon de entrega o una ruta nueva."
                )
            top = git(destino, "rev-parse", "--show-toplevel", **kw).stdout.strip()
            if Path(top).resolve() != destino:
                raise Bloqueo("El destino no es la raíz de su repositorio. Corrige --destino.")
            if git(destino, "status", "--porcelain", **kw).stdout.strip():
                raise Bloqueo(
                    "El destino tiene cambios locales. Revísalos con git -C <destino> diff antes de repetir; no se sobrescriben."
                )
            origen = git(destino, "remote", "get-url", "origin", **kw).stdout.strip()
            if origen_normalizado(origen, destino) != origen_normalizado(remoto, raiz):
                raise Bloqueo(
                    "origin no coincide con ENTREGA_REPO. Revisa git -C <destino> remote -v."
                )
            envio = git(
                destino, "remote", "get-url", "--push", "--all", "origin", **kw
            ).stdout.splitlines()
            if len(envio) != 1 or origen_normalizado(envio[0], destino) != origen_normalizado(
                remoto, raiz
            ):
                raise Bloqueo(
                    "El destino de push difiere de ENTREGA_REPO. Revisa git -C <destino> remote -v y remote.origin.pushurl."
                )
            remoto = origen
            local = git(destino, "rev-parse", "--verify", "HEAD", permite_fallo=True, **kw)
            refs = git(destino, "ls-remote", "origin", "refs/heads/main", **kw).stdout.split()
            if (local.stdout.strip() if local.returncode == 0 else "") != (refs[0] if refs else ""):
                raise Bloqueo(
                    "HEAD del destino difiere de origin/main (atrasado o sin publicar). Revisa git -C <destino> log y sincroniza antes de repetir."
                )
        # En seco, incluso la copia de archivos y el commit propuesto quedan en un clon temporal.
        identidad = destino if destino.exists() else raiz
        objetivo = destino if args.publicar else tmp / "repo"
        if not objetivo.exists():
            objetivo.parent.mkdir(parents=True, exist_ok=True)
            git(objetivo.parent, "clone", "--", remoto, str(objetivo), **kw)
        revisar_destino(objetivo, nombres)
        cambios = [
            n
            for n in nombres
            if not (objetivo / n).is_file() or huella(objetivo / n) != huella(salida / n)
        ]
        for n in nombres:
            print(f"{'M' if n in cambios else '='} {n} sha256={huella(salida / n)}")
        if not cambios:
            print("VERDE: sin diferencias con lo publicado; no hay commit ni push.")
            return
        for n in nombres:
            shutil.copyfile(salida / n, objetivo / n)
        revisar_destino(objetivo, nombres)
        if {p.name for p in objetivo.iterdir()} != {".git", *nombres}:
            raise Bloqueo(
                "El destino no contiene exactamente los entregables y .git. Revisa ls -A."
            )
        n1, n2 = sum(cuentas[1].values()), sum(cuentas[2].values())
        reparto = "/".join(str(cuentas[1][r]) for r in ("PAGAR", "ESCALAR", "NO_PAGAR"))
        mensaje = (
            f"entrega {ahora.isoformat(timespec='minutes')} · lote1 {n1} ({reparto})"
            + (f" · lote2 {n2}" if lote2.exists() else "")
            + f" · norma {norma} · erp {erp}"
        )
        if args.aceptar_rojo is not None:
            mensaje += "\n\nRojo aceptado: " + args.aceptar_rojo
        # Identidad de la persona que publica, nunca una identidad inventada en el remoto.
        for campo, variable in (("user.name", "NAME"), ("user.email", "EMAIL")):
            valor = git(
                identidad, "config", "--get", campo, permite_fallo=True, **kw
            ).stdout.strip()
            if not valor and identidad != raiz:
                valor = git(raiz, "config", "--get", campo, permite_fallo=True, **kw).stdout.strip()
            if not valor:
                raise Bloqueo(
                    f"Falta {campo}; configura git -C {identidad} config {campo} antes de publicar."
                )
            env[f"GIT_AUTHOR_{variable}"] = env[f"GIT_COMMITTER_{variable}"] = valor
        git(objetivo, "add", "--", *nombres, **kw)
        git(objetivo, "diff", "--cached", "--stat", **kw)
        git(objetivo, "commit", "-m", mensaje, **kw)
        if not args.publicar:
            git(objetivo, "push", "--dry-run", "origin", "HEAD:main", **kw)
            print(
                "VERDE: ensayo en seco; destino, remoto y registro intactos. Para publicar: make publicar ARGS=--publicar."
            )
            return
        git(objetivo, "push", "-u", "origin", "HEAD:main", **kw)
        commit = git(objetivo, "rev-parse", "HEAD", **kw).stdout.strip()
        motivo = (
            ""
            if args.aceptar_rojo is None
            else " · rojo aceptado: " + json.dumps(args.aceptar_rojo, ensure_ascii=False)
        )
        linea = f"{ahora.isoformat(timespec='minutes')} | {commit} | {n1} ({reparto}, sha256 {huella(salida / 'outcomes.jsonl')}) | {n2 if lote2.exists() else '—'} | {norma} | {erp} | {getpass.getuser()}{motivo}\n"
        registro = raiz / "docs/entregas.log"
        try:
            with registro.open("a", encoding="utf-8") as f:
                f.write(linea)
        except OSError as exc:
            raise Bloqueo(
                f"PUBLICADO {commit}, pero falló el registro ({exc}). Añade esta línea a {registro}:\n{linea}"
            ) from exc
        print("PUBLICADO y registrado: " + commit)


def main(argv=None, *, raiz=RAIZ, comandos=None, ahora=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--aceptar-rojo", metavar="MOTIVO")
    ap.add_argument("--despues-del-cierre", action="store_true")
    ap.add_argument(
        "--sin-gh", action="store_true", help="omite comprobación de visibilidad; pruebas locales"
    )
    ap.add_argument("--destino", type=Path, default=Path("../HS-Maisa-Entrega"))
    ap.add_argument(
        "--db", type=Path, default=Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    ap.add_argument("--plan", type=Path, default=Path("dist/entrega/albertitos_plan.pdf"))
    args = ap.parse_args(argv)
    try:
        publicar(
            args,
            Path(raiz).resolve(),
            comandos or Comandos(),
            (ahora or datetime.now(MADRID)).astimezone(MADRID),
        )
    except (Bloqueo, OSError, sqlite3.Error, ValueError, subprocess.SubprocessError) as exc:
        print(f"ROJO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
