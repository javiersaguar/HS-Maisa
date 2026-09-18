# pipeline/ — etapas, linaje, entrega · dueño: Miguel

| Fichero | Qué hace | Estado |
|---|---|---|
| `etapas.py` | `ingest` (PDF→ficheros), `extract` (delega en `extract/etapa.py`, **Javier**), `marcar_duplicados`, `decide` (norma → decisiones) | ingest/decide hechos |
| `run.py` | `correr(...)`: el `run` entero (ingest → maestro → ERP → extract → duplicados → decide → package) → `ResumenRun`. Sin extract, decide con los hechos que haya. `reprocesar(...)`: `reprocess --impacted` → `ResumenReproceso` | hecho |
| `linaje.py` | `evaluar(...)`: qué recalcular y por qué (hechos, norma, corte, o el diff de maestro/ERP toca su pedido o NIF), qué sigue valiendo con otra versión (evento `decide/skip`); `diff_maestro`; `diff_decisiones(desde_id=)` antes/después. ADR-0002 | hecho |
| `validar.py` | `listar_pdfs`, `validar_jsonl`: replica el verificador privado (conjunto exacto, NFC, únicos, enum, BOM) | hecho |
| `package.py` | `empaquetar`: BD → `dist/entrega/*.jsonl` todo o nada (`.tmp` → validar todos los lotes → sustituir); una entrega inválida no pisa la anterior | hecho |
| `bench.py` | cifras medidas desde `eventos` para `docs/benchmark.md` | hecho |

## Invariantes
- Cada etapa es idempotente: repetirla no duplica filas ni cambia resultados si no cambió nada.
- Cada etapa emite un `Event` por fichero (OK/ERROR/PENDIENTE) con latencia; si reintenta, un evento RETRY por intento.
- `decide` sólo recibe `InvoiceFacts` + snapshots + `ContextoDecision`. Nunca el texto del PDF.
- `reprocess --impacted` = `marcar_duplicados` → `linaje.evaluar(...)` → `decide(solo=..., por=...)` → diff de esta pasada. Con eso el cambio del sábado y el "dato en vivo" del domingo son el mismo mecanismo.
- Las decisiones no afectadas por un cambio de maestro/ERP **no se tocan**: conservan la versión con que se decidieron (ADR-0002). Supone que la norma lee maestro/ERP sólo por el pedido y el NIF de la factura; `test_la_norma_solo_lee_su_pedido_y_su_nif` lo vigila para cada norma del REGISTRO.
- `marcar_duplicados` pone y quita `DUPLICADO_SOSPECHOSO` (es la única que lo pone): borrar ficheros deshace la marca en la siguiente pasada.
- `run` = ingest → extract → marcar_duplicados → decide → package. Si `extract` deja PENDIENTES, `decide` no los toca y `package` se niega (entrega parcial = NO APTO).

## Lo que falta (en orden)
1. `run` corre ya sin LLM (`--sin-extraer` o mientras `extract` no exista) sobre hechos importados; cuando `extract` exista, extrae primero.
2. `chaos`: `sources/chaos.py` marca el modo; `extract/llm.py` lo respeta. Verificar que `run` con `--llm-down` deja PENDIENTES y no decide nada de esos ficheros.
3. Concurrencia en `extract` (ThreadPoolExecutor, `ALBERTITOS_WORKERS`), cuando funcione en serie.
