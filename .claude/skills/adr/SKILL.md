---
name: adr
description: Crea un ADR (Architecture Decision Record) en docs/adr con contexto, alternativas, decisión, consecuencias y evidencia. Úsalo en el momento en que se toma una decisión de diseño con alternativas reales; el PDF final resume entre 2 y 5 de ellos.
argument-hint: <titulo-en-kebab-case>
allowed-tools: Bash(ls *) Bash(git log *)
---
# Nuevo ADR: $ARGUMENTS

1. Numera: mira `ls docs/adr/` y usa el siguiente `NNNN` (4 cifras). Fichero: `docs/adr/NNNN-$ARGUMENTS.md`.
2. Copia la estructura de `docs/adr/0000-plantilla.md` y rellena **todas** las secciones. Pregunta al usuario lo que no sepas; no inventes evidencia.
3. Evidencia admitida: una cifra de `make bench`, un test que pasa/falla, un conteo sobre la Caja (p. ej. "29 de 500 sin texto"), un commit, una respuesta de un mentor (con hora).
4. Alternativas: mínimo dos, con por qué se descartan hoy (coste de aprendizaje, riesgo, tiempo), no por qué son malas en abstracto.
5. Consecuencias aceptadas: lo que perdemos con esta decisión. Si no perdemos nada, no era una decisión.
6. Añade una línea al índice `docs/adr/README.md` y, si el ADR va al PDF, un resumen de 5 líneas en `docs/plan/albertitos_plan.md` sección ADRs.

Candidatos ya identificados (no los dupliques si existen): el LLM extrae y la norma decide · formato CLI + consola de sólo lectura · SQLite con log de eventos como única fuente de verdad · snapshot del ERP en local vs. consulta en vivo · LLM para todo el viernes y plantillas como optimización medida · frontera NO_PAGAR/ESCALAR · degradación ante caída del LLM (PENDIENTE, nunca PAGAR por defecto) · versionado de norma v3/v4 y reprocesado por linaje.
