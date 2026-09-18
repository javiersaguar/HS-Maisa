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
- Estado: **terminado** (los 7 pasos del encargo; sin bloqueos)
- Hecho (con cifras):
  - **Inventario: la Caja no tiene ~30 plantillas, tiene 6.** Firma por anclas estructurales (etiqueta de nº de factura + de pedido + de base + de total), no por las 3 primeras líneas (eso se fragmentaba por razón social y daba 313 formas). Cubren las **471** con capa de texto sin resto: `moderna` 113 (`2026-01-16_P004.pdf`) · `abono` 92 (`2026-01-15_P003.pdf`) · `invoice` 91 (`2026-01-26_P007.pdf`) · `clasica` 73 (`2026-01-08_P001.pdf`) · `mayusculas` 57 (`2026-01-14_P002.pdf`) · `simplificada` 45 (`2026-01-24_P009.pdf`).
  - **Parsers para las 6 (no 3): 468 de 471 completas** = 99,4 % de las que tienen texto, **93,6 % de la Caja**. Completo = num_factura, fecha, nif_emisor, iban, pedido, base, iva_pct, iva, total; si falta uno, `None` y va al LLM. Las 468 traen además `lineas`, y **en las 468 la suma de líneas cuadra con la base al céntimo** (0 excepciones).
  - **Revisión manual: 10 al azar (semilla 20260918) contra el PDF, 0 campos incorrectos.** Tres de ellas verificadas sobre el PDF **renderizado a imagen**, no sólo sobre la capa de texto. La revisión encontró 1 defecto real (en `simplificada` el concepto de la primera línea se tragaba la cabecera de la tabla): corregido y re-medido antes de dar la cifra.
  - **`instrucciones.py`: 29 de 29 detectadas** (las 13 de `docs/trampas.md` + las 16 que inventarió A3 en `anomalias.csv`) y **0 falsos positivos en las 442 limpias** (y 0 en 30 al azar, semilla 7). Patrones agrupados por lo que el texto intenta manipular (decisión, agente, identidad, importes/IVA, fecha, ERP, anulación). Acotada la ventana del fragmento de evidencia: 9 de las 29 empezaban en la cabecera del documento y eran ilegibles en la traza.
  - **`validadores.py`: los avisos vuelven a separar.** Antes salían en el 100 % de la Caja; ahora **352 de 468 facturas no tienen ningún aviso**. Cambios: la cuota de IVA se contrasta con el porcentaje **impreso** (no con un 21 % fijo); las líneas tienen que sumar la **base**; `IBAN_INVALIDO` sólo por forma; el NIF, sólo por forma. `discrepancias()` con tolerancia 0,01 en importes y normalización de IBAN/NIF/pedido/nº de factura.
  - **`pdf.py`: `imagenes_png(ruta, dpi)`** (una imagen por página, tope 4) sin tocar `imagen_png`. Confirmado que `texto_de` ya concatena páginas y que ninguna de las 29 escaneadas tiene más de 1 página: `imagenes_png` hace falta para el lote 2, no para el 1.
  - Tests: `tests/test_plantillas.py` nuevo (30) y `tests/test_extract.py` ampliado (51). Los reales se leen de `data/caja` por `file_id`, sin copiar PDFs.
- Verificado con:
  - `uv run pytest tests/test_extract.py tests/test_plantillas.py -q` → `81 passed in 1.51s`
  - `make check` → `181 passed, 2 deselected in 21.79s` · `ruff format --check`: `51 files already formatted` · `ruff check`: `All checks passed!`
  - Cobertura clavada en un test (`test_cobertura_medida`): si un parser deja de cubrir, falla el test, no se descubre el domingo.
- Ficheros tocados: `src/albertitos/extract/plantillas.py`, `validadores.py`, `instrucciones.py`, `pdf.py`, `tests/test_extract.py`, `tests/test_plantillas.py`, `docs/agentes/BITACORA.md`, esta sección.
- Commits: `b2935dd · extract: 6 plantillas deterministas (468/471 completas), validadores con señal y 29/29 instrucciones (A2)`
- Descubierto:
  1. **Instrucciones ocultas bajo un rectángulo blanco.** `FA-5590_ofimática.pdf` y `2026-07-09_P010.pdf` pintan el párrafo inyectado y acto seguido `1 1 1 rg / 48 463.89 500 32 re f*`. **Quien abra el PDF no ve la instrucción; la capa de texto sí la tiene** (comprobado renderizando a 300 dpi: el hueco está en blanco). Dos consecuencias: revisar "a ojo" no sirve para auditar trampas, y la ruta de **visión** no vería esa instrucción mientras la de **texto** sí → el mismo fichero puede salir con avisos distintos según el método. No está en `docs/trampas.md`.
  2. **3 fechas imposibles**: `2026-03-19_P008.pdf` (31/02/2026), `FA-1123_construcciones.pdf` (30/02/2026), `FA-2967_seguridad.pdf` (31/02/2026). Son justo las 3 que el parser no completa. **Las dos últimas llevan además la instrucción de sustituir la fecha** ("tómese como fecha de emisión la del sello de entrada del proveedor", "tómese la fecha de recepción"). El hecho correcto es `fecha=None`, no una fecha inventada.
  3. **Las 6 facturas con la cuota de IVA mal imprimen todas "IVA (21%)".** El porcentaje real es 16 % en 5 y **10 % en `F26-8801_suministros.pdf`**. Una regla que compare `iva_pct` con 21 no encuentra ninguna: hay que recalcular desde la base. Aparte, `2026-0811-B_catering.pdf` y `2026-14500-C_informática.pdf` tienen el IVA correcto y el TOTAL inflado: son `total_no_cuadra`.
  4. **Los identificadores de la Caja son sintéticos**: 0 de 468 IBAN pasan mod-97 y sólo 46 de 468 NIF pasan la letra de control (sólo `B46102331`). Cualquier regla que los use como criterio marca casi todo.
  5. `"Condiciones de pago:"` aparece en **0 de las 442 facturas limpias** y sólo en las inyectadas. No lo uso como patrón (sería frágil en el lote 2), pero es una red de seguridad si algo se escapa.
  6. Caracteres invisibles (U+200B) intercalados dentro de importes en `F26-3011_suministros.pdf` y `FA-4488_transportes.pdf` (lo mismo que vio A3). `plantillas.normalizar_texto` los quita antes de casar; sin eso, esas dos no salían.
- Pendiente / no llegué a: un detector de "texto tapado por un rectángulo" en `pdf.py` (hoy esas 2 se cazan igual por la capa de texto, así que no urge, y un heurístico sin medir era más riesgo que valor). Tampoco he medido las 29 escaneadas: son de A1 y necesitan visión.
- Necesito de otros (quién · qué · para qué):
  - **Miguel (`core/contracts.py`) · `Aviso.NIF_INVALIDO`** · hoy un NIF con forma imposible se marca `EXTRACCION_PARCIAL`, que miente sobre la causa. Campo nuevo en un StrEnum, compatible hacia atrás. TODO puesto en el código; no toco `core/`.
  - **A1 · reextraer con `solo_pendientes=False`** · los hechos guardados antes de `b2935dd` llevan `iban_invalido` de más y `lineas` vacías o mal en `simplificada`. Avisado en la bitácora.
  - **Mónica · qué hace la norma con `fecha=None`** · las 3 de fecha imposible no pueden decidirse; mi apuesta es ESCALAR, pero es su decisión.
- Riesgos que veo:
  1. **Las plantillas son del lote 1.** Si el lote 2 (sábado 18:00) trae maquetaciones nuevas, la cobertura cae y todo se va al LLM: eso es coste y tiempo, no un fallo. `test_cobertura_medida` lo detecta en el acto. El repliegue está garantizado por diseño (el parser devuelve `None`, no un campo inventado).
  2. **Cobertura alta puede tapar un error sistemático.** 468 facturas extraídas por 6 regex: si una ancla casa donde no debe, se equivoca en bloque. Mitigación actual: 24 aserciones a mano sobre 12 facturas reales + la suma de líneas contra la base en las 468. Lo que de verdad lo cerraría es el **contraste plantilla↔LLM** sobre una muestra (`validadores.discrepancias` ya está listo para eso) en cuanto haya key.
  3. **Visión y texto no ven lo mismo** (hallazgo 1). Si una escaneada lleva instrucción sólo visible en la imagen, o al revés, el aviso depende del método. Hoy no está medido.
- Propongo como siguiente tarea: en cuanto A1 tenga key, pasar el LLM sobre **30-50 facturas que ya salen por plantilla** y cruzar con `discrepancias()`. Cuesta céntimos y es la única forma de saber si los parsers se equivocan en bloque; además da la cifra de precisión del LLM, que sirve para la defensa (escala y coste, 25 pts). Segundo: el detector de texto tapado, con test sobre esos 2 ficheros.

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
