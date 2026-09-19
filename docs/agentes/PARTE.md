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
- Estado: **terminado** (A y B; 01:48 → 04:10). Lo único abierto es **aplicar el arreglo de `scan_025` a la BD real**, que no he hecho a propósito: cambia una línea del lote 1 y la decisión es de Mónica.
- Hecho (con cifras):
  - **A · `scripts/auditoria_entrega.py`**, sólo lectura, 0,3 s sobre la BD real. 15 comprobaciones. ROJO (sale 1): ficheros fantasma · PDF sin decisión vigente · pago doble · duplicado sin marcar con algún PAGAR · PAGAR que no cuadra con el maestro y el ERP **con que se decidió** (pedido, IBAN, NIF, importe ±0,01, asiento, no PAGADA, importe del ERP, fecha ≤ corte) · decisión tomada con otros hechos · evidencia falsa ("None", cita que no está en el PDF, motivo de R6 que cita otra evidencia) · entrega en disco inválida. ÁMBAR: duplicado sin marcar sin PAGAR · hechos reescritos tras decidir · evidencia no literal · PAGAR con aviso no benigno · reparto > 15 % ESCALAR o > 5 % NO_PAGAR · PAGAR con confianza < 1 · entrega en disco desfasada. `--json` para otros scripts. 11 tests.
  - **B · `DOCUMENTO_SUPERPUESTO`** (`extract/etapa.py::_evidencia_de_lecturas`): la segunda lectura de una escaneada ya no se tira. Un fragmento que nombra a otro proveedor del maestro (razón social de ≥ 2 palabras o NIF exacto) marca el aviso con la evidencia en el evento, no en `texto_sospechoso`. Una instrucción que sólo ve la segunda lectura se adopta si casa con las regex; un sello no. 10 tests.
  - Sobre las 29 escaneadas, en una copia y desde la caché: **0 tokens**; el detector salta en **1 de 29** (`scan_025`: P006 dentro de una factura de P004), que además pierde el `texto_instruccion` falso. `scan_023` no es detectable (ninguna de sus 4 lecturas nombra a otro proveedor).
- Verificado con (comando → resultado literal):
  - `uv run python scripts/auditoria_entrega.py` (BD real) → `VEREDICTO: ROJO · 1 comprobación(es) en rojo` · sólo `scan_025.pdf: texto_sospechoso = 'None' (ESCALAR)` y `el motivo de R6 cita 'None'` · ámbar: 5 PAGAR con confianza 0,6. Exit 1.
  - En la copia `dist/ensayo/e2.db` (backup de SQLite; caos `llm_down` sólo en la copia): `extract --no-solo-pendientes --fixture <29> --workers 4` → `29/29 ok · métodos {'cache': 29} · tokens 0/0 · 42.5 s`; `reprocess --impacted --fecha-corte 2026-09-18 --erp v1` → `29 de 500 recalculadas · 1 cambian · scan_025.pdf: ESCALAR → PAGAR (hechos cambiados)`; auditoría → `VEREDICTO: VERDE` con ámbar `scan_025.pdf: documento_superpuesto`.
  - Con `DOCUMENTO_SUPERPUESTO` en `ANOMALIAS_HUMANO` (simulado en memoria sobre los 500 hechos de la copia, sin guardar): cambia sólo `scan_025.pdf` → ESCALAR `v3.R6: anomalía que debe ver una persona: documento_superpuesto`; reparto 443/48/9.
  - BD real y entrega intactas: `dist/albertitos.db` `9ef061ed2fca` y `outcomes.jsonl` `5ec17aaa5045`, antes y después.
  - `make check` → `332 passed, 2 deselected in 53.24s`. `make agentes-check` → mis 6 ficheros como E2; 6 marcas "NADIE" ajenas (hooks, skill de entrega, `tests/test_hooks.py`, fixture reexportado por E1, `ENSAYO-REPROCESADO.md`, `PLAN-05.md`).
