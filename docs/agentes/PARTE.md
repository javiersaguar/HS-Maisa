# Parte de fin de ciclo · ciclo 4

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2).

## D1 · Escala medida a 10.000 facturas
- Estado: **terminado** (00:46 → 01:15). Informe completo en `docs/agentes/ESCALA-10K.md`. Retomé sin nada de la sesión anterior de D1 (no llegó a este árbol): `scripts/bench_escala.py` está reescrito aquí.
- Hecho (con cifras). Portátil de Javier (WSL2, Ryzen 9 8940HX, 24 hilos), commit `95808e2`, **el mismo equipo que B2**:
  - **Pipeline real a 10.000 facturas: 3 min 39 s, pico de 653 MB, JSONL de 10.000 líneas APTO.**
    - ingest 12,4 s (808 f/s);
    - extract con 1 hilo 86,3 s: plantillas p50 1 ms, y el render de las 640 que van al LLM suma 66,4 s;
    - `decide` 20,3 s; package 0,19 s; validar 0,05 s; ERP 3,8 s fijo.
  - **Camino determinista: 57 s por 10.000** (5,7 ms por factura); **39 s con el índice** (3,9 ms).
  - **1 frente a 8 hilos en extract: 86,3 s frente a 89,7 s. 8 hilos no ganan**; la p95 de plantilla sube de 2 a 57 ms, con esperas de hasta 3 s por el bloqueo de escritura de SQLite.
  - **Caminos de LLM medidos sin la caché del gateway** (copias con marca única y el `extraer()` real con doble lectura; 0 respuestas por debajo de 1,7 s en texto ni de 6,7 s en visión):
    - texto: 1,30 f/s (4 hilos) y 1,80 (8);
    - **visión: 0,065 f/s (4) y 0,106 (8)**, p50 de 31-52 s, máximo de 200 s.
  - **T(10k) ≈ 1,5-2,5 h con 1 key**, más del 97 % en visión. **T(100k) ≈ 16 h con 1 key** (~5,5 h con 3). Los tramos de LLM están EXTRAPOLADOS de tandas de 12 y 24.
  - Coste marginal 0 €; suscripción amortizada 0,04 € por factura a 10.000/mes.
  - Umbrales de Postgres, almacén de objetos, cola y Spark, cada uno con su cifra (§9).
- Verificado con (comando → resultado literal):
  - `uv run python scripts/bench_escala.py --n 500 --etiqueta ensayo --workers 1,8` → 11 etapas, `APTO · … · 500 líneas`, 18 s.
  - `/usr/bin/time -v uv run python scripts/bench_escala.py --n 10000 --etiqueta 10k --workers 1,8` → `decide n=10000 20.28 s` · `package … APTO … 10000 líneas` · `Elapsed 3:38.83` · `Maximum resident set size 653244 kB`.
  - `… --n 0 --etiqueta 10k-decide --bd dist/escala/escala-10k-w8.db --decide-variantes`:
    - `reprocesado 67.81 s (plan: SCAN decisiones)`
    - `indice 1.70 s (SEARCH … USING INDEX)`
    - `indice_reprocesado 2.28 s`
  - `… --n 0 --etiqueta llm --llm-vision 24 --llm-texto 12 --workers-llm 4,8`:
    - `texto w4 12/12 9.24 s` · `visión w4 24/24 371.56 s`
    - `texto w8 12/12 6.66 s` · `visión w8 24/24 227.48 s`
    - 0 pendientes, 0 errores, `coste_eur 0`.
  - `make check` → `247 passed, 2 deselected`.
- Ficheros tocados:
  - `scripts/bench_escala.py` (nuevo) y `docs/agentes/ESCALA-10K.md` (nuevo);
  - `docs/agentes/BITACORA.md` (3 entradas) y esta sección;
  - datos sólo en `dist/escala/` (65 MB de BD y JSON; los PDFs los borra el banco).
