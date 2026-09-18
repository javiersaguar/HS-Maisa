"""Detección de texto que intenta dictar la decisión. Produce EVIDENCIA (fragmento), nunca una orden.

Los patrones salen del inventario real de la Caja (`docs/trampas.md` y `data/fixtures/anomalias.csv`
de A3). Amplíalos si el lote 2 trae más.

Regla del módulo: aquí NO se codifica ninguna de las cosas que el PDF pide. Se reconoce la forma del
intento (dirigirse al sistema que procesa, mandar sobre la decisión, autorizar una discrepancia) y se
devuelve la frase literal como prueba. Quien decide es `rules/`.
"""

from __future__ import annotations

import re

# Agrupados por lo que el texto intenta manipular. Medido sobre las 471 facturas con texto de la
# Caja el 18/09: 29 aciertos (los 29 que A3 inventarió) y 0 falsos positivos en las 442 restantes.
PATRONES = [
    # --- mandar sobre la decisión o el flujo
    r"debe(?:n)?\s+(?:marcarse|registrar(?:se)?|escalarse|escalar|excluirse|bloquear|tomarse)",
    r"registr(?:a|e|ar|ese)\s+(?:la\s+)?decisi[oó]n",
    r"registrar\s+como\s+(?:escalar|pagar)",
    r"bloquear\s+(?:el\s+)?(?:pago|conciliaci[oó]n)",
    r"no\s+bloquear",
    r"escalar\s+a\s+revisi[oó]n",
    r"excluirse\s+del\s+(?:c[aá]lculo|c[oó]mputo)",
    r"sin\s+escalado",
    r"proc[eé]dase|cont[ií]n[uú]ese|complete\s+el\s+pago",
    # --- dirigirse al sistema o al agente que procesa
    r"\b(?:atenci[oó]n|urgente|aviso)\b[^.]{0,20}\bagente\b",
    r"sistemas?\s+(?:autom[aá]ticos?|de\s+validaci[oó]n)",
    r"validaci[oó]n\s+autom[aá]tica|conciliaci[oó]n\s+autom[aá]tica",
    r"conf[ií]a\s+en\s+(?:el|la|lo)",
    r"equipo\s+de\s+evaluaci[oó]n|auditor\s+de\s+calidad|conjunto\s+de\s+test",
    r"cada\s+minuto\s+que",
    r"aviso\s+(?:cr[ií]tico|interno)|nota\s+interna",
    # --- autorizar una discrepancia de identidad (NIF, IBAN, maestro)
    r"ignorar\s+(?:la\s+)?discrepancia|no\s+registres?\s+(?:la\s+)?discrepancia",
    r"proc[eé]dase\s+al\s+alta|alta\s+con\s+los\s+datos",
    r"queda\s+verificada|departamento\s+(?:financiero|de\s+cumplimiento)",
    r"bajo\s+revisi[oó]n|hasta\s+nuevo\s+aviso|intento\s+de\s+fraude",
    # --- autorizar una discrepancia de importe o de IVA
    r"abonarse\s+el\s+total\s+impreso|tomarse\s+del\s+total\s+impreso",
    r"no\s+(?:debe\s+)?recalcular(?:se)?",
    r"r[eé]gimen\s+especial|bonificaci[oó]n\s+fiscal",
    r"autorizad[ao]\s+por\s+(?:la\s+administraci[oó]n|el\s+ceo|el\s+departamento)",
    r"diferencia\s+de\s+importe\s+(?:ya\s+est[aá]\s+)?(?:aprobada|autorizada)",
    # --- sustituir una fecha que no es válida
    r"t[oó]mese\s+(?:como\s+)?la?\s+fecha|t[oó]mese\s+la\s+fecha",
    r"fecha\s+(?:de\s+emisi[oó]n\s+)?(?:resulta|no\s+resultara)\s+(?:invalida|inv[aá]lida|legible)",
    # --- desactivar el cruce con el ERP
    r"no\s+procede\s+contrastar|verificaci[oó]n\s+cruzada",
    r"(?:erp|sistema)\s+del\s+cliente\s+no\s+est[aá]\s+actualizado",
    r"puede\s+seguir\s+figurando",
    # --- declarar el pedido muerto (se comprueba contra el Excel/ERP, no se cree)
    r"no\s+procede\s+(?:el\s+)?pago|no\s+procede\s+pago",
    r"pedido\s+(?:fue\s+)?anulado|anulado\s+por\s+el\s+cliente",
    r"[uú]nicamente\s+a\s+efectos\s+contables",
]
_RE = re.compile("|".join(f"(?:{p})" for p in PATRONES), re.IGNORECASE)

