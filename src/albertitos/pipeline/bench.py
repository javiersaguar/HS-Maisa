"""Cifras medidas a partir del log de eventos. Nada de estimaciones aquí."""

from __future__ import annotations

import sqlite3
from typing import Any


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    v = sorted(valores)
    k = min(len(v) - 1, int(round((len(v) - 1) * p)))
    return v[k]


def medir(conn: sqlite3.Connection) -> dict[str, Any]:
    etapas: dict[str, Any] = {}
    for fila in conn.execute("SELECT DISTINCT etapa FROM eventos ORDER BY etapa"):
        etapa = fila["etapa"]
        lat = [
            float(r["latencia_ms"])
            for r in conn.execute(
                "SELECT latencia_ms FROM eventos WHERE etapa=? AND estado='ok' AND latencia_ms IS NOT NULL",
                (etapa,),
            )
        ]
        agg = conn.execute(
            """SELECT count(*) n, sum(estado='ok') ok, sum(estado='error') err, sum(estado='retry') retry,
                      sum(estado='pendiente') pend, coalesce(sum(tokens_in),0) tin, coalesce(sum(tokens_out),0) tout,
                      round(coalesce(sum(coste_eur),0),4) eur, min(ts) t0, max(ts) t1
               FROM eventos WHERE etapa=?""",
            (etapa,),
        ).fetchone()
        etapas[etapa] = {
            **{k: agg[k] for k in agg.keys()},
            "p50_ms": _percentil(lat, 0.5),
            "p95_ms": _percentil(lat, 0.95),
        }
    ventana = conn.execute(
        "SELECT min(ts) t0, max(ts) t1, count(DISTINCT file_id) n FROM eventos"
    ).fetchone()
    return {"etapas": etapas, "ventana": dict(ventana) if ventana else {}}


def texto(medidas: dict[str, Any]) -> str:
    lineas = [
        "etapa        n     ok   err  retry  pend    p50ms    p95ms   tokens_in  tokens_out     EUR"
    ]
    for etapa, m in medidas["etapas"].items():
        lineas.append(
            f"{etapa:<10} {m['n']:>5} {m['ok'] or 0:>6} {m['err'] or 0:>5} {m['retry'] or 0:>6} {m['pend'] or 0:>5} "
            f"{(m['p50_ms'] or 0):>8.0f} {(m['p95_ms'] or 0):>8.0f} {m['tin']:>11} {m['tout']:>11} {m['eur']:>7}"
        )
    v = medidas.get("ventana") or {}
    lineas.append(f"ventana: {v.get('t0')} → {v.get('t1')} · ficheros con eventos: {v.get('n')}")
    lineas.append(
        "ficheros/s: divide el nº de ficheros entre el tiempo real de `time uv run albertitos run` (anótalo con el hardware)."
    )
    return "\n".join(lineas)