- Commits: el de cierre de D1 (ver `git log`).
- Descubierto:
  1. **Cuello cuadrático en `db.guardar_decision`.** El `UPDATE decisiones … WHERE sha256=?` no tiene índice y recorre la tabla una vez por decisión. `decide` pasa de 0,07 s a 20,3 s (×280 por ×20 de datos) y a **67,8 s al reprocesar**: el historial crece con cada reprocesado. Con índice, 1,70 s y 2,28 s.
  2. **`por_pedido()` no es el cuello hoy** (0,45 s de 20,3 s), pero crece con el ERP: 28 ms por llamada con 50.000 asientos, ~47 min a 100.000 facturas.
  3. **La visión real va a 0,065-0,106 f/s, no a 0,22.** RESILIENCIA §4 y `docs/benchmark.md` usan la cifra de una sola lectura (`bench_llm.py`); el pipeline hace dos. "10.000 en ~45 min" es optimista 2-3 veces. La cola de 94 s de texto con 8 hilos no apareció.
  4. RAM a 10k: `marcar_duplicados` usa 7 KB por factura y `package` 3,7 KB; con 1 M de facturas serían ~7 y ~4 GB (EXTRAPOLADO). Por debajo de eso, no importa.
- Pendiente / no llegué a:
  - una pasada entera de 10k con el índice (medido sólo `decide` sobre copias);
  - procesos en paralelo en el camino determinista;
  - aislar GIL frente a bloqueo de SQLite en 8 hilos;
  - el portátil de la demo (Alfonso);
  - el ERP con latencia real.
- Necesito de otros (quién · qué · para qué):
  - **Miguel** · `CREATE INDEX IF NOT EXISTS ix_decisiones_sha ON decisiones(sha256, vigente);` en `core/schema.sql` · que `decide`/`reprocess` sean lineales; una línea idempotente que no cambia ningún resultado. También · corregir en `docs/benchmark.md` la extrapolación de visión (0,22 → 0,065-0,106 f/s con la doble lectura).
  - **Mónica / Miguel** · construir `erp.por_pedido()` una vez por `decide` y pasarlo a la regla · que el ERP pueda crecer sin que `decide` se vuelva cuadrático.
  - **Alfonso** · plan § "Escala, evolución y coste": las 5 líneas del resumen de `ESCALA-10K.md`, y decir "en el portátil de desarrollo".
  - **Javier** · en `docs/agentes/plan.json`, `scripts/escala_sintetica.py` → `scripts/bench_escala.py` (única marca ✗ de D1 en `agentes-check`).
- Riesgos que veo:
  - Los tramos de LLM a 10k y 100k salen de tandas de 24 y 12, y la latencia del gateway varía por hora: la p50 de visión fue de 31 s con 4 hilos y de 52 s con 8, con la misma noche y el mismo modelo. Defended el rango, no el punto.
  - `docs/benchmark.md` y RESILIENCIA §4 contradicen hoy esta cifra de visión: que el tribunal no vea dos números distintos.
- Propongo como siguiente tarea:
  - Miguel mete el índice y se repite `bench_escala.py --n 10000` para tener la pasada entera medida (4 min);
  - con el lote 2, la misma medida sobre sus 40 facturas;
  - si hay tiempo el sábado, medir 4 procesos × 2.500 contra 1 × 10.000 para cerrar el §3.

