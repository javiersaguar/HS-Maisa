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
Implementado (commits `5d24886`, `4b5fe9c`): timeout **por modalidad** y por petición — `ALBERTITOS_LLM_TIMEOUT_S` = 60 s para texto (antes 180) y `ALBERTITOS_LLM_TIMEOUT_VISION_S` = 90 s para visión; `httpx.TimeoutException` → `ErrorLLM("LLM-TIMEOUT")`, reintentable con texto variado; al agotar los 3 intentos → PENDIENTE (y, en texto, el modelo de respaldo si está configurado). Modo de caos `llm_timeout` para el bloque 4 de la defensa.

Por qué dos valores (medido): texto p50 2,9-4,0 s; visión qwen3.6 a 150 dpi p50 11-13 s, p95 25-36 s, máximo ~41 s por lectura (bench de B2 + eventos de la Caja: 33 eventos de doble lectura, p95 67,7 s, máx 81,5 s = dos lecturas). Con un único timeout de 60 s, la medición de §5 a 300 dpi registró **`LLM-TIMEOUT` reales** (qwen razonando > 60 s sobre la imagen grande) y reintentos: el corte funciona, pero en visión cortaba trabajo útil. 90 s = 2,2× el máximo observado y sigue por debajo de la cola de 94 s.

## 5. Tercera lectura de los 29 escaneados — medida y **descartada**
Regla fijada ANTES de ver los datos (`scratchpad/analiza_tercera.py`): voto 2-de-3 por campo de identidad (principal 150 dpi,
recorte superior 200 dpi, tercera); se integra sólo con **0 regresiones** sobre lo guardado y si resuelve difíciles
**correctamente**. Referencia: NIF/IBAN del proveedor al que pertenece el pedido en el Excel (proxy: el PDF puede imprimir
otro dato a propósito).

| Lectura | Config | Tiempo (29, 4 hilos) | tokens/lectura p50 | NIF = maestro | IBAN = maestro | Pedido | Regresiones | Difíciles resueltos (= maestro) |
|---|---|---|---|---|---|---|---|---|
| 1ª (actual) | qwen3.6 · página 150 dpi | — | — | 24/29 | 21/29 | 29/29 | — | — |
| 2ª (actual) | qwen3.6 · 55 % superior 200 dpi | — | — | 25/29 | 21/29 | 28/29 | — | — |
| 3ª candidata A | qwen3.6 · 34 % superior **300 dpi** | **366 s** (1 `LLM-TIMEOUT` sin lectura: fax) | 6.161 | 25/29 | 20/29 | 28/29 | 0 | 1 (0) |
| 3ª candidata B | deepseek-v4-flash · página 150 dpi | 46 s | 2.419 | 19/29 | 14/29 | 27/29 | 0 | 1 (0) |

**Decisión: no se integra ninguna.** Ninguna resuelve un difícil correctamente; A cuesta +100 % de tiempo de visión por nada;
B es rápida pero **alucina** (NIF `B92345678` en `scan_021`, IBAN `ES4401825010012102033011` en el fax: patrones que no
están en el PDF). Confirma lo que midió B2: un segundo modelo compra disponibilidad, no precisión en identificadores.

**Los 5 difíciles, inspeccionados visualmente a 220 dpi — escalar es correcto en los cinco:**
| file_id | Qué imprime el PDF | Lecturas (1ª / 2ª) | Veredicto |
|---|---|---|---|
| `scan_016.pdf` | NIF `B90233808` (P011, legible) · **IBAN `ES71 3058 0022 7710 2233 8846` legible y ≠ maestro** (P011 = `ES93 6888…`) + instrucción inyectada | IBAN `…3058…` / `…3068…` (la 2ª confunde 5→6) | **Trampa de cambio de cuenta**. El hecho guardado (1ª lectura) es el correcto; R1 (IBAN ≠ maestro) y R6 → ESCALAR |
| `scan_023.pdf` | NIF e IBAN tapados por manchas; "OK. A." manuscrito; **otra factura superpuesta** (Informática Benimámet) transparentándose | NIF `B96233418` / `B08233419` | Ilegible + documento contaminado → ESCALAR |
| `scan_021.pdf` | Franja negra sobre el NIF; IBAN legible (= maestro) | NIF `B90203806` / `B0263808` | NIF ilegible → ESCALAR |
| `fax_2026_0411.pdf` | Trama de fax; NIF e IBAN emborronados | (ciclo 1) | Ilegible → ESCALAR |
| `copia_2026_0518.pdf` | IBAN atravesado por rayas verticales | (ciclo 1) | Ilegible → ESCALAR |

