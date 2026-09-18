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
