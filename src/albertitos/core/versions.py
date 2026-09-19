"""Versiones de los componentes que entran en el linaje de una decisión.

Súbelas cuando cambie el comportamiento: así `reprocess --impacted` sabe qué recalcular.
"""

ESQUEMA_VERSION = 3  # schema.sql (2: índice decisiones(sha256, vigente) · 3: identidades, P0-1)
EXTRACTOR_VERSION = "ext-0.1"  # extract/: parsers + validadores
PROMPT_VERSION = "p-0.2"  # extract/llm.py: prompt de extracción (entra en la clave de caché)
NORMA_VERSION_POR_DEFECTO = "v3"  # rules/REGISTRO