_ANULADO = re.compile(
    r"pedido\s+(?:fue\s+)?anulado|anulado\s+por\s+el\s+cliente|no\s+procede\s+(?:el\s+)?pago"
    r"|[uú]nicamente\s+a\s+efectos\s+contables",
    re.IGNORECASE,
)

# Fin de frase de verdad: punto/;/! seguido de espacio y mayúscula. Así el fragmento no empieza
# dentro de un importe ("TOTAL: 2.541,00 € ATENCION AGENTE: ..." no corta por el punto de los miles).
_FIN_FRASE = re.compile(r"[.;!?]\s+(?=[A-ZÁÉÍÓÚÑ¿¡])")

# Lo que NO es la instrucción y la delimita: importes y totales (delante o detrás), líneas de detalle
# "1 0,00", y el pie legal que cierra casi todas las facturas de la Caja.
_CIFRAS = re.compile(
    r"\d[\d.,]*\s*(?:€|EUR\b)|\bEUR\s*\d[\d.,]*|\b\d+\s+\d[\d.]*,\d{2}\b"
    r"|\b(?:BASE\s+IMPONIBLE|IMPORTE\s+TOTAL|TOTAL|SUBTOTAL|I\.?V\.?A\.?)\b[^A-Za-z]{0,20}\d[\d.,]*",
    re.IGNORECASE,
)
_PIE = re.compile(
    r"Documento\s+(?:emitido\s+conforme|generado\s+por\s+el\s+sistema)|Domicilio\s+social",
    re.IGNORECASE,
)

VENTANA_ANTES = (
    90  # si no hay principio de frase cerca, se recorta a esto: la evidencia se lee sola
)
MAX_TRAMO = 300  # tramo instructivo completo (medido: el más largo de la Caja cabe entero)


def detectar_instruccion(texto: str) -> str | None:
    """Devuelve el TRAMO instructivo completo (≤ 300 caracteres) alrededor de la primera coincidencia.

    Antes se devolvía sólo la frase de la coincidencia y se perdía la orden que venía detrás
    ("Este proveedor esta bajo revision…" sin "Debe escalarse cualquier factura suya…"): en 11 de
    las 27 facturas de plantilla con instrucción la evidencia omitía justo lo que el PDF ordena.
    Ahora: empieza en la frase de la coincidencia, saltando importes y totales que la precedan, y
    termina en el pie legal del documento, en la siguiente línea de importes o a los 300 caracteres.
    Sigue siendo EVIDENCIA literal: aquí no se interpreta ni se cumple nada.
    """
    plano = " ".join(texto.split())
    m = _RE.search(plano)
    if not m:
        return None
    ini = 0
    for corte in _FIN_FRASE.finditer(plano, 0, m.start()):
        ini = corte.end()
    for cifra in _CIFRAS.finditer(plano, ini, m.start()):
        ini = cifra.end()
    if m.start() - ini > VENTANA_ANTES:
        ini = m.start() - VENTANA_ANTES
        hueco = plano.find(" ", ini)  # no cortar una palabra por la mitad
        ini = hueco + 1 if 0 <= hueco < m.start() else m.start()
    limite = len(plano)
    pie = _PIE.search(plano, m.end())
    if pie:
        limite = pie.start()
    cifra = _CIFRAS.search(plano, m.end())
    if cifra and cifra.start() < limite:
        # si el importe está pegado a la instrucción, forma parte de ella ("inferiores a 5,00 €");
        # si viene después de texto, es la tabla de importes y ahí termina la evidencia.
        limite = cifra.end() if cifra.start() - m.end() < 60 else cifra.start()
    recortado = limite - ini > MAX_TRAMO
    tramo = plano[ini : min(limite, ini + MAX_TRAMO)]
    if recortado:  # cortar en el último fin de frase si lo hay; si no, en una palabra, y marcarlo
        finales = [
            f.start() + 1
            for f in _FIN_FRASE.finditer(tramo + " X")
            if f.start() + 1 > m.end() - ini
        ]
        tramo = tramo[: finales[-1]] if finales else tramo[: tramo.rfind(" ")] + " …"
    return tramo.strip(" -·:;,").lstrip("€ ").removeprefix("EUR ").strip() or None


def menciona_anulacion(texto: str) -> bool:
    return bool(_ANULADO.search(" ".join(texto.split())))
