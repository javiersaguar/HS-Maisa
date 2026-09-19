# Contratos (prosa de `src/albertitos/core/contracts.py`)

| Tipo | Quién lo produce | Quién lo consume | Campos clave |
|---|---|---|---|
| `InvoiceFacts` | extract/ | rules/, consola | `file_id` (NFC), `sha256`, `num_factura`, `fecha`, `nif_emisor`, `iban`, `pedido`, `base`, `iva_pct`, `iva`, `total`, `lineas`, `metodo`, `extractor_version`, `avisos[Aviso]`, `texto_sospechoso`. Sin campo de decisión. `hash()` = linaje |
| `MasterSnapshot` | sources/excel.py | rules/, pipeline/ | `version` (hash contenido), `proveedores{id}`, `pedidos{nº}`, `avisos_calidad` |
| `ErpSnapshot` | sources/erp.py | rules/, pipeline/ | `version` (tag v1/v2), `asientos{id}`, `por_pedido()`, `consultas`, `reintentos`, `lote2_cargado` |
| `ContextoDecision` | pipeline/ | rules/ | `norma_version`, `fecha_corte`, `maestro_version`, `erp_version` |
| `Motivo` | rules/ | consola, entrega | `regla_id` (`v3.R2`), `ok`, `detalle`, `evidencia{}` |
| `Decision` | rules/ | pipeline/, consola | `resultado`, `motivos`, `norma_version`, `fecha_corte`, `hechos_hash`, `maestro_version`, `erp_version`, `decidido_en` |
| `Event` | todas las etapas | consola, bench | `etapa`, `estado`, `intento`, `latencia_ms`, `tokens_in/out`, `coste_eur`, `error_codigo`, `detalle`, `version` |
| `Outcome` | pipeline/package.py | verificador | `file_id`, `result` (+ opcionales `motivo`, `norma_version`, `regla`) |

## Verbos de la CLI (congelados)
`db init` · `caja verify|manifest` · `ingest` · `extract` · `maestro` · `erp pull|diff` · `decide` · `reprocess --impacted` · `run` · `status` · `trace` · `validate` · `package` · `bench` · `chaos`

## Tablas
`ficheros` (sha256 PK, file_id UNIQUE, lote) · `identidades` (file_id + lote → sha256: nombres extra de un PDF ya registrado) · `hechos` (sha256 + extractor_version) · `snapshots` (tipo + version) ·
`decisiones` (historial con `vigente`) · `eventos` · `cache_llm` (sha256|prompt|modelo)

## Cambios
| Fecha | Qué | Por qué | Quién |
|---|---|---|---|
| 2026-09-18 | v1 inicial | plataforma | Javier (Miguel valida) |
| 2026-09-18 | v1 aceptada. `+Aviso.NIF_INVALIDO` | A2 valida la letra/dígito de control del NIF y necesita decirlo sin abusar de `CAMPO_AUSENTE`. Produce extract/validadores; consume rules/ | Miguel |
| 2026-09-18 | `Decision.decidido_en` opcional; lo sella `core.db.guardar_decision` | `decidir()` queda pura (sin reloj) y `pipeline/` sin `datetime.now()`. Compatible: quien lo pase, se respeta | Miguel |
| 2026-09-19 | `+Aviso.DOCUMENTO_SUPERPUESTO` | `scan_023` (y `scan_025`, según Javier) llevan otra factura superpuesta o transparentándose. Ningún aviso existente lo describe con honestidad (no es `EXTRACCION_PARCIAL` ni `TEXTO_INSTRUCCION`). Produce extract (Javier); consume rules/: **Mónica decide** si entra en `ANOMALIAS_HUMANO` (ESCALAR por R6). Hasta entonces sólo es evidencia | Miguel |
| 2026-09-19 | `ESQUEMA_VERSION` 2: índice `ix_decisiones_sha_vigente ON decisiones(sha256, vigente)` | `db.guardar_decision` (`UPDATE … WHERE sha256=? AND vigente=1`) y el JOIN de `linaje.evaluar` recorrían la tabla por decisión: cuadrático, y peor con cada reprocesado porque el historial no se borra. `reprocess --todo` sobre la BD real (500): 0,35 s → 0,11 s; con 4.500 decisiones previas, 2,34 s → 0,16 s; a 10.000 (500 hechos reales ×20), 160,6 s → 4,1 s y, con 10.000 previas, 297,6 s → 4,0 s. Compatible: sólo `CREATE INDEX IF NOT EXISTS`, ningún resultado cambia; las BD existentes lo ganan con `make db` o con cualquier comando que escriba (`init_schema`). Pedido por D1 | Miguel |
| 2026-09-19 | **Sin cambio (decidido):** `InvoiceFacts.hash()` sigue excluyendo `confianza` | Desde ADR-0011 (Mónica) R6 escala `confianza < 1`, así que la decisión depende de un campo que el hash no ve. No se rompe el linaje: `guardar_hechos` renueva siempre `creado_en`, y `linaje.evaluar` redecide unos hechos reescritos después de la decisión aunque el hash no cambie (la red de ADR-0006, la misma que para `texto_sospechoso`); lo fija `test_solo_cambia_la_confianza_y_tambien_se_redecide`. Meterla en el hash cambiaría el `hechos_hash` de todos los hechos ya guardados: cualquier BD que redecida sin reimportar antes saldría con 500 `decision_vieja` en ROJO en la auditoría (y en el preflight) a horas de la entrega. Se reconsidera después del domingo | Miguel |
| 2026-09-18 | **Descartado** `Aviso.PEDIDO_SIN_NIF_MAESTRO` | No es un hecho del PDF sino del maestro: meterlo en `InvoiceFacts` haría que `hechos_hash` cambiase al cambiar el Excel. Ya está en `MasterSnapshot.avisos_calidad` (20 pedidos) y la R2 lo recoge en `Motivo.evidencia` | Miguel |
| 2026-09-19 | `ESQUEMA_VERSION` 3: tabla `identidades(file_id, lote, sha256, ingerido_en)` y `db.guardar_identidad`, `identidades_vigentes`, `nombres_por_sha`, `hay_identidades`; `db.traza` encuentra un nombre extra (`identidad`, `copias`); `db.resumen` añade `copias`, `estado_actual` e `historico` | P0-1: un PDF idéntico con otro nombre (en el lote 2, o repetido del lote 1) reasignaba el `file_id` y el lote del original (el lote 1 perdía su línea: NO APTO) y, con hechos y decisión por sha256, las dos salían PAGAR. Ahora `ficheros` guarda el primero y no se toca; cada nombre extra tiene su línea en su lote con la decisión de la sha256, `marcar_duplicados` los marca como duplicado (ninguno se paga) y la auditoría los cuenta como filas. Sin copias no cambia nada: la misma BD da el mismo `outcomes.jsonl` byte a byte con y sin el cambio. Compatible: `CREATE TABLE IF NOT EXISTS`; una BD v2 en sólo lectura se lee como si no hubiera copias. Consumen: ingest, package, auditoría, traza; `scripts/verificar_material.py` puede detectar la capacidad por la tabla | Miguel |
