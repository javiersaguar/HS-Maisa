"""Calibración honesta de la confianza por factura (K3, ADR-0014): contra lo que hay FUERA del sistema.

Sólo lee la BD. Dice cómo se reparte la confianza, cuáles son las de menor confianza y si coinciden con lo que ya
sabemos que es dudoso, y la contrasta con cada referencia que exista hoy:
  1. el contraste plantilla↔LLM (lecturas independientes de las 468 de plantilla);
  2. las revisiones a mano de I2 (dist/ensayo/i2/comprobacion.csv) y su mapa de políticas por fichero;
  3. la muestra etiquetada de Mónica y Alfonso (data/fixtures/esperado_muestra.csv), SÓLO si `acordado` está completo;
  4. con `--con-h2`, la tercera lectura del agente H2 (fuera del repo): sólo recuentos por banda.
Mientras la muestra esté abierta, no enseña el nombre de ninguna factura de la muestra (salvo `--mostrar-muestra`).

    uv run python scripts/calibrar_confianza.py                    # informe en la terminal
    uv run python scripts/calibrar_confianza.py --markdown         # para pegar en docs/api/confianza.md
    uv run python scripts/calibrar_confianza.py --salida dist/ensayo/k3 --con-h2   # informe completo, fuera del repo
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from albertitos import confianza
from albertitos.core import db

BANDAS = confianza.BANDAS
MUESTRA_TXT = Path("data/fixtures/muestra.txt")
MUESTRA_CSV = Path("data/fixtures/esperado_muestra.csv")
I2_COMPROBACION = Path("dist/ensayo/i2/comprobacion.csv")
I2_FRONTERAS = (
    Path("dist/ensayo/i2/por_fichero_TODOS.csv"),
    Path("dist/ensayo/i2/por_fichero.csv"),
)
H2 = Path("dist/ensayo/h2/esperado_muestra_agente.csv")
POLITICA_DE_PREGUNTA = {  # pregunta del mapa de I2 → señal de la confianza
    "Q1": "politica.q1_texto",
    "Q2a": "politica.q2_anulado",
    "Q2b": "politica.q2_anulado",
    "Q3": "politica.q3_frontera",
    "Q5": "politica.q5_duplicado",
}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def _csv(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _muestra() -> tuple[set[str], dict[str, str], bool]:
    """(nombres de la muestra, acordado por fichero, ¿cerrada?)."""
    nombres = {nfc(x) for x in MUESTRA_TXT.read_text(encoding="utf-8").splitlines() if x.strip()}
    acordado: dict[str, str] = {}
    if MUESTRA_CSV.exists():
        for r in _csv(MUESTRA_CSV):
            if (r.get("acordado") or "").strip():
                acordado[nfc(r["file_id"])] = r["acordado"].strip().upper()
    return nombres, acordado, bool(nombres) and set(acordado) >= nombres


def _dudas(p: dict) -> set[str]:
    return {s["id"] for f in p["fuentes"].values() for s in f["dudas"]}


def calibrar(ps: list[dict], *, con_h2: bool) -> dict:
    muestra, acordado, cerrada = _muestra()
    por_id = {p["file_id"]: p for p in ps}
    inf: dict = {"total": len(ps), "muestra_cerrada": cerrada, "referencias": {}}

    tabla: dict[str, Counter] = defaultdict(Counter)
    for p in ps:
        tabla[p["resultado"]][p["banda"]] += 1
    inf["distribucion"] = {r: {b: c.get(b, 0) for b in BANDAS} for r, c in sorted(tabla.items())}
    inf["media"] = round(sum(p["puntuacion"] for p in ps) / len(ps), 1) if ps else None

    # «Lo que ya sabemos que es dudoso», con fuentes que no son la puntuación: los hechos (reconciliadas, avisos
    # de lectura) y el mapa de políticas de I2. No es independiente del todo (la puntuación usa los mismos avisos):
    # comprueba que los pesos los ponen abajo, no que acierten.
    sabido: dict[str, str] = {}
    for p in ps:
        if p["lecturas"].get("campos_distintos") or {
            "pdf.reconciliada",
            "pdf.discrepancia_extractores",
            "pdf.superpuesto",
        } & _dudas(p):
            sabido.setdefault(p["file_id"], "lectura dudosa (hechos y lecturas de la caché)")
    fronteras_i2: dict[str, set[str]] = defaultdict(set)
    ruta_i2 = next((r for r in I2_FRONTERAS if r.exists()), None)
    if ruta_i2:
        for r in _csv(ruta_i2):
            fronteras_i2[nfc(r["file_id"])].add(r["pregunta"])
            sabido.setdefault(
                nfc(r["file_id"]), f"frontera de política ({r['pregunta']}, mapa de I2)"
            )
    peores = sorted(ps, key=lambda p: (p["puntuacion"], p["file_id"]))[:10]
    inf["peores"] = [
        {
            "file_id": p["file_id"],
            "en_muestra": p["file_id"] in muestra,
            "resultado": p["resultado"],
            "puntuacion": p["puntuacion"],
            "banda": p["banda"],
            "razones": p["razones"][:2],
            "ya_sabida_dudosa": sabido.get(p["file_id"]),
        }
        for p in peores
    ]
    inf["peores_ya_sabidas"] = sum(1 for x in inf["peores"] if x["ya_sabida_dudosa"])
    inf["bajas_ya_sabidas"] = [
        sum(1 for p in ps if p["banda"] == "baja" and p["file_id"] in sabido),
        sum(1 for p in ps if p["banda"] == "baja"),
    ]

    # 1. Contraste plantilla ↔ LLM.
    plant = [p for p in ps if p["metodo"] == "plantilla"]
    con = [p for p in plant if p["lecturas"].get("contraste")]
    coinciden = [p for p in con if not p["lecturas"].get("campos_distintos")]
    inf["referencias"]["contraste_plantilla_llm"] = {
        "plantilla": len(plant),
        "con_contraste": len(con),
        "coinciden": len(coinciden),
        "bandas_de_las_que_coinciden": dict(Counter(p["banda"] for p in coinciden)),
        "lectura": "confirma la LECTURA de las facturas de plantilla, no su clasificación",
    }

    # 2. I2: revisiones a mano y mapa de políticas por fichero (mismo recuento por dos caminos distintos).
    if I2_COMPROBACION.exists():
        veredictos: dict[str, str] = {}
        for r in _csv(I2_COMPROBACION):
            v = veredictos.get(nfc(r["file_id"]))
            veredictos[nfc(r["file_id"])] = (
                r["veredicto"] if v in (None, r["veredicto"]) else "MIXTO"
            )
        inf["referencias"]["revision_a_mano_i2"] = {
            v: dict(
                Counter(
                    por_id[f]["banda"] for f, vv in veredictos.items() if vv == v and f in por_id
                )
            )
            for v in sorted(set(veredictos.values()))
        }
    if fronteras_i2:
        iguales = distintas = 0
        detalle = []
        for f, preguntas in fronteras_i2.items():
            p = por_id.get(f)
            if p is None:
                continue
            esperadas = {POLITICA_DE_PREGUNTA[q] for q in preguntas if q in POLITICA_DE_PREGUNTA}
            tiene = {d for d in _dudas(p) if d.startswith("politica.")}
            if esperadas <= tiene:
                iguales += 1
            else:
                distintas += 1
                detalle.append({"file_id": f, "i2": sorted(preguntas), "confianza": sorted(tiene)})
        inf["referencias"]["mapa_politicas_i2"] = {
            "ficheros": iguales + distintas,
            "coinciden": iguales,
            "no_coinciden": detalle,
            "fuente": str(ruta_i2),
        }

    # 3. Muestra de Mónica y Alfonso: la única verdad etiquetada. Sólo si está cerrada.
    if cerrada:
        aciertos: dict[str, Counter] = defaultdict(Counter)
        for f, etiqueta in acordado.items():
            p = por_id.get(f)
            if p is not None:
                aciertos[p["banda"]]["acierta" if etiqueta == p["resultado"] else "falla"] += 1
        inf["referencias"]["muestra_acordada"] = {b: dict(c) for b, c in aciertos.items()}
    else:
        inf["referencias"]["muestra_acordada"] = (
            f"abierta: acordado en {len(acordado)} de {len(muestra)}. Sin verdad etiquetada no se calibra."
        )

    # 4. Tercera lectura de H2 (fuera del repo): sólo recuentos por banda, nunca por fichero.
    if con_h2 and H2.exists():
        acuerdo: dict[str, Counter] = defaultdict(Counter)
        for r in _csv(H2):
            p = por_id.get(nfc(r["file_id"]))
            if p is not None and r.get("esperado_agente"):
                clave = (
                    "coincide" if r["esperado_agente"].strip().upper() == p["resultado"] else "no"
                )
                acuerdo[p["banda"]][clave] += 1
        inf["referencias"]["tercera_lectura_h2"] = {b: dict(c) for b, c in acuerdo.items()}
    return inf


def _nombre(x: dict, mostrar: bool, cerrada: bool) -> str:
    if x["en_muestra"] and not (mostrar or cerrada):
        return "(de la muestra: oculto hasta que Mónica cierre)"
    return x["file_id"]


def texto(inf: dict, *, markdown: bool, mostrar_muestra: bool) -> str:
    out = []
    h = "### " if markdown else ""
    out.append(f"{h}Distribución ({inf['total']} facturas, media {inf['media']})")
    out.append("| resultado | alta | media | baja |" if markdown else "resultado   alta media baja")
    if markdown:
        out.append("|---|---:|---:|---:|")
    for r, b in inf["distribucion"].items():
        fila = [r, *(str(b[x]) for x in BANDAS)]
        out.append(
            "| " + " | ".join(fila) + " |"
            if markdown
            else f"{r:10s} {b['alta']:5d} {b['media']:5d} {b['baja']:5d}"
        )
    out.append("")
    out.append(
        f"{h}Las 10 de menor confianza ({inf['peores_ya_sabidas']} de 10 ya se sabían dudosas)"
    )
    for x in inf["peores"]:
        sab = x["ya_sabida_dudosa"] or "NO se sabía dudosa: revisar los pesos"
        out.append(
            f"- {x['puntuacion']} {x['banda']} · {x['resultado']} · {_nombre(x, mostrar_muestra, inf['muestra_cerrada'])}"
            f" · {' | '.join(x['razones'])} · ya sabida: {sab}"
        )
    b, n = inf["bajas_ya_sabidas"]
    out.append(f"Banda baja: {b} de {n} ya se sabían dudosas por los hechos o por el mapa de I2.")
    out.append("")
    out.append(f"{h}Contra lo que hay fuera del sistema")
    for nombre, valor in inf["referencias"].items():
        out.append(f"- {nombre}: {json.dumps(valor, ensure_ascii=False)}")
    out.append("")
    out.append(
        "No es una probabilidad: es una puntuación ordinal. Sin la muestra cerrada no hay verdad etiquetada con que "
        "decir «el 90 % de las de banda alta acierta»."
    )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=db.RUTA_POR_DEFECTO)
    ap.add_argument("--lote", type=int, default=None)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument(
        "--salida", type=Path, help="carpeta para el informe completo (json + csv por fichero)"
    )
    ap.add_argument(
        "--con-h2",
        action="store_true",
        help="contrasta con la tercera lectura de H2 (sólo recuentos)",
    )
    ap.add_argument(
        "--mostrar-muestra",
        action="store_true",
        help="enseña los nombres de la muestra aunque esté abierta",
    )
    args = ap.parse_args(argv)
    if not args.db.exists():
        print(f"ERROR: no existe {args.db}", file=sys.stderr)
        return 2
    conn = db.conectar(args.db, solo_lectura=True)
    try:
        t0 = time.perf_counter()
        ps = confianza.puntuar_todas(conn, lote=args.lote)
        segundos = time.perf_counter() - t0
    finally:
        conn.close()
    inf = calibrar(ps, con_h2=args.con_h2)
    inf["segundos"] = round(segundos, 3)
    print(texto(inf, markdown=args.markdown, mostrar_muestra=args.mostrar_muestra))
    print(f"\n{len(ps)} puntuadas en {segundos:.3f} s (sólo lectura).")
    if args.salida:
        args.salida.mkdir(parents=True, exist_ok=True)
        (args.salida / "calibracion.json").write_text(
            json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        with (args.salida / "confianza_por_fichero.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            w = csv.writer(f)
            w.writerow(["file_id", "lote", "resultado", "puntuacion", "banda", "causa", "razones"])
            for p in ps:
                w.writerow(
                    [
                        p["file_id"],
                        p["lote"],
                        p["resultado"],
                        p["puntuacion"],
                        p["banda"],
                        p["causa"],
                        " | ".join(p["razones"]),
                    ]
                )
        print(f"Informe completo en {args.salida}/ (fuera del repo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