Para la norma (Mónica): `discrepancia_extractores` en escaneadas = **"el documento no permite leer con certeza un
identificador"** o **"imprime uno que no es el del maestro"**; en ambos casos ESCALAR con la evidencia de las dos lecturas.
Para trampas.md (quien lo lleve en el ciclo 4): `scan_016` (cambio de IBAN) y `scan_023` (documento superpuesto) son trampas nuevas.

## 6. Timeout: antes / después (texto, deepseek-v4-flash, 8 hilos, marcas nuevas para esquivar la caché del gateway)
| Tanda | Timeout | Resultado | Pared | f/s | p50 | p95 | Errores |
|---|---|---|---|---|---|---|---|
| 16 de texto | 180 s | 16/16 | 14,3 s | 1,12 | 3,9 s | 10,9 s | — |
| 16 de texto | 60 s | 16/16 | 8,6 s | 1,86 | 3,1 s | 7,9 s | — |
| 32 de texto | 180 s | 32/32 | 27,0 s | 1,18 | 3,6 s | 16,9 s | — |
| 32 de texto | 60 s | 32/32 | 30,5 s | 1,05 | 4,0 s | 16,1 s | — |

`uv run python scripts/bench_llm.py --texto {16,32} --vision 0 --workers 8 --sufijo c1-t{180,60}[-32]` con `ALBERTITOS_LLM_TIMEOUT_S={180,60}`.

**La cola de 94 s no se reprodujo esta noche** (0 de 96 peticiones por encima de 17 s). Las diferencias entre filas son ruido del gateway, no efecto del timeout: con ninguna petición por encima de 60 s, el timeout no llega a actuar. Lo que SÍ está demostrado: (a) el mecanismo, con tests (`test_timeout_real_de_httpx_se_traduce_a_llm_timeout`: 3 intentos de 60 s y PENDIENTE, sin colgarse; `test_timeout_por_modalidad`); (b) timeouts reales en visión con el valor único de 60 s (§4), que llevaron a separar los valores. Para la defensa: guion con `chaos --llm-timeout` (modo `llm_timeout`), no con una cola real que no sabemos provocar.

## 7. Guion de timeout para el bloque 4 de la defensa (ensayado, salidas literales)
Complementa el guion de caos de B2 (caída, 429, respuesta inválida, circuit breaker). Ensayado en una BD **aislada** con
las 3 facturas de texto que no tienen plantilla (las únicas de la Caja que obligan a llamar al LLM de texto).

> ⚠ (Corregido por D2, ciclo 4) El interruptor de caos ya **no es global**: vive junto a su BD (`<db>.chaos.json`), así
> que ensayar con `ALBERTITOS_DB=<otra BD>` no toca la extracción real. `ALBERTITOS_CHAOS=<fichero>` sigue mandando si se indica.
> `chaos --llm-timeout` en la CLI está pedido a Miguel; mientras: `uv run python -c "from albertitos.sources import chaos; chaos.activar('llm_timeout')"`.

```
$ chaos llm_timeout
$ albertitos extract --workers 3
extract: 0/3 ok · 3 pendientes · 0 pdf ilegibles · métodos {} · errores {'LLM-TIMEOUT': 3} · tokens 0/0 · 0.0000 EUR · 10.0 s
$ eventos
  ('2026-03-19_P008.pdf', 'pendiente', 3, 'LLM-TIMEOUT')
  ('FA-2967_seguridad.pdf', 'pendiente', 3, 'LLM-TIMEOUT')
  ('FA-1123_construcciones.pdf', 'pendiente', 3, 'LLM-TIMEOUT')
  hechos: 0 · decisiones: 0                  ← nada se decide sin hechos; nada se paga
$ chaos off
$ albertitos extract --workers 3
extract: 3/3 ok · 0 pendientes · métodos {'llm_texto': 3} · tokens 3368/1778 · 0.0000 EUR · 6.7 s
$ albertitos extract --no-solo-pendientes --workers 3     (repetición)
extract: 3/3 ok · métodos {'cache': 3} · tokens 0/0 · 0.0000 EUR · 0.0 s
  hechos: 3 · duplicados por sha256: 0
```
Qué se enseña: el proveedor "no contesta" → 3 intentos con backoff (visibles en el evento: `intento=3`) → PENDIENTE sin
escribir hechos ni decisiones → al volver, se reanuda sólo lo pendiente → repetir no cuesta ni duplica (caché por sha256 +
clave `(sha256, extractor_version)`). Con el timeout real (60 s texto / 90 s visión) cada intento espera ese tiempo;
en el ensayo `ALBERTITOS_CAOS_TIMEOUT_ESPERA_S=1` lo acorta a 1 s para que quepa en la defensa.
Commit `b85bd4d`: antes, el evento PENDIENTE decía `intento=1` aunque se hubieran consumido 3.
