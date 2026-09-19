"""Etiquetado de las escaneadas: lo que imprime cada PDF, copiado a mano, contra lo que extrae el sistema.

La incertidumbre está en la lectura, sobre todo en la visión. Por eso aquí se etiquetan los datos del PDF y no el
resultado: con los datos buenos, la norma calcula sola qué habría decidido el sistema, y la diferencia con su decisión
real es exactamente lo que cuestan los errores de lectura. Cómo se interpreta la norma es criterio del equipo y queda
fuera de este script.

    uv run python scripts/comparar_hechos.py plantilla        # crea data/fixtures/hechos_escaneadas.csv (escaneadas del lote 1)
    uv run python scripts/comparar_hechos.py plantilla --lote 2 --salida data/fixtures/hechos_escaneadas_lote2.csv
    uv run python scripts/comparar_hechos.py                  # progreso y errores de formato; el sistema, al terminar
    uv run python scripts/comparar_hechos.py --markdown       # para pegar en docs

A ciegas: mientras quede alguna fila sin completar, el script no lee los hechos del sistema ni la BD. Así nadie
etiqueta viendo lo que leyó el modelo. Para ver la comparación antes: --revelar --motivo "<por qué>".

Cómo se rellena: una fila por PDF, copiando lo que está IMPRESO. Espacios, puntos y comas se normalizan solos.
Se abre y se guarda con Excel sin más (separador ';', UTF-8): el script también lee lo que guarde Excel.
    nif, iban, pedido            B98120774 · ES44 1465 0100 9517 0430 2211 · PO-2026-0482
    fecha                        03/03/2026 (una fecha imposible como 31/02/2026 se copia tal cual)
    base, iva_pct, iva, total    1.025,49 · 21 · 215,35 · 1.240,84
    lineas                       importes de las líneas separados por '|'  →  912,69 | 61,53 | 51,27
    instruccion                  la frase literal si el documento intenta dar órdenes (un sello "RECIBIDO" no lo es)
    superpuesto                  'si' si se ve otro documento encima o transparentándose
    notas                        libre
Valores especiales: ILEGIBLE si está impreso pero no se lee con seguridad (no adivines); '-' si no aparece.
Vacío = sin etiquetar. Una fila está completa cuando tiene valor en todo salvo instruccion, superpuesto y notas.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from albertitos.core import db
from albertitos.core.contracts import Aviso, ContextoDecision, InvoiceFacts, LineaFactura
from albertitos.extract import instrucciones, validadores
from albertitos.formatos import (
    CENT,
    fecha_en_letra,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
)

PLANTILLA = Path("data/fixtures/hechos_escaneadas.csv")
HECHOS = Path("data/fixtures/hechos_caja.jsonl")
COLUMNAS = (
    "file_id", "nif", "iban", "pedido", "fecha", "base", "iva_pct", "iva", "total", "lineas",
    "instruccion", "superpuesto", "notas",
)  # fmt: skip
# columna del CSV → campo de InvoiceFacts. Obligatorias para que una fila cuente como completa.
CAMPOS = {
    "nif": "nif_emisor",
    "iban": "iban",
    "pedido": "pedido",
    "fecha": "fecha",
    "base": "base",
    "iva_pct": "iva_pct",
    "iva": "iva",
    "total": "total",
    "lineas": "lineas",
}
IMPORTES = {"base", "iva_pct", "iva", "total"}
ILEGIBLE = "ILEGIBLE"
# Los avisos que dependen de lo que dice el documento: en la versión "verdad" se ponen desde la etiqueta.
AVISOS_DEL_DOCUMENTO = {
    Aviso.TEXTO_INSTRUCCION,
    Aviso.DOCUMENTO_SUPERPUESTO,
    Aviso.PEDIDO_ANULADO_SEGUN_PDF,
    Aviso.DISCREPANCIA_EXTRACTORES,
}
_FECHA_NUM = re.compile(r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


# ------------------------------------------------------------------------------------ lectura del CSV


class _Ilegible:
    def __repr__(self) -> str:
        return ILEGIBLE


ILEG = _Ilegible()


def parsear(columna: str, crudo: str) -> Any:
    """Valor de una celda ya normalizado: None si '-', ILEG si ILEGIBLE. ValueError si no se entiende."""
    s = crudo.strip()
    if s.upper() == ILEGIBLE:
        return ILEG
    if s == "-":
        return [] if columna == "lineas" else None
    if columna == "nif":
        return normalizar_nif(s)
    if columna == "iban":
        return normalizar_iban(s)
    if columna == "pedido":
        return normalizar_pedido(s)
    if columna == "fecha":
        f = parse_fecha_es(s)
        if f is None and not (_FECHA_NUM.search(s) or fecha_en_letra(s)):
            raise ValueError(f"fecha {s!r} no se entiende (dd/mm/aaaa)")
        return f  # una fecha imposible impresa (31/02) queda en None, igual que en la extracción
    if columna == "lineas":
        importes = [parse_importe_es(x) for x in re.split(r"[|;]", s) if x.strip()]
        if not importes or any(x is None for x in importes):
            raise ValueError(f"lineas {s!r}: importes separados por '|'")
        return importes
    v = parse_importe_es(s)
    if v is None:
        raise ValueError(f"{columna} {s!r} no es un importe")
    return v


@dataclass
class Etiqueta:
    file_id: str
    valores: dict[str, Any]  # columna → valor parseado (sólo las rellenas)
    instruccion: str
    superpuesto: bool
    notas: str
    sin_lineas: bool = False  # --sin-lineas: el detalle no se etiqueta ni se mide

    @property
    def completa(self) -> bool:
        return all(c in self.valores for c in CAMPOS if not (self.sin_lineas and c == "lineas"))

    @property
    def empezada(self) -> bool:
        """Alguien ha escrito algo en la fila. Una fila vacía no dice "sin instrucción": no dice nada."""
        return bool(self.valores or self.instruccion or self.superpuesto or self.notas)


def _filas(ruta: Path) -> list[dict[str, str]]:
    """El CSV tal como lo deje Excel en español: `;` o `,` como separador, UTF-8 (con o sin BOM) o cp1252."""
    crudo = ruta.read_bytes()
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252")
    primera = texto.split("\n", 1)[0]
    sep = ";" if primera.count(";") > primera.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto, newline=""), delimiter=sep))


def leer_etiquetas(ruta: Path, *, sin_lineas: bool = False) -> tuple[list[Etiqueta], list[str]]:
    """Etiquetas y errores de formato (fichero:línea: qué)."""
    etiquetas, errores = [], []
    for n, r in enumerate(_filas(ruta), start=2):
        valores = {}
        for col in CAMPOS:
            crudo = (r.get(col) or "").strip()
            if not crudo:
                continue
            try:
                valores[col] = parsear(col, crudo)
            except ValueError as e:
                errores.append(f"{ruta}:{n} {r['file_id']}: {e}")
        etiquetas.append(
            Etiqueta(
                file_id=nfc(r["file_id"]),
                valores=valores,
                instruccion=(r.get("instruccion") or "").strip(),
                superpuesto=(r.get("superpuesto") or "").strip().lower() in ("si", "sí", "s"),
                notas=(r.get("notas") or "").strip(),
                sin_lineas=sin_lineas,
            )
        )
    return etiquetas, errores


_PEDIDO = re.compile(r"PO-\d{4}-\d{4}")


def revisar(e: Etiqueta) -> list[str]:
    """Lo que en la propia etiqueta huele a errata, sin mirar al sistema (no rompe el a ciegas).

    Formato de NIF, IBAN y pedido, y las cuentas de la factura. Un documento puede no cuadrar de verdad (una
    trampa): si el PDF lo imprime así, se deja. Sólo es un "mira otra vez"."""
    v = {c: x for c, x in e.valores.items() if x is not ILEG}
    avisos = []
    if isinstance(v.get("iban"), str) and len(v["iban"]) != 24:
        avisos.append(
            f"el IBAN tiene {len(v['iban'])} caracteres (uno español, 24): si no se lee entero, ILEGIBLE"
        )
    if isinstance(v.get("nif"), str) and len(v["nif"]) != 9:
        avisos.append(f"el NIF tiene {len(v['nif'])} caracteres (9): si no se lee entero, ILEGIBLE")
    if isinstance(v.get("pedido"), str) and not _PEDIDO.fullmatch(v["pedido"]):
        avisos.append(f"el pedido {v['pedido']} no tiene la forma PO-AAAA-NNNN")
    base, iva, total, pct = (v.get(c) for c in ("base", "iva", "total", "iva_pct"))
    if None not in (base, iva, total) and abs(base + iva - total) > CENT:
        avisos.append(f"base + IVA = {base + iva}, pero el total es {total}")
    if None not in (base, iva, pct) and abs(iva - (base * pct / 100).quantize(CENT)) > CENT:
        avisos.append(
            f"el {pct} % de {base} es {(base * pct / 100).quantize(CENT)}, pero el IVA es {iva}"
        )
    lineas = v.get("lineas")
    if lineas and base is not None and abs(sum(lineas) - base) > CENT:
        avisos.append(f"las líneas suman {sum(lineas)}, pero la base es {base}")
    if e.instruccion.upper().startswith("ILEG"):
        avisos.append("`instruccion` es para la frase literal que da órdenes; lo demás, en `notas`")
    return avisos


# ------------------------------------------------------------------------------------ comparación


def _valor_sistema(h: InvoiceFacts, col: str) -> Any:
    v = getattr(h, CAMPOS[col])
    return [x.importe for x in v] if col == "lineas" else v


def coincide(col: str, etiqueta: Any, sistema: Any) -> bool:
    if col == "lineas":
        return len(etiqueta) == len(sistema) and all(
            s is not None and abs(e - s) <= CENT for e, s in zip(etiqueta, sistema, strict=True)
        )
    if col in IMPORTES:
        if etiqueta is None or sistema is None:
            return etiqueta is sistema
        return abs(etiqueta - sistema) <= CENT
    return etiqueta == sistema


@dataclass
class Informe:
    aciertos: dict[str, list[int]] = field(default_factory=dict)  # columna → [aciertos, comparadas]
    fallos: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # file, col, etiqueta, sistema
    ilegibles: list[tuple[str, str, str]] = field(default_factory=list)  # file, col, sistema
    decisiones: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # file, sistema, verdad, motivo
    iguales: int = 0
    sin_hechos: list[str] = field(default_factory=list)


def _txt(v: Any) -> str:
    if isinstance(v, list):
        return "; ".join(str(x) for x in v) or "-"
    return "-" if v is None else str(v)


def comparar(etiquetas: list[Etiqueta], hechos: dict[str, InvoiceFacts]) -> Informe:
    inf = Informe()
    columnas = [*CAMPOS, "instruccion", "superpuesto"]
    inf.aciertos = {c: [0, 0] for c in columnas}
    for e in etiquetas:
        if not e.empezada:
            continue
        h = hechos.get(e.file_id)
        if h is None:
            inf.sin_hechos.append(e.file_id)
            continue
        for col, valor in e.valores.items():
            sistema = _valor_sistema(h, col)
            if valor is ILEG:
                inf.ilegibles.append((e.file_id, col, _txt(sistema)))
                continue
            inf.aciertos[col][1] += 1
            if coincide(col, valor, sistema):
                inf.aciertos[col][0] += 1
            else:
                inf.fallos.append((e.file_id, col, _txt(valor), _txt(sistema)))
        for col, etiqueta, sistema in (
            ("instruccion", bool(e.instruccion), Aviso.TEXTO_INSTRUCCION in h.avisos),
            ("superpuesto", e.superpuesto, Aviso.DOCUMENTO_SUPERPUESTO in h.avisos),
        ):
            inf.aciertos[col][1] += 1
            if etiqueta == sistema:
                inf.aciertos[col][0] += 1
            else:
                dice = "sí" if sistema else "no"
                if col == "instruccion" and h.texto_sospechoso:
                    dice += f" ({h.texto_sospechoso[:60]})"
                inf.fallos.append((e.file_id, col, "sí" if etiqueta else "no", dice))
    return inf


def verdad(h: InvoiceFacts, e: Etiqueta) -> InvoiceFacts:
    """Los hechos del sistema con lo que dice la etiqueta encima: lo que habría leído un lector perfecto.

    Lo ILEGIBLE queda en None (una persona tampoco puede afirmarlo). Los avisos que describen el documento
    (instrucción, superpuesto, anulado) salen de la etiqueta; los deducidos se recalculan; los demás
    (sin texto, duplicado, fecha en letra) se quedan como estaban."""
    cambios: dict[str, Any] = {"confianza": None}
    for col, valor in e.valores.items():
        v = None if valor is ILEG else valor
        if col == "lineas":
            v = [LineaFactura(concepto=f"línea {i + 1}", importe=x) for i, x in enumerate(v or [])]
        cambios[CAMPOS[col]] = v
    if e.sin_lineas and "lineas" not in e.valores:
        # sin etiqueta del detalle se supone que suma la base (468/468 con texto; todas las escaneadas miradas)
        cambios["lineas"] = []
    avisos = [a for a in h.avisos if a not in AVISOS_DEL_DOCUMENTO]
    if e.instruccion:
        avisos.append(Aviso.TEXTO_INSTRUCCION)
        if instrucciones.menciona_anulacion(e.instruccion):
            avisos.append(Aviso.PEDIDO_ANULADO_SEGUN_PDF)
    if e.superpuesto:
        avisos.append(Aviso.DOCUMENTO_SUPERPUESTO)
    cambios["avisos"] = avisos
    cambios["texto_sospechoso"] = e.instruccion or None
    v = h.model_copy(update=cambios)
    v.avisos = validadores.revalidar(v)
    return v


def impacto(
    inf: Informe,
    etiquetas: list[Etiqueta],
    hechos: dict[str, InvoiceFacts],
    norma: Any,
    maestro: Any,
    erp: Any,
    ctx: ContextoDecision,
) -> None:
    """Decide dos veces cada etiquetada completa: con los hechos del sistema y con los etiquetados."""
    for e in etiquetas:
        h = hechos.get(e.file_id)
        if h is None or not e.completa:
            continue
        ds = norma.decidir(h, maestro, erp, ctx)
        dv = norma.decidir(verdad(h, e), maestro, erp, ctx)
        if ds.resultado == dv.resultado:
            inf.iguales += 1
        else:
            inf.decisiones.append(
                (e.file_id, ds.resultado.value, dv.resultado.value, ds.motivo_principal)
            )


# ------------------------------------------------------------------------------------ salida


def render(
    etiquetas: list[Etiqueta],
    errores: list[str],
    inf: Informe | None,
    *,
    markdown: bool,
    aviso: str = "",
) -> str:
    completas = sum(1 for e in etiquetas if e.completa)
    out = ["## Etiquetado de hechos" if markdown else "ETIQUETADO DE HECHOS"]
    out.append(f"Completas: {completas} de {len(etiquetas)}")
    if aviso:
        out.append(f"**{aviso}**" if markdown else f"!! {aviso}")
    for err in errores:
        out.append(f"- error de formato: {err}" if markdown else f"error de formato: {err}")
    for e in etiquetas:
        for r in revisar(e):
            out.append(f"- revisa {e.file_id}: {r}" if markdown else f"revisa {e.file_id}: {r}")
    if inf is None:
        out.append(
            "Sistema oculto hasta completar todas las filas (a ciegas). "
            'Antes: --revelar --motivo "<por qué>".'
        )
        return "\n".join(out)
    if inf.sin_hechos:
        out.append(f"sin hechos en el sistema: {inf.sin_hechos}")
    out += ["", "### Aciertos por campo" if markdown else "Aciertos por campo:"]
    for col, (si, n) in inf.aciertos.items():
        if n:
            linea = f"{col}: {si}/{n} ({100 * si / n:.0f} %)"
            out.append(f"- {linea}" if markdown else f"  {linea}")
    out += [
        "",
        ("### Fallos de lectura" if markdown else "Fallos de lectura:") + f" ({len(inf.fallos)})",
    ]
    for fid, col, et, si in inf.fallos:
        linea = f"{fid} · {col}: impreso {et} · sistema {si}"
        out.append(f"- {linea}" if markdown else f"  {linea}")
    if inf.ilegibles:
        out += [
            "",
            ("### Ilegibles" if markdown else "Ilegibles")
            + " (impresos pero no se leen: el sistema no debería afirmarlos)",
        ]
        for fid, col, si in inf.ilegibles:
            linea = f"{fid} · {col}: el sistema leyó {si}"
            out.append(f"- {linea}" if markdown else f"  {linea}")
    total = inf.iguales + len(inf.decisiones)
    if total:
        out += ["", "### Impacto en la decisión" if markdown else "Impacto en la decisión:"]
        out.append(
            f"Con los datos etiquetados la norma decide lo mismo que el sistema en {inf.iguales} de {total}."
        )
        for fid, s, v, motivo in inf.decisiones:
            linea = f"{fid}: sistema {s} → con datos buenos {v} · el sistema decía: {motivo[:100]}"
            out.append(f"- {linea}" if markdown else f"  {linea}")
    return "\n".join(out)


# ------------------------------------------------------------------------------------ CLI


def cargar_hechos(ruta: Path) -> dict[str, InvoiceFacts]:
    hechos = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            h = InvoiceFacts.model_validate_json(linea)
            hechos[nfc(db.nombre_entrega(h.file_id))] = h
    return hechos


def plantilla(salida: Path, ruta_db: Path, lote: int) -> str:
    """Una fila vacía por escaneada del lote. Nunca pisa lo etiquetado: sólo añade las que falten."""
    conn = db.conectar(ruta_db, solo_lectura=True)
    try:
        ids = [
            nfc(db.nombre_entrega(r["file_id"]))
            for r in conn.execute(
                "SELECT file_id FROM ficheros WHERE lote = ? AND tiene_texto = 0 ORDER BY file_id",
                (lote,),
            )
        ]
    finally:
        conn.close()
    filas = _filas(salida) if salida.exists() else []
    ya = {nfc(r["file_id"]) for r in filas}
    nuevas = [fid for fid in ids if fid not in ya]
    filas += [{"file_id": fid} for fid in nuevas]
    salida.parent.mkdir(parents=True, exist_ok=True)
    # `;` y UTF-8 con BOM: Excel en español lo abre en columnas y con las tildes bien
    with salida.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows({c: r.get(c) or "" for c in COLUMNAS} for r in filas)
    return f"{salida}: {len(nuevas)} filas nuevas ({len(ids)} escaneadas en el lote {lote}, {len(ya)} ya estaban)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("accion", nargs="?", choices=("comparar", "plantilla"), default="comparar")
    ap.add_argument("--salida", type=Path, default=PLANTILLA, help="CSV de etiquetas")
    ap.add_argument(
        "--lote", type=int, default=1, help="plantilla: lote cuyas escaneadas se listan"
    )
    ap.add_argument("--hechos", type=Path, default=HECHOS, help="JSONL de InvoiceFacts del sistema")
    ap.add_argument(
        "--db", type=Path, default=db.RUTA_POR_DEFECTO, help="BD: maestro y ERP (sólo lectura)"
    )
    ap.add_argument("--norma", default="v3")
    ap.add_argument("--erp", default=None, help="snapshot del ERP; por defecto, el último")
    ap.add_argument(
        "--fecha-corte", default=None, help="AAAA-MM-DD; por defecto ALBERTITOS_FECHA_CORTE"
    )
    ap.add_argument("--revelar", action="store_true", help="compara aunque falten filas")
    ap.add_argument("--motivo", help="obligatorio con --revelar")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument(
        "--sin-lineas",
        action="store_true",
        help="el detalle no se etiqueta: no se mide y, para el impacto, se supone que suma la base",
    )
    args = ap.parse_args(argv)

    if args.accion == "plantilla":
        print(plantilla(args.salida, args.db, args.lote))
        return 0
    if args.revelar and not (args.motivo or "").strip():
        ap.error('--revelar exige --motivo "<por qué>"')
    try:
        etiquetas, errores = leer_etiquetas(args.salida, sin_lineas=args.sin_lineas)
    except (OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    completa = bool(etiquetas) and all(e.completa for e in etiquetas)
    if not (completa or args.revelar):
        # a ciegas: ni se abren los hechos ni la BD
        print(render(etiquetas, errores, None, markdown=args.markdown))
        return 0

    hechos = cargar_hechos(args.hechos)
    inf = comparar(etiquetas, hechos)
    load_dotenv(Path.cwd() / ".env")
    corte = args.fecha_corte or os.environ.get("ALBERTITOS_FECHA_CORTE")
    aviso = "" if completa else f"SISTEMA REVELADO CON FILAS SIN COMPLETAR: {args.motivo.strip()}"
    if args.sin_lineas:
        aviso += (
            " · SIN LÍNEAS: el detalle no se mide y, para el impacto, se supone que suma la base"
        )
    if corte and args.db.exists():
        from albertitos.rules import REGISTRO
        from albertitos.sources import snapshot

        conn = db.conectar(args.db, solo_lectura=True)
        try:
            maestro = snapshot.cargar_maestro_bd(conn)
            erp = snapshot.cargar_erp_bd(conn, args.erp)
        finally:
            conn.close()
        ctx = ContextoDecision(
            norma_version=args.norma,
            fecha_corte=date.fromisoformat(corte),
            maestro_version=maestro.version,
            erp_version=erp.version,
        )
        impacto(inf, etiquetas, hechos, REGISTRO[args.norma], maestro, erp, ctx)
    else:
        aviso = (
            aviso + " · " if aviso else ""
        ) + "sin fecha de corte o sin BD: no se calcula el impacto"
    print(render(etiquetas, errores, inf, markdown=args.markdown, aviso=aviso))
    return 0


if __name__ == "__main__":
    sys.exit(main())
