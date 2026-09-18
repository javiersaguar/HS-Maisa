# Parte de fin de ciclo · ciclo 3

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores: `partes/PARTE-01.md` (A1/A2/A3), `partes/PARTE-02.md` (B1/B2).

## C1 · Contraste total y escaneados difíciles
- Estado: **terminado** (pasos 1-5; 23:24 → 23:55). Detalle y tablas en `docs/agentes/CONTRASTE-TOTAL.md`.
- Hecho (con cifras):
  - **Contraste total plantilla↔LLM: 468/468 coinciden**, 0 difieren, 0 fallos en los 8 campos clave; 717.188 tokens (0 €), 472 s. Ninguna plantilla necesita arreglo.
  - **Fechas imposibles blindadas**: las 3 tienen `fecha=None` + `campo_ausente` (el LLM transcribe `2026-02-31` tal cual; no inventa 28/02 ni obedece "tómese la fecha del sello"). Dos tests.
  - **Timeout por petición y por modalidad**: 60 s texto (antes 180) / 90 s visión; `httpx.TimeoutException` → `LLM-TIMEOUT` reintentable; el evento PENDIENTE registra los intentos reales (3, antes decía 1). Modo de caos `llm_timeout` + **guion ensayado con salidas literales** (bloque 4 de la defensa, pedido en la web del 18/09 23:00).
  - **Tercera lectura de los 29 escaneados medida y descartada** (regla fijada antes): qwen 300 dpi NIF 25/29 · IBAN 20/29 en 366 s; deepseek NIF 19/29 · IBAN 14/29 y alucina; 0 regresiones, 0 difíciles resueltos correctamente. Los 5 difíciles, inspeccionados a 220 dpi, son ilegibles o trampas: escalar es correcto en los cinco.
  - **Merge de Miguel integrado** y árbol devuelto a `javier/ingesta` (estaba en `main`). **Caché re-etiquetada p-0.1→p-0.2** (728 lecturas, mismo prompt comprobado por hash): sin eso, `PROMPT_VERSION=p-0.2` las dejaba huérfanas. **`Aviso.NIF_INVALIDO`** en validadores (0 hechos cambian).
- Verificado con (comando → resultado literal):
  - `etapa.contrastar(conn, file_ids=<468>, workers=4)` → `468/468 coinciden · 0 difieren · 0 fallos · 717188 tokens · 472 s`
  - `make check` → 203 verdes tras el merge; al cierre, ver bitácora · `scripts/agentes_check.py --base origin/main` → todos mis ficheros ✓ C1 (los ✗ son del commit de plataforma 90bdca2, previo al ciclo)
  - Guion de timeout (BD y caos aislados): `extract: 0/3 ok · 3 pendientes · errores {'LLM-TIMEOUT': 3}` → eventos `('…', 'pendiente', 3, 'LLM-TIMEOUT')` · hechos 0 · decisiones 0 → `chaos off` → `3/3 ok · llm_texto 3` → repetición `cache 3 · tokens 0/0` · duplicados 0
  - bench texto 8 hilos: 180 s → 16/16 p95 10,9 s y 32/32 p95 16,9 s; 60 s → 16/16 p95 7,9 s y 32/32 p95 16,1 s
- Ficheros tocados: `src/albertitos/extract/{llm,etapa,validadores}.py`, `src/albertitos/sources/chaos.py`, `tests/test_{llm,extract}.py`, `docs/agentes/CONTRASTE-TOTAL.md`, `docs/agentes/{BITACORA,PARTE}.md`. Fixtures de hechos **sin cambios** (ningún hecho cambió: no hay que reimportar).
- Commits (hash · mensaje): 5d24886 timeout + caos + fechas · dc499b8 NIF_INVALIDO · 4b5fe9c timeout por modalidad · b85bd4d intentos en el evento PENDIENTE · (formato) · (cierre: CONTRASTE-TOTAL + parte)
- Descubierto:
  - **La cola de 94 s no se reproduce esta noche** (0 de 96 peticiones de texto > 17 s). El timeout está probado por tests y por timeouts reales en visión, no por esa cola: no afirmarlo en la defensa.
  - **Un timeout único de 60 s cortaba lecturas legítimas de visión** (qwen razona > 60 s sobre imágenes grandes) → timeouts separados por modalidad.
  - **Dos trampas nuevas en escaneadas**: `scan_016` imprime un IBAN legible distinto del maestro (cambio de cuenta) y `scan_023` lleva otra factura superpuesta y un "OK. A." manuscrito.
  - **El interruptor de caos es global** (`dist/chaos.json`): activarlo durante un lote real tumba cualquier extracción en curso. Para ensayar, `ALBERTITOS_CHAOS=<otro>` + `ALBERTITOS_DB=<otra>`.
  - `PROMPT_VERSION` entra en la clave de caché: subirla sin re-etiquetar cuesta ~15 min de visión.
  - El hook `guard_bash` bloquea cualquier comando que combine `rm -r` con una ruta `data/` en otra parte del comando (falso positivo sobre el scratchpad; esquivado sin borrar).
- Pendiente / no llegué a: nada del encargo. `chaos --llm-timeout` en la CLI (cli.py, de Miguel) sigue pedido.
- Necesito de otros (quién · qué · para qué):
  - Miguel · flag `chaos --llm-timeout` en cli.py (hoy: `python -c "from albertitos.sources import chaos; chaos.activar('llm_timeout')"`) · al subir `PROMPT_VERSION` en el futuro, avisar a quien tenga caché (o re-etiquetar como aquí).
  - Mónica · `NIF_INVALIDO` a `ANOMALIAS_HUMANO`; tratar `discrepancia_extractores` como "identificador ilegible o distinto del maestro" → ESCALAR; `fecha=None` → ESCALAR (R4 ya lo hace).
  - C2 · para ADR-0002: 468/468; para ADR-0003: tercera lectura medida y descartada (tabla §5) y los 5 difíciles verificados visualmente.
  - Javier · antes del lote 2, no dejar `dist/chaos.json` activo.
- Riesgos que veo: (1) el contraste valida plantillas contra un LLM que lee la misma capa de texto: un error de capa (texto oculto, caracteres invisibles) lo compartirían ambos; lo cubren validadores + maestro/ERP. (2) Si el lote 2 trae una plantilla nueva, sus facturas irán al LLM (≈ 1 f/s en texto): bien; pero pásales `contrastar(lote=2)` no aplica (no son de plantilla); el riesgo es sólo de tiempo. (3) El caos global puede quedarse activo tras un ensayo.
- Propongo como siguiente tarea: (ciclo 4) `contrastar(lote=2)` y `extract --workers 4` del lote real en el primer cuarto de hora; `chaos --llm-timeout` en la CLI y el caos por BD (no global); inventario de trampas actualizado con `scan_016`/`scan_023`; ensayo del bloque 4 completo (caída + 429 + inválida + timeout) en el portátil de Alfonso.

## C2 · ADRs de ingesta y test de integración del lote 2
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
