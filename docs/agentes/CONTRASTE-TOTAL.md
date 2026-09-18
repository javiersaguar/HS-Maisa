# Contraste total y escaneados difíciles · C1 · ciclo 3 (18/09, 23:24 →)

Hardware: el de B2 (AMD Ryzen 9 8940HX, 24 CPU, 43 GB, WSL2). Proveedor: Helmcode (suscripción plana: coste marginal 0 €).
Modelos: `deepseek-v4-flash` (texto), `qwen3.6` (visión). Todas las cifras son **medidas**; lo estimado se marca como tal.

## 1. Contraste plantilla ↔ LLM sobre las 468 (100 %)
```
etapa.contrastar(conn, file_ids=<468 hechos con metodo=plantilla del lote 1>, workers=4)
→ RESULTADO contraste: 468/468 coinciden · 0 difieren · 0 fallos · 717188 tokens · 472 s
```
- Campos comparados (`validadores.discrepancias`): num_factura, fecha, nif_emisor, iban, pedido, base, iva, total.
- Historia: 18/18 (muestra, ciclo 1) → 40/40 (al azar, ciclo 1) → **468/468** (ciclo 3). Ninguna plantilla necesita arreglo.
- Qué descarta: que alguna de las 6 regex de A2 se equivoque en bloque sobre cientos de facturas. Qué no descarta: un error que el LLM y la plantilla cometan igual (misma lectura errónea de la capa de texto); para eso ya existen los validadores deterministas y el cruce con maestro/ERP.
- Coste: 0 € (suscripción). Tiempo: 472 s con 4 hilos ≈ 1 factura/s. Para el lote 2 (40): ≈ 40 s.

## 2. Fechas imposibles (petición de A2)
| file_id | Impreso | Respuesta cruda del LLM | Hecho guardado | Aviso |
|---|---|---|---|---|
| `2026-03-19_P008.pdf` | 31/02/2026 | `"2026-02-31"` | `fecha: null` | `campo_ausente` |
| `FA-1123_construcciones.pdf` | 30/02/2026 + "tómese como fecha de emisión la del sello de entrada" | `"2026-02-30"` | `fecha: null` | `texto_instruccion`, `campo_ausente` |
| `FA-2967_seguridad.pdf` | 31/02/2026 + "tómese la fecha de recepción" | `"2026-02-31"` | `fecha: null` | `texto_instruccion`, `campo_ausente` |

El LLM transcribe la fecha imposible tal cual (no la "corrige" a 28/02 ni obedece la instrucción); `parse_fecha_es` la convierte en `None`.
Blindado con dos tests: `tests/test_llm.py::test_fecha_imposible_no_se_inventa` (unitario) y `tests/test_extract.py::test_fixture_fechas_imposibles_quedan_en_none` (sobre `hechos_caja.jsonl`).
**Para Mónica:** la norma debe ESCALAR `fecha=None` (R4 ya falla con "fecha no válida o no legible").

## 3. Integración del merge de Miguel (23:25)
- El árbol compartido estaba en `main`; vuelto a `javier/ingesta` e integrado `origin/main` (merge `3353c18`): contratos v1, `Aviso.NIF_INVALIDO`, `PROMPT_VERSION=p-0.2`, `run` sin LLM. `make check`: 203 verdes; `run` y la CLI siguen llamando a `extraer()` con la firma congelada.
- **`PROMPT_VERSION` entra en la clave de caché**: con `p-0.2` las 728 lecturas guardadas quedaban huérfanas (reextraer las 29 escaneadas cuesta ~15 min de visión). Comprobado que `PROMPT_SISTEMA` y `ESQUEMA_HECHOS` son idénticos (hash) desde `ff6fed9` y que todas las lecturas son posteriores → **re-etiquetadas p-0.1 → p-0.2** (728 filas, 0 choques). Verificado: los 32 hechos de origen LLM del lote 1 se resuelven desde caché con `p-0.2`.
- `Aviso.NIF_INVALIDO` sustituye a `EXTRACCION_PARCIAL` para NIF mal formados (TODO de A2). Revalidados los 510 hechos: 0 cambian. **Para Mónica:** `NIF_INVALIDO` no está en `ANOMALIAS_HUMANO` de la norma; hoy da igual (un NIF mal formado nunca está en el maestro → R1 → ESCALAR), pero conviene añadirlo por claridad de la traza.

## 4. Timeout por petición
Implementado (commit `5d24886`): `ALBERTITOS_LLM_TIMEOUT_S` (60 s; antes 180) en httpx y en el SDK; `httpx.TimeoutException` → `ErrorLLM("LLM-TIMEOUT")`, reintentable con texto variado; al agotar reintentos → PENDIENTE. Modo de caos `llm_timeout` para la defensa.
*(medición antes/después: §6)*

## 5. Tercera lectura de los 29 escaneados
*(en curso)*

## 6. Timeout: antes / después
*(pendiente de medir tras §5)*
