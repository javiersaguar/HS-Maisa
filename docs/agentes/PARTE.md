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
