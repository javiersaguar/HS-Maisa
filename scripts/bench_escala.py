"""Escala MEDIDA: el pipeline real sobre N copias sintéticas de la Caja, en una BD aparte (D1, ciclo 4).

Por qué existe: `docs/benchmark.md` y RESILIENCIA-Y-COSTE §4 extrapolan 10.000 facturas desde tandas de
8-32. Esto las pasa DE VERDAD por el código de `src/` (sin tocarlo) y mide cada etapa por separado.

Copias: se replican los 500 PDFs de `data/caja/facturas` en round-robin (la mezcla de la Caja es exacta:
468 plantilla · 29 escaneadas · 3 texto sin plantilla) y a cada una se le añade un comentario PDF al
final (`%% albertitos-escala copia=NNNNN`). El sha256 cambia (nuestra caché no las reconoce) y PyMuPDF
las lee igual.

Aislamiento: todo vive en `dist/escala/` (BD propias, PDFs, caos). `ALBERTITOS_CHAOS` se fija siempre
aquí dentro; nunca `dist/chaos.json` ni la BD real. En el camino determinista el caos está en `llm_down`,
así que las copias que irían al LLM quedan PENDIENTE sin llamar a nadie (el render de la imagen sí se
mide), y después reciben sus hechos REALES de `data/fixtures/hechos_caja.jsonl` re-etiquetados con su
file_id y su sha256, como haría `albertitos hechos import`. Sin eso `package` se niega (regla 6).

Cada etapa corre en un proceso hijo: así el pico de RSS es el de esa etapa y el tiempo no incluye imports.
Copiar una BD en WAL exige `wal_checkpoint(TRUNCATE)` y la conexión cerrada, o la copia sale vacía.

Caminos de LLM (`--llm-vision/--llm-texto`): copias con la IMAGEN o el TEXTO alterados de forma única
(un punto gris en el margen superior, dentro del recorte de la segunda lectura, o una línea de texto
al pie), así que el cuerpo de la petición cambia y la caché del gateway no puede contestar. Pasan por el
`extraer()` real, con doble lectura y reconciliación incluidas.

Uso:
    uv run python scripts/bench_escala.py --n 10000 --etiqueta 10k --workers 1,8
    uv run python scripts/bench_escala.py --n 0 --etiqueta llm --llm-vision 20 --llm-texto 12 --workers-llm 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "dist" / "escala"
CAJA = RAIZ / "data" / "caja"
HECHOS_CAJA = RAIZ / "data" / "fixtures" / "hechos_caja.jsonl"
MARCA = "@@MEDIDA "

sys.path.insert(0, str(RAIZ / "src"))


# ----------------------------------------------------------------------------- utilidades


def _proc_status(clave: str) -> float:
    """MB de /proc/self/status (VmRSS actual, VmHWM pico). 0 si no es Linux."""
    try:
        for linea in Path("/proc/self/status").read_text().splitlines():
            if linea.startswith(clave + ":"):
                return int(linea.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


def _checkpoint_y_cerrar(conn: sqlite3.Connection) -> None:
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


def _copiar_bd(origen: Path, destino: Path) -> None:
    for sufijo in ("", "-wal", "-shm"):
        Path(str(destino) + sufijo).unlink(missing_ok=True)
    wal = Path(str(origen) + "-wal")
    if wal.exists() and wal.stat().st_size > 0:
        raise RuntimeError(f"{origen} tiene WAL sin volcar: la copia saldría incompleta")
    shutil.copy2(origen, destino)


def _pct(valores: list[float], q: float) -> float:
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[min(len(v) - 1, int(q * len(v)))]


def _lat_por_metodo(conn: sqlite3.Connection, desde_id: int = 0) -> dict[str, dict]:
    """p50/p95 de los eventos EXTRACT por (estado, método o error)."""
    grupos: dict[str, list[float]] = {}
    for f in conn.execute(
        "SELECT estado, detalle, error_codigo, latencia_ms FROM eventos WHERE etapa='extract' AND id>?",
        (desde_id,),
    ):
        clave = (
            f"{f['estado']}:{(f['detalle'] or '').split(' ')[0]}"
            if f["estado"] == "ok"
            else f"{f['estado']}:{f['error_codigo']}"
        )
        grupos.setdefault(clave, []).append(float(f["latencia_ms"] or 0))
    return {
        k: {
            "n": len(v),
            "p50_ms": statistics.median(v),
            "p95_ms": _pct(v, 0.95),
            "max_ms": max(v),
            "suma_s": sum(v) / 1000,
        }
        for k, v in sorted(grupos.items())
    }


# ----------------------------------------------------------------------------- etapas (proceso hijo)


def etapa_generar(ctx: dict) -> dict:
    n, destino = ctx["n"], Path(ctx["facturas"])
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    originales = [(p.name, p.read_bytes()) for p in sorted((CAJA / "facturas").glob("*.pdf"))]
    t0 = time.perf_counter()
    total = 0
    for i in range(n):
        nombre, crudo = originales[i % len(originales)]
        dato = crudo + f"\n%% albertitos-escala copia={i:05d}\n".encode()
        (destino / unicodedata.normalize("NFC", f"S{i:05d}-{nombre}")).write_bytes(dato)
        total += len(dato)
    return {"segundos": time.perf_counter() - t0, "n": n, "disco_mb": total / 2**20}


def etapa_ingest(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.extract import pdf  # noqa: F401 — pymupdf cargado antes de medir
    from albertitos.pipeline import etapas

    conn = db.conectar(ctx["bd"])
    db.init_schema(conn)
    t0 = time.perf_counter()
    n = etapas.ingest(conn, Path(ctx["facturas"]), lote=1)
    seg = time.perf_counter() - t0
    sin_texto = conn.execute("SELECT count(*) FROM ficheros WHERE tiene_texto=0").fetchone()[0]
    _checkpoint_y_cerrar(conn)
    return {"segundos": seg, "n": n, "sin_texto": sin_texto}


def etapa_extract(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.extract import etapa
    from albertitos.sources import chaos

    if ctx.get("caos"):
        chaos.activar(ctx["caos"])
    else:
        chaos.desactivar()
    conn = db.conectar(ctx["bd"])
    desde = conn.execute("SELECT coalesce(max(id), 0) FROM eventos").fetchone()[0]
    fixture = Path(ctx["fixture"]) if ctx.get("fixture") else None
    r = etapa.extraer(conn, workers=int(ctx["workers"]), fixture=fixture)
    lat = _lat_por_metodo(conn, desde)
    _checkpoint_y_cerrar(conn)
    return {
        "segundos": r.segundos,
        "n": r.candidatos,
        "ok": r.ok,
        "pendientes": r.pendientes,
        "errores_pdf": r.errores_pdf,
        "por_metodo": r.por_metodo,
        "errores": r.errores,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "coste_eur": r.coste_eur,
        "latencias": lat,
    }


def etapa_inyectar(ctx: dict) -> dict:
    """Hechos REALES de la Caja para las copias que el banco no manda al LLM (= `hechos import`)."""
    from albertitos.core import db
    from albertitos.core.contracts import EstadoEvento, Etapa, Event, InvoiceFacts
    from albertitos.core.versions import EXTRACTOR_VERSION

    reales = {}
    for linea in HECHOS_CAJA.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            d = json.loads(linea)
            reales[d["file_id"]] = d
    conn = db.conectar(ctx["bd"])
    t0 = time.perf_counter()
    filas = conn.execute(
        """SELECT f.file_id, f.sha256 FROM ficheros f LEFT JOIN hechos h
           ON h.sha256=f.sha256 AND h.extractor_version=? WHERE h.sha256 IS NULL""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    metodos: dict[str, int] = {}
    for f in filas:
        original = f["file_id"].split("-", 1)[1]
        h = InvoiceFacts.model_validate(
            {**reales[original], "file_id": f["file_id"], "sha256": f["sha256"]}
        )
        db.guardar_hechos(conn, h)
        db.registrar_evento(
            conn,
            Event(
                file_id=h.file_id,
                sha256=h.sha256,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.OK,
                version=h.extractor_version,
                detalle=f"import:{h.metodo.value}",
            ),
        )
        metodos[h.metodo.value] = metodos.get(h.metodo.value, 0) + 1
    seg = time.perf_counter() - t0
    _checkpoint_y_cerrar(conn)
    return {"segundos": seg, "n": len(filas), "por_metodo": metodos}


