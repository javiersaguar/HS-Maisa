"""Contraste de la muestra etiquetada: Mónica, Alfonso, acordado, la lectura del agente y el sistema.

Lee `data/fixtures/esperado_muestra.csv` (las personas), la CSV de la tercera lectura (`--agente`) y las decisiones
vigentes de la BD en sólo lectura. Sólo informa: no escribe nada.

La muestra sólo sirve si se etiqueta a ciegas. Por eso, mientras la parte humana no esté cerrada (`acordado`
completo, o `esperado_monica` completo si Alfonso no ha etiquetado), el script no enseña ni la columna del sistema
ni la del agente, y ni siquiera abre la BD. Para verlas antes hace falta `--revelar-sistema` / `--revelar-agente`
con `--motivo "<por qué>"`, y la salida lo dice arriba.

    uv run python scripts/comparar_muestra.py                     # lo que se pueda enseñar hoy
    uv run python scripts/comparar_muestra.py --markdown          # para pegar en MUESTRA-CONTRASTE.md
    uv run python scripts/comparar_muestra.py --revelar-sistema --motivo "Mónica cerró la muestra"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from albertitos.core import db

RESULTADOS = ("PAGAR", "NO_PAGAR", "ESCALAR")
MUESTRA = Path("data/fixtures/esperado_muestra.csv")
AGENTE = Path("data/fixtures/esperado_muestra_agente.csv")
COLUMNAS = (  # clave interna, título
    ("monica", "Mónica"),
    ("alfonso", "Alfonso"),
    ("acordado", "Acordado"),
    ("agente", "Agente"),
    ("sistema", "Sistema"),
)


def nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto.strip())


def _resultado(valor: str | None, donde: str) -> str:
    v = (valor or "").strip().upper()
    if v and v not in RESULTADOS:
        raise ValueError(f"{donde}: {valor!r} no es PAGAR, NO_PAGAR ni ESCALAR")
    return v


def leer_humanos(ruta: Path) -> dict[str, dict[str, str]]:
    """file_id → monica, alfonso, acordado, motivo, pregunta_mentor. El orden del CSV se conserva."""
    filas: dict[str, dict[str, str]] = {}
    with ruta.open(encoding="utf-8", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            fid = nfc(r["file_id"])
            if fid in filas:
                raise ValueError(f"{ruta}:{n}: {fid} repetido")
            filas[fid] = {
                "monica": _resultado(r.get("esperado_monica"), f"{ruta}:{n}"),
                "alfonso": _resultado(r.get("esperado_alfonso"), f"{ruta}:{n}"),
                "acordado": _resultado(r.get("acordado"), f"{ruta}:{n}"),
                "motivo": (r.get("motivo") or "").strip(),
                "pregunta_mentor": (r.get("pregunta_mentor") or "").strip(),
            }
    return filas


def leer_agente(ruta: Path) -> dict[str, dict[str, str]] | None:
    """file_id → agente, motivo, confianza. None si el fichero no existe (columna vacía)."""
    if not ruta.exists():
        return None
    filas: dict[str, dict[str, str]] = {}
    with ruta.open(encoding="utf-8", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            filas[nfc(r["file_id"])] = {
                "agente": _resultado(r.get("esperado_agente"), f"{ruta}:{n}"),
                "motivo": (r.get("motivo") or "").strip(),
                "confianza": (r.get("confianza") or "").strip(),
            }
    return filas


def estado_cierre(humanos: dict[str, dict[str, str]]) -> tuple[bool, str]:
    """¿Está cerrada la parte humana? `acordado` completo, o Mónica completa si Alfonso no ha etiquetado."""
    total = len(humanos)
    cuenta = {
        c: sum(1 for h in humanos.values() if h[c]) for c in ("monica", "alfonso", "acordado")
    }
    estado = f"acordado {cuenta['acordado']}/{total} · Mónica {cuenta['monica']}/{total} · Alfonso {cuenta['alfonso']}/{total}"
    if total and cuenta["acordado"] == total:
        return True, estado
    if total and cuenta["alfonso"] == 0 and cuenta["monica"] == total:
        return True, estado + " (sin Alfonso: cuenta la de Mónica)"
    return False, estado


def motivo_principal(motivos_json: str) -> str:
    """La primera regla que falla; si no falla ninguna, "cumple todas"."""
    try:
        motivos = json.loads(motivos_json or "[]")
    except json.JSONDecodeError:
        return "(motivos ilegibles)"
    for m in motivos:
        if not m.get("ok", True):
            return f"{m.get('regla_id', '?')}: {m.get('detalle', '')}".strip()
    return "cumple todas" if motivos else ""


def leer_sistema(ruta_db: Path, file_ids: list[str]) -> dict[str, dict[str, str]] | None:
    """Decisión vigente y motivo principal de cada file_id, en sólo lectura. None si no hay BD."""
    if not ruta_db.exists():
        return None
    conn = db.conectar(ruta_db, solo_lectura=True)
    try:
        filas = conn.execute(
            "SELECT file_id, resultado, motivos_json FROM decisiones WHERE vigente = 1"
        ).fetchall()
    finally:
        conn.close()
    buscados = set(file_ids)
    return {
        nfc(r["file_id"]): {
            "sistema": r["resultado"],
            "motivo": motivo_principal(r["motivos_json"]),
        }
        for r in filas
        if nfc(r["file_id"]) in buscados
    }


@dataclass
class Informe:
    filas: list[dict[str, str]]
    columnas: list[tuple[str, str]]  # las que se enseñan
    ocultas: dict[str, str] = field(default_factory=dict)  # título → por qué no se enseña
    vacias: list[str] = field(default_factory=list)  # títulos sin ningún valor
    # (columna a, columna b, coinciden, comparadas)
    pares: list[tuple[str, str, int, int]] = field(default_factory=list)
    discrepancias: list[dict[str, str]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    estado: str = ""  # cierre de la parte humana, en una línea


def construir(
    humanos: dict[str, dict[str, str]],
    agente: dict[str, dict[str, str]] | None,
    sistema: dict[str, dict[str, str]] | None,
    *,
    mostrar_agente: bool,
    mostrar_sistema: bool,
) -> Informe:
    filas = []
    for fid, h in humanos.items():
        fila = {
            "file_id": fid,
            "monica": h["monica"],
            "alfonso": h["alfonso"],
            "acordado": h["acordado"],
        }
        fila["agente"] = (agente or {}).get(fid, {}).get("agente", "")
        s = (sistema or {}).get(fid, {})
        fila["sistema"] = s.get("sistema", "")
        fila["motivo_sistema"] = s.get("motivo", "")
        filas.append(fila)

    informe = Informe(filas=filas, columnas=[])
    if agente is not None:
        sobran = sorted(set(agente) - set(humanos))
        if sobran:
            informe.avisos.append(
                f"el agente etiqueta ficheros que no están en la muestra: {sobran}"
            )
    if sistema is not None:
        sin = [f["file_id"] for f in filas if not f["sistema"]]
        if sin:
            informe.avisos.append(f"{len(sin)} fichero(s) sin decisión vigente en la BD: {sin}")

    visibles = {"monica", "alfonso", "acordado"}
    if mostrar_agente:
        visibles.add("agente")
    if mostrar_sistema:
        visibles.add("sistema")
    for clave, titulo in COLUMNAS:
        if clave not in visibles:
            continue
        if any(f[clave] for f in filas):
            informe.columnas.append((clave, titulo))
        else:
            informe.vacias.append(titulo)

    for (a, ta), (b, tb) in combinations(informe.columnas, 2):
        comparadas = [f for f in filas if f[a] and f[b]]
        informe.pares.append((ta, tb, sum(1 for f in comparadas if f[a] == f[b]), len(comparadas)))
    claves = [c for c, _ in informe.columnas]
    informe.discrepancias = [f for f in filas if len({f[c] for c in claves if f[c]}) > 1]
    return informe


def _celdas(fila: dict[str, str], informe: Informe) -> list[str]:
    celdas = [fila["file_id"]] + [fila[c] or "·" for c, _ in informe.columnas]
    if any(c == "sistema" for c, _ in informe.columnas):
        celdas.append(fila["motivo_sistema"])
    return celdas


def _cabecera(informe: Informe) -> list[str]:
    cab = ["file_id"] + [t for _, t in informe.columnas]
    if any(c == "sistema" for c, _ in informe.columnas):
        cab.append("Motivo principal del sistema")
    return cab


def render(informe: Informe, *, markdown: bool, revelado: list[str]) -> str:
    out: list[str] = []
    titulo = "## Contraste de la muestra" if markdown else "CONTRASTE DE LA MUESTRA"
    out.append(titulo)
    if informe.estado:
        out.append(f"Muestra humana: {informe.estado}")
    for r in revelado:
        out.append(f"**{r}**" if markdown else f"!! {r}")
    for t, porque in informe.ocultas.items():
        out.append(f"- {t}: oculta. {porque}" if markdown else f"{t}: oculta. {porque}")
    for t in informe.vacias:
        out.append(f"- {t}: vacía, no cuenta" if markdown else f"{t}: vacía, no cuenta")
    for a in informe.avisos:
        out.append(f"- aviso: {a}" if markdown else f"aviso: {a}")
    out.append("")
    out.append("### Coincidencias por pares" if markdown else "Coincidencias por pares:")
    if not informe.pares:
        out.append("(hace falta al menos dos columnas con valores)")
    for a, b, si, n in informe.pares:
        linea = f"{a} = {b}: {si} de {n}"
        out.append(f"- {linea}" if markdown else f"  {linea}")
    out.append("")
    disc = informe.discrepancias
    out.append(("### Discrepancias" if markdown else "Discrepancias:") + f" ({len(disc)})")
    for f in disc:
        valores = " · ".join(f"{t} {f[c]}" for c, t in informe.columnas if f[c])
        out.append(f"- `{f['file_id']}`: {valores}" if markdown else f"  {f['file_id']}: {valores}")
    out.append("")
    cab = _cabecera(informe)
    filas = [_celdas(f, informe) for f in informe.filas]
    if markdown:
        out.append("| " + " | ".join(cab) + " |")
        out.append("|" + "---|" * len(cab))
        out.extend("| " + " | ".join(c.replace("|", "/") for c in fila) + " |" for fila in filas)
    else:
        anchos = [max(len(x) for x in col) for col in zip(cab, *filas, strict=True)]
        anchos[-1] = min(anchos[-1], 90)
        for fila in [cab, *filas]:
            out.append(
                "  ".join(c[:90].ljust(w) for c, w in zip(fila, anchos, strict=True)).rstrip()
            )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--muestra", type=Path, default=MUESTRA, help="CSV de Mónica y Alfonso")
    ap.add_argument("--agente", type=Path, default=AGENTE, help="CSV de la tercera lectura")
    ap.add_argument("--db", type=Path, default=db.RUTA_POR_DEFECTO, help="BD (sólo lectura)")
    ap.add_argument(
        "--revelar-sistema", action="store_true", help="enseña el sistema aunque no esté cerrada"
    )
    ap.add_argument(
        "--revelar-agente", action="store_true", help="enseña el agente aunque no esté cerrada"
    )
    ap.add_argument(
        "--motivo", help="obligatorio con --revelar-*: por qué se enseña antes de tiempo"
    )
    ap.add_argument("--markdown", action="store_true", help="salida en Markdown")
    args = ap.parse_args(argv)
    if (args.revelar_sistema or args.revelar_agente) and not (args.motivo or "").strip():
        ap.error('--revelar-sistema / --revelar-agente exigen --motivo "<por qué>"')

    try:
        humanos = leer_humanos(args.muestra)
        agente = leer_agente(args.agente)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    cerrada, estado = estado_cierre(humanos)
    mostrar_sistema = cerrada or args.revelar_sistema
    mostrar_agente = cerrada or args.revelar_agente
    revelado = []
    if not cerrada:
        for flag, titulo in ((args.revelar_sistema, "sistema"), (args.revelar_agente, "agente")):
            if flag:
                revelado.append(
                    f"COLUMNA DEL {titulo.upper()} REVELADA ANTES DE CERRAR LA MUESTRA ({estado}): {args.motivo.strip()}"
                )
    # Sin permiso para enseñar el sistema, la BD ni se abre: nada que se pueda imprimir por error.
    sistema = leer_sistema(args.db, list(humanos)) if mostrar_sistema else None

    informe = construir(
        humanos, agente, sistema, mostrar_agente=mostrar_agente, mostrar_sistema=mostrar_sistema
    )
    informe.estado = ("cerrada · " if cerrada else "abierta · ") + estado
    pendiente = f"La muestra humana no está cerrada ({estado})."
    if not mostrar_agente:
        informe.ocultas["Agente"] = pendiente + ' Antes de tiempo: --revelar-agente --motivo "..."'
    elif agente is None:
        informe.avisos.append(f"no hay CSV del agente en {args.agente}")
    if not mostrar_sistema:
        informe.ocultas["Sistema"] = (
            pendiente + ' Antes de tiempo: --revelar-sistema --motivo "..."'
        )
    elif sistema is None:
        informe.avisos.append(f"no hay BD en {args.db}")
    print(render(informe, markdown=args.markdown, revelado=revelado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
