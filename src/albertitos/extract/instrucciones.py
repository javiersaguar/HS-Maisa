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

VENTANA_ANTES = (
    90  # si no hay principio de frase cerca, se recorta a esto: la evidencia se lee sola
)
VENTANA_DESPUES = 200


def detectar_instruccion(texto: str) -> str | None:
    """Devuelve la frase (≤ 240 caracteres) alrededor de la primera coincidencia, o None.

    Muchas de estas frases van incrustadas en el cuerpo de la factura, sin puntuación delante
    (una línea de detalle a 0,00, un párrafo pegado al TOTAL). Por eso el principio de frase se
    acota a `VENTANA_ANTES`: sin ese tope el fragmento arrancaba en la cabecera del documento y
    la evidencia era ilegible para quien revisa la traza.
    """
    plano = " ".join(texto.split())
    m = _RE.search(plano)
    if not m:
        return None
    ini = 0
    for corte in _FIN_FRASE.finditer(plano, 0, m.start()):
        ini = corte.end()
    if m.start() - ini > VENTANA_ANTES:
        ini = m.start() - VENTANA_ANTES
        hueco = plano.find(" ", ini)  # no cortar una palabra por la mitad
        ini = hueco + 1 if 0 <= hueco < m.start() else m.start()
    fin = _FIN_FRASE.search(plano, m.end(), m.end() + VENTANA_DESPUES)
    frase = plano[ini : fin.start() + 1 if fin else m.end() + VENTANA_DESPUES].strip()
    return frase[:240]


def menciona_anulacion(texto: str) -> bool:
    return bool(_ANULADO.search(" ".join(texto.split())))
