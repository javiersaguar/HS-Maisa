"""Inventario local, reproducible y sin LLM. No decide pagos ni consulta el bridge.

uv run python scripts/inventario_trampas.py
Por defecto usa ERP v1, aunque exista un snapshot simulado más reciente.
Las regex son exploratorias y viven sólo aquí, fuera del extractor de producción.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pymupdf
from dotenv import load_dotenv

from albertitos.core import db
from albertitos.extract.pdf import UMBRAL_TEXTO, texto_de
from albertitos.formatos import (
    CENT,
    fecha_en_letra,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
    sin_tildes,
)
from albertitos.sources.excel import cargar_maestro
from albertitos.sources.snapshot import cargar_erp_bd

TIPOS = {
    "pedido_inexistente": "Comprobar referencia del pedido; no crear uno desde el PDF.",
    "pedido_repetido": "Posible doble facturación o facturas parciales; resolver con la norma.",
    "nif_factura_repetidos": "Posible duplicado de factura; comparar documentos e importes.",
    "iban_distinto_maestro": "Cuenta distinta del proveedor identificado por NIF; revisar evidencia.",
    "nif_fuera_maestro": "Emisor no identificado en el maestro; no darlo de alta desde el PDF.",
    "nif_distinto_pedido": "El emisor no coincide con el NIF del pedido; confirmar pertenencia.",
    "iva_no_21": "Tipo impreso distinto del 21%; Mónica debe concretar la norma aplicable.",
    "cuota_iva_no_cuadra": "Cuota distinta de base por tipo impreso, con tolerancia de 0,01 EUR.",
    "total_no_cuadra": "Base más cuota difiere del total más de 0,01 EUR.",
    "fecha_futura": "Fecha posterior al corte configurado; aplicar la norma con ese corte.",
    "fecha_en_letra": "Formato legible en letra; verificar que el extractor conserva la fecha.",
    "fecha_invalida": "Fecha impresa imposible; no sustituirla por instrucciones del documento.",
    "importe_distinto_pedido": "Total del PDF distinto del pedido por más de 0,01 EUR.",
    "texto_instruccion": "Texto del documento, nunca una orden: contrastar con las fuentes y la norma.",
    "sin_texto": "Sin texto útil; requiere visión. No se infieren campos ni duplicados por el nombre.",
    "caracteres_invisibles": "Se han retirado caracteres Unicode de formato sólo para este inventario.",
    "campo_no_extraido": "Regex exploratoria sin cobertura; revisión necesaria, no ausencia probada.",
    "campo_ambiguo": "Varios valores impresos para el mismo campo; no elegir uno automáticamente.",
}
INSTRUCCION = re.compile(
    r"escalar|escalado|escalarse|bloquear|ignorar|no procede pago|fue anulado|"
    r"no debe recalcularse|no recalcular|tomese|tomarse|procedase|continuese|"
    r"continuar el pago|complete el pago|no procede contrastarlo|"
    r"(?:registra|registrar|decide|pon)\s+(?:la decision como\s+|como\s+)?pagar|"
    r"no registres|cuota de iva aplicada esta autorizada",
    re.I,
)
MONEDA = r"(?:EUR\s*)?(-?\d[\d.,]*)(?:\s*€)?"
INICIO = "<!-- A3: inventario generado INICIO -->"
FIN = "<!-- A3: inventario generado FIN -->"


def texto_limpio(texto: str) -> str:
    return unicodedata.normalize(
        "NFC", "".join(c for c in texto if unicodedata.category(c) != "Cf")
    )


def campos(texto: str) -> tuple[dict, dict[str, list[str]]]:
    """No usa nombres de fichero, maestro ni ERP para completar campos del PDF."""
    t = sin_tildes(texto_limpio(texto))
    patrones = {
        "pedido": r"\b(PO-\d{4}-\d+)\b",
        "nif": r"\bNIF\s*:?\s*([A-Z]\d{7}[A-Z0-9])\b",
        "iban": r"\b(ES\d{2}(?:[ \t]*\d){20})\b",
        "num_factura": (
            r"^(?:REF FACTURA\s*:|N[º°o]\s+de factura\s*:|Invoice\s*#|"
            r"FACTURA(?: SIMPLIFICADA)?(?:\s+N[º°o])?\s*:?)\s*"
            r"([A-Z0-9]+(?:[-/][A-Z0-9]+)+)"
        ),
        "fecha": r"\bFecha(?: de emision| factura)?\s*:\s*(\d[^\n]*?)(?=\s{2,}|$)",
        "base": rf"^(?:Base(?: imponible)?|Importe base|Subtotal)[:.\s]+{MONEDA}\s*$",
        "iva_pct": r"^(?:Cuota\s+)?I\.?V\.?A\.?\s*\((\d+(?:[.,]\d+)?)\s*%\)",
        "iva": rf"^(?:Cuota\s+)?I\.?V\.?A\.?\s*\([\d.,]+\s*%\)[:.\s]+{MONEDA}\s*$",
        "total": rf"^(?:Importe total|Total(?: factura| a pagar)?)[:.\s]+{MONEDA}\s*$",
    }
    valores = {}
    ambiguos = {}
    for campo, patron in patrones.items():
        encontrados = sorted(set(re.findall(patron, t, re.I | re.M)))
        if len(encontrados) > 1:
            ambiguos[campo] = encontrados
        crudo = encontrados[0] if len(encontrados) == 1 else None
        if campo in {"base", "iva_pct", "iva", "total"}:
            valores[campo] = parse_importe_es(crudo)
        elif campo == "fecha":
            valores["fecha_cruda"] = crudo
            valores[campo] = parse_fecha_es(crudo)
        else:
            normalizar = {
                "iban": normalizar_iban,
                "nif": normalizar_nif,
                "pedido": normalizar_pedido,
            }.get(campo, str.upper)
            valores[campo] = normalizar(crudo) if crudo else None
    return valores, ambiguos


def tabla(cabecera, filas) -> str:
    def celda(v):
        return str(v).replace("|", "\\|").replace("\n", " ")

    filas = list(filas)
    return "\n".join(
        ["| " + " | ".join(cabecera) + " |", "| " + " | ".join(["---"] * len(cabecera)) + " |"]
        + ["| " + " | ".join(map(celda, f)) + " |" for f in filas]
    )


def imagenes_pdf(ruta: Path) -> str:
    imagenes = []
    with pymupdf.open(ruta) as doc:
        for numero, pagina in enumerate(doc, 1):
            for im in pagina.get_image_info():
                rect = pymupdf.Rect(im["bbox"])
                # DPI efectivo sobre la página, no sólo la etiqueta del fichero embebido.
                dx = round(im["width"] * 72 / rect.width, 1) if rect.width else "?"
                dy = round(im["height"] * 72 / rect.height, 1) if rect.height else "?"
                imagenes.append(
                    f"p{numero}: {im['width']}x{im['height']} px; {dx}x{dy} dpi efectivos"
                )
        return f"{ruta.stat().st_size} bytes; {len(doc)} páginas; " + (
            "; ".join(imagenes) or "sin imagen raster identificada"
        )


def inventariar(caja: Path, maestro, erp, corte: date):
    filas = []
    facturas = {}
    cobertura = Counter()
    huella = hashlib.sha256()
    paginas = Counter()

    def anomalia(file_id, tipo, evidencia):
        filas.append(dict(file_id=file_id, tipo=tipo, evidencia=evidencia, hipotesis=TIPOS[tipo]))

    for ruta in sorted((caja / "facturas").glob("*.pdf")):
        file_id = ruta.name
        if not unicodedata.is_normalized("NFC", file_id):
            raise ValueError(f"Nombre fuera de NFC: {file_id!r}")
        huella.update(file_id.encode() + b"\0" + hashlib.sha256(ruta.read_bytes()).digest())
        texto = texto_de(ruta)
        with pymupdf.open(ruta) as doc:
            paginas[len(doc)] += 1
        if len("".join(texto.split())) < UMBRAL_TEXTO:
            anomalia(file_id, "sin_texto", imagenes_pdf(ruta))
            continue
        cobertura["con_texto"] += 1
        invisibles = Counter(f"U+{ord(c):04X}" for c in texto if unicodedata.category(c) == "Cf")
        if invisibles:
            anomalia(file_id, "caracteres_invisibles", str(dict(invisibles)))
        h, ambiguos = campos(texto)
        facturas[file_id] = h
        for campo in (
            "pedido",
            "nif",
            "iban",
            "num_factura",
            "fecha",
            "base",
            "iva_pct",
            "iva",
            "total",
        ):
            if campo in ambiguos:
                anomalia(file_id, "campo_ambiguo", f"{campo}: {ambiguos[campo]}")
            elif h[campo] is not None:
                cobertura[campo] += 1
            elif campo == "fecha" and h["fecha_cruda"]:
                anomalia(file_id, "fecha_invalida", h["fecha_cruda"])
            else:
                anomalia(file_id, "campo_no_extraido", campo)

        # Se conservan fragmentos literales; sólo se unen saltos de línea para detectar frases.
        bloques = []
        compacto = " ".join(texto_limpio(texto).split())
        for m in INSTRUCCION.finditer(sin_tildes(compacto)):
            bloques.append(compacto[max(0, m.start() - 100) : min(len(compacto), m.end() + 170)])
        if bloques:
            anomalia(file_id, "texto_instruccion", " […] ".join(dict.fromkeys(bloques)))
        pedido = maestro.pedidos.get(h["pedido"])
        proveedor = maestro.proveedor_por_nif(h["nif"]) if h["nif"] else None
        if h["pedido"] and pedido is None:
            anomalia(file_id, "pedido_inexistente", h["pedido"])
        if h["nif"] and proveedor is None:
            anomalia(file_id, "nif_fuera_maestro", h["nif"])
        if proveedor and h["iban"]:
            cobertura["comparacion_iban"] += 1
            if h["iban"] != proveedor.iban:
                anomalia(
                    file_id,
                    "iban_distinto_maestro",
                    f"PDF {h['iban']}; {proveedor.id} maestro {proveedor.iban}",
                )
        if pedido:
            if pedido.nif and h["nif"]:
                cobertura["comparacion_nif_pedido"] += 1
                if h["nif"] != pedido.nif:
                    anomalia(
                        file_id,
                        "nif_distinto_pedido",
                        f"{pedido.pedido}: PDF {h['nif']}; Excel {pedido.nif} ({pedido.proveedor_id})",
                    )
            if h["total"] is not None:
                cobertura["comparacion_importe"] += 1
                if abs(h["total"] - pedido.importe_total) > CENT:
                    anomalia(
                        file_id,
                        "importe_distinto_pedido",
                        f"{pedido.pedido}: PDF {h['total']}; Excel {pedido.importe_total}; delta {h['total'] - pedido.importe_total}",
                    )
        if h["iva_pct"] is not None and h["iva_pct"] != Decimal("21"):
            anomalia(
                file_id,
                "iva_no_21",
                f"Tipo impreso {h['iva_pct']}%; base {h['base']}; cuota {h['iva']}",
            )
        if all(h[c] is not None for c in ("base", "iva_pct", "iva")):
            cuota = (h["base"] * h["iva_pct"] / 100).quantize(CENT, rounding=ROUND_HALF_UP)
            if abs(cuota - h["iva"]) > CENT:
                anomalia(
                    file_id,
                    "cuota_iva_no_cuadra",
                    f"Base {h['base']} x {h['iva_pct']}% = {cuota}; cuota impresa {h['iva']}",
                )
        if all(h[c] is not None for c in ("base", "iva", "total")):
            if abs(h["base"] + h["iva"] - h["total"]) > CENT:
                anomalia(
                    file_id,
                    "total_no_cuadra",
                    f"Base {h['base']} + IVA {h['iva']} = {h['base'] + h['iva']}; total {h['total']}",
                )
        if h["fecha"] and h["fecha"] > corte:
            anomalia(file_id, "fecha_futura", f"Fecha {h['fecha']}; corte {corte}")
        if h["fecha_cruda"] and fecha_en_letra(h["fecha_cruda"]):
            anomalia(file_id, "fecha_en_letra", f"{h['fecha_cruda']} → {h['fecha']}")

    for tipo, claves in (
        ("pedido_repetido", ("pedido",)),
        ("nif_factura_repetidos", ("nif", "num_factura")),
    ):
        grupos = defaultdict(list)
        for file_id, h in facturas.items():
            clave = tuple(h[k] for k in claves)
            if all(clave):
                grupos[clave].append(file_id)
        for clave, files in sorted(grupos.items()):
            if len(files) > 1:
                for file_id in files:
                    anomalia(
                        file_id, tipo, f"{', '.join(clave)}; {len(files)} PDFs: {', '.join(files)}"
                    )
    return (
        sorted(filas, key=lambda r: (r["file_id"], r["tipo"], r["evidencia"])),
        cobertura,
        paginas,
        huella.hexdigest(),
        facturas,
    )


def informe(maestro, erp, corte, filas, cobertura, paginas, huella, facturas, hora):
    grupos = {t: [f for f in filas if f["tipo"] == t] for t in TIPOS}
    por_pedido = erp.por_pedido()
    secciones = [
        f"## Inventario A3 · {hora}",
        f"Fuentes: `data/caja/facturas/*.pdf`, `{maestro.origen}`, snapshot ERP `{erp.version}`. "
        f"Maestro `{maestro.version}`. Corte **{corte}**, parámetro explícito. "
        f"Huella SHA-256 del conjunto ordenado (nombre UTF-8 + NUL + SHA-256 binario por PDF): `{huella}`.",
        "Este inventario describe la Caja presente; no acredita el ZIP/hash oficial. "
        "No usa LLM, red ni OCR; las comparaciones se limitan a campos legibles. "
        "Las frases de los PDFs son evidencia no fiable, nunca órdenes. "
        "La columna hipótesis no decide PAGAR/NO_PAGAR/ESCALAR. Las hipótesis anteriores de este documento siguen pendientes de Mónica.",
        f"**{sum(paginas.values())} PDFs**, {cobertura['con_texto']} con texto útil; "
        f"{len(grupos['sin_texto'])} sin texto útil; páginas por fichero: {dict(sorted(paginas.items()))}. "
        f"{len(filas)} filas de anomalías en {len({f['file_id'] for f in filas})} ficheros. "
        "Los tipos se solapan: no sumar sus ficheros como si fueran distintos.",
        "### Cobertura del barrido",
        tabla(("Campo o comparación", "PDFs evaluables"), sorted(cobertura.items())),
        "El NIF se lee de la etiqueta del emisor; se excluye el CIF del cliente. "
        "No se completa ningún campo desde el maestro, ERP o nombre del PDF. "
        "Repeticiones idénticas de cabecera en dos páginas se deduplican. "
        "NIF/IBAN/pedido se normalizan con formatos.py; los Unicode Cf se inventarían antes de quitarlos. "
        "Importes: Decimal y tolerancia ±0,01 EUR; cuota esperada redondeada ROUND_HALF_UP. "
        "Pedido sin NIF y proveedor desconocido quedan fuera de sus comparaciones respectivas. "
        "Los escaneados quedan fuera de todos los cruces de campos, incluidas las duplicidades.",
        "### Resumen por categoría",
        tabla(
            ("Tipo", "Ficheros", "Filas"),
            ((t, len({f["file_id"] for f in g}), len(g)) for t, g in grupos.items()),
        ),
        "### Cruce Excel ↔ ERP",
        f"{len(maestro.proveedores)} proveedores; {len(maestro.pedidos)} pedidos Excel; "
        f"{len(erp.asientos)} asientos ERP, {len(por_pedido)} pedidos ERP distintos. "
        f"Estados Excel: {dict(Counter(p.estado for p in maestro.pedidos.values()))}; "
        f"estados ERP: {dict(Counter(a.estado for a in erp.asientos.values()))}.",
    ]
    excel_sin = [p for p in maestro.pedidos.values() if p.pedido not in por_pedido]
    erp_sin = [a for a in erp.asientos.values() if a.pedido not in maestro.pedidos]
    cruces = [
        (a, maestro.pedidos[a.pedido]) for a in erp.asientos.values() if a.pedido in maestro.pedidos
    ]
    tablas = [
        (
            "Pedidos Excel sin asiento ERP",
            ("Pedido", "Proveedor", "NIF", "Importe", "Estado"),
            [
                (p.pedido, p.proveedor_id, p.nif or "SIN NIF", p.importe_total, p.estado)
                for p in excel_sin
            ],
        ),
        (
            "Asientos ERP sin pedido Excel",
            ("Asiento", "Pedido", "Proveedor", "NIF", "Importe", "Estado"),
            [
                (a.asiento_id, a.pedido, a.proveedor_id, a.nif, a.importe_esperado, a.estado)
                for a in erp_sin
            ],
        ),
        (
            "Importe Excel distinto del ERP",
            ("Pedido", "Asiento", "Excel", "ERP", "Delta ERP − Excel"),
            [
                (
                    p.pedido,
                    a.asiento_id,
                    p.importe_total,
                    a.importe_esperado,
                    a.importe_esperado - p.importe_total,
                )
                for a, p in cruces
                if abs(a.importe_esperado - p.importe_total) > CENT
            ],
        ),
        (
            "NIF/proveedor Excel distintos del ERP",
            ("Pedido", "Asiento", "Proveedor Excel", "Proveedor ERP", "NIF Excel", "NIF ERP"),
            [
                (
                    p.pedido,
                    a.asiento_id,
                    p.proveedor_id,
                    a.proveedor_id,
                    p.nif or "SIN NIF (no comparable)",
                    a.nif,
                )
                for a, p in cruces
                if a.proveedor_id != p.proveedor_id or (p.nif and a.nif != p.nif)
            ],
        ),
        (
            "Asientos PAGADA",
            ("Asiento", "Pedido", "Proveedor", "NIF", "Importe", "PDFs con texto"),
            [
                (
                    a.asiento_id,
                    a.pedido,
                    f"{a.proveedor_id} {maestro.proveedores[a.proveedor_id].razon_social}"
                    if a.proveedor_id in maestro.proveedores
                    else a.proveedor_id,
                    a.nif,
                    a.importe_esperado,
                    ", ".join(f for f, h in facturas.items() if h["pedido"] == a.pedido)
                    or "ninguno identificado",
                )
                for a in erp.asientos.values()
                if a.estado == "PAGADA"
            ],
        ),
        (
            "Pedidos sin NIF",
            ("Pedido", "Proveedor", "NIF del proveedor (no imputado)", "Importe", "ERP"),
            [
                (
                    p.pedido,
                    p.proveedor_id,
                    maestro.proveedores[p.proveedor_id].nif
                    if p.proveedor_id in maestro.proveedores
                    else "?",
                    p.importe_total,
                    ", ".join(a.asiento_id for a in por_pedido.get(p.pedido, [])) or "sin asiento",
                )
                for p in maestro.pedidos.values()
                if not p.nif
            ],
        ),
        (
            "Pedidos con estado distinto de ABIERTO",
            ("Pedido", "Proveedor", "Estado", "Importe"),
            [
                (p.pedido, p.proveedor_id, p.estado, p.importe_total)
                for p in maestro.pedidos.values()
                if p.estado != "ABIERTO"
            ],
        ),
        (
            "Asientos múltiples por pedido",
            ("Pedido", "Asientos"),
            [
                (p, ", ".join(a.asiento_id for a in aa))
                for p, aa in por_pedido.items()
                if len(aa) > 1
            ],
        ),
    ]
    for titulo, cabecera, datos in tablas:
        secciones += [
            f"#### {titulo} · {len(datos)}",
            tabla(cabecera, sorted(datos)) if datos else "0 casos en los datos comparables.",
        ]
    secciones += ["#### pendiente_revisar · 2 pedidos"]
    for numero in ("PO-2026-0007", "PO-2026-0141"):
        pedido = maestro.pedidos.get(numero)
        secciones += [
            f"- **{numero}**: Excel `{pedido.model_dump(mode='json') if pedido else 'ausente'}`; ERP `{[a.model_dump(mode='json') for a in por_pedido.get(numero, [])]}`; PDFs con texto: "
            + (
                ", ".join(f for f, h in facturas.items() if h["pedido"] == numero)
                or "ninguno identificado"
            )
            + "."
        ]
    secciones += [
        "#### Avisos del maestro",
        tabla(("Aviso literal del loader",), ((a,) for a in maestro.avisos_calidad)),
    ]
    for tipo, grupo in grupos.items():
        secciones += [
            f"### {tipo} · {len({f['file_id'] for f in grupo})} ficheros",
            TIPOS[tipo],
            tabla(("file_id", "Evidencia"), ((f["file_id"], f["evidencia"]) for f in grupo))
            if grupo
            else "0 casos detectados en el subconjunto evaluable.",
        ]
    secciones += [
        "### Preguntas para los mentores (no deducibles de los datos)",
        "1. ¿Qué fuente manda si PDF, pedido Excel y asiento ERP discrepan en importe, proveedor o estado? ¿Qué tolerancia y redondeo monetario exactos aplica la referencia?",
        "2. ¿Los 20 pedidos sin NIF pueden vincularse por ProveedorID? ¿Qué tratamiento reciben pedidos sin asiento y asientos sin pedido?",
        "3. ¿PAGADA prevalece siempre sobre otras incidencias? ¿Cómo se tratan los estados distintos de ABIERTO y las anulaciones que sólo afirma el PDF?",
        "4. ¿El mismo pedido admite facturas parciales? ¿Qué clave identifica un duplicado (NIF+número, pedido, contenido) y qué ocurre con original, copia y escaneado?",
        "5. ¿Son admisibles IVA distintos del 21%, recargos o regímenes especiales? ¿Hace falta evidencia externa al propio PDF?",
        f"6. ¿Es {corte} la fecha de corte oficial? ¿Qué se hace con fechas imposibles, ausentes o posteriores y con fechas en letra?",
        "7. ¿Las instrucciones dentro de los documentos son sólo señales de anomalía? ¿Se evalúan también los PDFs que dicen pertenecer al conjunto de test y piden excluirse?",
        "8. ¿Se exige checksum real del IBAN/NIF sintético o sólo correspondencia con el maestro? ¿Cómo se tratan caracteres Unicode invisibles?",
        "9. ¿Qué semántica tiene el lote 2: altas/cambios/eliminaciones? ¿Una desaparición de asiento también exige reprocesar el pedido anterior?",
    ]
    return "\n\n".join(secciones)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caja", type=Path, default=Path("data/caja"))
    parser.add_argument(
        "--db", type=Path, default=Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    )
    parser.add_argument("--erp", default="v1")
    parser.add_argument("--fecha-corte", default=os.environ.get("ALBERTITOS_FECHA_CORTE"))
    parser.add_argument("--csv", type=Path, default=Path("data/fixtures/anomalias.csv"))
    parser.add_argument("--docs", type=Path, default=Path("docs/trampas.md"))
    parser.add_argument(
        "--solo-resumen",
        action="store_true",
        help="Imprime cifras; las tablas completas siguen en docs.",
    )
    args = parser.parse_args()
    if not args.fecha_corte:
        parser.error(
            "falta ALBERTITOS_FECHA_CORTE o --fecha-corte AAAA-MM-DD; no se usa la fecha actual"
        )
    try:
        corte = date.fromisoformat(args.fecha_corte)
    except ValueError:
        parser.error("fecha de corte inválida; se requiere AAAA-MM-DD")
    inicio = time.perf_counter()
    maestro = cargar_maestro(args.caja / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    with closing(db.conectar(args.db, solo_lectura=True)) as conn:
        erp = cargar_erp_bd(conn, args.erp)
    filas, cobertura, paginas, huella, facturas = inventariar(args.caja, maestro, erp, corte)
    if not paginas:
        parser.error("no hay PDFs; no se sobrescribe el inventario")
    hora = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y %H:%M %Z")
    reporte = informe(maestro, erp, corte, filas, cobertura, paginas, huella, facturas, hora)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8", newline="") as salida:
        writer = csv.DictWriter(salida, fieldnames=("file_id", "tipo", "evidencia", "hipotesis"))
        writer.writeheader()
        writer.writerows(filas)
    anterior = (
        args.docs.read_text(encoding="utf-8") if args.docs.exists() else "# Trampas de la Caja\n"
    )
    bloque = INICIO + "\n\n" + reporte + "\n\n" + FIN
    if INICIO in anterior and FIN in anterior:
        antes, resto = anterior.split(INICIO, 1)
        _, despues = resto.split(FIN, 1)
        contenido = antes + bloque + despues
    else:
        contenido = anterior.rstrip() + "\n\n" + bloque + "\n"
    args.docs.parent.mkdir(parents=True, exist_ok=True)
    args.docs.write_text(contenido, encoding="utf-8")
    if args.solo_resumen:
        print(
            tabla(
                ("Tipo", "Ficheros", "Filas"),
                (
                    (
                        t,
                        len({f["file_id"] for f in filas if f["tipo"] == t}),
                        sum(f["tipo"] == t for f in filas),
                    )
                    for t in TIPOS
                ),
            )
        )
        print("Cobertura:", dict(cobertura))
    else:
        print(reporte)
    print(
        f"{len(filas)} filas; {len({f['file_id'] for f in filas})} ficheros; {sum(paginas.values())} PDFs; {time.perf_counter() - inicio:.2f} s; ERP {erp.version}; corte {corte}"
    )
    print(f"Escritos {args.csv} y {args.docs}")


if __name__ == "__main__":
    main()
