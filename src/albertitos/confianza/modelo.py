"""La puntuación de confianza: cuánta seguridad tenemos de que la CLASIFICACIÓN de una factura es la correcta.

No es la probabilidad de pagar: un ESCALAR por una orden inyectada evidente tiene confianza alta. Y no es una
probabilidad calibrada: es una puntuación ordinal 0-100, determinista y explicable, que parte de 100 y resta una
penalización por cada duda con nombre. Cada peso está en `PESOS`, con la frase que lo justifica (ADR-0014).

La idea que ordena los pesos: una duda sólo pesa en la medida en que la decisión depende de ella.
- Un PAGAR necesita que todo esté bien, pero el maestro y el ERP ya han corroborado al céntimo lo que se leyó:
  las dudas de lectura cuentan a la mitad (lo que queda es lo que la lectura pudo no ver).
- Un ESCALAR o un NO_PAGAR por una causa clara (una orden en el PDF, un IVA mal hecho, el ERP la da por PAGADA)
  aguanta aunque la lectura sea mejorable: también a la mitad.
- Un ESCALAR sólo porque no se leyó con seguridad no dice nada de la factura: si el original está limpio, lo
  correcto sería PAGAR. Ésa es la duda grande (`decision.escala_por_lectura`).
- Si la clasificación depende de una política de empresa aún no fijada (mapa de I2), también es una duda.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from albertitos.confianza.datos import Expediente
from albertitos.formatos import normalizar_iban, normalizar_nif, normalizar_pedido, parse_importe_es

VERSION = "confianza-1"
UMBRAL_ALTA = 80
UMBRAL_MEDIA = 50
TOPE_CONTINGENCIA = 25  # ADR-0009: sin hechos validados, confianza baja por definición
TOPE_POLITICA = 30  # varias preguntas abiertas a la vez no suman sin límite: la duda es la misma
# Una diferencia de importe de hasta 1 € puede ser un redondeo o una mala lectura.
MARGEN_CERCA = Decimal("1.00")
CAMPOS_CLAVE = ("nif_emisor", "iban", "pedido", "total")


@dataclass(frozen=True)
class Peso:
    fuente: str
    puntos: int
    por_que: str  # una línea: la justificación (va al ADR y a /confianza/fichero)


#: La tabla de pesos. Penalizaciones sobre 100.
PESOS: dict[str, Peso] = {
    # --- el PDF y su lectura
    "pdf.plantilla_sin_contraste": Peso(
        "pdf",
        5,
        "La plantilla es determinista, pero sin la lectura del LLM al lado no se descarta un error del parser.",
    ),
    "pdf.contraste_difiere": Peso(
        "pdf",
        30,
        "Dos extractores independientes (plantilla y LLM) leen distinto un campo que decide.",
    ),
    "pdf.llm_texto": Peso(
        "pdf",
        10,
        "Una sola lectura, del LLM, sobre la capa de texto: no hay segundo extractor que la contraste.",
    ),
    "pdf.vision": Peso(
        "pdf",
        15,
        "Escaneada: sólo hay imagen y la leyó la visión, la vía con más errores (17 desacuerdos en 29).",
    ),
    "pdf.una_lectura": Peso(
        "pdf", 10, "De la imagen hay una sola lectura: nada con qué contrastarla."
    ),
    "pdf.lecturas_discrepan": Peso(
        "pdf",
        20,
        "Las lecturas independientes de la imagen no coinciden en un campo que decide.",
    ),
    "pdf.reconciliada": Peso(
        "pdf",
        30,
        "Las lecturas no coincidían y se eligió la que cuadra con el maestro (confianza 0,6, ADR-0003/0011).",
    ),
    "pdf.discrepancia_extractores": Peso(
        "pdf", 30, "La extracción marcó que sus lecturas no coinciden y no pudo reconciliarlas."
    ),
    "pdf.superpuesto": Peso(
        "pdf", 30, "Hay otro documento encima o transparentándose (ADR-0010): la lectura es frágil."
    ),
    "pdf.parcial": Peso(
        "pdf",
        15,
        "Faltan campos o hay un importe ambiguo: la norma decide con menos datos (15 por aviso, hasta 30).",
    ),
    "pdf.respaldo": Peso(
        "pdf", 5, "La leyó el modelo de respaldo, no el principal: menos historia medida."
    ),
    # --- el maestro y el ERP
    "maestro.calidad": Peso(
        "maestro",
        10,
        "El maestro avisa de un problema con ese pedido (p. ej. sin NIF en el Excel): el cruce es más débil.",
    ),
    "maestro.sin_snapshot": Peso(
        "maestro", 25, "No está el maestro con el que se decidió: no se puede comprobar el cruce."
    ),
    "erp.sin_snapshot": Peso(
        "erp", 25, "No está el ERP con el que se decidió: no se puede comprobar el asiento."
    ),
    "erp.varios_asientos": Peso(
        "erp", 10, "El pedido tiene más de un asiento en el ERP: la norma mira el primero."
    ),
    # --- la decisión
    "decision.escala_por_lectura": Peso(
        "decision",
        55,
        "Se escala sólo porque no se pudo leer con seguridad, no porque la factura esté mal: si el original "
        "está limpio, lo correcto sería PAGAR.",
    ),
    "decision.cerca_del_limite": Peso(
        "decision",
        15,
        "El importe se queda a menos de 1 € de lo que se esperaba: puede ser un redondeo o una mala lectura.",
    ),
    "decision.contingencia": Peso(
        "decision",
        75,
        "Decidida por la contingencia (ADR-0009), sin hechos validados: confianza baja por definición.",
    ),
    "decision.sin_hechos": Peso(
        "decision", 100, "No hay hechos extraídos: no hay nada que respalde la clasificación."
    ),
    # --- las políticas de empresa que aún no están fijadas (docs/agentes/MAPA-POLITICAS.md)
    "politica.q1_texto": Peso(
        "politica",
        25,
        "Lo único que la frena es un texto del documento que intenta dictar la decisión: según la política de\n"
        "la empresa sobre esos textos, podría ser PAGAR.",
    ),
    "politica.q2_anulado": Peso(
        "politica",
        25,
        "El PDF dice que el pedido está anulado y el Excel y el ERP no: la política de anulaciones\n"
        "determina cuál manda.",
    ),
    "politica.q3_frontera": Peso(
        "politica",
        25,
        "Falla una comprobación objetiva: dónde está la frontera entre escalar y no pagar la fija la\n"
        "política de la empresa.",
    ),
    "politica.q5_duplicado": Peso(
        "politica",
        25,
        "Comparte pedido o número de factura con otro PDF: la política de duplicados determina si se paga\n"
        "uno, otro o ninguno.",
    ),
    # --- el revisor LLM, si se pide
    "revisor.desacuerdo": Peso(
        "revisor",
        15,
        "Una segunda opinión del LLM no ve coherente la clasificación con los hechos (sólo una señal).",
    ),
}

# PAGAR / NO_PAGAR / ESCALAR por causa clara: las dudas de lectura, a la mitad.
FACTOR_CORROBORADA = 0.5

_EVALUADOR = re.compile(
    r"evaluaci|auditor de calidad|c[oó]mputo|precisi[oó]n|conjunto de test", re.I
)
_FALTA_DATO = re.compile(
    r"legible|faltan base|no es válida o no se ha podido leer|no referencia ningún pedido|sin pedido"
)
_AVISOS_LECTURA = {
    "discrepancia_extractores",
    "extraccion_parcial",
    "documento_superpuesto",
    "importe_ambiguo",
}
_AVISOS_PARCIALES = ("extraccion_parcial", "campo_ausente", "importe_ambiguo")
#: Qué campos leídos sostienen cada regla: si en una escaneada las lecturas no coinciden en ellos, el fallo de la
#: regla puede ser de lectura y no de la factura.
CAMPOS_DE_REGLA = {
    "R1": ("nif_emisor", "iban"),
    "R2": ("pedido", "total", "nif_emisor"),
    "R3": ("total",),
    "R5": ("pedido", "total", "nif_emisor"),
}


@dataclass
class Senal:
    id: str
    texto: str  # para Alberto, con los datos de esta factura
    factor: float = 1.0

    @property
    def peso(self) -> Peso:
        return PESOS[self.id]

    @property
    def aplicado(self) -> float:
        return round(self.peso.puntos * self.factor, 1)

    def json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fuente": self.peso.fuente,
            "texto": self.texto,
            "puntos": self.peso.puntos,
            "factor": self.factor,
            "aplicado": self.aplicado,
            "por_que": self.peso.por_que,
        }


@dataclass
class Evaluacion:
    senales: list[Senal] = field(default_factory=list)
    a_favor: list[tuple[str, str]] = field(default_factory=list)  # (fuente, frase)
    causa: str = ""  # qué sostiene la clasificación
    lecturas: dict[str, Any] = field(default_factory=dict)

    def dudas(self, id_: str, texto: str, factor: float = 1.0) -> None:
        self.senales.append(Senal(id_, texto, factor))

    def bien(self, fuente: str, frase: str) -> None:
        self.a_favor.append((fuente, frase))


# ------------------------------------------------------------------------------------------ utilidades


def _norm(campo: str, valor: Any) -> Any:
    if valor is None or valor == "":
        return None
    if campo == "iban":
        return normalizar_iban(str(valor))
    if campo == "nif_emisor":
        return normalizar_nif(str(valor))
    if campo == "pedido":
        return normalizar_pedido(str(valor))
    if campo == "total":
        return parse_importe_es(valor)
    return valor


def _distintos(hechos: Any, lectura: dict[str, Any]) -> list[str]:
    """Campos clave en que una lectura cruda del LLM no coincide con los hechos (si la lectura lo trae)."""
    out = []
    for c in CAMPOS_CLAVE:
        otro = _norm(c, lectura.get(c))
        if otro is None:
            continue
        if _norm(c, getattr(hechos, c, None)) != otro:
            out.append(c)
    return out


def _motivo(e: Expediente, regla: str) -> dict[str, Any] | None:
    for m in e.motivos:
        if str(m.get("regla_id", "")).endswith(f".{regla}"):
            return m
    return None


def _fallos(e: Expediente) -> list[dict[str, Any]]:
    return [m for m in e.motivos if not m.get("ok", True)]


def _dec(v: Any) -> Decimal | None:
    try:
        return None if v in (None, "", "None") else Decimal(str(v))
    except Exception:  # noqa: BLE001 — una evidencia rara no puede tumbar la puntuación
        return None


# ------------------------------------------------------------------------------------------- señales


def _pdf(e: Expediente, ev: Evaluacion) -> None:
    h = e.hechos
    if h is None:
        return
    metodo = h.metodo.value if hasattr(h.metodo, "value") else str(h.metodo)
    avisos = {a.value if hasattr(a, "value") else str(a) for a in h.avisos}
    vision = e.tiene_texto is False or metodo == "llm_vision"

    if metodo == "plantilla":
        contraste = [d for v, d in e.lecturas if v.endswith("contraste")]
        if not contraste:
            ev.dudas("pdf.plantilla_sin_contraste", "leída por plantilla, sin contraste con el LLM")
        else:
            difs = sorted({c for d in contraste for c in _distintos(h, d)})
            ev.lecturas = {"contraste": True, "campos_distintos": difs}
            if difs:
                ev.dudas(
                    "pdf.contraste_difiere",
                    f"la plantilla y el LLM leen distinto: {', '.join(difs)}",
                )
            else:
                ev.bien("pdf", "leída por plantilla y confirmada por el LLM campo a campo")
    elif not vision:
        ev.dudas("pdf.llm_texto", "leída por el LLM sobre el texto del PDF (sin plantilla)")
    else:
        lecturas = [d for v, d in e.lecturas if not v.endswith("contraste")]
        difs = sorted({c for d in lecturas for c in _distintos(h, d)})
        ev.lecturas = {"n": len(lecturas), "campos_distintos": difs}
        ev.dudas("pdf.vision", "escaneada: leída por visión")
        if len(lecturas) <= 1:
            ev.dudas("pdf.una_lectura", "de la imagen hay una sola lectura")
        elif difs:
            ev.dudas(
                "pdf.lecturas_discrepan",
                f"{len(lecturas)} lecturas de la imagen; no coinciden en {', '.join(difs)}",
            )
        else:
            ev.bien(
                "pdf",
                f"las {len(lecturas)} lecturas de la imagen coinciden en NIF, IBAN, pedido e importe",
            )

    if h.confianza is not None and h.confianza < 1:
        ev.dudas(
            "pdf.reconciliada",
            f"la lectura se eligió reconciliándola con el maestro (confianza {h.confianza})",
        )
    if "discrepancia_extractores" in avisos:
        ev.dudas("pdf.discrepancia_extractores", "sus lecturas no coinciden y no se reconciliaron")
    if "documento_superpuesto" in avisos:
        ev.dudas("pdf.superpuesto", "otro documento aparece superpuesto o transparentándose")
    parciales = [a for a in _AVISOS_PARCIALES if a in avisos]
    if parciales:
        ev.dudas(
            "pdf.parcial",
            "faltan datos o hay un importe ambiguo: " + ", ".join(parciales),
            factor=min(len(parciales), 2),
        )
    if e.detalle_extract and "respaldo=si" in e.detalle_extract:
        ev.dudas("pdf.respaldo", "la leyó el modelo de respaldo")


def _coherencia(e: Expediente, ev: Evaluacion) -> None:
    h = e.hechos
    if h is None or None in (h.base, h.iva, h.total):
        return
    cuadra = abs(h.base + h.iva - h.total) <= Decimal("0.01")
    iva21 = abs(h.iva - (h.base * Decimal("21") / 100).quantize(Decimal("0.01"))) <= Decimal("0.01")
    if cuadra and iva21:
        ev.bien("coherencia", "base + IVA = total, con el IVA al 21 %")


def _maestro_erp(e: Expediente, ev: Evaluacion) -> None:
    h = e.hechos
    if e.maestro is None:
        ev.dudas("maestro.sin_snapshot", f"no está el maestro {e.decision.get('maestro_version')}")
    else:
        r1, r2 = _motivo(e, "R1"), _motivo(e, "R2")
        if r1 and r1.get("ok") and r2 and r2.get("ok"):
            prov = (r1.get("evidencia") or {}).get("proveedor", "")
            ev.bien(
                "maestro", f"NIF, IBAN y pedido casan con el maestro ({prov})".replace(" ()", "")
            )
        pedido = h.pedido if h else None
        if pedido:
            avisos = [a for a in e.maestro.avisos_calidad if pedido in a]
            if avisos:
                ev.dudas("maestro.calidad", f"el maestro avisa: {avisos[0]}")
    if e.erp is None:
        ev.dudas("erp.sin_snapshot", f"no está el ERP {e.decision.get('erp_version')}")
        return
    if h and h.pedido:
        asientos = [a for a in e.erp.asientos.values() if a.pedido == h.pedido]
        if len(asientos) > 1:
            ev.dudas(
                "erp.varios_asientos",
                f"el pedido {h.pedido} tiene {len(asientos)} asientos en el ERP",
            )
    r5 = _motivo(e, "R5")
    if r5 and r5.get("ok"):
        asiento = (r5.get("evidencia") or {}).get("asiento", "")
        ev.bien("erp", f"el ERP espera el mismo importe al céntimo (asiento {asiento}, PENDIENTE)")


def _tipo_fallo(e: Expediente, m: dict[str, Any], vision: bool, dudosos: set[str]) -> str:
    """'lectura' si el fallo puede venir de no haber leído bien; 'objetiva' si es un dato que falla;
    'erp_pagada' si el ERP ya la da por pagada; 'anomalia' si es un aviso de contenido (R6)."""
    ev = m.get("evidencia") or {}
    regla = str(m.get("regla_id", "")).split(".")[-1]
    if ev.get("no_pagar"):
        return "erp_pagada"
    if regla == "R6":
        return "anomalia"
    if _FALTA_DATO.search(str(m.get("detalle", ""))):
        # En un PDF con texto, un dato que falta falta en el documento; en una escaneada puede no haberse leído.
        return "lectura" if vision else "objetiva"
    if vision and dudosos & set(CAMPOS_DE_REGLA.get(regla, ())):
        return (
            "lectura"  # las lecturas de la imagen no coinciden justo en lo que hace fallar la regla
        )
    return "objetiva"


def _decision_y_politica(e: Expediente, ev: Evaluacion) -> float:
    """Clasifica qué sostiene la decisión, añade sus dudas y devuelve el factor para las dudas de lectura."""
    h = e.hechos
    vision = e.tiene_texto is False or (h is not None and str(h.metodo) in ("llm_vision",))
    fallos = _fallos(e)
    r6 = _motivo(e, "R6")
    r6_ev = (r6 or {}).get("evidencia") or {}
    graves = set(r6_ev.get("avisos") or []) if r6 and not r6.get("ok", True) else set()
    lectura_floja = r6 is not None and not r6.get("ok", True) and r6_ev.get("confianza") is not None

    if any(str(m.get("regla_id", "")).startswith("contingencia") for m in e.motivos):
        ev.dudas("decision.contingencia", "decidida por la contingencia, sin hechos validados")
        ev.causa = "contingencia"
        return 1.0
    if h is None:
        ev.dudas("decision.sin_hechos", "no hay hechos extraídos")
        ev.causa = "sin hechos"
        return 1.0

    dudosos = set(ev.lecturas.get("campos_distintos") or [])
    if lectura_floja or "discrepancia_extractores" in graves:
        dudosos |= {"nif_emisor", "iban", "pedido", "total"}
    tipos = [_tipo_fallo(e, m, vision, dudosos) for m in fallos]
    anomalias_contenido = graves - _AVISOS_LECTURA
    causas_claras = [t for t in tipos if t in ("objetiva", "erp_pagada")] + (
        ["anomalia"] if anomalias_contenido else []
    )

    factor = FACTOR_CORROBORADA
    resultado = e.resultado
    if resultado == "PAGAR":
        ev.causa = "cumple las seis reglas, corroborada por maestro y ERP"
    elif resultado == "NO_PAGAR":
        ev.causa = "el ERP ya la da por pagada: pagarla sería pagar dos veces"
        ev.bien("decision", "el ERP marca el pedido PAGADA: no se paga dos veces")
    elif causas_claras:
        ev.causa = "se escala por una causa clara del documento o del cruce"
        textos = [
            str(m.get("detalle", ""))
            for m, t in zip(fallos, tipos, strict=True)
            if t != "lectura" and not (t == "anomalia" and not anomalias_contenido)
        ]
        if textos:
            ev.bien("decision", "se escala por: " + textos[0][:160])
    else:
        ev.causa = "se escala sólo por dudas de lectura"
        ev.dudas(
            "decision.escala_por_lectura",
            "se escala porque no se leyó con seguridad, no porque la factura esté mal",
        )
        factor = 0.0  # las dudas de lectura ya son el motivo: no se cuentan dos veces

    # Importes que se quedan cerca de lo esperado (fallan por poco o pasan por la tolerancia).
    for m in fallos:
        evd = m.get("evidencia") or {}
        a = _dec(evd.get("total_factura"))
        b = _dec(evd.get("importe_pedido") or evd.get("importe_erp"))
        if a is not None and b is not None and Decimal("0.01") < abs(a - b) <= MARGEN_CERCA:
            ev.dudas(
                "decision.cerca_del_limite",
                f"el total ({a}) se queda a {abs(a - b)} € de lo esperado ({b})",
            )
            break

    # Las políticas aún no fijadas (MAPA-POLITICAS.md): si se leen distinto, la clasificación cambia.
    # Q3 movería a NO_PAGAR cualquier fallo de R1-R4, venga de la factura o de una mala lectura (la clasificación
    # cambiaría igual). Sólo se excluye el dato que falta en una escaneada: ahí no hay nada que comprobar.
    objetivas_r1_r4 = [
        m
        for m in fallos
        if str(m.get("regla_id", "")).split(".")[-1] in ("R1", "R2", "R3", "R4")
        and not (vision and _FALTA_DATO.search(str(m.get("detalle", ""))))
    ]
    solo_texto = (
        [str(m.get("regla_id", "")).split(".")[-1] for m in fallos] == ["R6"]
        and graves == {"texto_instruccion"}
        and not lectura_floja
    )
    if solo_texto:
        evaluador = bool(_EVALUADOR.search(h.texto_sospechoso or ""))
        ev.dudas(
            "politica.q1_texto",
            "la única pega es un texto que ordena qué hacer"
            + (" y que dice ser una prueba del evaluador" if evaluador else ""),
        )
    if "pedido_anulado_segun_pdf" in graves:
        ev.dudas("politica.q2_anulado", "el PDF dice que el pedido está anulado")
    if resultado == "ESCALAR" and objetivas_r1_r4:
        regla = str(objetivas_r1_r4[0].get("regla_id", "")).split(".")[-1]
        ev.dudas("politica.q3_frontera", f"falla {regla} de forma objetiva: ESCALAR o NO_PAGAR")
    if "duplicado_sospechoso" in graves:
        pareja = f" (mismo PDF que {', '.join(e.mismo_pdf_que)})" if e.mismo_pdf_que else ""
        ev.dudas("politica.q5_duplicado", "comparte pedido o factura con otro PDF" + pareja)
    return factor


# ----------------------------------------------------------------------------------------- puntuación


def banda(puntuacion: int) -> str:
    if puntuacion >= UMBRAL_ALTA:
        return "alta"
    if puntuacion >= UMBRAL_MEDIA:
        return "media"
    return "baja"


def _revisor(
    e: Expediente, ev: Evaluacion, revision: dict[str, Any] | None
) -> dict[str, Any] | None:
    """La segunda opinión del LLM, si está activada y es de esta misma decisión (si no, está caducada)."""
    if revision is None:
        from albertitos.confianza.revisor import opiniones_guardadas

        revision = opiniones_guardadas()
    op = revision.get(e.file_id)
    if not op or op.get("sha256") != e.sha256 or op.get("resultado") != e.resultado:
        return None
    if op.get("opinion") == "desacuerdo":
        ev.dudas(
            "revisor.desacuerdo",
            f"una segunda opinión (LLM) no la ve coherente: {op.get('frase', '')}",
        )
    elif op.get("opinion") == "de_acuerdo":
        ev.bien("revisor", f"una segunda opinión (LLM) está de acuerdo: {op.get('frase', '')}")
    return {k: op.get(k) for k in ("opinion", "frase", "modelo")}


def puntuar_expediente(e: Expediente, revision: dict[str, Any] | None = None) -> dict[str, Any]:
    """`revision`: opiniones del revisor LLM por file_id; None = las del fichero de ALBERTITOS_CONFIANZA_REVISOR
    (si no está puesto, ninguna); {} = sin revisor."""
    ev = Evaluacion()
    _pdf(e, ev)
    _coherencia(e, ev)
    _maestro_erp(e, ev)
    factor_lectura = _decision_y_politica(e, ev)
    opinion = _revisor(e, ev, revision)
    for s in ev.senales:
        if s.peso.fuente == "pdf":
            s.factor = round(s.factor * factor_lectura, 2)

    politica = sum(s.aplicado for s in ev.senales if s.peso.fuente == "politica")
    resto = sum(s.aplicado for s in ev.senales if s.peso.fuente != "politica")
    puntos = 100 - resto - min(politica, TOPE_POLITICA)
    if ev.causa == "contingencia":
        puntos = min(puntos, TOPE_CONTINGENCIA)
    puntuacion = int(max(0, min(100, round(puntos))))

    # Primero lo que más resta; después las dudas que no restan porque ya son el motivo (p. ej. qué lectura falló
    # cuando se escala por lectura); y si sobra sitio, lo que la respalda.
    orden = sorted(ev.senales, key=lambda s: (-s.aplicado, -s.peso.puntos))
    razones = [s.texto for s in orden[:3]]
    # Lo que la respalda, empezando por lo que sostiene la propia decisión (p. ej. «el ERP la marca PAGADA»).
    for _, frase in sorted(ev.a_favor, key=lambda x: x[0] != "decision"):
        if len(razones) >= 3:
            break
        razones.append(frase)

    fuentes: dict[str, dict[str, Any]] = {}
    for nombre in ("pdf", "coherencia", "maestro", "erp", "decision", "politica", "revisor"):
        propias = [s for s in ev.senales if s.peso.fuente == nombre]
        fuentes[nombre] = {
            "penalizacion": round(sum(s.aplicado for s in propias), 1),
            "dudas": [s.json() for s in propias],
            "a_favor": [f for fu, f in ev.a_favor if fu == nombre],
        }
    fuentes["politica"]["tope"] = TOPE_POLITICA
    fuentes["revisor"]["opinion"] = opinion  # None: apagado, sin opinión o caducada

    regla = next(
        (str(m.get("regla_id")) for m in e.motivos if not m.get("ok", True)),
        None,
    )
    return {
        "file_id": e.file_id,
        "lote": e.lote,
        "resultado": e.resultado,
        "regla": regla,
        "puntuacion": puntuacion,
        "banda": banda(puntuacion),
        "razones": razones,
        "causa": ev.causa,
        "metodo": (e.hechos.metodo.value if e.hechos is not None else None),
        "lecturas": ev.lecturas,
        "mismo_pdf_que": e.mismo_pdf_que,
        "fuentes": fuentes,
        "version": VERSION,
        "escala": "puntuación ordinal 0-100 (100 = sin dudas conocidas); no es una probabilidad calibrada",
    }
