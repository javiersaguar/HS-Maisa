# pipeline/ — etapas, linaje, entrega · dueño: Miguel

| Fichero | Qué hace | Estado |
|---|---|---|
| `etapas.py` | `ingest` (PDF→ficheros), `extract` (delega en `extract/etapa.py`, **Javier**), `marcar_duplicados`, `decide` (norma → decisiones) | ingest/decide hechos |
| `run.py` | `correr(...)`: el `run` entero (ingest → maestro → ERP → extract → duplicados → decide → package) → `ResumenRun`. Sin extract, decide con los hechos que haya. `reprocesar(...)`: `reprocess --impacted` → `ResumenReproceso` | hecho |
| `linaje.py` | `evaluar(...)`: qué recalcular y por qué (hechos, norma, corte, o el diff de maestro/ERP toca su pedido o NIF), qué sigue valiendo con otra versión (evento `decide/skip`); `diff_maestro`; `diff_decisiones(desde_id=)` antes/después. ADR-0006 | hecho |
| `validar.py` | `listar_pdfs`, `validar_jsonl`: replica el verificador privado (conjunto exacto, NFC, únicos, enum, BOM) | hecho |
| `package.py` | `empaquetar`: BD → `dist/entrega/*.jsonl` todo o nada (`.tmp` → validar todos los lotes → **auditar** → sustituir); una entrega inválida o con la auditoría roja (o rota) no pisa la anterior. `auditar=` recibe `Auditor = (conn, {lote: dir}) -> InformeAuditoria` (`ok`, `rojos`, `texto()`); `auditor_de_entrega()` lo toma de `pipeline/auditoria.py` (E2) cuando exista, y el CLI lo pasa en `package` y `run` (`--sin-auditoria` lo salta a mano). Eventos emit: uno por intento y lote (`auditoria`: verde / no ejecutada; `AUDITORIA-ROJA`/`AUDITORIA-ERROR` si niega); por fichero, al cambiar lo entregado o si no se puede entregar | hecho; falta `pipeline/auditoria.py` (E2) |
| `bench.py` | cifras medidas desde `eventos` para `docs/benchmark.md` | hecho |

## Invariantes
- Cada etapa es idempotente: repetirla no duplica filas ni cambia resultados si no cambió nada.
- Cada etapa emite un `Event` por fichero (OK/ERROR/PENDIENTE) con latencia; si reintenta, un evento RETRY por intento.
- Evento por transición (`etapas.registrar_transicion`): los de estado (decide/skip de un PENDIENTE, emit por fichero) sólo se escriben si cambia el estado. La traza de un PENDIENTE: extract pendiente (LLM-DOWN) → decide skip → emit pendiente. `marcar_duplicados` deja validate/ok con `accion` y `con` (los otros PDFs del grupo).
- El linaje ve versiones, no código: si se edita una norma publicada sin cambiar su versión, `reprocess --impacted` no lo nota (`run` y `--todo` sí). ADR-0006.
- `decide` sólo recibe `InvoiceFacts` + snapshots + `ContextoDecision`. Nunca el texto del PDF.
- `reprocess --impacted` = `marcar_duplicados` → `linaje.evaluar(...)` → `decide(solo=..., por=...)` → diff de esta pasada. Con eso el cambio del sábado y el "dato en vivo" del domingo son el mismo mecanismo.
- Las decisiones no afectadas por un cambio de maestro/ERP **no se tocan**: conservan la versión con que se decidieron (ADR-0006). Supone que la norma lee maestro/ERP sólo por el pedido y el NIF de la factura; `test_la_norma_solo_lee_su_pedido_y_su_nif` lo vigila para cada norma del REGISTRO.
- `marcar_duplicados` pone y quita `DUPLICADO_SOSPECHOSO` (es la única que lo pone): borrar ficheros deshace la marca en la siguiente pasada.
- `run` = ingest → extract → marcar_duplicados → decide → package. Si `extract` deja PENDIENTES, `decide` no los toca y `package` se niega (entrega parcial = NO APTO).

## Demo de resiliencia
`make demo-caos` (`scripts/demo_caos.py`): copia de la BD en `dist/demo.db`, caos en `dist/demo_chaos.json`, entrega en
`dist/demo_entrega/` (no toca lo real). 3 facturas que sólo lee el LLM llegan nuevas → `--llm-down`: PENDIENTE, sin
decisión, package se niega → `--off`: se leen y se entrega → otra vez: mismo JSONL. 21,9 s medidos (un cuelgue del
proveedor la llevó a 103 s: el timeout del cliente LLM manda).

## Lo que falta (en orden)
1. G5: `bench` sin ficheros/s; EUR = 0 en los modelos abiertos; los eventos de ingest se duplican con cada run (500 por run).
