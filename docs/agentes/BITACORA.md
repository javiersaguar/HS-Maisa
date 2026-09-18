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
