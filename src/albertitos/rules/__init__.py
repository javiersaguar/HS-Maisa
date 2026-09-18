"""Norma de pagos como código, versionada. Dueño: Mónica.

REGISTRO: versión → módulo con `decidir(hechos, maestro, erp, ctx) -> Decision`.
La v4 del sábado se añade como módulo nuevo; la v3 no se toca.
"""

from albertitos.rules import norma_v3

REGISTRO = {"v3": norma_v3}
