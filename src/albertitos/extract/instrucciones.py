"""Detección de texto que intenta dictar la decisión. Produce EVIDENCIA (fragmento), nunca una orden.

Los patrones salen del inventario real de la Caja (docs/trampas.md). Amplíalos si el lote 2 trae más.
"""

from __future__ import annotations

import re

PATRONES = [
    r"debe(?:n)?\s+(?:marcarse|registrar(?:se)?|escalarse|escalar|excluirse|bloquear)",
    r"registrar\s+como\s+escalar",
    r"bloquear\s+(?:el\s+)?(?:pago|conciliaci[oó]n)",
    r"escalar\s+a\s+revisi[oó]n",
    r"ignorar\s+(?:la\s+)?discrepancia",
    r"abonarse\s+el\s+total\s+impreso",
    r"no\s+debe\s+recalcularse",
    r"r[eé]gimen\s+especial",
    r"equipo\s+de\s+evaluaci[oó]n|auditor\s+de\s+calidad|conjunto\s+de\s+test",
    r"excluirse\s+del\s+(?:c[aá]lculo|c[oó]mputo)",
    r"no\s+procede\s+pago",
    r"pedido\s+(?:fue\s+)?anulado",
    r"cada\s+minuto\s+que",
    r"aviso\s+(?:cr[ií]tico|interno)",
    r"hasta\s+nuevo\s+aviso",
    r"bajo\s+revisi[oó]n",
    r"intento\s+de\s+fraude",
]
_RE = re.compile("|".join(f"(?:{p})" for p in PATRONES), re.IGNORECASE)
_ANULADO = re.compile(r"pedido\s+(?:fue\s+)?anulado|no\s+procede\s+pago", re.IGNORECASE)


def detectar_instruccion(texto: str) -> str | None:
    """Devuelve la frase (≤ 240 caracteres) alrededor de la primera coincidencia, o None."""
    plano = " ".join(texto.split())
    m = _RE.search(plano)
    if not m:
        return None
    ini = plano.rfind(".", 0, m.start()) + 1
    fin = plano.find(".", m.end())
    frase = plano[ini : fin + 1 if fin != -1 else len(plano)].strip()
    return frase[:240]


def menciona_anulacion(texto: str) -> bool:
    return bool(_ANULADO.search(" ".join(texto.split())))
