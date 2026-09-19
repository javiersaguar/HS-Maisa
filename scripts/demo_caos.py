"""Demo de resiliencia (≈60 s): el LLM se cae, nada se paga a ciegas; vuelve y se reanuda sin duplicados.

Trabaja sobre una COPIA de la BD (dist/demo.db), su propio interruptor de caos (dist/demo_chaos.json) y su
propia entrega (dist/demo_entrega/): no toca dist/albertitos.db, dist/chaos.json ni dist/entrega/.

Preparación: en la copia, 3 facturas con texto que ninguna plantilla reconoce (sólo las lee el LLM)
"llegan nuevas": se borra todo lo suyo, caché del LLM incluida. Luego, con cronómetro:
  1. chaos --llm-down → run: las 3 quedan PENDIENTE, decide se las salta, package se niega (exit 1).
  2. chaos --off      → run: el LLM las lee, se deciden, la entrega se valida (500 líneas).
  3. run otra vez     → 0 llamadas al LLM (caché por sha256), mismo JSONL byte a byte.

Uso: uv run python scripts/demo_caos.py [--fecha-corte 2026-09-18] [--origen dist/albertitos.db]
Necesita red y la key del LLM en .env (3 lecturas de texto).

`--sin-red` hace la misma demo sin tocar el proveedor: guarda las 3 lecturas de la caché antes de
borrarlas y las devuelve entre el paso 1 y el 2, así que la reanudación se sirve de la caché. Prueba
que el pipeline se recupera y que el JSONL sale idéntico, pero NO que el proveedor conteste. Es el
repliegue para la defensa si el wifi de la sala falla; se dice en voz alta, no se disimula.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

NUEVAS = ["2026-03-19_P008.pdf", "FA-1123_construcciones.pdf", "FA-2967_seguridad.pdf"]
DB, CAOS, ENTREGA = Path("dist/demo.db"), Path("dist/demo_chaos.json"), Path("dist/demo_entrega")


def preparar(origen: Path) -> list[tuple]:
    """Deja la copia como si las 3 facturas acabaran de llegar. Devuelve su caché del LLM, que
    `--sin-red` reinyecta después para simular la vuelta del proveedor sin salir a internet."""
    for p in (DB, DB.with_name(DB.name + "-wal"), DB.with_name(DB.name + "-shm"), CAOS):
        p.unlink(missing_ok=True)
    src = sqlite3.connect(f"file:{origen}?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)  # copia coherente aunque otra ventana esté escribiendo en el origen
    src.close()
    marcas = ",".join("?" * len(NUEVAS))
    shas = [
        r[0]
        for r in dst.execute(f"SELECT sha256 FROM ficheros WHERE file_id IN ({marcas})", NUEVAS)
    ]
    if len(shas) != len(NUEVAS):
        sys.exit(f"{origen} no tiene las {len(NUEVAS)} facturas de la demo: ¿ingest hecho?")
    guardadas: list[tuple] = []
    for sha in shas:
        for tabla in ("eventos", "decisiones", "hechos"):
            dst.execute(f"DELETE FROM {tabla} WHERE sha256=?", (sha,))
        guardadas += list(dst.execute("SELECT * FROM cache_llm WHERE clave LIKE ?", (sha + "|%",)))
        dst.execute("DELETE FROM cache_llm WHERE clave LIKE ?", (sha + "|%",))
        dst.execute("DELETE FROM ficheros WHERE sha256=?", (sha,))
    dst.execute(f"DELETE FROM eventos WHERE file_id IN ({marcas})", NUEVAS)
    dst.commit()
    dst.close()
    ENTREGA.mkdir(parents=True, exist_ok=True)
    for f in ENTREGA.glob("*.jsonl"):
        f.unlink()
    return guardadas


def devolver_cache(filas: list[tuple]) -> int:
    """Reinyecta las lecturas guardadas: el siguiente `run` las encuentra antes de llamar a nadie."""
    if not filas:
        return 0
    c = sqlite3.connect(DB)
    marcas = ",".join("?" * len(filas[0]))
    c.executemany(f"INSERT OR REPLACE INTO cache_llm VALUES ({marcas})", filas)
    c.commit()
    c.close()
    return len(filas)


def albertitos(*args: str, corte: str) -> int:
    env = {
        **os.environ,
        "ALBERTITOS_DB": str(DB),
        "ALBERTITOS_CHAOS": str(CAOS),
        "ALBERTITOS_FECHA_CORTE": corte,
        "ALBERTITOS_WORKERS": os.environ.get("ALBERTITOS_WORKERS", "3"),
        "PYTHONUTF8": "1",
    }
    print(f"\n$ albertitos {' '.join(args)}", flush=True)
    return subprocess.run([sys.executable, "-m", "albertitos.cli", *args], env=env).returncode


def rastro() -> None:
    """Último evento de cada etapa para las 3 nuevas y si tienen decisión: lo que se ve en la consola."""
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    for fid in NUEVAS:
        pasos = []
        for etapa in ("extract", "decide", "emit"):
            e = c.execute(
                "SELECT estado, error_codigo, tokens_in, tokens_out FROM eventos "
                "WHERE file_id=? AND etapa=? ORDER BY id DESC LIMIT 1",
                (fid, etapa),
            ).fetchone()
            if e:
                extra = e[1] or (f"{e[2]}/{e[3]} tokens" if e[2] else "")
                pasos.append(f"{etapa} {e[0]}" + (f" ({extra})" if extra else ""))
        d = c.execute(
            "SELECT resultado FROM decisiones WHERE file_id=? AND vigente=1", (fid,)
        ).fetchone()
        print(f"   {fid}: {' → '.join(pasos)} · decisión: {d[0] if d else 'NINGUNA'}")
    c.close()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "—"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origen", type=Path, default=Path("dist/albertitos.db"))
    ap.add_argument("--fecha-corte", default=os.environ.get("ALBERTITOS_FECHA_CORTE", "2026-09-18"))
    ap.add_argument(
        "--sin-red",
        action="store_true",
        help="la reanudación se sirve de la caché guardada: misma demo sin llamar al proveedor",
    )
    a = ap.parse_args()

    cache = preparar(a.origen)
    print(f"Copia de {a.origen} en {DB}; llegan {len(NUEVAS)} facturas nuevas que sólo lee el LLM.")
    if a.sin_red:
        if len(cache) < len(NUEVAS):
            sys.exit(
                f"--sin-red necesita las {len(NUEVAS)} lecturas en la caché de {a.origen} y sólo hay "
                f"{len(cache)}. Corre la demo normal una vez con red y vuelve a intentarlo."
            )
        print(
            f"Modo sin red: {len(cache)} lecturas guardadas de la caché; el paso 2 las devuelve en "
            "lugar de llamar al proveedor. Dilo en voz alta: prueba que el pipeline reanuda, no que "
            "el LLM conteste."
        )
    salida = ENTREGA / "outcomes.jsonl"
    t0 = time.perf_counter()

    print("\n== 1. El proveedor del LLM se cae")
    albertitos("chaos", "--llm-down", corte=a.fecha_corte)
    codigo = albertitos("run", "--salida", str(ENTREGA), corte=a.fecha_corte)
    rastro()
    escrita = salida.exists()
    print(f"   run → exit {codigo} · entrega escrita: {'sí' if escrita else 'no'}")

    print("\n== 2. Vuelve el LLM: el mismo run reanuda")
    albertitos("chaos", "--off", corte=a.fecha_corte)
    if a.sin_red:
        print(f"   (sin red: devueltas {devolver_cache(cache)} lecturas a la caché)")
    codigo2 = albertitos("run", "--salida", str(ENTREGA), corte=a.fecha_corte)
    rastro()
    primera = sha(salida)
    print(f"   run → exit {codigo2} · outcomes.jsonl {primera}")

    print("\n== 3. Otra vez: idempotente (caché por sha256, sin duplicados)")
    codigo3 = albertitos("run", "--salida", str(ENTREGA), corte=a.fecha_corte)
    igual = sha(salida) == primera
    print(f"   run → exit {codigo3} · outcomes.jsonl {sha(salida)} (igual: {igual})")

    oficial = Path("dist/entrega/outcomes.jsonl")
    if oficial.exists() and salida.exists():
        a_, b_ = resultados(oficial), resultados(salida)
        distintas = sorted(k for k in a_ if a_.get(k) != b_.get(k))
        print(f"   frente a {oficial}: {len(distintas)} resultados distintos {distintas}")
    print(f"\nDemo: {time.perf_counter() - t0:.1f} s")
    ok = codigo != 0 and not escrita and codigo2 == 0 and codigo3 == 0 and igual
    sys.exit(0 if ok else 1)


def resultados(p: Path) -> dict[str, str]:
    lineas = (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines())
    return {o["file_id"]: o["result"] for o in lineas}


if __name__ == "__main__":
    main()
