"""Cifras medidas a partir del log de eventos. Nada de estimaciones aquí.

ficheros/s de una etapa = ficheros distintos con evento en la ventana / (último ts − primer ts de la
ventana). Con `desde` (ISO) se mide sólo lo posterior: el log acumula todas las pasadas. Los EUR son
los `coste_eur` de los eventos: 0 en los modelos abiertos del gateway (suscripción plana, ADR de Javier).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    v = sorted(valores)
    k = min(len(v) - 1, int(round((len(v) - 1) * p)))
    return v[k]


def _segundos(t0: str | None, t1: str | None) -> float:
    if not t0 or not t1:
        return 0.0
    return (datetime.fromisoformat(t1) - datetime.fromisoformat(t0)).total_seconds()


def medir(conn: sqlite3.Connection, desde: str | None = None) -> dict[str, Any]:
    filtro, args = ("AND ts >= ?", (desde,)) if desde else ("", ())
    etapas: dict[str, Any] = {}
    for fila in conn.execute(
        f"SELECT DISTINCT etapa FROM eventos WHERE 1=1 {filtro} ORDER BY etapa", args
    ).fetchall():
        etapa = fila["etapa"]
        lat = [
            float(r["latencia_ms"])
            for r in conn.execute(
                f"SELECT latencia_ms FROM eventos WHERE etapa=? AND estado='ok' "
                f"AND latencia_ms IS NOT NULL {filtro}",
                (etapa, *args),
            )
        ]
        agg = conn.execute(
            f"""SELECT count(*) n, sum(estado='ok') ok, sum(estado='error') err, sum(estado='retry') retry,
                      sum(estado='pendiente') pend, coalesce(sum(tokens_in),0) tin, coalesce(sum(tokens_out),0) tout,
                      round(coalesce(sum(coste_eur),0),4) eur, min(ts) t0, max(ts) t1,
                      count(DISTINCT file_id) ficheros
               FROM eventos WHERE etapa=? {filtro}""",
            (etapa, *args),
        ).fetchone()
        s = _segundos(agg["t0"], agg["t1"])
        etapas[etapa] = {
            **{k: agg[k] for k in agg.keys()},
            "p50_ms": _percentil(lat, 0.5),
            "p95_ms": _percentil(lat, 0.95),
            "fps": agg["ficheros"] / s if s > 0 else None,
        }
    ventana = conn.execute(
        f"SELECT min(ts) t0, max(ts) t1, count(DISTINCT file_id) n FROM eventos WHERE 1=1 {filtro}",
        args,
    ).fetchone()
    reintentos = {
        str(r["error_codigo"]): r["n"]
        for r in conn.execute(
            f"SELECT error_codigo, count(*) n FROM eventos WHERE estado='retry' {filtro} "
            "GROUP BY error_codigo ORDER BY n DESC",
            args,
        )
    }
    return {
        "etapas": etapas,
        "ventana": dict(ventana) if ventana else {},
        "reintentos": reintentos,
        "desde": desde,
    }


def texto(medidas: dict[str, Any]) -> str:
    lineas = [
        "etapa        n     ok   err  retry  pend  ficheros   f/s    p50ms    p95ms   tokens_in  tokens_out     EUR"
    ]
    for etapa, m in medidas["etapas"].items():
        fps = f"{m['fps']:.1f}" if m["fps"] else "—"
        lineas.append(
            f"{etapa:<10} {m['n']:>5} {m['ok'] or 0:>6} {m['err'] or 0:>5} {m['retry'] or 0:>6} {m['pend'] or 0:>5} "
            f"{m['ficheros']:>9} {fps:>5} {(m['p50_ms'] or 0):>8.0f} {(m['p95_ms'] or 0):>8.0f} "
            f"{m['tin']:>11} {m['tout']:>11} {m['eur']:>7}"
        )
    v = medidas.get("ventana") or {}
    s = _segundos(v.get("t0"), v.get("t1"))
    fps = f"{(v.get('n') or 0) / s:.1f} ficheros/s" if s > 0 else "—"
    desde = f" (desde {medidas['desde']})" if medidas.get("desde") else " (todo el log)"
    lineas.append(
        f"ventana{desde}: {v.get('t0')} → {v.get('t1')} · {s:.1f} s · {v.get('n')} ficheros · {fps}"
    )
    if medidas.get("reintentos"):
        lineas.append(
            "reintentos: " + " · ".join(f"{k} {n}" for k, n in medidas["reintentos"].items())
        )
    lineas.append("EUR: coste_eur de los eventos (modelos abiertos del gateway = 0).")
    return "\n".join(lineas)
