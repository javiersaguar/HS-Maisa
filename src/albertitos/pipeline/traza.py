"""La traza de una decisión, legible: hechos → maestro → ERP → reglas → resultado (`albertitos trace`).

Sólo lectura. Lo que no está en la BD no se inventa: si falta un snapshot o un evento, se dice.
El grupo de un duplicado se calcula al vuelo con la misma función que lo marca (`grupos_duplicados`),
así que la traza nombra a la pareja aunque no quede el evento `validate` que la anotó.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from albertitos.core import db
from albertitos.core.contracts import InvoiceFacts
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.pipeline.etapas import grupos_duplicados, hechos_vigentes
from albertitos.sources import snapshot

try:
    MADRID: Any = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:  # Windows sin tzdata: mejor UTC dicho que una hora mal
    MADRID = None

SANGRIA = " " * 14

ATRIBUCION = {
    "explicita": "reintentos enlazados a esta descarga",
    "inferida_por_ventana": "atribución histórica inferida",
    "no_disponible": "sin eventos atribuibles a esta descarga",
}


def hora(iso: str | datetime | None) -> str:
    """'19/09 10:05 Madrid' (o UTC si no hay zona)."""
    if not iso:
        return "—"
    t = iso if isinstance(iso, datetime) else datetime.fromisoformat(iso)
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    if MADRID is None:
        return t.astimezone(UTC).strftime("%d/%m %H:%M UTC")
    return t.astimezone(MADRID).strftime("%d/%m %H:%M Madrid")


def linea_erp(r: dict[str, Any], titulo: bool = True) -> str:
    """Una línea con lo que costó bajar un snapshot del ERP (`sources.snapshot.resumen_erp`)."""
    errores = r.get("errores_por_codigo") or {}
    reintentos = f"{r['reintentos']} reintentos"
    if errores:
        reintentos += " (" + ", ".join(f"{c}×{n}" for c, n in errores.items()) + ")"
    partes = [
        f"ERP {r['version']}" if titulo else str(r["version"]),
        f"bajado {hora(r['descargado_en'])}",
        f"{r['asientos']} asientos",
        f"{r['consultas']} consultas",
        reintentos,
    ]
    if r.get("latencia_total_ms") is not None:
        partes.append(f"HTTP acumulado {r['latencia_total_ms']} ms")
    partes.append(ATRIBUCION.get(r.get("atribucion", ""), str(r.get("atribucion"))))
    return " · ".join(partes)


def resumen_erp_o_nada(conn: sqlite3.Connection, version: str) -> dict[str, Any] | None:
    try:
        return snapshot.resumen_erp(conn, version)
    except LookupError:
        return None


def duplicado_con(conn: sqlite3.Connection, sha256: str) -> dict[str, str]:
    """file_id de los otros PDFs de su grupo de duplicados → qué comparten (vacío si no hay grupo)."""
    return grupos_duplicados(hechos_vigentes(conn)).get(sha256, {})


def _v(x: Any) -> str:
    return "—" if x is None or x == "" else str(x)


def _json(texto: str | None) -> dict[str, Any]:
    try:
        d = json.loads(texto or "")
    except (TypeError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def porques(decisiones: list[dict], eventos: list[dict]) -> dict[int, str]:
    """id de decisión → por qué se tomó, del evento decide/ok que la acompaña (el primero con ts
    desde su `decidido_en` y antes de la siguiente decisión)."""
    decide = [
        (datetime.fromisoformat(e["ts"]), _json(e["detalle"]))
        for e in eventos
        if e["etapa"] == "decide" and e["estado"] == "ok"
    ]

    def ms(iso: str) -> datetime:  # el evento guarda milisegundos; decidido_en, a veces micro
        t = datetime.fromisoformat(iso)
        return t.replace(microsecond=t.microsecond // 1000 * 1000)

    out: dict[int, str] = {}
    orden = sorted(decisiones, key=lambda d: d["id"])
    for i, d in enumerate(orden):
        desde = ms(d["decidido_en"])
        hasta = ms(orden[i + 1]["decidido_en"]) if i + 1 < len(orden) else None
        for ts, det in decide:
            if ts >= desde and (hasta is None or ts < hasta):
                if det.get("contingencia"):
                    out[d["id"]] = f"contingencia: {det.get('motivo', '')}".strip()
                elif det.get("por"):
                    out[d["id"]] = str(det["por"])
                break
    return out


def legible(conn: sqlite3.Connection, file_id: str) -> str | None:
    """La traza en texto, un paso por bloque. None si el fichero no está en la BD."""
    t = db.traza(conn, file_id)
    f = t["fichero"]
    if not f:
        return None
    L: list[str] = [
        f"{file_id} · lote {f['lote']} · {_v(f['paginas'])} pág. · "
        f"{'con texto' if f['tiene_texto'] else 'escaneada'} · sha256 {f['sha256'][:12]}"
    ]
    eventos = t["eventos"]
    decisiones = t["decisiones"]
    vigente = next((d for d in decisiones if d["vigente"]), None)

    # 1 · hechos
    fila_h = next((h for h in t["hechos"] if h["extractor_version"] == EXTRACTOR_VERSION), None)
    h: InvoiceFacts | None = None
    if fila_h is None:
        L.append(f"1 HECHOS      ninguno con {EXTRACTOR_VERSION}: no se puede decidir (PENDIENTE)")
    else:
        h = InvoiceFacts.model_validate_json(fila_h["hechos_json"])
        L += [
            f"1 HECHOS      {h.metodo.value} · {h.extractor_version} · confianza {_v(h.confianza)}",
            f"{SANGRIA}{_v(h.razon_social)} · NIF {_v(h.nif_emisor)} · IBAN {_v(h.iban)}",
            f"{SANGRIA}factura {_v(h.num_factura)} del {_v(h.fecha)} · pedido {_v(h.pedido)}",
            f"{SANGRIA}base {_v(h.base)} + IVA {_v(h.iva_pct)} % {_v(h.iva)} = total {_v(h.total)}",
        ]
        if h.avisos:
            L.append(f"{SANGRIA}avisos: {', '.join(a.value for a in h.avisos)}")
        if h.texto_sospechoso:
            L.append(f'{SANGRIA}el PDF dice: "{h.texto_sospechoso}" (es un dato, no una orden)')
    extract = [e for e in eventos if e["etapa"] == "extract"]
    fallos = [e for e in extract if e["estado"] in ("error", "pendiente")]
    if fallos:
        L.append(
            f"{SANGRIA}extract falló {len(fallos)} vez/veces antes: "
            + " → ".join(f"{e['error_codigo'] or e['estado']} ({hora(e['ts'])})" for e in fallos)
        )
    ok = [e for e in extract if e["estado"] == "ok"]
    if ok:
        e = ok[-1]
        coste = "" if e["coste_eur"] is None else f" · {e['coste_eur']:.4f} EUR registrados"
        L.append(
            f"{SANGRIA}última extracción {hora(e['ts'])} · {_v(e['detalle'])[:120]}"
            f" · {_v(e['latencia_ms'])} ms · tokens {_v(e['tokens_in'])}/{_v(e['tokens_out'])}{coste}"
        )

    # 2 y 3 · maestro y ERP con los que se decidió (o los últimos, si no hay decisión)
    maestro_v = vigente["maestro_version"] if vigente else None
    erp_v = vigente["erp_version"] if vigente else None
    try:
        m = snapshot.cargar_maestro_bd(conn, maestro_v)
    except LookupError:
        m = None
        L.append(f"2 MAESTRO     {_v(maestro_v)}: el snapshot ya no está en la BD")
    if m is not None:
        L.append(f"2 MAESTRO     {m.version} ({m.origen})")
        if h is not None:
            prov = m.proveedor_por_nif(h.nif_emisor) if h.nif_emisor else None
            L.append(
                f"{SANGRIA}NIF → {prov.id} {prov.razon_social} · IBAN {prov.iban}"
                if prov
                else f"{SANGRIA}NIF {_v(h.nif_emisor)} → ningún proveedor del Excel"
            )
            ped = m.pedidos.get(h.pedido) if h.pedido else None
            L.append(
                f"{SANGRIA}pedido {ped.pedido} → {ped.proveedor_id} · {ped.importe_total} · {ped.estado}"
                if ped
                else f"{SANGRIA}pedido {_v(h.pedido)} → no está en el Excel"
            )
    try:
        e_snap = snapshot.cargar_erp_bd(conn, erp_v)
    except LookupError:
        e_snap = None
        L.append(f"3 ERP         {_v(erp_v)}: el snapshot ya no está en la BD")
    if e_snap is not None:
        r = resumen_erp_o_nada(conn, e_snap.version)
        L.append("3 ERP         " + (linea_erp(r, titulo=False) if r else e_snap.version))
        if h is not None and h.pedido:
            asientos = e_snap.por_pedido().get(h.pedido, [])
            for a in asientos:
                L.append(
                    f"{SANGRIA}asiento {a.asiento_id} · {a.estado} · {a.importe_esperado}"
                    f" · registrado {a.fecha_registro}"
                )
            if not asientos:
                L.append(f"{SANGRIA}ningún asiento para {h.pedido}")

    # 4 · duplicados, calculados al vuelo
    pareja = duplicado_con(conn, f["sha256"])
    if pareja:
        L.append(
            "4 DUPLICADO   "
            + " · ".join(f"comparte {que} con {otro}" for otro, que in sorted(pareja.items()))
        )

    # 5 y 6 · reglas y resultado
    if vigente is None:
        L.append("5 REGLAS      sin decisión vigente: package se niega a entregar")
    else:
        motivos = json.loads(vigente["motivos_json"])
        L.append(f"5 REGLAS      norma {vigente['norma_version']} · corte {vigente['fecha_corte']}")
        for mo in motivos:
            L.append(f"{SANGRIA}{'✓' if mo['ok'] else '✗'} {mo['regla_id']}  {mo['detalle']}")
        fallo = next((mo for mo in motivos if not mo["ok"]), None)
        por = porques(decisiones, eventos)
        L.append(
            f"6 RESULTADO   {vigente['resultado']} · "
            + (
                f"{fallo['regla_id']}: {fallo['detalle']}"
                if fallo
                else "todas las reglas cumplidas"
            )
        )
        L.append(
            f"{SANGRIA}decidida {hora(vigente['decidido_en'])}"
            + (f" · por: {por[vigente['id']]}" if vigente["id"] in por else "")
        )
        emit = [e for e in eventos if e["etapa"] == "emit" and e["estado"] in ("ok", "pendiente")]
        if emit:
            d = _json(emit[-1]["detalle"])
            L.append(
                f"{SANGRIA}entregado {hora(emit[-1]['ts'])}: {d.get('entrega')} → {d.get('result')}"
                if emit[-1]["estado"] == "ok"
                else f"{SANGRIA}NO entregado {hora(emit[-1]['ts'])}: {d.get('pendiente')}"
            )
        if len(decisiones) > 1:
            L.append(f"  historial: {len(decisiones)} decisiones, la vigente primero")
            for d in sorted(decisiones, key=lambda x: x["id"], reverse=True):
                L.append(
                    f"{SANGRIA}{hora(d['decidido_en'])}  {d['resultado']:<8} norma {d['norma_version']}"
                    f" · erp {d['erp_version']} · corte {d['fecha_corte']}"
                    + (" · VIGENTE" if d["vigente"] else "")
                    + (f" · por: {por[d['id']]}" if d["id"] in por else "")
                )

    cuenta = Counter((e["etapa"], e["estado"]) for e in eventos)
    L.append(
        f"  eventos ({len(eventos)}): "
        + " · ".join(f"{et} {es}×{n}" for (et, es), n in sorted(cuenta.items()))
    )
    return "\n".join(L)