## D2 · Evidencia completa para la demo y trampas al día
- Estado: **terminado** (los 4 pasos; 00:14 → 01:10). Queda **un test ajeno en rojo** con parche de una línea propuesto (ver "Necesito de otros").
- Hecho (con cifras):
  - **Tramo instructivo completo** (`extract/instrucciones.py`): empieza en la frase de la instrucción saltando los importes que la preceden y termina en el pie legal, en la siguiente línea de importes o a los 300 caracteres. Antes se devolvía sólo la frase de la coincidencia y **en 11 de las 27 facturas de plantilla se perdía la orden**. Ahora las 29 con instrucción en capa de texto la incluyen.
  - **Tests**: tabla `ORDENES` con la orden exacta que debe contener cada una de las 29 (una por fichero), sin empezar por importe y ≤ 300 caracteres; 0 falsos positivos en 60 facturas limpias; `MAX_TRAMO` sustituye al tope de 240 en el test de A2.
  - **Falso positivo destapado**: las instrucciones inyectadas son **31, no 32**. `scan_025.pdf` no tiene ninguna; el modelo devolvió la cadena `"None"` y el código la tomó por instrucción (hoy se escala con el motivo `el documento dice: "None"`). Arreglado en `llm.py` (`_fragmento_valido`) con 8 casos de prueba. **No he reextraído `scan_025`**: quitarle el aviso podría pasarla de ESCALAR a PAGAR y la factura lleva otra transparentándose por detrás; es decisión de norma.
  - **Reextracción**: 29 facturas en 0,2 s, 0 tokens, 0 € · **15 fragmentos actualizados · 0 avisos cambian → ninguna huella de hechos cambia** (ninguna decisión queda invalidada, pero la traza guardada cita el fragmento viejo hasta que se ejecute `decide`).
  - **Fixtures reexportados**: `hechos_caja.jsonl` con **500** hechos (la exportación anterior incluía por error los 10 del lote 2 simulado de B1) y `hechos_muestra.jsonl` con 21.
  - **Caos por BD** (`sources/chaos.py`): el fichero vive junto a su base de datos (`<db>.chaos.json`) y se resuelve en cada llamada; `ALBERTITOS_CHAOS` sigue mandando. Test de aislamiento: el caos de una BD de ensayo no afecta a otra. Aviso del guion actualizado en `CONTRASTE-TOTAL.md` §7.
  - **`docs/trampas.md`**: recuento corregido (31), las 11 órdenes que se perdían, y tabla de trampas de escaneadas verificadas a 220 dpi (`scan_016` cambio de cuenta, `scan_023` documento contaminado, `scan_021` NIF tapado, `scan_025` transparencia invertida sin instrucción).
- Verificado con (comando → resultado literal):
  - `uv run pytest tests/test_extract.py tests/test_llm.py -q` → `117 passed, 2 deselected`
  - `uv run albertitos extract --no-solo-pendientes --fixture <29 de texto> --workers 4` → `29/29 ok · plantilla 27 · cache 2 · tokens 0/0 · 0.0000 EUR · 0.2 s`
  - `grep -c 'Debe escalarse cualquier factura suya' data/fixtures/hechos_caja.jsonl` → `1` (antes: 0)
  - `make check` → **1 fallo ajeno**: `tests/test_lote2_sim.py::test_extract_con_el_llm_caido…` (de C2)
- Ficheros tocados: `src/albertitos/extract/{instrucciones,llm}.py`, `src/albertitos/sources/chaos.py`, `tests/test_{extract,llm}.py`, `data/fixtures/hechos_{caja,muestra}.jsonl`, `docs/trampas.md`, `docs/agentes/CONTRASTE-TOTAL.md`, `docs/agentes/{BITACORA,PARTE}.md`
- Commits (hash · mensaje): (este ciclo) `extract: tramo instructivo completo, fragmento vacío no es instrucción y caos por BD (D2)`
- Descubierto:
  - El campo `texto_sospechoso` del LLM viene con la palabra `"None"` en **838 lecturas cacheadas**; sólo afectaba a un hecho guardado, pero con el lote 2 volvería a pasar.
  - `scan_025.pdf` y `scan_023.pdf` comparten trampa: **otro documento transparentándose** (en `scan_025`, invertido, con sello "URGENTE"). No hay aviso honesto para eso en `core`.
  - La exportación de fixtures arrastraba los 10 ficheros del lote 2 simulado: cualquiera que importara `hechos_caja.jsonl` se traía hechos de ficheros que no tiene.
