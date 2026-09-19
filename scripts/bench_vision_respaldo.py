"""Candidatos a respaldo de VISIÓN, medidos contra el gateway. Dueño: Javier (agente J3).

Por qué existe: `ALBERTITOS_MODELO_VISION_FALLBACK` está vacío. Si `qwen3.6` se cae o da 429 a las
18:00, las 29 escaneadas del lote 2 se quedan PENDIENTES y acaban, con suerte, en la contingencia
(ESCALAR, ADR-0009). El respaldo de TEXTO se midió el 18/09 (glm5.3-flash, 3/3); el de visión nunca.

Qué mide, por modelo y factura escaneada, con UNA lectura (no la doble de `extract/etapa.py`):
- si acierta los campos frente a dos referencias distintas:
    · `hechos`   → lo que hoy tiene la BD para esa factura (qwen3.6 + reconciliación con el maestro),
    · `maestro`  → el NIF y el IBAN del proveedor dueño del pedido, según el Excel. Ésta es la única
      verdad independiente del sistema que tenemos sin etiquetar a mano;
- latencia, tokens y cómo falla (`LLM-INVALID` = no devolvió la tool ni un JSON aprovechable).

Cómo no falsear la medida:
- cada lectura usa `variante`/`marca` propias (`j3-<modelo>`), así que no pisa la caché de la Caja
  y el gateway no puede servir de la suya (cuerpo de petición distinto). Repetir con el mismo
  `--sufijo` sale de caché y **no vale**: cambia el sufijo para volver a medir.
- la caché se escribe en una BD de ensayo (`--db-ensayo`), nunca en `dist/albertitos.db`.
- la BD real se abre SIEMPRE en sólo lectura y sólo para elegir la muestra y las referencias.

Tope de llamadas: el guardián es `--max-llamadas` (30 por defecto, el que fijó PLAN-10). El script
se planta antes de pasarse y lo dice en el informe.

Uso:
    uv run python scripts/bench_vision_respaldo.py --listar
    uv run python scripts/bench_vision_respaldo.py --modelos qwen3.6,gemma4,deepseek-v4-flash \
        --facturas 8 --max-llamadas 30 --sufijo a
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from albertitos.core import db  # noqa: E402
from albertitos.core.contracts import InvoiceFacts  # noqa: E402
from albertitos.extract import pdf  # noqa: E402
from albertitos.extract.llm import ClienteLLM, ErrorLLM, EstadoLLM  # noqa: E402
from albertitos.formatos import (  # noqa: E402
    CENT,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
)
from albertitos.sources import snapshot  # noqa: E402

DPI = int(os.environ.get("ALBERTITOS_DPI_VISION", "150"))
CAMPOS = ("nif_emisor", "iban", "pedido", "total", "fecha")
# Los frontier del gateway devuelven 402 sin crédito (RESILIENCIA §1): no son candidatos a respaldo.
PREFIJOS_SIN_CREDITO = ("claude-", "gpt-", "gemini-", "o1-", "o3-")


def _normalizar(campo: str, valor: object) -> str | None:
    """El valor de un campo en la forma con la que se comparan dos lecturas (la de `validadores`)."""
    if valor is None:
        return None
    if campo == "nif_emisor":
        return normalizar_nif(str(valor))
    if campo == "iban":
        return normalizar_iban(str(valor))
    if campo == "pedido":
        return normalizar_pedido(str(valor))
    if campo == "total":
        try:
            return str(Decimal(str(valor)).quantize(CENT))
        except (InvalidOperation, ValueError):
            return str(valor)
    return str(valor)


def _igual(campo: str, a: object, b: object) -> bool:
    x, y = _normalizar(campo, a), _normalizar(campo, b)
    if x is None or y is None:
        return False
    if campo == "total":
        try:
            return abs(Decimal(x) - Decimal(y)) <= CENT
        except (InvalidOperation, ValueError):
            return x == y
    return x == y


def muestra(conn_ro, *, n: int) -> list[dict[str, Any]]:
    """Escaneadas del lote 1 con hechos vigentes, las que tienen pedido en el maestro primero.

    Con pedido conocido hay verdad independiente (el NIF y el IBAN del Excel); sin él, sólo se puede
    comparar contra los hechos de hoy. Orden estable por file_id: las tandas se pueden comparar.
    """
    try:
        maestro = snapshot.cargar_maestro_bd(conn_ro)
    except LookupError:
        maestro = None
    filas = conn_ro.execute(
        """SELECT f.file_id, f.sha256, h.hechos_json FROM ficheros f
             JOIN hechos h ON h.sha256 = f.sha256
             WHERE f.lote = 1 AND f.tiene_texto = 0 ORDER BY f.file_id"""
    ).fetchall()
    candidatas: list[dict[str, Any]] = []
    for fila in filas:
        hechos = InvoiceFacts.model_validate_json(fila["hechos_json"])
        proveedor = None
        if maestro is not None and hechos.pedido:
            pedido = maestro.pedidos.get(hechos.pedido)
            if pedido is not None:
                proveedor = maestro.proveedores.get(pedido.proveedor_id)
        candidatas.append(
            {
                "file_id": fila["file_id"],
                "sha256": fila["sha256"],
                "hechos": hechos,
                "proveedor": proveedor,
            }
        )
    candidatas.sort(key=lambda c: (c["proveedor"] is None, c["file_id"]))
    return candidatas[:n]


def modelos_del_gateway() -> list[dict[str, Any]]:
    """GET /models del gateway. La key la carga `dotenv` en el entorno; aquí no se lee ni se imprime."""
    base = os.environ.get("ALBERTITOS_LLM_BASE_URL", "https://api.helmcode.com/v1").rstrip("/")
    key = os.environ.get("ALBERTITOS_LLM_API_KEY", "")
    if not key:
        raise SystemExit("falta ALBERTITOS_LLM_API_KEY en el entorno (.env lo carga el script)")
    r = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
    r.raise_for_status()
    datos = r.json()
    return list(datos.get("data") or datos.get("models") or [])


def _acepta_imagen(m: dict[str, Any]) -> bool | None:
    """Lo que el gateway DICE de la visión. La doc se equivocó el 18/09 (RESILIENCIA §5): informativo."""
    for clave in ("vision", "supports_vision", "image", "multimodal"):
        if clave in m:
            return bool(m[clave])
    modalidades = m.get("input_modalities") or m.get("modalities") or m.get("capabilities")
    if isinstance(modalidades, list):
        return any("image" in str(x).lower() or "vision" in str(x).lower() for x in modalidades)
    return None


def una_lectura(
    fila: dict[str, Any], modelo: str, *, variante: str, ruta_db: str, estado: EstadoLLM
) -> dict[str, Any]:
    """Una llamada de visión con `modelo`, cronometrada. Devuelve el resultado ya comparado."""
    conn = db.conectar(ruta_db)
    t0 = time.perf_counter()
    try:
        png = pdf.imagen_png(Path("data/caja/facturas") / fila["file_id"], dpi=DPI)
        cliente = ClienteLLM(conn, modelo_vision=modelo, estado=estado)
        leidos, uso = cliente.extraer(
            sha256=fila["sha256"],
            file_id=fila["file_id"],
            png=png,
            variante=variante,
            marca=variante,
        )
    except ErrorLLM as e:
        return {
            "file_id": fila["file_id"],
            "ok": False,
            "codigo": e.codigo,
            "detalle": e.detalle[:120],
            "s": time.perf_counter() - t0,
        }
    except Exception as e:  # noqa: BLE001 — un fichero no puede tumbar el banco de pruebas
        return {
            "file_id": fila["file_id"],
            "ok": False,
            "codigo": f"BENCH-{type(e).__name__}",
            "detalle": str(e)[:120],
            "s": time.perf_counter() - t0,
        }
    finally:
        conn.close()

    hechos = fila["hechos"]
    proveedor = fila["proveedor"]
    contra_hechos = {c: _igual(c, getattr(leidos, c), getattr(hechos, c)) for c in CAMPOS}
    contra_maestro: dict[str, bool] = {}
    if proveedor is not None:
        contra_maestro["nif_emisor"] = _igual("nif_emisor", leidos.nif_emisor, proveedor.nif)
        contra_maestro["iban"] = _igual("iban", leidos.iban, proveedor.iban)
    return {
        "file_id": fila["file_id"],
        "ok": True,
        "s": time.perf_counter() - t0,
        "cache": bool(uso.get("cache")),
        "tin": int(uso.get("tokens_in", 0)),
        "tout": int(uso.get("tokens_out", 0)),
        "leido": {c: _normalizar(c, getattr(leidos, c)) for c in CAMPOS},
        "esperado_hechos": {c: _normalizar(c, getattr(hechos, c)) for c in CAMPOS},
        "esperado_maestro": (
            {}
            if proveedor is None
            else {
                "nif_emisor": _normalizar("nif_emisor", proveedor.nif),
                "iban": _normalizar("iban", proveedor.iban),
            }
        ),
        "contra_hechos": contra_hechos,
        "contra_maestro": contra_maestro,
    }


def resumen_modelo(modelo: str, lecturas: list[dict[str, Any]]) -> dict[str, Any]:
    buenas = [r for r in lecturas if r["ok"]]
    latencias = sorted(r["s"] for r in buenas)
    errores: dict[str, int] = {}
    for r in lecturas:
        if not r["ok"]:
            errores[r["codigo"]] = errores.get(r["codigo"], 0) + 1

    def aciertos(clave: str, campo: str) -> tuple[int, int]:
        con_referencia = [r for r in buenas if campo in r[clave]]
        return sum(1 for r in con_referencia if r[clave][campo]), len(con_referencia)

    return {
        "modelo": modelo,
        "llamadas": len(lecturas),
        "ok": len(buenas),
        "errores": errores,
        "desde_cache": sum(1 for r in buenas if r["cache"]),
        "p50_s": statistics.median(latencias) if latencias else None,
        "max_s": max(latencias) if latencias else None,
        "tin": sum(r["tin"] for r in buenas),
        "tout": sum(r["tout"] for r in buenas),
        "contra_hechos": {c: aciertos("contra_hechos", c) for c in CAMPOS},
        "contra_maestro": {c: aciertos("contra_maestro", c) for c in ("nif_emisor", "iban")},
    }


def tabla_markdown(resumenes: list[dict[str, Any]]) -> str:
    def frac(par: tuple[int, int]) -> str:
        aciertos, total = par
        return "—" if not total else f"{aciertos}/{total}"

    filas = [
        "| Modelo | ok | NIF (maestro) | IBAN (maestro) | pedido | total | fecha | p50 | máx | tokens | errores |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resumenes:
        errores = ", ".join(f"{k}×{v}" for k, v in sorted(r["errores"].items())) or "—"
        filas.append(
            "| `{modelo}` | {ok}/{n} | {nif} | {iban} | {pedido} | {total} | {fecha} | "
            "{p50} | {mx} | {tin}/{tout} | {err} |".format(
                modelo=r["modelo"],
                ok=r["ok"],
                n=r["llamadas"],
                nif=frac(r["contra_maestro"]["nif_emisor"]),
                iban=frac(r["contra_maestro"]["iban"]),
                pedido=frac(r["contra_hechos"]["pedido"]),
                total=frac(r["contra_hechos"]["total"]),
                fecha=frac(r["contra_hechos"]["fecha"]),
                p50="—" if r["p50_s"] is None else f"{r['p50_s']:.1f} s",
                mx="—" if r["max_s"] is None else f"{r['max_s']:.1f} s",
                tin=r["tin"],
                tout=r["tout"],
                err=errores,
            )
        )
    return "\n".join(filas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--listar", action="store_true", help="sólo GET /models del gateway y salir")
    ap.add_argument("--modelos", default="", help="candidatos separados por coma (máx. 3)")
    ap.add_argument("--facturas", type=int, default=8, help="escaneadas por modelo")
    ap.add_argument("--max-llamadas", type=int, default=30, help="tope duro de llamadas al LLM")
    ap.add_argument("--sufijo", default="a", help="cámbialo para medir de nuevo sin caché")
    ap.add_argument("--db", default=os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    ap.add_argument("--db-ensayo", default="dist/ensayo/j3/bench.db")
    ap.add_argument("--salida", default="dist/ensayo/j3/resultados.json")
    args = ap.parse_args()

    load_dotenv(".env")  # la key la pone dotenv en el entorno; el script no lee el fichero

    if args.listar:
        for m in modelos_del_gateway():
            ident = str(m.get("id") or m.get("name") or m)
            vision = _acepta_imagen(m)
            marca = "?" if vision is None else ("imagen" if vision else "sólo texto")
            sin_credito = (
                " · frontier (402 sin saldo)" if ident.startswith(PREFIJOS_SIN_CREDITO) else ""
            )
            print(f"{ident:28s} {marca}{sin_credito}")
        return 0

    candidatos = [x.strip() for x in args.modelos.split(",") if x.strip()]
    if not candidatos:
        raise SystemExit("--modelos es obligatorio (o usa --listar)")
    if len(candidatos) > 3:
        raise SystemExit(f"tope de 3 modelos (PLAN-10); has pedido {len(candidatos)}")

    conn_ro = db.conectar(args.db, solo_lectura=True)
    try:
        filas = muestra(conn_ro, n=args.facturas)
    finally:
        conn_ro.close()
    if not filas:
        raise SystemExit("no hay escaneadas con hechos en la BD: ¿es la BD real?")

    previstas = len(candidatos) * len(filas)
    if previstas > args.max_llamadas:
        raise SystemExit(
            f"{len(candidatos)} modelos × {len(filas)} facturas = {previstas} llamadas, "
            f"por encima del tope de {args.max_llamadas}. Baja --facturas o --modelos."
        )

    ruta_ensayo = Path(args.db_ensayo)
    ruta_ensayo.parent.mkdir(parents=True, exist_ok=True)
    conn_ensayo = db.conectar(ruta_ensayo)
    db.init_schema(conn_ensayo)
    conn_ensayo.close()

    con_maestro = sum(1 for f in filas if f["proveedor"] is not None)
    print(f"muestra: {len(filas)} escaneadas ({con_maestro} con pedido en el maestro) · dpi {DPI}")
    print(f"modelos: {', '.join(candidatos)} · tope {args.max_llamadas} · previstas {previstas}")
    print(
        "una lectura por factura (sin la doble de etapa.py): esto mide el modelo, no el pipeline\n"
    )

    hechas = 0
    resumenes: list[dict[str, Any]] = []
    detalle: dict[str, list[dict[str, Any]]] = {}
    for modelo in candidatos:
        lecturas: list[dict[str, Any]] = []
        estado = EstadoLLM()
        for fila in filas:
            if hechas >= args.max_llamadas:
                print(f"  tope de {args.max_llamadas} llamadas alcanzado: paro aquí")
                break
            variante = f"j3-{args.sufijo}-{modelo}"
            r = una_lectura(
                fila, modelo, variante=variante, ruta_db=str(ruta_ensayo), estado=estado
            )
            hechas += 1
            lecturas.append(r)
            if r["ok"]:
                nif = "✓" if r["contra_maestro"].get("nif_emisor") else "✗"
                marca_cache = "  (DESDE CACHÉ: no vale)" if r["cache"] else ""
                print(
                    f"  {modelo:20s} {r['file_id']:24s} {r['s']:6.1f}s  NIF {nif}  "
                    f"pedido {'✓' if r['contra_hechos']['pedido'] else '✗'}"
                    f"  total {'✓' if r['contra_hechos']['total'] else '✗'}{marca_cache}"
                )
            else:
                print(f"  {modelo:20s} {r['file_id']:24s} {r['s']:6.1f}s  {r['codigo']}")
        detalle[modelo] = lecturas
        resumenes.append(resumen_modelo(modelo, lecturas))

    print(f"\nllamadas hechas: {hechas} de un tope de {args.max_llamadas}\n")
    print(tabla_markdown(resumenes))

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        json.dumps(
            {
                "dpi": DPI,
                "sufijo": args.sufijo,
                "llamadas": hechas,
                "max_llamadas": args.max_llamadas,
                "muestra": [f["file_id"] for f in filas],
                "resumenes": resumenes,
                "detalle": detalle,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\ndetalle en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