- Ficheros tocados: `scripts/auditoria_entrega.py`, `tests/test_auditoria.py`, `docs/agentes/AUDITORIA-ENTREGA.md`, `src/albertitos/extract/etapa.py`, `tests/test_superpuesto.py`, `docs/trampas.md`, `docs/agentes/BITACORA.md` (3 entradas), esta sección. Datos sólo en `dist/ensayo/e2.db`.
- Commits (hash · mensaje): `63abec8` auditoría · `b678cfd` detector de documentos superpuestos · `511c44a` docs (AUDITORIA-ENTREGA y trampas) · el de este parte.
- Descubierto:
  1. La segunda lectura de `scan_025` sí había visto la otra factura ("Electricidad Montcada S.A. NIF: A48990201 …") y el código la tiraba: la evidencia existía desde el viernes.
  2. Con la v3 de hoy, arreglar `scan_025` la pasa a PAGAR: NIF, IBAN, pedido, importe y asiento cuadran, y `DOCUMENTO_SUPERPUESTO` no está en `ANOMALIAS_HUMANO`.
  3. Las secciones de D2 en `docs/trampas.md` están dentro de los marcadores que `inventario_trampas.py` reescribe sin `--sin-docs`: una regeneración las borraría.
  4. Reextraer las 29 desde la caché tardó 42,5 s con 0 tokens. No lo he investigado (render de 58 imágenes y 4 hilos sobre SQLite, probablemente).
  5. Mi primera entrada de la bitácora salió rota por las comillas de la shell. La reparé y restauré 4 retornos de carro de entradas de A3 que la edición había normalizado: el diff sólo añade.
- Pendiente / no llegué a: aplicar lo de `scan_025` a la BD real (espera a Mónica; comandos al final de `AUDITORIA-ENTREGA.md`) · repetirlo en la copia de E3 (se lo he pasado) · las comprobaciones de PAGAR de la norma v4, cuando llegue la regla nueva.
- Necesito de otros (quién · qué · para qué):
  - **Mónica** · decidir si `DOCUMENTO_SUPERPUESTO` entra en `ANOMALIAS_HUMANO` · que `scan_025` escale con el motivo verdadero y no pase a PAGAR. Recomendación: sí.
  - **Javier** · cuando conteste, los comandos de `AUDITORIA-ENTREGA.md` sobre la BD real, en ese orden, y reexportar el fixture.
  - **Miguel** · que `package` / `/entrega` ejecuten la auditoría y se nieguen si sale 1.
- Riesgos que veo:
  - Si alguien ejecuta `extract --no-solo-pendientes` sobre las escaneadas de la BD real antes de que Mónica decida, `scan_025` pasa a PAGAR sin ruido. La auditoría lo avisa en ámbar, no en rojo.
  - El detector depende de que el modelo escriba el texto superpuesto en `texto_sospechoso`. Con otro modelo, otro prompt o la escaneada de `scan_023`, puede no verlo.
  - Las comprobaciones de PAGAR son las de la v3. Si la regla nueva añade una condición para pagar, la auditoría no la conoce.
  - `pago_doble` sólo salta con dos PAGAR en el mismo grupo. Si la política acaba siendo "pagar una y no la otra", la auditoría no la juzga.
- Propongo como siguiente tarea: tras las 18:00, pasar la auditoría al lote 2 con la v4 y añadirle lo que la regla nueva exija para pagar; y que Miguel la enganche a `package`.

