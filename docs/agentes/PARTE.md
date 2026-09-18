# Parte de fin de ciclo · ciclo 1

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Sé concreto: cifras, comandos
literales y su salida, rutas. Este fichero se le pasa entero al planificador para repartir el ciclo siguiente.

## A1 · LLM y etapa de extracción
- Estado: **parcial / bloqueado** (sin `ANTHROPIC_API_KEY` real en `.env`: los pasos 1, 2, 4, 5 y 8 no se han podido ejecutar)
- Hecho (con cifras):
  - `extract/etapa.py::extraer` implementada completa: candidatos (pendientes o todos, filtro `--fixture`), plantilla de A2 antes que LLM, LLM texto/visión, `validadores.validar`, hechos + evento OK (latencia, tokens, coste, versión, método), `ErrorLLM` → evento PENDIENTE con `error_codigo` y sigue, `workers` con una conexión SQLite por hilo, `ResumenExtraccion` con ficheros/s.
  - `extract/llm.py`: estado compartido entre hilos (`EstadoLLM`: presupuesto, circuit breaker a los 5 fallos/60 s, cliente HTTP) con lock. Llamada al SDK 1.7 verificada por introspección (`messages.create(model, max_tokens, system, tools, tool_choice, messages)`, `ToolUseBlock.input`, `usage`).
  - `tests/test_llm.py`: 9 tests sin red (caché precargada → 0 tokens; caos llm_down → PENDIENTE sin perder nada; plantilla evita el LLM; respuesta inválida → 3 intentos y PENDIENTE; API simulada extrae, cachea y la 2ª pasada es gratis; escaneada → llm_vision + SIN_TEXTO; trampa F26-2201 → Aviso texto_instruccion + fragmento, sin campo de decisión; workers=3; presupuesto 0 → LLM-PRESUPUESTO sin llamar). 2 tests `llm` contra la API real (se saltan sin key).
- Verificado con (comando → resultado literal):
  - `uv run pytest tests/test_llm.py -q` → `9 passed, 2 deselected`
  - `make check` → `103 passed, 2 deselected in 20.31s` (con los cambios sin commitear de A2 y A3 en el árbol)
  - `uv run albertitos chaos --llm-down && uv run albertitos extract --fixture data/fixtures/muestra.txt` → `extract: 18/21 ok · 3 pendientes · 0 pdf ilegibles · métodos {'plantilla': 18} · errores {'LLM-DOWN': 3} · tokens 0/0 · 0.0000 EUR · 0.6 s (32.72 ficheros/s)`; después `chaos --off` → 482 candidatos pendientes, 18 hechos, 0 decisiones.
- Ficheros tocados: `src/albertitos/extract/etapa.py`, `src/albertitos/extract/llm.py`, `tests/test_llm.py`, `docs/agentes/BITACORA.md`
- Commits (hash · mensaje): ver `git log --oneline -1` de la rama → `extract: etapa extraer() completa con caché/caos/workers y tests sin red (A1)`
- Descubierto (datos, trampas, sorpresas del SDK/ERP):
  - Las plantillas de A2 ya resuelven 18 de las 21 facturas de la muestra sin LLM (coste 0). Sólo las 3 escaneadas necesitan visión.
  - Los 11 IBAN del maestro fallan mod-97 (sintéticos) → `Aviso.IBAN_INVALIDO` es ruido en toda la Caja (no afecta a la decisión hoy; sí a la traza). Avisado a A2.
  - Render de una escaneada a 150 dpi ≈ 200 ms (latencia del evento PENDIENTE de los scans).
- Pendiente / no llegué a: pasos 1-2 (extracción real de una de texto y una escaneada, anotar tokens y coste), 4 (revisar 5 a mano), 5 (`hechos_muestra.jsonl` para Mónica/Miguel), 8 (las 500 con `--workers 4`, coste real y ficheros/s con LLM), y el 6 con `chaos --off` de verdad (reanudación con la API).
- Necesito de otros (quién · qué · para qué): Javier · `ANTHROPIC_API_KEY` real en `.env` (+ `ALBERTITOS_PRESUPUESTO_EUR=3`) · todo lo pendiente. Javier · confirmar que los modelos de `.env` (`claude-sonnet-5` texto y visión) son los que queremos pagar. A2 · avisar si cambia un parser para reextraer con `solo_pendientes=False`.
- Riesgos que veo: (1) sin key hasta tarde, el hito de las 23:30 (hechos_muestra.jsonl) se cae: con plantillas al menos 18/21 salen igual, así que se puede exportar un `hechos_muestra.jsonl` parcial de plantilla para desbloquear a Mónica/Miguel. (2) Los hechos de plantilla ya guardados no se recalculan si A2 corrige un parser. (3) Precios de `.env` (3/15 EUR por Mtok) sin revisar contra la tarifa real: el coste del benchmark será estimado hasta que se revisen.
- Propongo como siguiente tarea: en cuanto haya key, ejecutar pasos 1-2-4-5-8 tal cual (todo el código está listo); si no hay key antes de las 22:30, exportar el `hechos_muestra.jsonl` parcial (18 de plantilla) y marcar las 3 escaneadas como pendientes en la bitácora.

## A2 · Plantillas, validadores e instrucciones
- Estado:
- Hecho (con cifras):
- Verificado con:
- Ficheros tocados:
- Commits:
- Descubierto:
- Pendiente / no llegué a:
- Necesito de otros:
- Riesgos que veo:
- Propongo como siguiente tarea:

## A3 · Fuentes y trampas
- Estado:
- Hecho (con cifras):
- Verificado con:
- Ficheros tocados:
- Commits:
- Descubierto:
- Pendiente / no llegué a:
- Necesito de otros:
- Riesgos que veo:
- Propongo como siguiente tarea:

## Javier (a mano, al cerrar el ciclo)
- `make check`: 
- `make agentes-check`: 
- `/handoff` hecho (PR): 
- Preguntas a mentores pendientes:
