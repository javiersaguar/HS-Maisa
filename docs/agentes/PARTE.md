# Parte de fin de ciclo · ciclo 5

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2).

## E1 · Preflight, breaker y documentación
- Estado: **terminado** (A, B y C; 01:50 → 02:20)
- Hecho (con cifras):
  - **A · Preflight.** `sources/estado_bd.py` (funciones puras: `ficheros_fantasma`, `ficheros_sin_hechos`, `ficheros_sin_decision`, `hechos_huerfanos`, `ultimo_erp`, `resumen_estado`) y `scripts/preflight_lote2.py`: 9 comprobaciones con semáforo, el comando exacto para arreglar cada una, y salida 1 si hay rojo. Sólo lee salvo `--limpiar` (borra lo fantasma y sus eventos/decisiones/hechos) y `--respaldar` (copia con la API de backup de SQLite, no `cp`). Contra la BD real: **todo verde** tras crear la copia.
  - **B · Circuit breaker.** `_comprobar_disponible` lanzaba `LLM-DOWN` **antes** de contar el fallo, así que con una caída el breaker no se abría nunca. Ahora una caída simulada cuenta igual que una real (y sigue siendo instantánea, sin backoff), el breaker se comprueba **antes de cada intento** (corta también a los hilos que ya habían pasado), y umbral/ventana son configurables (`ALBERTITOS_BREAKER_FALLOS`, `ALBERTITOS_BREAKER_SEGUNDOS`) con los valores de siempre.
  - **C · Documentación.** ADR-0005 con la cifra buena del reprocesado (2 de 500 en 0,04 s; la vieja queda sólo como evolución), ADR-0002 con el contraste ya medido (468/468), `RESILIENCIA §4` con nota de corrección sobre la visión, `RESILIENCIA §3` con el comando reproducible del breaker, y los dos `CLAUDE.md` de módulo reescritos al estado real (dueño, 6 plantillas, doble lectura y reconciliación, gateway por httpx, caché por variante, timeouts 60/90 s, caos por BD, breaker, `estado_bd`).
- Verificado con (comando → resultado literal):
  - `uv run python scripts/preflight_lote2.py` → 9 comprobaciones, `Todo en verde: puedes seguir con el lote 2` (exit 0). Antes de `--respaldar` salía 1 aviso ámbar por no haber copia.
  - `uv run albertitos extract --fixture dist/ensayo/ocho_escaneadas.txt --workers 1` con `llm_down` → `errores {'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3} · 0.5 s`, con los eventos `LLM-CIRCUIT-OPEN: 5 fallos seguidos; reabre en 60s`
  - `uv run pytest tests/test_preflight.py -q` → `6 passed` · `tests/test_llm.py` → `40 passed`
  - `uv run pytest tests/test_lote2_sim.py tests/test_pipeline.py -q` (ajenos, sin tocarlos) → verdes
  - `uv run python scripts/bench_escala.py --n 500 --etiqueta e1 --workers 1` → todas las etapas, **13,3 s** (D1 midió 18 s)
  - `make check` → **299 passed**
- Ficheros tocados: `src/albertitos/sources/estado_bd.py`, `scripts/preflight_lote2.py`, `tests/test_preflight.py`, `src/albertitos/extract/llm.py`, `tests/test_llm.py`, `src/albertitos/{extract,sources}/CLAUDE.md`, `docs/adr/0002-*`, `docs/adr/0005-*`, `docs/agentes/RESILIENCIA-Y-COSTE.md`
- Commits: `e9cbe1e` preflight · `f760184` breaker · `95fc261` documentación · (cierre) RESILIENCIA §3 y parte
- Descubierto:
  - **El riesgo del snapshot del ERP es real pero hoy no está activo**: el más reciente es `v1` (E2 lo confirmó). En cuanto alguien haga `erp pull --tag v2-sim`, `decide`/`run` sin `--erp` decidirían con el simulado. El preflight lo vigila (`--erp-esperado`).
  - **Los hechos huérfanos no se pueden crear por la vía normal** (hay clave foránea), pero sí con el `DELETE` que documenta la skill: el cliente `sqlite3` no activa las claves foráneas. El test lo reproduce así.
  - `make demo-caos` fija 3 hilos y 3 facturas: con el umbral de 5, el breaker no llega a verse ahí (los tres entran antes de que ninguno falle). Por eso el comando de §3 usa 8 escaneadas y un hilo.
  - No hay copia de seguridad de la BD en ningún runbook. Ya existe `dist/albertitos.db.bak` (7,7 MB, API de backup).
- Hecho después (mientras terminaban E2 y E3):
  - **Tres comprobaciones más en el preflight**, con tests: *entorno* (variables de un ensayo aún exportadas; con `ALBERTITOS_BREAKER_FALLOS=2` una pasada real se cortaría a los dos fallos → rojo, era el riesgo que yo mismo había dejado abierto), *caché del LLM* (lecturas de otra versión de prompt) y *fixture vs BD*.
  - **La comprobación nueva encontró un fallo real de elegibilidad**: `data/fixtures/hechos_caja.jsonl` estaba sin reexportar desde `marcar_duplicados`, así que quien lo importara devolvía a PAGAR `2026-0233-A_catering.pdf` y `factura_41082.pdf` (el mismo pedido, 1.512,50 € dos veces). Reexportado; el preflight sale **todo en verde**.
  - **El modelo de respaldo no se usaba nunca**: su llamada pasaba por el breaker, que para entonces ya estaba abierto por los 3 intentos fallidos del principal. Ahora se salta el breaker (sus propios fallos siguen contando). Con test y documentado en `RESILIENCIA §3 (e)`.
- Pendiente / no llegué a: nada de mi encargo.
- Necesito de otros (quién · qué · para qué):
  - **E3**: el preflight ya acepta `--db`, `--dir-lote1`, `--dir-lote2`, `--fixture`, `--erp-url`, `--erp-lote2`, `--erp-esperado`, `--limpiar` y `--respaldar`; llámalo con `--db dist/ensayo/ensayo.db` y los directorios del simulado y no verás falsos fantasmas.
  - **Miguel**: `demo_caos.py` fija `ALBERTITOS_WORKERS=3`; si aceptara el valor del entorno, la demo podría enseñar el breaker sin bajar el umbral. Y `ALBERTITOS_BREAKER_FALLOS`/`_SEGUNDOS` deberían ir a `.env.example` (no es mío).
  - **Alfonso**: para el minuto 8-10 usa el comando de `RESILIENCIA §3 (b bis)`: 8 escaneadas, un hilo, 0,8 s, y se ve el paso de `LLM-DOWN` a `LLM-CIRCUIT-OPEN`. Es más claro que el de `llm-invalid`, que tarda 23 s.
- Riesgos que veo: (1) bajar el umbral por entorno en la demo y olvidarlo puesto en una pasada real haría que el lote se cortara a los 2 fallos: el preflight **no** lo detecta (queda para el ciclo 6); (2) el preflight comprueba el ERP por HTTP: si alguien lo arranca en otro puerto, hay que pasarle `--erp-url`.
- Propongo como siguiente tarea: que el preflight avise si `ALBERTITOS_BREAKER_FALLOS` o los timeouts están fuera de sus valores por defecto, y engancharlo a la skill `/lote2` como paso 0 (eso es de E3).

## E2 · Auditoría de entrega: que no se cuele un PAGAR que no toca
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

## E3 · Materiales verificados y runbook cronometrado de punta a punta
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
- `git push` (y merge a main):
- Preguntas a mentores pendientes:
