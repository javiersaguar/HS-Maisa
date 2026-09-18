# Parte de fin de ciclo · ciclo 2

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Sé concreto: cifras, comandos
literales y su salida, rutas. Este fichero se le pasa entero al planificador para repartir el ciclo siguiente.
El parte del ciclo 1 está en `partes/PARTE-01.md`.

## B1 · Lote 2 en frío (ensayo del sábado 18:00)
- Estado: **terminado** (pasos 1-6; cerrado 22:45)
- Hecho (con cifras):
  - `data/fixtures/lote2_sim/` (10 PDFs derivados con sha distinto: 6 plantillas de A2 elegidas con sus detectores, 1 de dos páginas, 1 con instrucción, 2 escaneadas) + README con tabla y comando de limpieza.
  - Ensayo cronometrado: ingest 0,31 s · extract 10/10 en 68 s (8 plantilla, 2 visión) · diff 0,17 s · inventario 0,07 s · reprocess 0,5 s · package 1 s. Extrapolado a 40: ≈ 9 s por escaneada con 4 hilos, resto < 15 s.
  - Cruce ERP v2-sim ↔ Excel ↔ Caja: los 2 asientos cambiados tocan exactamente 2 facturas (`F26-9865_ofimática.pdf` → NO_PAGAR, `2026-06-27_P001.pdf` → ESCALAR); los 3 SIM no los referencia nadie. **Confirmado** ejecutando `reprocess --impacted --erp v2-sim` (510 recalculadas, cambian 2) y restaurado a v1.
  - `scripts/inventario_trampas.py`: `--facturas`, `--erp-tag`, `--salida`, `--sin-docs`; resumen por categoría siempre en pantalla. Probado sobre el simulado: encuentra la instrucción (1), las escaneadas (2) y la fecha en letra (1) sin tocar `docs/trampas.md`.
  - `.claude/skills/lote2/SKILL.md` reescrita con comandos literales, tiempos, paso 0 de limpieza, bridge v2 en :8011 y qué hacer con PENDIENTES.
  - `docs/agentes/ENSAYO-LOTE2.md`: tiempos, 9 huecos del runbook con su estado, cruce verificado, checklist del sábado y bloque para reconstruir la tabla con el lote real.
- Verificado con (comando → resultado literal): ver tabla §1 de ENSAYO-LOTE2.md (salidas literales copiadas). `uv run albertitos package` con filas `L2-*` en BD y sin `data/lote2/facturas` → `APTO · outcomes.jsonl · 500 líneas`.
- Ficheros tocados: `data/fixtures/lote2_sim/**`, `scripts/inventario_trampas.py`, `.claude/skills/lote2/SKILL.md`, `docs/agentes/ENSAYO-LOTE2.md`, `docs/agentes/BITACORA.md`, `docs/agentes/PARTE.md`. (Plataforma, antes de abrir el ciclo: `extract/etapa.py` con `ALBERTITOS_DIR_LOTE2`.)
- Commits (hash · mensaje): `lote2: ensayo en frío — lote simulado, inventario parametrizado, skill con tiempos, cruce verificado (B1)`
- Descubierto (huecos del runbook, trampas nuevas, tiempos): (1) `package` mete en `outcomes_lote2.jsonl` cualquier fichero con `lote=2` de la BD → limpiar el simulado antes del real; (2) el inventario reescribía siempre `trampas.md`; (3) `linaje.impactados` recalcula los 510 al cambiar la versión del ERP (0,5 s; la demo debe decir "cambian 2"); (4) las facturas de plantilla no pasan por el LLM: una instrucción con redacción nueva sólo la ven las regex; (5) :8010 ocupado en este portátil, :8011 libre.
- Pendiente / no llegué a: nada del encargo. La BD de Javier conserva los 10 `L2-*` con hechos y decisiones (evidencia del ensayo): quitarlos con el comando del paso 0 antes del lote real.
- Necesito de otros (quién · qué · para qué): Miguel · `caja verify --dir` y `caja manifest --lote 2` en cli.py · verificar el lote 2 simulado o real fuera de `data/lote2/`. B2 · limitar `contrastar` a un lote/lista de file_id · recoger `texto_sospechoso` por LLM también en las facturas de plantilla del lote 2. Mónica · nada nuevo; el caso `2026-06-27_P001.pdf` (Excel cuadra, ERP no) es un buen test de R5 vs R2.
- Riesgos que veo: (1) si el lote 2 trae muchas escaneadas, extract tarda ~9 s/escaneada (40 → 6 min): lanzar `extract` en cuanto termine `ingest`, antes de la norma v4; (2) los PDFs del zip pueden venir en una subcarpeta con otro nombre: la skill lo contempla (`--dir` + `ALBERTITOS_DIR_LOTE2`); (3) nombres NFD en el zip del sábado → `caja verify --lote 2` los detecta; renombrar antes de ingerir.
- Propongo como siguiente tarea: (ciclo 3) ensayar el sábado completo con Miguel y Mónica en sus portátiles (`hechos import` + `decide` + `reprocess` + `package` de lote 2 simulado) para medir el tiempo de punta a punta con tres personas, y añadir un test de integración `tests/test_lote2_sim.py` (ingest + extract sin LLM vía plantillas + diff) que corra en `make check`.

