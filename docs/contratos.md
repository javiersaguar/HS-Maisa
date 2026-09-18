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
`ficheros` (sha256 PK, file_id UNIQUE, lote) · `hechos` (sha256 + extractor_version) · `snapshots` (tipo + version) ·
`decisiones` (historial con `vigente`) · `eventos` · `cache_llm` (sha256|prompt|modelo)

## Cambios
| Fecha | Qué | Por qué | Quién |
|---|---|---|---|
| 2026-09-18 | v1 inicial | plataforma | Javier (Miguel valida) |
| 2026-09-18 | v1 aceptada. `+Aviso.NIF_INVALIDO` | A2 valida la letra/dígito de control del NIF y necesita decirlo sin abusar de `CAMPO_AUSENTE`. Produce extract/validadores; consume rules/ | Miguel |
| 2026-09-18 | `Decision.decidido_en` opcional; lo sella `core.db.guardar_decision` | `decidir()` queda pura (sin reloj) y `pipeline/` sin `datetime.now()`. Compatible: quien lo pase, se respeta | Miguel |
| 2026-09-19 | `+Aviso.DOCUMENTO_SUPERPUESTO` | `scan_023` (y `scan_025`, según Javier) llevan otra factura superpuesta o transparentándose. Ningún aviso existente lo describe con honestidad (no es `EXTRACCION_PARCIAL` ni `TEXTO_INSTRUCCION`). Produce extract (Javier); consume rules/: **Mónica decide** si entra en `ANOMALIAS_HUMANO` (ESCALAR por R6). Hasta entonces sólo es evidencia | Miguel |
| 2026-09-19 | `ESQUEMA_VERSION` 2: índice `ix_decisiones_sha_vigente ON decisiones(sha256, vigente)` | `db.guardar_decision` (`UPDATE … WHERE sha256=? AND vigente=1`) y el JOIN de `linaje.evaluar` recorrían la tabla por decisión: cuadrático, y peor con cada reprocesado porque el historial no se borra. `reprocess --todo` sobre la BD real (500): 0,35 s → 0,11 s; con 4.500 decisiones previas, 2,34 s → 0,16 s; a 10.000 (500 hechos reales ×20), 160,6 s → 4,1 s y, con 10.000 previas, 297,6 s → 4,0 s. Compatible: sólo `CREATE INDEX IF NOT EXISTS`, ningún resultado cambia; las BD existentes lo ganan con `make db` o con cualquier comando que escriba (`init_schema`). Pedido por D1 | Miguel |
| 2026-09-18 | **Descartado** `Aviso.PEDIDO_SIN_NIF_MAESTRO` | No es un hecho del PDF sino del maestro: meterlo en `InvoiceFacts` haría que `hechos_hash` cambiase al cambiar el Excel. Ya está en `MasterSnapshot.avisos_calidad` (20 pedidos) y la R2 lo recoge en `Motivo.evidencia` | Miguel |
