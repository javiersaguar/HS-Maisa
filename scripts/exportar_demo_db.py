"""La BD de la demo pública (ADR-0023): una copia de sólo lectura de la BD publicada, para el servidor de Render.

    uv run python scripts/exportar_demo_db.py                       # dist/albertitos.db → deploy/demo.db
    uv run python scripts/exportar_demo_db.py --origen dist/otra.db

Qué cambia respecto al origen (que no se toca): sin `cache_llm` (respuestas crudas del modelo, la consola no las lee)
y sin WAL (`journal_mode=DELETE`), para que el servidor la abra en sólo lectura con un solo fichero. Después:
`git add deploy/demo.db`, commit y push; Render redespliega solo. Hay que repetirlo tras cada `make publicar`.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


def exportar(origen: Path, destino: Path) -> dict:
    if not origen.is_file():
        raise SystemExit(f"no existe {origen}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    temporal.unlink(missing_ok=True)
    fuente = sqlite3.connect(f"file:{origen}?mode=ro", uri=True)
    copia = sqlite3.connect(temporal)
    try:
        fuente.backup(copia)
        copia.execute("DELETE FROM cache_llm")
        copia.commit()
        copia.execute("PRAGMA journal_mode=DELETE")
        copia.execute("VACUUM")
        resumen = {
            "ficheros": copia.execute("SELECT count(*) FROM ficheros").fetchone()[0],
            "por_lote": dict(
                copia.execute("SELECT lote, count(*) FROM ficheros GROUP BY lote").fetchall()
            ),
            "decisiones": dict(
                copia.execute(
                    "SELECT resultado, count(*) FROM decisiones WHERE vigente=1 GROUP BY resultado"
                ).fetchall()
            ),
        }
    finally:
        copia.close()
        fuente.close()
    temporal.replace(destino)
    resumen["bytes"] = destino.stat().st_size
    resumen["sha256"] = hashlib.sha256(destino.read_bytes()).hexdigest()[:12]
    return resumen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origen", type=Path, default=Path("dist/albertitos.db"))
    ap.add_argument("--destino", type=Path, default=Path("deploy/demo.db"))
    a = ap.parse_args(argv)
    r = exportar(a.origen, a.destino)
    print(  # noqa: T201 — script de operación
        f"{a.destino}: {r['ficheros']} ficheros {r['por_lote']} · {r['decisiones']} · "
        f"{r['bytes'] / 1e6:.1f} MB · sha256 {r['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