## B2 · Resiliencia demostrable y coste real
- Estado: **terminado** (los 5 pasos; sin bloqueos). Entrega: `docs/agentes/RESILIENCIA-Y-COSTE.md`, listo para que Alfonso lo copie al plan y Miguel a `benchmark.md`.
- Hecho (con cifras):
  - **El coste por token que contábamos no existe.** Helmcode cobra **suscripción plana por key** para los modelos abiertos (`helmcode.com/pricing`, 18/09/2026: Starter 399 €/mes · Growth 1.299 € · Scale 3.199 €). `deepseek-v4-flash`, `qwen3.6`, `glm5.3-flash` y `gemma4` van **sin coste por token**; los frontier van por crédito prepago y **no tenemos crédito**: probados los 8, los 8 devuelven `402` ("*your organisation has no credit balance*"). → **coste marginal por factura = 0 EUR**, no los **2,30 EUR** que daba `bench` (salían de `ALBERTITOS_PRECIO_IN/OUT=3/15`, inventados). Si hace falta una cifra en euros, la honesta es la suscripción amortizada: **0,80 €/factura a 500/mes · 0,040 € a 10.000 · 0,004 € a 100.000**.
  - **Coste y tamaño por camino, desde `eventos`** (500 facturas = 468 plantilla · 29 visión · 3 texto): plantilla **5 ms**, 0 tokens, 0 € · LLM texto **3,3 s**, 1.123/665 tok · LLM visión **35,3 s**, 5.476/3.450 tok. La visión es **7.000× más lenta** que una plantilla.
  - **Capacidad medida con 1/2/4/8 hilos** (`scripts/bench_llm.py`, 16 de texto + 8 escaneadas por tanda, llamadas reales): texto **0,41 → 0,76 → 1,28 f/s** (casi lineal hasta 4); visión **0,08 → 0,13 → 0,22 → 0,22 f/s**, o sea **satura en 4**, que cuadra con el límite publicado de **5 concurrentes por modelo**. **Cero 429 en las 8 tandas**: el cuello de botella no es el límite de tasa, es la **cola de latencia** (una petición colgada 94 s con p50 en 2,9 s, repetida dos veces clavada en ~94 s). Recomendación medida: **`--workers 4`** (que es lo que ya usaba A1, ahora con evidencia).
  - **Límites del gateway, documentados y localizados** (`helmcode.com/docs/rate-limits`): 100 RPM, 2M TPM, **5 concurrentes por modelo** (10 en deepseek-v4-flash y glm5.3), 429 con **`Retry-After`**. `llm.py` **tiraba esa cabecera** y esperaba a ciegas 1/2/4 s: corregido (con tope de 60 s).
  - **Modelo de respaldo implementado y probado contra el gateway real.** `ALBERTITOS_MODELO_TEXTO_FALLBACK` / `..._VISION_FALLBACK`: si el principal agota reintentos, **una** llamada al respaldo, con **clave de caché propia**, y el evento dice quién respondió. No se intenta con `LLM-AUTH`/`LLM-CONFIG`/`LLM-PRESUPUESTO`. Prueba real: principal `claude-sonnet-5` (402) → `glm5.3-flash` responde 3/3 y los hechos son **idénticos campo a campo** a los del principal.
  - **Guion de resiliencia de 2 min ensayado**, sobre 5 facturas sin caché y sobre una **copia** de la BD: (a) caído → `0/5 ok · 5 pendientes · LLM-DOWN · 0,7 s`; (b) 429 → `5/5 ok` en **`intento=2`**, 32,6 s; (c) basura → `LLM-INVALID ×4 + LLM-CIRCUIT-OPEN ×1` (el **circuit breaker salta solo** al 5º fallo), 23,2 s; (d) recuperación → `5/5 ok` 30 s y segunda pasada `{'cache': 5} · 0 tokens · 1,1 s`, con **0 sha256 duplicados**.
  - **11 tests nuevos** en `tests/test_llm.py` (precios por modelo y `ALBERTITOS_PRECIOS_JSON`, `Retry-After` en segundos/fecha/absurdos, respaldo responde / no se usa con key mala / cachea aparte / sin respaldo queda PENDIENTE, `contrastar` acotado).
  - **Petición de B1 atendida**: `contrastar` acepta ahora `lote=` y `file_ids=`.
- Verificado con:
  - `uv run pytest tests/test_llm.py -q` → `23 passed, 2 deselected in 1.28s`
  - `make check` → `195 passed, 2 deselected in 22.58s` · `ruff format`: `52 files already formatted` · `ruff check`: `All checks passed!`
  - `make agentes-check` → `OK: cada fichero tiene un único dueño`
  - `uv run python scripts/bench_llm.py --texto 16 --vision 8 --workers 1,2,4,8 --sufijo m2` → tabla de §4 del documento
