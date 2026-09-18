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