def etapa_maestro(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.sources import excel, snapshot

    conn = db.conectar(ctx["bd"])
    t0 = time.perf_counter()
    m = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    snapshot.guardar_maestro(conn, m)
    seg = time.perf_counter() - t0
    _checkpoint_y_cerrar(conn)
    return {"segundos": seg, "n": len(m.pedidos), "proveedores": len(m.proveedores)}


def etapa_erp(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.sources import erp, snapshot

    conn = db.conectar(ctx["bd"])
    t0 = time.perf_counter()
    s = erp.ClienteERP(ctx["erp_url"], conn=conn).descargar_todo("v1")
    snapshot.guardar_erp(conn, s)
    seg = time.perf_counter() - t0
    _checkpoint_y_cerrar(conn)
    return {
        "segundos": seg,
        "n": len(s.asientos),
        "consultas": s.consultas,
        "reintentos": s.reintentos,
    }


def etapa_duplicados(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.pipeline import etapas

    conn = db.conectar(ctx["bd"])
    n_hechos = conn.execute("SELECT count(*) FROM hechos").fetchone()[0]
    t0 = time.perf_counter()
    marcados = etapas.marcar_duplicados(conn)
    seg = time.perf_counter() - t0
    _checkpoint_y_cerrar(conn)
    return {"segundos": seg, "n": n_hechos, "marcados": marcados}


def etapa_decide(ctx: dict) -> dict:
    """`decide` real, con `ErpSnapshot.por_pedido` cronometrado por fuera (envoltorio, sin tocar src/)."""
    from albertitos.core import db
    from albertitos.core.contracts import ErpSnapshot
    from albertitos.pipeline import etapas
    from albertitos.rules import norma_v3  # noqa: F401 — import fuera del tiempo
    from albertitos.sources import snapshot

    acumulado = {"s": 0.0, "llamadas": 0}
    original = ErpSnapshot.por_pedido

    def por_pedido_cronometrado(self):  # type: ignore[no-untyped-def]
        t = time.perf_counter()
        try:
            return original(self)
        finally:
            acumulado["s"] += time.perf_counter() - t
            acumulado["llamadas"] += 1

    ErpSnapshot.por_pedido = por_pedido_cronometrado  # type: ignore[method-assign]
    conn = db.conectar(ctx["bd"])
    m = snapshot.cargar_maestro_bd(conn)
    e = snapshot.cargar_erp_bd(conn, "v1")
    t0 = time.perf_counter()
    n = etapas.decide(
        conn,
        norma_version="v3",
        fecha_corte=date.fromisoformat(ctx["fecha_corte"]),
        maestro=m,
        erp=e,
    )
    seg = time.perf_counter() - t0
    dist = dict(
        conn.execute(
            "SELECT resultado, count(*) FROM decisiones WHERE vigente=1 GROUP BY 1"
        ).fetchall()
    )
    _checkpoint_y_cerrar(conn)
    return {
        "segundos": seg,
        "n": n,
        "distribucion": dist,
        "por_pedido_s": acumulado["s"],
        "por_pedido_llamadas": acumulado["llamadas"],
        "asientos": len(e.asientos),
    }


def etapa_decide_variante(ctx: dict) -> dict:
    """`decide` sobre una COPIA de la BD final, para aislar el coste de `db.guardar_decision`.

    - `reprocesado`: la tabla ya tiene N decisiones (lo que pasa en cada `reprocess`), sin índice.
    - `indice`: tabla vacía y un índice sobre `decisiones(sha256, vigente)` creado SÓLO en la copia.
    - `indice_reprocesado`: lo mismo con el índice y N decisiones previas.
    """
    from albertitos.core import db
    from albertitos.pipeline import etapas
    from albertitos.rules import norma_v3  # noqa: F401
    from albertitos.sources import snapshot

    bd = Path(ctx["bd_copia"])
    _copiar_bd(Path(ctx["bd"]), bd)
    conn = db.conectar(bd)
    variante = ctx["variante"]
    if variante.startswith("indice"):
        conn.execute("CREATE INDEX ix_bench_decisiones_sha ON decisiones(sha256, vigente)")
    if variante == "indice":
        conn.execute("DELETE FROM decisiones")
    conn.commit()
    previas = conn.execute("SELECT count(*) FROM decisiones").fetchone()[0]
    plan = " | ".join(
        r[3]
        for r in conn.execute(
            "EXPLAIN QUERY PLAN UPDATE decisiones SET vigente=0 WHERE sha256=? AND vigente=1",
            ("x",),
        )
    )
    m = snapshot.cargar_maestro_bd(conn)
    e = snapshot.cargar_erp_bd(conn, "v1")
    t0 = time.perf_counter()
    n = etapas.decide(
        conn,
        norma_version="v3",
        fecha_corte=date.fromisoformat(ctx["fecha_corte"]),
        maestro=m,
        erp=e,
    )
    seg = time.perf_counter() - t0
    conn.close()
    for sufijo in ("", "-wal", "-shm"):
        Path(str(bd) + sufijo).unlink(missing_ok=True)
    return {
        "segundos": seg,
        "n": n,
        "variante": variante,
        "decisiones_previas": previas,
        "plan": plan,
    }


def etapa_package(ctx: dict) -> dict:
    from albertitos.core import db
    from albertitos.pipeline import package as pk

    conn = db.conectar(ctx["bd"], solo_lectura=True)
    salida = Path(ctx["entrega"])
    t0 = time.perf_counter()
    try:
        gen = pk.empaquetar(conn, salida, Path(ctx["caja"]), None, con_traza=True)
        ok, texto = True, gen[0][1].texto().splitlines()[0]
    except pk.EntregaInvalida as err:
        ok, texto = False, str(err)[:300]
    seg = time.perf_counter() - t0
    conn.close()
    jsonl = salida / "outcomes.jsonl"
    return {
        "segundos": seg,
        "n": sum(1 for _ in jsonl.open(encoding="utf-8")) if jsonl.exists() else 0,
        "apto": ok,
        "informe": texto,
        "jsonl_mb": jsonl.stat().st_size / 2**20 if jsonl.exists() else 0,
    }


def etapa_validar(ctx: dict) -> dict:
    from albertitos.pipeline.validar import listar_pdfs, validar_jsonl

    t0 = time.perf_counter()
    esperados = listar_pdfs(Path(ctx["facturas"]))
    t_listar = time.perf_counter() - t0
    inf = validar_jsonl(Path(ctx["entrega"]) / "outcomes.jsonl", esperados, 1)
    return {
        "segundos": time.perf_counter() - t0,
        "listar_s": t_listar,
        "n": inf.n_lineas,
        "apto": inf.ok,
        "errores": inf.errores[:3],
        "distribucion": inf.distribucion,
    }


def etapa_micro_por_pedido(ctx: dict) -> dict:
    """Coste de UNA llamada a `ErpSnapshot.por_pedido()` según el tamaño del ERP (asientos sintéticos)."""
    from albertitos.core.contracts import ErpEntry, ErpSnapshot

    out = {}
    for a in ctx["asientos"]:
        asientos = {
            f"AS-{i:07d}": ErpEntry(
                asiento_id=f"AS-{i:07d}",
                fecha_registro=date(2026, 1, 1),
                proveedor_id="P001",
                nif="B46102331",
                pedido=f"PO-{i:07d}",
                importe_esperado="100.00",
                estado="PENDIENTE",
            )
            for i in range(a)
        }
        s = ErpSnapshot(version="micro", asientos=asientos, descargado_en=datetime.now(UTC))
        repes = max(3, min(2000, 2_000_000 // a))
        t0 = time.perf_counter()
        for _ in range(repes):
            s.por_pedido()
        out[str(a)] = (time.perf_counter() - t0) / repes * 1000
    return {"segundos": 0.0, "n": len(out), "ms_por_llamada": out}


def etapa_generar_llm(ctx: dict) -> dict:
    """Copias con cuerpo de petición único: punto gris (visión) o línea al pie (texto)."""
    import pymupdf

    from albertitos.extract import pdf, plantillas

    destino = Path(ctx["facturas"])
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    escaneadas, sin_plantilla = [], []
    for p in sorted((CAJA / "facturas").glob("*.pdf")):
        _pags, tiene_texto = pdf.info(p)
        if not tiene_texto:
            escaneadas.append(p)
        elif plantillas.extraer_por_plantilla(pdf.texto_de(p), file_id=p.name, sha256="x") is None:
            sin_plantilla.append(p)
    listas: dict[str, list[str]] = {"vision": [], "texto": []}
    t0 = time.perf_counter()
    for camino, origen, n in (
        ("vision", escaneadas, ctx["llm_vision"]),
        ("texto", sin_plantilla, ctx["llm_texto"]),
    ):
        for i in range(n):
            src = origen[i % len(origen)]
            marca = f"{ctx['sufijo']}-{camino[0]}{i:03d}"
            k = int(hashlib.sha256(marca.encode()).hexdigest()[:12], 16)
            with pymupdf.open(src) as doc:
                pag = doc[0]
                if camino == "vision":
                    # dos puntos grises cuya posición y tono dependen de la marca: la imagen (y el
                    # recorte superior de la segunda lectura) es distinta en cada copia y en cada tanda
                    for j in range(2):
                        x, y = 6 + (k >> (8 * j)) % 150, 6 + (k >> (8 * j + 4)) % 40
                        gris = 0.70 + ((k >> (3 * j)) % 25) / 100
                        pag.draw_rect(
                            pymupdf.Rect(x, y, x + 2, y + 2), color=None, fill=(gris,) * 3
                        )
                else:
                    pag.insert_text((36, pag.rect.height - 8), f"ref {marca}", fontsize=5)
                nombre = unicodedata.normalize("NFC", f"L{camino[0].upper()}{i:03d}-{src.name}")
                (destino / nombre).write_bytes(doc.tobytes())
            listas[camino].append(nombre)
    for camino, nombres in listas.items():
        (destino.parent / f"fixture-{camino}.txt").write_text(
            "\n".join(nombres) + "\n", encoding="utf-8"
        )
    return {
        "segundos": time.perf_counter() - t0,
        "n": sum(len(v) for v in listas.values()),
        "originales_vision": len(escaneadas),
        "originales_texto": [p.name for p in sin_plantilla],
    }


ETAPAS = {
    "generar": etapa_generar,
    "ingest": etapa_ingest,
    "extract": etapa_extract,
    "inyectar": etapa_inyectar,
    "maestro": etapa_maestro,
    "erp": etapa_erp,
    "duplicados": etapa_duplicados,
    "decide": etapa_decide,
    "decide_variante": etapa_decide_variante,
    "package": etapa_package,
    "validar": etapa_validar,
    "micro_por_pedido": etapa_micro_por_pedido,
    "generar_llm": etapa_generar_llm,
}


def hijo(nombre: str, ctx: dict) -> None:
    import pydantic  # noqa: F401 — imports pesados antes de medir la base
    import pymupdf  # noqa: F401

    base = _proc_status("VmRSS")
    res = ETAPAS[nombre](ctx)
    res.update(rss_base_mb=base, rss_pico_mb=_proc_status("VmHWM"))
    print(MARCA + json.dumps(res, default=str), flush=True)


# ----------------------------------------------------------------------------- orquestador


def correr(nombre: str, ctx: dict, env: dict[str, str]) -> dict:
    t0 = time.perf_counter()
    p = subprocess.run(
        [sys.executable, __file__, "--etapa", nombre, "--ctx", json.dumps(ctx)],
        capture_output=True,
        text=True,
        env=env,
        cwd=RAIZ,
    )
    linea = next((x for x in reversed(p.stdout.splitlines()) if x.startswith(MARCA)), None)
    if p.returncode != 0 or linea is None:
        raise RuntimeError(f"etapa {nombre} falló ({p.returncode}):\n{p.stderr[-3000:]}")
    res = json.loads(linea[len(MARCA) :])
    res["pared_proceso_s"] = time.perf_counter() - t0
    fps = res["n"] / res["segundos"] if res.get("segundos") else 0.0
    print(
        f"  {nombre:<20s} n={res['n']:<6} {res['segundos']:8.2f} s  {fps:9.1f} f/s  "
        f"RSS base {res['rss_base_mb']:6.0f} MB · pico {res['rss_pico_mb']:6.0f} MB",
        flush=True,
    )
    return res


def condiciones() -> dict:
    def sh(cmd: list[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ).stdout.strip()
        except OSError:
            return ""

    cpu = next(
        (
            x.split(":", 1)[1].strip()
            for x in sh(["lscpu"]).splitlines()
            if x.startswith("Model name")
        ),
        "",
    )
    mem = next(
        (
            x.split()[1]
            for x in Path("/proc/meminfo").read_text().splitlines()
            if x.startswith("MemTotal")
        ),
        "0",
    )
    return {
        "fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": sh(["git", "rev-parse", "--short", "HEAD"]),
        "cpu": cpu,
        "hilos": os.cpu_count(),
        "ram_gb": round(int(mem) / 2**20, 1),
        "so": platform.platform(),
        "python": platform.python_version(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--n", type=int, default=500, help="copias sintéticas (0 = sólo caminos de LLM)"
    )
    ap.add_argument("--etiqueta", default="ensayo")
    ap.add_argument("--workers", default="1,8", help="hilos de extract a comparar")
    ap.add_argument("--fecha-corte", default="2026-09-18", help="nunca date.today()")
    ap.add_argument("--erp-url", default="http://127.0.0.1:8009")
    ap.add_argument(
        "--llm-vision", type=int, default=0, help="escaneadas con marca única por el LLM real"
    )
    ap.add_argument(
        "--llm-texto", type=int, default=0, help="facturas sin plantilla por el LLM real"
    )
    ap.add_argument("--workers-llm", default="4")
    ap.add_argument(
        "--decide-variantes",
        action="store_true",
        help="decide sobre copias: reprocesado, con índice en decisiones(sha256), ambos",
    )
    ap.add_argument(
        "--bd", help="BD final de una pasada anterior, para --decide-variantes con --n 0"
    )
    ap.add_argument("--conservar", action="store_true", help="no borrar los PDFs generados")
    ap.add_argument("--etapa", help=argparse.SUPPRESS)
    ap.add_argument("--ctx", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.etapa:
        hijo(args.etapa, json.loads(args.ctx))
        return 0

    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")  # la key sólo hace falta en los caminos de LLM
    BASE.mkdir(parents=True, exist_ok=True)
    etq = args.etiqueta
    dir_caja = BASE / f"caja-{etq}"
    facturas = dir_caja / "facturas"
    env = {
        **os.environ,
        "ALBERTITOS_CHAOS": str(BASE / f"chaos-{etq}.json"),  # nunca dist/chaos.json
        "ALBERTITOS_DB": str(BASE / f"escala-{etq}.db"),
        "ALBERTITOS_DIR_CAJA": str(facturas),
        "ALBERTITOS_DIR_LOTE2": str(facturas),
        "PYTHONPATH": str(RAIZ / "src"),
    }
    medidas: dict = {"condiciones": condiciones(), "args": vars(args), "etapas": {}}
    print(f"condiciones: {medidas['condiciones']}")
    ctx = {
        "n": args.n,
        "facturas": str(facturas),
        "caja": str(dir_caja),
        "entrega": str(BASE / f"entrega-{etq}"),
        "fecha_corte": args.fecha_corte,
        "erp_url": args.erp_url,
    }
    E = medidas["etapas"]
    try:
        if args.n > 0:
            bd_ingest = BASE / f"escala-{etq}-ingest.db"
            E["generar"] = correr("generar", ctx, env)
            _copiar = [bd_ingest, Path(str(bd_ingest) + "-wal"), Path(str(bd_ingest) + "-shm")]
            for f in _copiar:
                f.unlink(missing_ok=True)
            E["ingest"] = correr("ingest", {**ctx, "bd": str(bd_ingest)}, env)
            bd = bd_ingest
            for w in [int(x) for x in args.workers.split(",") if x.strip()]:
                bd = BASE / f"escala-{etq}-w{w}.db"
                _copiar_bd(bd_ingest, bd)
                E[f"extract_w{w}"] = correr(
                    "extract", {**ctx, "bd": str(bd), "workers": w, "caos": "llm_down"}, env
                )
            ctx["bd"] = str(bd)
            for nombre in (
                "inyectar",
                "maestro",
                "erp",
                "duplicados",
                "decide",
                "package",
                "validar",
            ):
                E[nombre] = correr(nombre, ctx, env)
            E["bd_mb"] = {"final": Path(ctx["bd"]).stat().st_size / 2**20}
            E["micro_por_pedido"] = correr(
                "micro_por_pedido", {"asientos": [516, 5_000, 50_000]}, env
            )
        if args.decide_variantes:
            if "bd" not in ctx:  # sobre la BD final de una pasada anterior (--bd)
                ctx["bd"] = str(Path(args.bd).resolve())
            for variante in ("reprocesado", "indice", "indice_reprocesado"):
                E[f"decide_{variante}"] = correr(
                    "decide_variante",
                    {
                        **ctx,
                        "variante": variante,
                        "bd_copia": str(BASE / f"escala-{etq}-{variante}.db"),
                    },
                    env,
                )
        if args.llm_vision or args.llm_texto:
            for w in [int(x) for x in args.workers_llm.split(",") if x.strip()]:
                # copias NUEVAS por tanda: repetir cuerpos de petición mediría la caché del gateway
                dir_llm = BASE / f"llm-{etq}" / f"w{w}"
                ctx_llm = {
                    **ctx,
                    "facturas": str(dir_llm / "facturas"),
                    "llm_vision": args.llm_vision,
                    "llm_texto": args.llm_texto,
                    "sufijo": f"{etq}-w{w}-{int(time.time())}",
                }
                env_llm = {
                    **env,
                    "ALBERTITOS_CHAOS": str(BASE / f"chaos-{etq}-llm.json"),  # nunca activado
                    "ALBERTITOS_DIR_CAJA": str(dir_llm / "facturas"),
                    "ALBERTITOS_DIR_LOTE2": str(dir_llm / "facturas"),
                }
                E[f"generar_llm_w{w}"] = correr("generar_llm", ctx_llm, env_llm)
                bd = BASE / f"escala-{etq}-llm-w{w}.db"
                for s in ("", "-wal", "-shm"):
                    Path(str(bd) + s).unlink(missing_ok=True)
                c = {**ctx_llm, "bd": str(bd)}
                correr("ingest", c, env_llm)
                correr("maestro", c, env_llm)  # la reconciliación de la visión lo lee de la BD
                for camino in ("texto", "vision"):
                    fx = dir_llm / f"fixture-{camino}.txt"
                    if fx.exists() and fx.read_text().strip():
                        E[f"llm_{camino}_w{w}"] = correr(
                            "extract",
                            {**c, "workers": w, "caos": None, "fixture": str(fx)},
                            env_llm,
                        )
    finally:
        salida = BASE / f"medidas-{etq}.json"
        salida.write_text(
            json.dumps(medidas, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        print(f"medidas → {salida.relative_to(RAIZ)}")
        if not args.conservar:
            for d in (BASE / f"caja-{etq}", BASE / f"llm-{etq}"):
                if d.exists():
                    shutil.rmtree(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
