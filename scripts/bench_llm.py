"""Capacidad real del gateway LLM: ficheros/s, latencias y 429 con 1, 2, 4 y 8 hilos.

Por qué existe: `albertitos bench` lee los eventos de una ejecución ya hecha; esto provoca carga
controlada para encontrar el techo. Helmcode publica 100 RPM, 2M TPM y **concurrencia 5 por modelo**
(10 en deepseek-v4-flash y glm5.3); esto comprueba si esos límites se notan de verdad y dónde.

Cada nivel de concurrencia usa su propia `variante` de caché (`bench-wN`), así que:
- no toca ni pisa las lecturas de la Caja (regenerarlas cuesta minutos),
- la SEGUNDA vez que se ejecuta con la misma variante sale de caché y las cifras NO valen.
  Para volver a medir de verdad, usa `--sufijo` con algo distinto.

OJO con la caché del GATEWAY, que es otra: Helmcode devuelve la misma respuesta si el cuerpo de la
petición es idéntico. La primera versión de este script medía 4 escaneadas en 2,9 s con 2 hilos
frente a 151 s con 1, y los tokens de entrada eran idénticos: no era concurrencia, era su caché.
Por eso cada tanda manda además `marca=<variante>`, que cambia el cuerpo. Si al comparar dos tandas
ves los mismos `tok in`, desconfía.

Uso:
    uv run python scripts/bench_llm.py --texto 8 --vision 4 --workers 1,2,4,8 --sufijo a
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from albertitos.core import db  # noqa: E402
from albertitos.extract import pdf  # noqa: E402
from albertitos.extract.llm import ClienteLLM, ErrorLLM, EstadoLLM  # noqa: E402

DPI = int(os.environ.get("ALBERTITOS_DPI_VISION", "150"))


def candidatos(conn, *, n_texto: int, n_vision: int) -> tuple[list[dict], list[dict]]:
    """Ficheros reales de la Caja, los mismos en todas las tandas para que se puedan comparar."""
    filas = conn.execute(
        "SELECT file_id, sha256, tiene_texto FROM ficheros WHERE lote=1 ORDER BY file_id"
    ).fetchall()
    con = [dict(f) for f in filas if f["tiene_texto"]][:n_texto]
    sin = [dict(f) for f in filas if not f["tiene_texto"]][:n_vision]
    return con, sin


def una(fila: dict, variante: str, ruta_db: str, estado: EstadoLLM) -> dict:
    """Una extracción por LLM, cronometrada. Conexión propia por hilo (WAL aguanta escritores)."""
    conn = db.conectar(ruta_db)
    t0 = time.perf_counter()
    try:
        ruta = Path("data/caja/facturas") / fila["file_id"]
        cliente = ClienteLLM(conn, estado=estado)
        if fila["tiene_texto"]:
            _h, uso = cliente.extraer(
                sha256=fila["sha256"],
                file_id=fila["file_id"],
                texto=pdf.texto_de(ruta),
                variante=variante,
                marca=variante,  # impide que el gateway sirva de SU caché y falsee la tanda
            )
            camino = "texto"
        else:
            _h, uso = cliente.extraer(
                sha256=fila["sha256"],
                file_id=fila["file_id"],
                png=pdf.imagen_png(ruta, dpi=DPI),
                variante=variante,
                marca=variante,
            )
            camino = "vision"
        return {
            "ok": True,
            "camino": camino,
            "s": time.perf_counter() - t0,
            "cache": bool(uso.get("cache")),
            "tin": int(uso.get("tokens_in", 0)),
            "tout": int(uso.get("tokens_out", 0)),
            "modelo": uso.get("modelo", ""),
        }
    except ErrorLLM as e:
        return {"ok": False, "camino": "texto" if fila["tiene_texto"] else "vision",
                "s": time.perf_counter() - t0, "codigo": e.codigo}  # fmt: skip
    except Exception as e:  # noqa: BLE001 — el banco de pruebas no puede caerse por un fichero
        return {"ok": False, "camino": "texto" if fila["tiene_texto"] else "vision",
                "s": time.perf_counter() - t0, "codigo": f"BENCH-{type(e).__name__}"}  # fmt: skip


def tanda(filas: list[dict], workers: int, variante: str, ruta_db: str) -> dict:
    estado = EstadoLLM()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        res = list(pool.map(lambda f: una(f, variante, ruta_db, estado), filas))
    segundos = time.perf_counter() - t0
    ok = [r for r in res if r["ok"]]
    desde_cache = sum(1 for r in ok if r["cache"])
    errores: dict[str, int] = {}
    for r in res:
        if not r["ok"]:
            errores[r["codigo"]] = errores.get(r["codigo"], 0) + 1
    lat = sorted(r["s"] for r in ok) or [0.0]
    return {
        "n": len(filas),
        "ok": len(ok),
        "cache": desde_cache,
        "segundos": segundos,
        "por_segundo": len(filas) / segundos if segundos else 0.0,
        "p50": statistics.median(lat),
        "p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
        "tin": sum(r.get("tin", 0) for r in ok),
        "tout": sum(r.get("tout", 0) for r in ok),
        "errores": errores,
    }


def linea(camino: str, w: int, r: dict) -> str:
    err = ", ".join(f"{k}×{v}" for k, v in sorted(r["errores"].items())) or "—"
    aviso = "  (¡DESDE CACHÉ: no vale como medida!)" if r["cache"] else ""
    return (
        f"{camino:7s} w={w:<2d} {r['ok']:2d}/{r['n']:<2d}  {r['segundos']:6.1f}s  "
        f"{r['por_segundo']:5.2f} f/s  p50 {r['p50']:6.1f}s  p95 {r['p95']:6.1f}s  "
        f"tok {r['tin']:>6d}/{r['tout']:<6d}  err {err}{aviso}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--texto", type=int, default=8, help="facturas con capa de texto por tanda")
    ap.add_argument("--vision", type=int, default=4, help="escaneadas por tanda")
    ap.add_argument("--workers", default="1,2,4,8")
    ap.add_argument("--sufijo", default="a", help="cambia esto para medir de nuevo sin caché")
    args = ap.parse_args()

    load_dotenv(".env")
    ruta_db = os.environ.get("ALBERTITOS_DB", "dist/albertitos.db")
    conn = db.conectar(ruta_db)
    con_texto, sin_texto = candidatos(conn, n_texto=args.texto, n_vision=args.vision)
    print(f"hardware: {os.cpu_count()} CPUs · db {ruta_db} · dpi visión {DPI}")
    print(
        f"muestra: {len(con_texto)} de texto · {len(sin_texto)} escaneadas · sufijo '{args.sufijo}'"
    )
    print(
        f"modelos: texto {os.environ.get('ALBERTITOS_MODELO_TEXTO')} · visión {os.environ.get('ALBERTITOS_MODELO_VISION')}\n"
    )

    for w in [int(x) for x in args.workers.split(",") if x.strip()]:
        if con_texto:
            print(linea("texto", w, tanda(con_texto, w, f"bench-{args.sufijo}-t-w{w}", ruta_db)))
        if sin_texto:
            print(linea("visión", w, tanda(sin_texto, w, f"bench-{args.sufijo}-v-w{w}", ruta_db)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