- Hecho después (mientras terminaba D1, con permiso de Javier):
  - **CI desbloqueada**: parche de una línea en `tests/test_lote2_sim.py` (cita literal con espacios normalizados). `make check` verde, 247 tests.
  - **Adelanto de Mónica** en `rules/norma_v3.py`: evidencia a 300 caracteres y `NIF_INVALIDO` en `ANOMALIAS_HUMANO`; 0 decisiones cambian. Dossier con los ficheros afectados por cada política abierta en `docs/agentes/DECISIONES-NORMA.md`.
  - **`marcar_duplicados` nunca se había ejecutado**: `PO-2026-0492` está facturado dos veces (`factura_41082.pdf` y `2026-0233-A_catering.pdf`, 1.512,50 € cada una) y **ambas estaban en PAGAR**. Ejecutado el paso + `decide` completo → ambas ESCALAR. Reparto: **443 PAGAR · 48 ESCALAR · 9 NO_PAGAR**; sólo esas 2 cambian en toda la noche. Antes hubo que limpiar de la BD los 10 ficheros del lote 2 simulado, que hacían pasar por duplicados a sus originales del lote 1 (20 decisiones tocadas) — la limpieza del paso 0 de la skill `/lote2` es obligatoria antes del lote real.
  - **Auditoría de los 443 PAGAR**: 0 avisos no benignos y 0 incoherencias en seis comprobaciones duras contra maestro y ERP.
  - **Barrido de documentos superpuestos** en las 29 escaneadas usando sólo lecturas cacheadas (sin gastar llamadas, para no falsear la medición de D1): únicamente `scan_025` da indicios de un segundo proveedor.
  - **`--con-hechos` en `scripts/inventario_trampas.py`** (lo que quedaba pendiente): el inventario ya incluye lo que sólo ve la extracción; probado sobre la Caja (239 filas, 1,04 s) y documentado para el lote 2 en `docs/trampas.md`.
- Pendiente / no llegué a: el test de los dos cambios de norma en `tests/test_rules.py` (fichero de Mónica) y la reextracción de `scan_025`, que espera al aviso `DOCUMENTO_SUPERPUESTO` de Miguel.
- Necesito de otros (quién · qué · para qué):
  - **Javier / dueño de `tests/test_lote2_sim.py`** (de C2; no está en mi lista y no lo toco): el test exige cita literal sobre el texto crudo y el tramo ya cruza un salto de línea. Parche: `assert trampa.texto_sospechoso in " ".join(pdf.texto_de(LOTE2_SIM / CON_INSTRUCCION).split())`. Sin eso `make check` queda rojo.
  - **Miguel**: `Aviso.DOCUMENTO_SUPERPUESTO` en core; y tras reimportar los fixtures, **`decide` completo** (no `reprocess --impacted`), porque la evidencia no entra en la huella de los hechos.
  - **Mónica**: R6 a 300 caracteres (hoy 120 y el tramo de F26-2201 mide 127); `NIF_INVALIDO` en `ANOMALIAS_HUMANO`; política para documento superpuesto.
- Riesgos que veo: (1) si nadie ejecuta `decide` completo, la demo del minuto 0-2 seguirá citando el fragmento viejo aunque los hechos ya estén bien; (2) `scan_025` sigue escalando por un motivo falso hasta que exista el aviso nuevo: es seguro (escala), pero es una traza que el tribunal puede preguntar; (3) el tramo más largo (269 c) se acerca al tope de 300: si el lote 2 trae párrafos más largos, se cortarán (se marca con "…").
- Propongo como siguiente tarea: (ciclo 5) `--con-hechos` en el inventario y pasarlo al lote 2 en cuanto llegue; revisar con Mónica los 31 fragmentos uno a uno en la muestra etiquetada; y un repaso de las 29 escaneadas buscando más documentos superpuestos.

## Javier (a mano, al cerrar el ciclo)
- `make check`:
- `make agentes-check`:
- `git push` (y merge a main por Miguel):
- Preguntas a mentores pendientes:
