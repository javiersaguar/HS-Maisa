---
description: Sigue una decisión de principio a fin y explícala como se la contarías a Alberto.
argument-hint: <file_id.pdf>
allowed-tools: Bash(uv run *) Bash(sqlite3 *)
---
Traza la decisión de `$ARGUMENTS`:

1. `uv run albertitos trace "$ARGUMENTS"` (si falla porque no hay decisión, `uv run albertitos status` y explica en qué etapa se quedó).
2. Explica en español llano, en este orden: qué se extrajo del PDF (y con qué método), qué dice el maestro, qué dice el asiento del ERP, qué regla decidió, y el resultado. Cita los eventos: latencias, reintentos, tokens, coste.
3. Si el resultado te parece incorrecto, NO lo cambies: di qué regla o qué hecho está mal y a quién le toca (rules/ → Mónica, extract/ → Alfonso, sources/ → Javier).