## E3 · Materiales verificados y runbook cronometrado de punta a punta
- Estado: implementación y ensayo **terminados**; cierre global pendiente de conciliar hashes concurrentes y propiedad de ocho rutas ajenas.
- Hecho: verificador ZIP/directorio de sólo lectura con hash publicado, apertura PDF, NFC, colisiones de nombres y SHA, estructura compatible con ingest, CSV tipado y diff contra v1; adjuntos mostrados como datos. Skill lote2 reescrita con preflight, respaldo, hash, manifiesto antes de verify, duplicados, ERP explícito, linaje granular y auditoría antes/después de package.
- Ensayo: copia SQLite en dist/ensayo/ensayo.db; 10 hechos nuevos, 20 marcas de duplicado y **9 originales PAGAR→ESCALAR**. Pull ERP 3 altas/2 cambios; reproceso **2/510**. Primera auditoría roja por scan_025; recuperación cacheada (0 tokens, sin caos, proveedor bloqueado en memoria), reproceso **1/510**, auditoría VERDE. Package APTO **500 + 10 líneas**, sólo en dist/ensayo/entrega. Lote 1 final 433 PAGAR / 57 ESCALAR / 10 NO_PAGAR; lote 2 10 ESCALAR. Ámbar DOCUMENTO_SUPERPUESTO pendiente de Mónica.
- Tiempos: run 1,380 s; pull 3,969 s; diff 0,135 s; reproceso ERP 0,220 s; package final 0,163 s; auditoría final 0,381 s. Primera pasada 7,597 s, caliente, excluye recuperación y pausas. Tabla comparada y receta completa en docs/agentes/ENSAYO-LOTE2.md.
- Verificado: `uv run pytest tests/test_material.py -q` → **21 passed**; `make check` → **323 passed, 9 skipped, 2 deselected**, Ruff verde. Frontmatter YAML válido, conservada política Claude disable-model-invocation.
- `make agentes-check` → **8 problemas** fuera de E3: .claude/hooks/guard_bash.py, .claude/skills/entrega/SKILL.md, data/fixtures/hechos_caja.jsonl, docs/agentes/ENSAYO-REPROCESADO.md, docs/agentes/PLAN-05.md, docs/demo/transcripcion-demo-caos.txt, scripts/demo_caos.py, tests/test_hooks.py. No cambio plan.json ni ficheros ajenos.
- Ficheros: scripts/verificar_material.py, tests/test_material.py, .claude/skills/lote2/SKILL.md, docs/agentes/ENSAYO-LOTE2.md; bitácora append y esta sección.
- Commits: **58fc78f** verificador inicial y tests; **99ca183** protección de identidad; documentación y cierre en el commit que contiene este parte.
- Descubierto: ingest sobrescribe identidad cuando dos nombres comparten SHA; omite .PDF y subcarpetas; run no admite --erp. Verificador bloquea los casos peligrosos; alternativa probada `extract` + `reprocess --todo --erp v1` incluye duplicados. PIDO A Miguel registrado.
- Integridad: E3 sólo escribió artefactos de ejecución en dist/ensayo. **No se puede certificar igualdad global**: durante las sesiones concurrentes cambiaron BD real y PDF (origen no atribuido por E3), y hechos_caja.jsonl (reexportación anunciada por E1). JSONL oficial idéntico; 524/525 archivos de data idénticos y cero nuevos. No se revierten escrituras ajenas.
  - dist/albertitos.db: antes `8c163e859dd63022c10fa55bed116b7a694e026ab8bfc9b6b037bbb5bbf4bcc7`; después `9ef061ed2fca79e82046fce4a78375b3d662d685a6ad05384c31ed88985170c0`.
  - dist/entrega/outcomes.jsonl: antes `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3`; después `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3`.
  - dist/entrega/albertitos_plan.pdf: antes `eaeb1f1f5cf443c56a305ae91514f3d58d8f89b1fa93cb5476c128f925ad8797`; después `a67e695b4e7990ba38fe09e9446eafb35af2482813334e0fb0543967cc4f5218`.
- Necesito de otros: **Javier**, conciliar hashes BD/PDF y las ocho autorizaciones de agentes-check; **Mónica**, política DOCUMENTO_SUPERPUESTO y duplicados entre lotes; **Miguel**, run --erp, identidad por fichero y auditoría integrada en package. No queda implementación pendiente dentro de las rutas E3.

## Javier (a mano, al cerrar el ciclo)
- `make check`:
- `make agentes-check`:
- `git push` (y merge a main):
- Preguntas a mentores pendientes:
