# Bitácora de agentes · SÓLO AÑADIR AL FINAL

Tres agentes trabajan a la vez en este directorio y esta rama, en ficheros distintos. Esta bitácora es su
único canal. Reglas: (1) añade tu entrada al final, nunca edites ni borres las de otros; (2) una entrada al
empezar, una por hito y una al terminar; (3) antes de cada hito, lee las entradas nuevas de los demás;
(4) si necesitas algo de otro agente, pídelo aquí con `PIDO A A2:`; el otro responde con `RESPONDO A A1:`.

Plantilla (cópiala tal cual):

```
### HH:MM · A1 · <hito en 5 palabras>
- hice: 
- toco ahora (ficheros): 
- necesito / bloqueo: 
- para los demás: 
```

---

### 20:40 · plataforma · ciclo 1 abierto
- hice: plan en `docs/agentes/PLAN-01.md`; `extract/etapa.py` con la firma congelada; `albertitos hechos export/import`.
- toco ahora (ficheros): nada más; a partir de aquí escriben A1, A2 y A3.
- necesito / bloqueo: A1 necesita `ANTHROPIC_API_KEY` en `.env` (Javier).
- para los demás: la Caja oficial sale a las 21:00; si `make caja-verify` falla, Javier sustituye `data/caja` y avisa aquí.

### 20:41 · A2 · arranco plantillas/validadores
- hice: leídos CLAUDE.md, extract/CLAUDE.md, .claude/rules/texto-es-dato.md, docs/trampas.md y el estado actual de plantillas.py / validadores.py / instrucciones.py / pdf.py.
- toco ahora (ficheros): ninguno todavía; primero el inventario de firmas de plantilla sobre las 471 con texto (script de exploración en /tmp, no se commitea).
- necesito / bloqueo: nada. Firmas congeladas como contrato: `extraer_por_plantilla(texto, *, file_id, sha256)`, `validar(h)`, `discrepancias(a, b)`, `detectar_instruccion(texto)`, `menciona_anulacion(texto)`.
- para los demás: A3, cuando publiques `data/fixtures/anomalias.csv` avísame aquí y meto sus tipos en `instrucciones.PATRONES` y en los tests. A1: no toco etapa.py ni llm.py.

### 20:42 · A1 · arranco LLM + etapa extract
- hice: leídos CLAUDE.md, extract/CLAUDE.md, texto-es-dato.md, trampas.md; comprobado estado: rama javier/ingesta, 500 ficheros ingeridos, cache_llm=0.
- toco ahora (ficheros): src/albertitos/extract/etapa.py (implemento `extraer()`), tests/test_llm.py (tests sin red: caché, caos, plantilla). llm.py sólo si la firma del SDK lo exige.
- necesito / bloqueo: **PIDO A Javier: `ANTHROPIC_API_KEY` real en `.env`** (hoy es el placeholder `sk-ant-...`). Sin ella no puedo hacer los pasos 1, 2, 4, 5 y 8 (muestra de 21, hechos_muestra.jsonl, las 500). Mientras, dejo `extraer()` listo y probado con caché simulada y caos.
- para los demás: A2, `extraer()` llamará a `plantillas.extraer_por_plantilla(texto, file_id=..., sha256=...)` y, si devuelve hechos, NO llama al LLM; luego siempre `validadores.validar(h)`. Si el LLM también corrió (modo contraste, desactivado por defecto), usaré `validadores.discrepancias`.

### 20:42 · A3 · arranco fuentes e inventario
- hice: leídos encargo, reglas y bitácora; rama javier/ingesta confirmada. BD con 500 ficheros y descarga previa ERP (27 ok, 3 retry); verificaré tags antes de repetir pulls.
- toco ahora (ficheros): sources/erp.py y test_erp.py; sources/excel.py y test_excel.py; sources/snapshot.py y test_snapshot.py; script, fixtures y docs A3. Subtareas internas separadas por fichero.
- necesito / bloqueo: PIDO A Javier: confirmar ZIP/hash oficial después de las 21:00; el inventario inicial corresponde a la Caja ya presente, no acredita publicación oficial.
- para los demás: A2, publicaré pronto anomalias.csv y cifras aquí. Bridge v1 arrancado --rapido en 8009 porque no respondía; permanece arriba. No leo ni muestro la key LLM.

### 20:45 · A3 · más instrucciones encontradas
- hice: confirmados snapshots ya existentes maestro 80911e429c6c y ERP v1; no repito descargas. Barrido inicial de las 500 encuentra más instrucciones que las 13 documentadas: falsear fecha inválida (FA-1123_construcciones.pdf, FA-2967_seguridad.pdf), dar alta proveedor y pagar (factura_4485.pdf, factura_7265.pdf), ignorar ERP (2026-06-04_P006.pdf, 2026-07-08_P010.pdf, factura_5911.pdf), presión emocional (FA-5044_mensajería2.pdf, FA-9104_electricidad.pdf).
- toco ahora (ficheros): scripts/inventario_trampas.py y anomalias.csv; sources y sus tests en subtareas A3.
- necesito / bloqueo: ninguno.
- para los demás: A2, inspecciona también estos patrones; el CSV dará cifras completas. Detectados caracteres invisibles en IBAN de F26-3011_suministros.pdf y TOTAL de FA-4488_transportes.pdf; son datos, no instrucciones ejecutables.

### 20:58 · A1 · extraer() implementada y probada sin red
- hice: `extract/etapa.py::extraer` completa (candidatos, plantilla→LLM texto/visión, validadores, hechos + evento OK, ErrorLLM→PENDIENTE con error_codigo, `--fixture`, `workers` con conexión por hilo). `llm.py`: estado compartido `EstadoLLM` (presupuesto, circuit breaker, cliente HTTP) con lock para hilos; firma del SDK 1.7 verificada. `tests/test_llm.py`: 9 tests sin red (caché, caos, plantilla, respuesta inválida ×3 intentos, API simulada, visión, trampa como evidencia, workers, presupuesto) + 2 marcados `llm` contra la API real. `make check` 103 verdes.
- verificado: `chaos --llm-down` + `extract --fixture muestra.txt` → `18/21 ok (plantilla) · 3 pendientes LLM-DOWN · 0 EUR · 0.6 s`; `chaos --off`; 482 candidatos siguen pendientes, nada decidido. Esos 18 hechos ya están en `dist/albertitos.db` gracias a las plantillas de A2.
- toco ahora (ficheros): nada hasta tener key. Después: pasos 1-2 (una de texto, una escaneada), 4-5 (muestra + `hechos_muestra.jsonl`), 8 (las 500).
- necesito / bloqueo: **sigo sin `ANTHROPIC_API_KEY` real** (placeholder en .env). PIDO A Javier.
- para los demás: A2 → (1) tus plantillas ya cubren 18/21 de la muestra a coste 0, enhorabuena; cuando cambies un parser avísame para reextraer con `solo_pendientes=False` (los hechos de plantilla no se recalculan solos). (2) Los 11 IBAN del maestro FALLAN mod-97 (sintéticos): `Aviso.IBAN_INVALIDO` sale en toda la Caja; propongo quitarlo o dejarlo sólo si el formato es imposible (longitud/país), y decírselo a Mónica. A3 → he visto tus cambios en sources/ y test_snapshot: no los toco.

### 20:53 · A3 · fuentes probadas y lote preparado
- hice: maestro real 11 proveedores / 516 pedidos / 41 avisos; loader mantiene versión 80911e429c6c. Tests nuevos prueban cierre de libros, duplicados conflictivos y normalización. Diff ya incluye pedidos eliminados y pedido anterior al reasignar asiento.
- toco ahora (ficheros): inventario CSV/docs, pruebas de integración A3.
- necesito / bloqueo: ninguno. Puerto 8010 pertenece a otro servicio y no se toca; bridge lote2 simulado arriba en http://127.0.0.1:8011 (PID WSL 2168965).
- para los demás: crearé snapshot v2-sim para ensayar diff; es SIMULADO y no es el ERP oficial. A1/Miguel usad explícitamente ERP v1 para las decisiones del lote 1. CSV erp_lote2_simulado.csv listo para ensayar reprocess (3 nuevos, 2 cambiados).

### 21:01 · A3 · CSV de anomalías disponible
- hice: primer inventario completo en 0,93 s: 500 PDFs, 471 con texto/29 sin texto; 192 filas en 154 ficheros, nueve campos cubiertos en los 471 salvo 3 fechas imposibles (sin campos omitidos ni ambiguos).
- toco ahora (ficheros): revisión del inventario y docs/trampas.md; validación final de ERP/diff.
- necesito / bloqueo: PIDO A Javier: confirmar procedencia/hash oficial de la Caja antes de tratar estas cifras como oficiales.
- para los demás: A2/Mónica, data/fixtures/anomalias.csv YA está disponible: fecha_en_letra 90, texto_instruccion 29 (incluye las 13 conocidas), sin_texto 29, importe_distinto_pedido 13, iban_distinto_maestro 8, cuota_iva_no_cuadra 6, fecha_invalida 3, pedido_inexistente 3, nif_fuera_maestro 3, pedido_repetido 2 (un grupo), nif_distinto_pedido 2, total_no_cuadra 2, caracteres_invisibles 2. Ninguna fecha futura al corte 2026-09-18 ni duplicado (NIF,número) entre los 471 legibles. IVA impreso dice 21% en todos: las 6 cuotas incorrectas NO deben confundirse con 0 incidencias de IVA.

### 21:02 · A1 · hechos_muestra.jsonl PARCIAL publicado (18/21, plantilla)
- hice: `data/fixtures/hechos_muestra.jsonl` con los 18 hechos que las plantillas de A2 resolvieron sin LLM (verificado 2026-01-08_P001 contra el PDF: num 2026/11604, pedido PO-2026-0096, total 3012.89). Faltan las 3 escaneadas (scan_001, fax_2026_0411, copia_2026_0518): necesitan visión → key.
- toco ahora (ficheros): nada; espero key.
- necesito / bloqueo: PIDO A Javier: `ANTHROPIC_API_KEY`. En cuanto esté, reextraigo la muestra, reviso 5 a mano y reexporto las 21.
- para los demás: Mónica/Miguel → `uv run albertitos hechos import data/fixtures/hechos_muestra.jsonl` ya carga 18 hechos reales (tras `make db && uv run albertitos ingest`). Ojo: llevan `iban_invalido` en avisos por los IBAN sintéticos (ver entrada de 20:58).

### 20:47 · A3 · cruce y diff confirmados
- hice: ERP v2-sim real: 519 asientos, 30 consultas, 2 reintentos; diff v1→v2-sim confirma AS-SIM-00001..3 nuevos, AS-00001 PENDIENTE→PAGADA y AS-00002 10325.90→10449.35. Cinco pedidos afectados.
- toco ahora (ficheros): revisión final y pruebas A3.
- necesito / bloqueo: ninguno para A3; validación oficial del ZIP sigue pendiente de Javier.
- para los demás: Excel↔v1 contiene 0 pedidos sin asiento, 0 asientos sin pedido, 0 diferencias de importe, pero 17 ProveedorID distintos entre los 20 pedidos sin NIF. Los 9 PAGADA y todos sus PDFs están listados en docs/trampas.md. Aclaro un error de transcripción mío: las entradas A3 rotuladas 20:53 y 21:01 se escribieron antes de las 21:00; la hora comprobada ahora es 20:47 Madrid. No acreditan publicación oficial.

### 21:20 · A2 · inventario de plantillas: 6 familias, 468/471
- hice: **la Caja no tiene ~30 plantillas: tiene 6**. Firma = anclas estructurales (etiqueta de nº de factura + de pedido + de base + de total), no las 3 primeras líneas (eso se fragmentaba por razón social). Cubren las 471 con texto sin resto:

  | # | familia | n | ejemplo | anclas |
  |---|---|---|---|---|
  | 1 | `moderna` | 113 | `2026-01-16_P004.pdf` | `FACTURA Nº:` · `Ref. Pedido:` · `Base imponible:` · `TOTAL:` |
  | 2 | `abono` | 92 | `2026-01-15_P003.pdf` | `Nº de factura:` · `Su pedido:` · `Importe base:` · `Total factura:` |
  | 3 | `invoice` | 91 | `2026-01-26_P007.pdf` | `Invoice #` · `PO:` · `Subtotal:` · `TOTAL A PAGAR:` |
  | 4 | `clasica` | 73 | `2026-01-08_P001.pdf` | `FACTURA` + `Factura:` · `Pedido:` · `Base:` · `TOTAL:` |
  | 5 | `mayusculas` | 57 | `2026-01-14_P002.pdf` | `REF FACTURA:` · `PEDIDO CLIENTE:` · `BASE IMPONIBLE....` · `TOTAL....` |
  | 6 | `simplificada` | 45 | `2026-01-24_P009.pdf` | `FACTURA SIMPLIFICADA Nº` · `Pedido asociado:` · `BASE IMPONIBLE:` · `IMPORTE TOTAL:` |

  Las 22 de 2 páginas son **todas** de la familia 1, y llevan base/IVA/total en la página 2 (la 1 acaba en `Suma y sigue:`, que NO es el total). `pdf.texto_de` ya concatena páginas: verificado con `2026-01-25_P001.pdf` (57 líneas, total 5.817,98 de la p. 2).
- cifras: **468 de 471 salen COMPLETAS** (num_factura, fecha, nif, iban, pedido, base, iva_pct, iva, total) = 99,4 % de las que tienen texto, 93,6 % de la Caja. Las 468 traen además `lineas`, y en las 468 la suma de líneas cuadra con la base al céntimo (0 excepciones). 10 revisadas a mano contra el PDF renderizado: 0 campos incorrectos (había 1 defecto en `simplificada`, el concepto se tragaba la cabecera de la tabla, corregido antes de medir).
- toco ahora (ficheros): plantillas.py (hecho), instrucciones.py (hecho), ahora validadores.py y pdf.py; luego tests.
- **DOS HALLAZGOS NUEVOS, no están en docs/trampas.md:**
  1. **Texto inyectado tapado con un rectángulo blanco.** En `FA-5590_ofimática.pdf` y `2026-07-09_P010.pdf` el flujo del PDF pinta el párrafo y justo después `1 1 1 rg / 48 463.89 500 32 re f*`: un rectángulo blanco encima. **Quien abra el PDF no ve la instrucción; la capa de texto sí la tiene.** Consecuencias: (a) revisar "a ojo" no vale para auditar trampas; (b) la ruta de VISIÓN no vería esa instrucción y la de TEXTO sí → dos métodos pueden dar avisos distintos para el mismo fichero. **PIDO A A1:** si reextraes algo con visión, no des por bueno que visión y texto coinciden en `texto_instruccion`. **PIDO A Javier:** vale la pena decírselo a Mónica (es argumento de defensa: "el LLM no decide" también cubre lo que un humano no puede ver).
  2. **3 fechas imposibles**: `2026-03-19_P008.pdf` (31/02/2026), `FA-1123_construcciones.pdf` (30/02/2026), `FA-2967_seguridad.pdf` (31/02/2026). Son exactamente las 3 que mi parser NO completa (`parse_fecha_es` devuelve None, correcto). Coincide con `fecha_invalida` de A3. **Las 2 últimas llevan además la instrucción de sustituir la fecha** ("tómese como fecha de emisión la del sello de entrada", "tómese la fecha de recepción"). **PIDO A A1:** al mandarlas al LLM, vigila que no se invente un 28/02: el hecho correcto es `fecha=None` + campo_ausente. **PIDO A Javier/Mónica:** la norma debería ESCALAR fecha ilegible, no rellenarla.
- instrucciones.py ampliado con los patrones de `anomalias.csv` de A3: **29 de 29 detectadas** (las 13 de trampas.md + las 16 de A3) y **0 falsos positivos en las 442 limpias** (y 0 en 30 al azar, semilla 7). Dato útil: `"Condiciones de pago:"` aparece en 0 de las 442 limpias y sólo en inyectadas; no lo uso como patrón (sería frágil para el lote 2) pero sirve de red de seguridad si hiciera falta. También acoté la ventana del fragmento: antes 9 evidencias empezaban en la cabecera del documento y no se entendían.
- necesito / bloqueo: nada.
- para los demás: A1 → ya puedes contar con ~468 por plantilla a coste 0 sobre las 500 (las 29 escaneadas + las 3 de fecha imposible van al LLM). Cuando cierre validadores te aviso para reextraer con `solo_pendientes=False`. A3 → tu `anomalias.csv` me ha servido tal cual, gracias; te devuelvo los 2 hallazgos de arriba por si los quieres en `docs/trampas.md` (yo no lo toco).

### 20:55 · A2 · validadores con señal + tests verdes + commit
- hice: `validadores.py` reescrito, `pdf.py::imagenes_png`, `tests/test_plantillas.py` nuevo (30 tests) y `tests/test_extract.py` ampliado (51). Commit `b2935dd` con mis 6 ficheros y rutas explícitas.
- verificado: `uv run pytest tests/test_extract.py tests/test_plantillas.py -q` → `81 passed in 1.51s`. `make check` → `181 passed, 2 deselected in 21.79s` (con lo de A1 y A3 en el árbol; no he tocado nada ajeno).
- **RESPONDO A A1 (IBAN):** confirmado y medido por mi lado: **0 de los 468 IBAN de factura pasan mod-97**, y de los NIF sólo 46 de 468 pasan la letra de control (sólo `B46102331`). Los dos son sintéticos. He hecho lo que proponías: `IBAN_INVALIDO` sólo si el IBAN está mal FORMADO (ES + 24 caracteres). El mod-97 sigue disponible como `validadores.iban_checksum_ok` (y `nif_letra_control_ok`) por si el lote 2 trae datos reales, pero no emite aviso. **Resultado: los avisos pasan de salir en el 100 % de la Caja a 352 de 468 facturas sin ningún aviso.** Cuando reextraigas, los hechos ya guardados llevan `iban_invalido` de más: hay que rehacerlos con `solo_pendientes=False`.
- **AVISO A A1: ya puedes reextraer.** He terminado de tocar plantillas/validadores. Los hechos de plantilla guardados antes de `b2935dd` están desfasados en dos cosas: (1) `iban_invalido` ya no se emite; (2) `lineas` ahora viene rellena y en `simplificada` el primer concepto estaba mal (se tragaba la cabecera de la tabla). `uv run albertitos extract --solo-pendientes=False` o como lo tengas, y reexporta `hechos_muestra.jsonl`.
- **PIDO A Javier (para Miguel, `core/contracts.py`): falta `Aviso.NIF_INVALIDO`.** Hoy un NIF con forma imposible (p. ej. `B4610233`, 8 caracteres) se marca como `EXTRACCION_PARCIAL`, que es lo menos malo que hay pero miente sobre la causa. Es un campo nuevo en un StrEnum, compatible hacia atrás. Mientras no exista lo dejo con el TODO puesto en el código. No toco `core/`.
- cifras de los avisos sobre las 468 (cada una coincide fichero a fichero con el inventario de A3, sacado por otra vía): `fecha_en_letra` 90 · `texto_instruccion` 27 (las otras 2 de las 29 son las de fecha imposible, que no salen por plantilla) · `iva_no_estandar` 6 · `total_no_cuadra` 2 · `pedido_anulado_segun_pdf` 2 · `iban_invalido` 0 · `campo_ausente` 0 · `importe_ambiguo` 0.
- **dato para Mónica (norma):** las 6 facturas con la cuota de IVA mal **imprimen todas "IVA (21%)"**; el porcentaje real es 16 % en 5 (`F26-5240`, `F26-6702`, `F26-6964`, `F26-9012`, `FA-5590`) y **10 % en `F26-8801_suministros.pdf`** (base 2.500,00, cuota 250,00). Una regla que compare `iva_pct` con 21 no encuentra **ninguna**: hay que recalcular la cuota desde la base. Aparte, `2026-0811-B_catering.pdf` y `2026-14500-C_informática.pdf` tienen el IVA bien al 21 % pero el TOTAL inflado (2.310,00 + 485,10 = 2.795,10 impreso como 2.920,10; y 1.450,00 + 304,50 = 1.754,50 impreso como 1.819,00): son `total_no_cuadra`, no `iva_no_estandar`.
- toco ahora (ficheros): nada más de código; relleno mi sección de PARTE.md.
- necesito / bloqueo: nada.

### 21:05 · A2 · cierro. Los 7 pasos hechos
- hice: los 7 pasos del encargo. Cifras en mi sección de `PARTE.md`. Resumen: 6 familias de plantilla (no ~30), **468/471 completas** con 0 errores en las 10 revisadas a mano, **29/29 instrucciones** con 0 falsos positivos en 442 limpias, avisos con señal (352/468 facturas sin ningún aviso, antes el 100 % llevaba `iban_invalido`), `imagenes_png` en pdf.py, 81 tests míos verdes y `make check` 181 verdes.
- verificado: `uv run pytest tests/test_extract.py tests/test_plantillas.py -q` → `81 passed in 1.51s`; `make check` → `181 passed, 2 deselected in 21.79s`; `make agentes-check` → `OK: cada fichero tiene un único dueño`.
- toco ahora (ficheros): nada. Firmas intactas: `extraer_por_plantilla(texto, *, file_id, sha256)`, `validar(h)`, `discrepancias(a, b)`, `detectar_instruccion(texto)`, `menciona_anulacion(texto)`.
- necesito / bloqueo: nada. Quedan pedidas 3 cosas (arriba): `Aviso.NIF_INVALIDO` a Miguel, reextracción a A1, y qué hace la norma con `fecha=None` a Mónica.
- para los demás: lo que más valor tendría ahora es el **contraste plantilla↔LLM**: pasar el LLM por 30-50 de las que ya salen por plantilla y cruzar con `validadores.discrepancias()` (ya tolera formato). Cuesta céntimos y es lo único que descarta que 6 regex se equivoquen en bloque sobre 468 facturas. A1, cuando tengas key, si lo montas te leo el resultado en el próximo ciclo.

### 21:35 · A1 · key de Helmcode operativa · muestra 21/21 con LLM real · A3 cerrado
- hice: (1) cerrado A3 (commit bf24010: sus 10 ficheros, parte A3, hallazgo de A2 en trampas.md). (2) `.env` con Helmcode (`ALBERTITOS_LLM_PROVEEDOR=openai_compat`, base `https://api.helmcode.com/v1`): sus modelos claude-* dan 402 (crédito aparte); los 600 M tokens valen para deepseek-v4-flash (texto, exacto en 2,4 s) y qwen3.6 (visión, acepta imágenes). `llm.py` reescrito con dos proveedores (Anthropic SDK / gateway OpenAI-compatible vía httpx, sin dependencia nueva), formato de NIF/IBAN en el prompt, `max_tokens` 8000 en visión (qwen razona ~3000 tokens antes de la tool call; con 1500/3000 se cortaba y fallaba "sin tool_calls"), variante de caché. (3) `etapa.py`: segunda lectura de cada escaneada a 130 dpi → `discrepancia_extractores` si difieren campos clave; `contrastar(n)` plantilla↔LLM (propuesta de A2). (4) `extract --no-solo-pendientes --fixture muestra.txt --workers 3` → `21/21 ok · plantilla 18 · llm_vision 3 · 26.444 tokens · 51 s`; hechos de la muestra refrescados (sin `iban_invalido`, como pedía A2). (5) Contraste 18/18 coinciden (deepseek vs plantillas de A2), 34.311 tokens.
- verificado a mano contra la imagen: scan_001 exacto en todos los campos (NIF B98120774, IBAN …9517 0430 2211, 1025,49+215,35=1240,84, líneas 912,69/61,53/61,27); fax_2026_0411 y copia_2026_0518 tienen NIF/IBAN emborronados o tachados en el propio PDF → dos lecturas discrepan → aviso; es lo honesto.
- toco ahora (ficheros): revisando el falso positivo de discrepancia en scan_001; después las 500 (`--no-solo-pendientes --workers 4`) y `hechos_muestra.jsonl` definitivo.
- necesito / bloqueo: PIDO A Javier/Miguel: subir `PROMPT_VERSION` a `p-0.2` en core/versions.py (el prompt cambió; hoy invalido la caché de visión a mano). PIDO A Mónica: qué hace la norma con `discrepancia_extractores` en escaneadas (hoy R6 → ESCALAR) y con `importe_ambiguo` (scan_001: las líneas del propio PDF no suman la base).
- para los demás: Miguel → el ERP simulado de A3 sigue vivo en :8011 (`--tag v2-sim`); el v1 en :8009. A2 (si vuelve) → tus 6 plantillas coinciden 18/18 con el LLM; el contraste a 40 va tras la pasada completa.

### 22:20 · A1 · ciclo 1 de A1 cerrado: 500/500 hechos, contraste 40/40, A3 cerrado
- hice: pasos 1-8 completos con Helmcode (deepseek texto, qwen visión); 500/500 hechos (468 plantilla · 29 visión con doble lectura y reconciliación con el maestro · 3 texto LLM); `hechos_caja.jsonl` (500) y `hechos_muestra.jsonl` (21) exportados; contraste plantilla↔LLM 40/40; fix de `database is locked` con hilos; reintentos con variación; A3 cerrado y commiteado. Detalle y cifras en PARTE.md (sección A1).
- toco ahora (ficheros): nada más este ciclo.
- necesito / bloqueo: PIDO A Miguel: `hechos import data/fixtures/hechos_caja.jsonl` → `decide` → `package` antes de las 02:00. PIDO A Mónica: política para `discrepancia_extractores` (5 escaneadas), `importe_ambiguo` (2), `confianza=0.6` (6), `fecha=None` (3).
- para los demás: la BD `dist/albertitos.db` de Javier tiene los 500 hechos y 102 lecturas en caché; en otros portátiles, `hechos import` evita gastar tokens.

### 22:45 · plataforma · ciclo 1 cerrado / ciclo 2 abierto (2 agentes)
- hice: parte del ciclo 1 archivado en `partes/PARTE-01.md`; `PARTE.md` vacío para B1/B2; `plan.json` ciclo 2; `PLAN-02.md` con los prompts. `extract/etapa.py`: `ALBERTITOS_DIR_LOTE2`/`ALBERTITOS_DIR_CAJA` (env) para ensayar el lote 2 sin tocar `data/lote2/`.
- toco ahora (ficheros): nada más; escriben B1 y B2.
- necesito / bloqueo: Javier hace `git push` + merge a main antes de lanzar (main ya tiene hasta 3e217c0; faltan ef4d441, 0779512 y este).
- para los demás: B1 = ensayo del lote 2 en frío (sources/, inventario, skill lote2); B2 = resiliencia demostrable y coste real (extract/llm+etapa, bench). Miguel: `hechos import data/fixtures/hechos_caja.jsonl` → `decide` → `package` (repliegue 1, 02:00).

### 22:50 · B2 · arranco resiliencia y coste
- hice: leídos CLAUDE.md, extract/CLAUDE.md, texto-es-dato.md, skills/benchmark, PLAN-02 y PARTE-01 (sección A1: visión, caché del gateway, bloqueo SQLite, reconciliación).
- toco ahora (ficheros): ninguno todavía. Empiezo por el paso 1 (precios reales de Helmcode) y por releer `eventos` para el coste por camino. Después: sondeo de modelos de respaldo, guion de caos, `scripts/bench_llm.py`.
- necesito / bloqueo: nada. No borro nada de `cache_llm`: para medir usaré `variante="bench-wN"` / `"demo"`.
- para los demás: B1 → no toco `sources/` ni tu lote simulado. Si lo publicas aquí te lo pido antes de usarlo para medir; mientras, mido con variantes de caché sobre la Caja, que no gastan tu trabajo.

### 22:06 · B1 · arranco lote 2 en frío
- hice: leído PLAN-02, skill lote2, sources/CLAUDE.md, trampas.md y PARTE-01 (A1/A3). Rama al día con main; bridges v1 (:8009, 516) y v2-sim (:8011, 519) vivos; snapshots v1/v2-sim/maestro en BD; 0 ficheros de lote 2.
- toco ahora (ficheros): data/fixtures/lote2_sim/** (10 PDFs derivados con sha distinto + README), después scripts/inventario_trampas.py (--facturas/--erp-tag/--salida), .claude/skills/lote2/SKILL.md y docs/agentes/ENSAYO-LOTE2.md.
- necesito / bloqueo: nada. No escribo en data/lote2/ ni en data/caja/.
- para los demás: B2, el lote simulado estará en data/fixtures/lote2_sim/facturas (nombres `L2-*`); si lo usas para medir, dilo aquí y no lo modifiques. Miguel, el ensayo dejará 10 ficheros con lote=2 en la BD de Javier (no en la tuya).

### 22:45 · B1 · ensayo del lote 2 terminado
- hice: lote simulado `data/fixtures/lote2_sim/` (10 PDFs, README); ensayo completo cronometrado (ingest 0,3 s · extract 10/10 en 68 s · diff 0,2 s · inventario 0,07 s); cruce ERP v2-sim↔Excel↔Caja verificado con `reprocess` (510 recalculadas, cambian exactamente 2: `F26-9865_ofimática.pdf`→NO_PAGAR, `2026-06-27_P001.pdf`→ESCALAR) y BD restaurada a v1; `scripts/inventario_trampas.py` con `--facturas/--erp-tag/--salida/--sin-docs`; skill `lote2` reescrita con tiempos y paso 0 de limpieza; `docs/agentes/ENSAYO-LOTE2.md` con huecos y checklist.
- toco ahora (ficheros): nada más este ciclo.
- necesito / bloqueo: PIDO A Miguel: `caja verify --dir <ruta>` y `caja manifest --lote 2` (cli.py). PIDO A B2: poder limitar `contrastar` a un lote o lista de file_id, para recoger `texto_sospechoso` por LLM también en las facturas de plantilla del lote 2 (las plantillas no pasan por el LLM; una instrucción con redacción nueva sólo la ven las regex).
- para los demás: la BD de Javier tiene 10 ficheros `L2-*` con lote=2 (hechos y decisiones): antes del lote real, paso 0 de la skill (`delete … where file_id like 'L2-%'`). `package` hoy los ignora porque no existe `data/lote2/facturas`.

### 23:30 · B2 · precios reales: Helmcode NO cobra por token
- **HALLAZGO 1 · el coste del benchmark está mal por construcción.** Helmcode no tiene tarifa por token para los modelos que usamos: es **suscripción plana por key** (`helmcode.com/pricing`: Starter 399 €/mes, Growth 1.299 €, Scale 3.199 €; consultado 18/09/2026). Los modelos abiertos (`deepseek-v4-flash`, `qwen3.6`, `glm5.3-flash`, `gemma4`) van **sin coste por token**; sólo los "frontier" (claude-\*, gpt-5.6-\*, gemini-\*) se pagan de crédito prepago, y **nuestra organización no tiene crédito**: los 8 que probé devuelven `402` con el texto literal *"is a third-party model billed per token from prepaid credit. Your organisation has no credit balance"*. Conclusión: **el coste marginal por factura en nuestro camino es 0 EUR**, y los `2,30 EUR` que da hoy `albertitos bench` salen de `ALBERTITOS_PRECIO_IN/OUT_EUR_MTOK=3/15`, que son inventados. Lo que hay que defender no es "coste por token" sino **coste amortizado de suscripción por factura** y, sobre todo, el **límite de tasa**. Lo dejo parametrizado por modelo y con los abiertos a 0.
- **HALLAZGO 2 · los límites de tasa son la restricción real, y están publicados** (`helmcode.com/docs/rate-limits`): **100 RPM**, **2M TPM**, y **concurrencia 5 por modelo**, salvo deepseek-v4-flash y glm5.3 que tienen **10**. Al superarlos: `429` con cabecera **`Retry-After`**. → `qwen3.6` (visión) está limitado a **5 concurrentes**: los `--workers 4` de A1 estaban justo por debajo sin saberlo, y subir a 8 en visión chocará contra el techo. **`llm.py` hoy ignora `Retry-After`** y usa backoff a ciegas (1/2/4 s): lo arreglo, es fichero mío.
- **HALLAZGO 3 · la doc del gateway miente sobre la visión, para bien.** `docs/models` dice que `deepseek-v4-flash` y `glm5.3-flash` NO aceptan imágenes. **Sí las aceptan** y devuelven tool call: comprobado con tres facturas distintas (aciertan `pedido` y `total` de cada una, así que están leyendo la imagen, no adivinando). Además el gateway expone `glm5.3-flash` y `gemini-3.5-flash-lite`, no los `glm5.3`/`glm5.2`/`gemini-3.6-flash` que decía el plan.
- **HALLAZGO 4 · ningún modelo de visión lee el NIF de forma fiable.** En las lecturas completadas, los tres fallan dígitos del NIF en facturas distintas (qwen `B88120774`/`B88125774`/`B60233808`, deepseek `89812077W`/`B90233805`, glm `B00233858`) mientras aciertan `pedido` y `total` casi siempre. **Esto valida la reconciliación con el maestro que montó A1**: el NIF de una escaneada no se puede creer de una sola lectura, venga del modelo que venga. Un modelo de respaldo compra **disponibilidad, no precisión**.
- **Aviso metodológico:** a mitad de la comparativa, 15 llamadas seguidas (los 3 modelos × 5 ficheros) murieron con `ConnectError`. Sospeché del `httpx.Client` compartido de `llm.py`, pero el experimento de control (mismo cliente, 6 imágenes seguidas) da **6/6 en 200**: era un **corte transitorio del gateway**, no el cliente. Lo anoto porque es exactamente el escenario del guion de resiliencia, y hoy el sistema responde bien: 3 reintentos, circuit breaker a los 5 fallos y `PENDIENTE`, sin perder nada.
- toco ahora (ficheros): `llm.py` (precios por modelo, `Retry-After`, fallback), `.env.example`, luego `etapa.py`, `tests/test_llm.py`, `scripts/bench_llm.py`.
- necesito / bloqueo: nada.
- para los demás: **PIDO A Miguel:** cuando rehagas `bench`, el coste en EUR de los modelos abiertos es **0**, no 2,30; si quieres una cifra de dinero para la defensa, la honesta es la suscripción amortizada. **PIDO A B1:** he visto `L2-scan_002.pdf` y `L2-scan_004.pdf` ya ingeridos con hechos; no los toco.

### 01:05 · B2 · cierro. Resiliencia y coste, los 5 pasos
- hice: los 5 pasos. Entrega en `docs/agentes/RESILIENCIA-Y-COSTE.md` (7 secciones, la última es "qué NO está medido"). Commit `0f4175e`.
- verificado: `uv run pytest tests/test_llm.py -q` → `23 passed, 2 deselected in 1.28s`; `make check` → `195 passed, 2 deselected in 22.58s`; `make agentes-check` → `OK: cada fichero tiene un único dueño`.
- resumen de cifras: coste marginal **0 EUR/factura** (no 2,30) · plantilla 5 ms · texto 3,3 s · visión 35,3 s · texto escala a **1,28 f/s con 4 hilos**, visión **satura en 4** (0,22 f/s) · **0 429 en 8 tandas** · guion de caos (a) 0,7 s (b) 32,6 s (c) 23,2 s con el breaker saltando solo (d) 30 s y segunda pasada 1,1 s a 0 tokens sin duplicados · respaldo `glm5.3-flash` probado contra el gateway real con hechos idénticos al principal.
- **RESPONDO A B1:** hecho, `contrastar` acepta ya `lote=` y `file_ids=` (`etapa.contrastar(conn, lote=2)` o `file_ids=[...]`; con lista explícita contrasta todas, sin muestreo). Es la vía para que una factura de plantilla del lote 2 pase por el LLM y suelte su `texto_sospechoso`.
- **PIDO A Miguel:** el EUR de los modelos abiertos es 0; 2,30 € en la defensa es indefendible porque nadie los paga.
- **PIDO A Javier:** decidir si `ALBERTITOS_MODELO_TEXTO_FALLBACK=glm5.3-flash` se queda activo en el `.env` real; en `.env.example` ya está.
- aviso para quien mida: **el gateway cachea por cuerpo de petición**. Sin variar el cuerpo (`marca`), cualquier benchmark de throughput mide su caché, no la nuestra. Me pasó: 2,9 s con 2 hilos frente a 151 s con 1, mismos tokens de entrada.
- toco ahora (ficheros): nada.

### 23:10 · plataforma · ciclo 2 cerrado / ciclo 3 abierto (2 agentes)
- hice: parte del ciclo 2 archivado en `partes/PARTE-02.md`; `PARTE.md` vacío para C1/C2; `plan.json` ciclo 3; `PLAN-03.md` con los prompts.
- toco ahora (ficheros): nada más; escriben C1 y C2.
- necesito / bloqueo: Javier hace `git push` + merge a main antes de lanzar; decide el respaldo de texto en su `.env` (recomendado: sí, glm5.3-flash).
- para los demás: C1 = contraste de las 468 al 100 %, tercera lectura medida para los 5 escaneados difíciles, timeout 60 s, fechas imposibles blindadas. C2 = ADRs 0002-0005 de ingesta con evidencia + `tests/test_lote2_sim.py` offline. Miguel: el coste de los modelos abiertos es 0 (suscripción), no 2,30; `caja verify --dir` y `caja manifest --lote 2` siguen pedidos; `hechos import` + `decide` + `package` antes de las 02:00. Mónica: políticas de `discrepancia_extractores` (5), `importe_ambiguo` (2), `confianza=0.6` (6), `fecha=None` (3), y ratificar la reconciliación con el maestro como criterio.

### 23:25 · plataforma · cambios en la web y en el README upstream
- hice: releída hackathon.maisa.ai y `git fetch` del repo de participantes (2 commits "update readme", sólo README.md: "Viernes 21:00"→"19:00" y la celda del sábado pasa a "40 facturas adicionales"; **datos intactos**, `data/caja/README.md` y `data/caja.sha256` actualizados, `caja verify` OK). Web: material inicial = el repo (sin zip a las 21:00); sábado "40 facturas, ERP actualizado" + "una regla nueva" (ya no "norma v4" ni fichero); cierre oficial **dom 11:00** (interno 10:30); defensa hora por confirmar; bloque 4 pide demostrar **timeout**, rate limit, respuesta inválida o caída; bonus distinto del lote 2, máximo 110.
- toco ahora (ficheros): `docs/hitos.md`, `CLAUDE.md` (fechas), `.claude/skills/lote2/SKILL.md`, `docs/agentes/ENSAYO-LOTE2.md`, `docs/reparto-backend.md`, `docs/agentes/PLAN-03.md` + `plan.json` (C1 añade `sources/chaos.py` y el escenario `llm_timeout`).
- necesito / bloqueo: nada.
- para los demás: Mónica, la regla nueva puede llegar por el canal/zip/Excel: seguimos llamando `v4` a la norma resultante. Miguel, el ERP actualizado puede no venir: `reprocess` debe funcionar con o sin `--erp v2`. Alfonso, el bloque 4 de la defensa ahora enumera timeout/429/inválida/caída: el guion de B2 cubre tres, C1 añade el timeout.

### 23:35 · C1 · arranco contraste total y escaneados difíciles
- hice: leídos PLAN-03 (versión con timeout), extract/CLAUDE.md, PARTE-01 (A1/A2), PARTE-02 (B2), RESILIENCIA-Y-COSTE.md.
- toco ahora (ficheros): primero `etapa.contrastar` sobre las 468 de plantilla (≈ 6 min, coste 0) y en paralelo los tests de fechas imposibles (tests/test_extract.py, tests/test_llm.py). Después tercera lectura medida sobre los 29 escaneados, timeout 60 s + modo `llm_timeout` (sources/chaos.py + llm.py).
- necesito / bloqueo: nada. No borro caché de la Caja; lecturas nuevas con `variante=`.
- para los demás: C2, publicaré aquí la cifra del contraste total (N/468) en cuanto salga, para el ADR-0002.

### 23:58 · C1 · contraste total 468/468 · merge de Miguel integrado
- hice: `etapa.contrastar(file_ids=<468 de plantilla>, workers=4)` → **468/468 coinciden · 0 difieren · 0 fallos** en los 8 campos clave (num_factura, fecha, NIF, IBAN, pedido, base, IVA, total); 717.188 tokens a coste 0; 472 s. Las 6 plantillas de A2 quedan validadas al 100 % por una vía independiente (deepseek-v4-flash).
- hice también: el árbol compartido estaba en `main` (no en `javier/ingesta`); lo he devuelto a `javier/ingesta` y he integrado `origin/main` de Miguel (merge 3353c18: contratos v1, NIF_INVALIDO, PROMPT_VERSION p-0.2, run sin LLM). `make check` 203 verdes. Commit 5d24886: timeout 60 s configurable, `LLM-TIMEOUT`, caos `llm_timeout`, fechas imposibles blindadas.
- toco ahora (ficheros): caché del LLM (re-etiqueto p-0.1→p-0.2: el prompt no cambió desde ff6fed9 y todas las lecturas son posteriores), `validadores.py` (NIF_INVALIDO), tercera lectura medida sobre los 29 escaneados.
- necesito / bloqueo: nada.
- para los demás: **C2, cifra para el ADR-0002: 468/468 (antes 18/18 y 40/40).** Miguel: tu `PROMPT_VERSION=p-0.2` habría dejado huérfanas las 727 lecturas en caché; las re-etiqueto en la BD de Javier. En otros portátiles no hay caché: usad `hechos import`, no `extract`.

### 23:36 · C1 · corrección de horas · NIF_INVALIDO integrado
- corrijo: mis dos entradas anteriores llevan hora adelantada; se escribieron a las 23:24 y 23:32 (reloj del portátil).
- hice: `validadores.py` usa `Aviso.NIF_INVALIDO` (antes `EXTRACCION_PARCIAL`) para NIF mal formados; revalidados los 510 hechos: 0 cambian → no hay que reextraer ni reimportar (commit dc499b8). Caché re-etiquetada p-0.1→p-0.2 (728 filas, 0 choques); los 32 hechos LLM del lote 1 se resuelven desde caché.
- toco ahora (ficheros): tercera lectura de los 29 escaneados en curso (qwen 300 dpi tercio superior + deepseek página 150 dpi; ~20 min), después medición del timeout 180 vs 60 s con `scripts/bench_llm.py`. `docs/agentes/CONTRASTE-TOTAL.md` en marcha.
- necesito / bloqueo: PIDO A Mónica: añadir `Aviso.NIF_INVALIDO` a `ANOMALIAS_HUMANO` de norma_v3 (hoy no cambia ningún resultado; mejora la traza).
- para los demás: C2, la cifra del ADR-0002 es 468/468; la del ADR-0003 (tercera lectura) llegará con la tabla.
