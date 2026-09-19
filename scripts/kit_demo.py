"""Kit de la demo: lleva `dist/albertitos.db` a otro portátil, con un manifiesto que se comprueba al instalar.

Por qué existe. La BD (hechos, decisiones, eventos y la caché del LLM) está gitignorada y sólo vive en el
portátil donde se corrió el pipeline. Sin ella, en otro portátil no hay demo, ni traza, ni consola con datos,
y la demo sin red tampoco: las lecturas del LLM salen de su caché. La defensa se hace en el portátil de
Alfonso. Pasar el material tiene que ser un comando, y comprobable.

    uv run python scripts/kit_demo.py empaquetar                 # → dist/kit/albertitos-kit-<fecha>.tar.gz
    uv run python scripts/kit_demo.py instalar <kit.tar.gz>      # en el otro portátil, tras ./bootstrap.sh
    uv run python scripts/kit_demo.py instalar <kit.tar.gz> --forzar   # sustituye una BD con datos

Reglas:
- La copia se hace con la API de backup de SQLite, nunca con `cp`: con el WAL a medias, una copia por fichero
  sale incoherente (ADR-0008). La BD de origen sólo se lee.
- El caos es por BD (`<bd>.chaos.json`) y NO viaja en el kit. Al instalar se avisa si hay uno encendido.
- Instalar no pisa datos: si la BD de destino tiene ficheros, hace falta `--forzar`, y antes se copia a
  `<bd>.antes-del-kit` (si ya existe esa copia, la nueva lleva la hora: nunca se sobrescribe una copia).
  Una BD sin ficheros (la que crea `./bootstrap.sh` con `db init`) se sustituye sin `--forzar`, con copia
  igualmente: si no, `--forzar` se usaría siempre y dejaría de proteger nada.
- Los `-wal`/`-shm` de la BD anterior se borran al instalar: SQLite intentaría aplicarlos a la nueva.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
BD = "albertitos.db"
MANIFIESTO = "MANIFIESTO.json"
MIEMBROS = {BD, MANIFIESTO}
ENTREGAS = ("outcomes.jsonl", "outcomes_lote2.jsonl")
MADRID = ZoneInfo("Europe/Madrid")


# ----------------------------------------------------------------------------- utilidades


def sha256_de(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def copiar_bd(origen: Path, destino: Path) -> None:
    """Copia coherente con `backup()` y deja un único fichero autocontenido (sin WAL al lado)."""
    with (
        closing(sqlite3.connect(f"file:{origen}?mode=ro", uri=True)) as src,
        closing(sqlite3.connect(destino)) as dst,
    ):
        src.backup(dst)
        # el fichero viaja solo, sin -wal al lado; al abrirlo, la CLI vuelve a ponerlo en WAL
        dst.execute("PRAGMA journal_mode=DELETE")


def recuentos(ruta: Path) -> dict[str, Any]:
    """Lo que tiene que coincidir a los dos lados: si no coincide, no es la misma BD."""
    with closing(sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)) as c:
        tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "ficheros" not in tablas:
            return {"ficheros_por_lote": {}, "decisiones": {}, "hechos": 0, "cache_llm": 0}
        return {
            "ficheros_por_lote": {
                str(lote): n
                for lote, n in c.execute(
                    "SELECT lote, count(*) FROM ficheros GROUP BY lote ORDER BY lote"
                )
            },
            "decisiones": {
                r: n
                for r, n in c.execute(
                    "SELECT resultado, count(*) FROM decisiones WHERE vigente=1 "
                    "GROUP BY resultado ORDER BY resultado"
                )
            },
            "hechos": c.execute("SELECT count(*) FROM hechos").fetchone()[0],
            "cache_llm": c.execute("SELECT count(*) FROM cache_llm").fetchone()[0],
        }


def versiones_vigentes(ruta: Path) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)) as c:
        return [
            {"norma": n, "fecha_corte": f, "maestro": m, "erp": e, "decisiones": k}
            for n, f, m, e, k in c.execute(
                "SELECT norma_version, fecha_corte, maestro_version, erp_version, count(*) "
                "FROM decisiones WHERE vigente=1 GROUP BY 1, 2, 3, 4 ORDER BY 5 DESC"
            )
        ]


def git(*args: str, repo: Path = RAIZ) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _ficheros(recuento: dict[str, Any]) -> int:
    return sum(recuento["ficheros_por_lote"].values())


# ----------------------------------------------------------------------------- empaquetar


def empaquetar(
    origen: Path, salida: Path, entrega: Path, *, repo: Path = RAIZ, ahora: datetime | None = None
) -> Path:
    if not origen.is_file():
        raise SystemExit(
            f"no existe {origen}: el kit sale de la BD del portátil donde se corrió el pipeline"
        )
    ahora = ahora or datetime.now(UTC)
    salida.mkdir(parents=True, exist_ok=True)
    nombre = f"albertitos-kit-{ahora.astimezone(MADRID):%Y%m%d-%H%M}.tar.gz"
    with tempfile.TemporaryDirectory(dir=salida) as tmp:
        copia = Path(tmp) / BD
        copiar_bd(origen, copia)
        commit = git("rev-parse", "HEAD", repo=repo).stdout.strip() or None
        sucios = git("status", "--porcelain", "--untracked-files=no", repo=repo).stdout.splitlines()
        manifiesto = {
            "creado_en": ahora.isoformat(timespec="seconds"),
            "origen": str(origen),
            "commit": commit,
            "commit_con_cambios_sin_commitear": len(sucios),
            "bd": {"fichero": BD, "sha256": sha256_de(copia), "bytes": copia.stat().st_size},
            "recuentos": recuentos(copia),
            "versiones_vigentes": versiones_vigentes(copia),
            "entrega": {
                n: sha256_de(entrega / n) if (entrega / n).is_file() else None for n in ENTREGAS
            },
        }
        (Path(tmp) / MANIFIESTO).write_text(
            json.dumps(manifiesto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        destino = salida / nombre
        with tarfile.open(destino, "w:gz") as tar:
            tar.add(copia, arcname=BD)
            tar.add(Path(tmp) / MANIFIESTO, arcname=MANIFIESTO)
    r = manifiesto["recuentos"]
    print(f"kit: {destino} · {destino.stat().st_size / 1e6:.1f} MB")
    print(
        f"  BD {manifiesto['bd']['sha256'][:12]} · commit {str(commit)[:9]} · ficheros {r['ficheros_por_lote']}"
        f" · decisiones {r['decisiones']} · caché LLM {r['cache_llm']}"
    )
    if sucios:
        print(
            f"  ! hay {len(sucios)} ficheros con cambios sin commitear: el commit del manifiesto no los lleva"
        )
    print(
        "  en el otro portátil, tras ./bootstrap.sh y con el .tar.gz copiado a dist/kit/:\n"
        f"    uv run python scripts/kit_demo.py instalar dist/kit/{nombre}"
    )
    return destino


# ----------------------------------------------------------------------------- instalar


class KitInvalido(Exception):
    pass


def _extraer(kit: Path, dentro: Path) -> dict[str, Any]:
    """Sólo acepta los dos miembros esperados, como ficheros normales y sin rutas: nada de `../`."""
    with tarfile.open(kit, "r:gz") as tar:
        miembros = tar.getmembers()
        nombres = {m.name for m in miembros}
        if nombres != MIEMBROS or any(not m.isfile() for m in miembros):
            raise KitInvalido(
                f"el kit debe traer exactamente {sorted(MIEMBROS)}; trae {sorted(nombres)}"
            )
        for m in miembros:
            origen = tar.extractfile(m)
            assert origen is not None
            with origen, open(dentro / m.name, "wb") as f:
                shutil.copyfileobj(origen, f)
    return json.loads((dentro / MANIFIESTO).read_text(encoding="utf-8"))


def estado_del_codigo(commit: str | None, repo: Path = RAIZ) -> tuple[str, str]:
    """(nivel, texto). El kit se hizo con un commit; aquí el código tiene que tenerlo."""
    if not commit:
        return "ÁMBAR", "el manifiesto no dice con qué commit se hizo el kit"
    if git("cat-file", "-e", f"{commit}^{{commit}}", repo=repo).returncode != 0:
        return "ÁMBAR", (
            f"tu código no conoce el commit del kit ({commit[:9]}): `git pull --ff-only` antes de la demo"
        )
    if git("merge-base", "--is-ancestor", commit, "HEAD", repo=repo).returncode != 0:
        return "ÁMBAR", (
            f"tu código es más viejo que el kit (le falta {commit[:9]}): `git pull --ff-only` antes de la demo"
        )
    return "OK", f"el código contiene el commit del kit ({commit[:9]})"


def _copia_de_seguridad(destino: Path) -> Path:
    antes = destino.with_name(destino.name + ".antes-del-kit")
    if (
        antes.exists()
    ):  # nunca se pisa una copia anterior: la primera puede ser la única con los datos buenos
        antes = destino.with_name(
            f"{destino.name}.antes-del-kit-{datetime.now(UTC).astimezone(MADRID):%Y%m%d-%H%M%S}"
        )
    copiar_bd(destino, antes)
    return antes


def instalar(
    kit: Path,
    destino: Path,
    *,
    forzar: bool = False,
    repo: Path = RAIZ,
    con_status: bool = True,
) -> int:
    """Devuelve 0 si queda instalado y coincide con el manifiesto (con avisos o sin ellos), 1 si no."""
    avisos: list[str] = []
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as tmp:
        try:
            man = _extraer(kit, Path(tmp))
        except (KitInvalido, tarfile.TarError, OSError, ValueError) as e:
            print(f"ROJO  el kit no se puede abrir: {e}")
            return 1
        nueva = Path(tmp) / BD
        if sha256_de(nueva) != man["bd"]["sha256"]:
            print(
                "ROJO  la BD del kit no es la del manifiesto (sha256 distinto): el kit está dañado o se "
                "modificó. Pide otro con `uv run python scripts/kit_demo.py empaquetar`."
            )
            return 1
        print(
            f"OK    BD del kit íntegra ({man['bd']['sha256'][:12]}, {man['bd']['bytes'] / 1e6:.1f} MB)"
        )
        nivel, texto = estado_del_codigo(man.get("commit"), repo)
        print(f"{nivel:<5} {texto}")
        if nivel != "OK":
            avisos.append(texto)

        if destino.exists():
            previa = recuentos(destino)
            if _ficheros(previa) and not forzar:
                print(
                    f"ROJO  ya hay una BD con datos en {destino} ({previa['ficheros_por_lote']} ficheros, "
                    f"{previa['decisiones']}). No la piso. Si de verdad quieres sustituirla: `--forzar` "
                    f"(antes la copia a {destino.name}.antes-del-kit)."
                )
                return 1
            copia = _copia_de_seguridad(destino)
            vacia = "" if _ficheros(previa) else " (estaba vacía: la crea ./bootstrap.sh)"
            print(f"OK    la BD anterior{vacia} queda en {copia}")
        for resto in (
            destino.with_name(destino.name + "-wal"),
            destino.with_name(destino.name + "-shm"),
        ):
            resto.unlink(
                missing_ok=True
            )  # son de la BD anterior: aplicados a la nueva, la corromperían
        os.replace(nueva, destino)

    instalados = recuentos(destino)
    if instalados != man["recuentos"]:
        print(
            f"ROJO  los recuentos no coinciden: manifiesto {man['recuentos']} · instalada {instalados}"
        )
        return 1
    r = instalados
    print(
        f"OK    instalada en {destino}: ficheros {r['ficheros_por_lote']} · decisiones {r['decisiones']}"
        f" · caché LLM {r['cache_llm']}"
    )
    caos = destino.with_suffix(destino.suffix + ".chaos.json")
    if caos.exists():
        texto = f"hay un caos encendido junto a esta BD ({caos}): `uv run albertitos chaos --off` antes de la demo"
        print(f"ÁMBAR {texto}")
        avisos.append(texto)
    if os.environ.get("ALBERTITOS_CHAOS"):
        texto = f"ALBERTITOS_CHAOS está definido ({os.environ['ALBERTITOS_CHAOS']}): manda sobre el caos de la BD"
        print(f"ÁMBAR {texto}")
        avisos.append(texto)
    entrega = man.get("entrega", {}).get("outcomes.jsonl")
    if entrega:
        print(f"      la entrega de ese momento: outcomes.jsonl {entrega[:12]}")
    if con_status:
        env = {**os.environ, "ALBERTITOS_DB": str(destino), "PYTHONUTF8": "1"}
        salida = subprocess.run(
            [sys.executable, "-m", "albertitos.cli", "status"],
            env=env,
            capture_output=True,
            text=True,
        )
        print("\n$ albertitos status\n" + (salida.stdout + salida.stderr).strip())
        if salida.returncode != 0:
            print("ROJO  `albertitos status` falla con la BD instalada")
            return 1
    print("\nVEREDICTO: " + ("instalado, con avisos: léelos" if avisos else "instalado"))
    return 0


# ----------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # la misma BD que la CLI (el entorno explícito manda sobre .env)
    bd = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    e = sub.add_parser("empaquetar", help="BD real → dist/kit/albertitos-kit-<fecha>.tar.gz")
    e.add_argument("--origen", type=Path, default=bd)
    e.add_argument("--salida", type=Path, default=Path("dist/kit"))
    e.add_argument("--entrega", type=Path, default=Path("dist/entrega"))
    i = sub.add_parser("instalar", help="kit → la BD de este portátil")
    i.add_argument("kit", type=Path)
    i.add_argument("--destino", type=Path, default=bd)
    i.add_argument(
        "--forzar", action="store_true", help="sustituye una BD con datos (antes la copia)"
    )
    i.add_argument(
        "--sin-status", action="store_true", help="no ejecuta `albertitos status` al final"
    )
    a = ap.parse_args(argv)
    if a.orden == "empaquetar":
        empaquetar(a.origen, a.salida, a.entrega)
        return 0
    return instalar(a.kit, a.destino, forzar=a.forzar, con_status=not a.sin_status)


if __name__ == "__main__":
    sys.exit(main())