- Ficheros tocados: `src/albertitos/extract/{llm,etapa}.py`, `tests/test_llm.py`, `scripts/bench_llm.py`, `docs/agentes/RESILIENCIA-Y-COSTE.md`, `.env.example`, `docs/agentes/{BITACORA,PARTE}.md`
- Commits: `0f4175e · extract: coste real (0 EUR, no 2,30), Retry-After, modelo de respaldo y capacidad medida (B2)`
- Descubierto:
  1. **La doc del gateway se equivoca sobre la visión, para bien.** `docs/models` dice que `deepseek-v4-flash` y `glm5.3-flash` **no** aceptan imágenes: sí las aceptan y devuelven tool call. Comprobado con tres facturas distintas (aciertan `pedido` y `total` de cada una, luego leen la imagen). Además el gateway expone `glm5.3-flash` y `gemini-3.5-flash-lite`, **no** los `glm5.3`/`glm5.2`/`gemini-3.6-flash` que decía el plan.
  2. **Ningún modelo de visión lee el NIF de forma fiable.** `scan_002`: qwen `B88125774`, deepseek `89812077W`; `scan_004`: qwen `B60233808`, deepseek `B90233805`, glm `B00233858`; verdad `B98120774` y `B90233808`. El `pedido` y el `total` sí salen casi siempre. **Valida la reconciliación con el maestro de A1**: un respaldo compra disponibilidad, no precisión. `gemma4` descartado (75 s en texto, 47 s en imagen, y acierta menos).
  3. **El gateway cachea por cuerpo de petición y eso falsea cualquier benchmark.** Mi primera tanda daba 4 escaneadas en 2,9 s con 2 hilos frente a 151 s con 1 hilo, **con los mismos tokens de entrada**. No era concurrencia: era su caché. De ahí el parámetro `marca`. Quien mida throughput contra este gateway sin variar el cuerpo, medirá humo.
  4. Un corte transitorio del gateway tumbó 15 llamadas seguidas con `ConnectError`. Sospeché del `httpx.Client` compartido de `llm.py`; el control (mismo cliente, 6 imágenes) dio **6/6 en 200**, así que **no era el cliente**. El sistema degrada bien: reintentos, breaker y `PENDIENTE`.
- Pendiente / no llegué a: **no hemos provocado un 429 real** (los límites están publicados y son coherentes con la saturación en visión, pero el 429 del guion es caos simulado); el respaldo de **visión** queda vacío a propósito (ningún candidato lee el NIF mejor que qwen); los **94 s** de la tanda de 8 hilos no están explicados; las facturas/hora de §4 son extrapolación de tandas de 16 y 8, no una ejecución de 10.000.
- Necesito de otros (quién · qué · para qué):
  - **Miguel** · al rehacer `bench`, que el EUR de los modelos abiertos sea **0** y no 2,30 · es la cifra que va a la defensa, y 2,30 € es indefendible porque nadie los paga. Si quiere dinero, la tabla de suscripción amortizada del documento.
  - **Alfonso** · §4 (capacidad), §5 (modelos) y §6 (formatos nuevos) están escritos para copiarse al plan tal cual.
  - **Mónica** · el hallazgo 2 es argumento de norma, no sólo de infra: el NIF de una escaneada no se puede creer de una sola lectura.
  - **Javier** · decidir si `ALBERTITOS_MODELO_TEXTO_FALLBACK=glm5.3-flash` se queda activo en el `.env` real (en `.env.example` ya está puesto).
- Riesgos que veo: (1) todas las cifras son de **un** proveedor y **una** noche; si Helmcode va lento el sábado, la tabla de capacidad no vale y hay que rehacerla con `--sufijo` nuevo. (2) El respaldo de texto añade un camino que en producción **no se ha ejercitado** salvo en la prueba de 3 facturas: si el principal cae durante el lote 2, será su estreno. (3) Los 94 s de cola larga son el riesgo real de plazo en el lote 2: con 40 facturas y varias escaneadas, un par de colgadas se comen minutos.
- Propongo como siguiente tarea: (a) provocar un **429 real** lanzando >100 peticiones/min contra un modelo para ver la cabecera `Retry-After` de verdad y cerrar el único hueco del guion; (b) un **timeout por petición** más agresivo (hoy 180 s) con reintento, que convertiría los 94 s de cola en 2 reintentos rápidos; (c) medir el camino de visión con `deepseek-v4-flash` como principal sobre las 29 escaneadas (3-6 s frente a 12-35 s) y cruzarlo con la reconciliación, que es donde está el único ahorro de tiempo grande que queda.

## Javier (a mano, al cerrar el ciclo)
- `make check`:
- `make agentes-check`:
- `/handoff` hecho (PR):
- Preguntas a mentores pendientes:
