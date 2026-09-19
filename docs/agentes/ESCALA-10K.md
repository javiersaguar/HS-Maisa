# Escala medida a 10.000 facturas · D1 · ciclo 4 (sábado 19/09/2026, 00:50-01:15)

**Referencia para la defensa:** [CIFRAS.md](../CIFRAS.md) reúne fuente, fecha, comando y vigencia.
Este documento conserva la medida en `95808e2`: sus «hoy» describen aquel commit. El PR #1 de Miguel
ya incorporó el índice de decisiones al esquema; las cifras sin índice son históricas. No se ha repetido
el banco completo después de ese cambio en G2. El tiempo con índice de §2 es una suma de etapas, no
una pasada completa medida de nuevo. No trasladar los tiempos de Javier al portátil de Alfonso.

Qué es esto: el pipeline real (el código de `src/` tal cual, sin tocarlo) sobre **10.000 facturas sintéticas** en
una BD aparte, etapa por etapa, con tiempo y RAM. Los caminos de LLM se miden por separado, con llamadas reales
que la caché del gateway no puede contestar. Todo sale de `scripts/bench_escala.py`. Los JSON crudos están en
`dist/escala/medidas-*.json` (no se commitean).

**Regla de lectura:** cada cifra lleva al lado si es **MEDIDA** (ejecutada aquí, a esa escala) o **EXTRAPOLADA**
(calculada desde una medida más pequeña, diciendo desde cuál). Lo que no se ha medido pone "no medido".

## Resumen para el plan (5 líneas)
- Medimos **10.000 facturas** con el pipeline real en el portátil de desarrollo: el camino determinista (93,6 %
  de las facturas) tarda **57 s por cada 10.000 en un solo núcleo** (39 s con una línea de índice), el JSONL
  sale APTO y el pico de RAM es de 653 MB.
- La visión con doble lectura, **medida sin la caché del gateway**, va a **0,106 facturas/s por key**. Las 580
  escaneadas de 10.000 son **~1,5 h**, más del 97 % del tiempo. La cifra de "10.000 en 45 min" era optimista
  2-3 veces.
- Para escalar 10× **no hace falta más máquina**, hace falta que **menos facturas lleguen al LLM** (o más keys).
  El coste marginal es 0 €: la suscripción amortizada sale a 0,04 € por factura a 10.000/mes.
- El banco encontró un **cuello cuadrático real**: sin índice en `decisiones(sha256)`, `decide` pasa de 0,07 s a
  20 s (×280 por ×20 de datos) y 68 s al reprocesar. Con el índice, 1,7 s.
- Postgres, un almacén de objetos o una cola sólo entran **cuando haya más de una máquina escribiendo**, no por
  volumen: 1 M de facturas son 3,7 GB de BD y 13 GB de PDFs. Spark, nunca: lo caro es una API con límite de
  concurrencia.

---

## 1. Condiciones

| Qué | Valor |
|---|---|
| Máquina | Portátil de Javier: AMD Ryzen 9 8940HX (24 hilos), 43 GB de RAM visibles en WSL2 |
| SO · Python | Linux 6.18 WSL2 (Windows) · Python 3.12.13 |
| Commit | `95808e2` (`javier/ingesta`), sin cambios en `src/` |
| Fecha | 19/09/2026, 00:51-01:10 (hora de Madrid) |
| ERP | bridge local `:8009` **sin latencia** (`make erp-fast`), 516 asientos |
| LLM | gateway Helmcode · texto `deepseek-v4-flash` · visión `qwen3.6` con doble lectura |
| BD | SQLite WAL propia en `dist/escala/`; la BD de la entrega no se toca |
| Caos | fichero propio `dist/escala/chaos-<etiqueta>.json`; `dist/chaos.json` nunca |

**Comparabilidad.** B2 midió los caminos de LLM (RESILIENCIA-Y-COSTE §4) **en esta misma máquina**, así que
sus cifras y estas se pueden comparar. Miguel midió G5 (`docs/benchmark.md` en `main`) en otra: un i5-1235U con
Windows 11 y 7,7 GB. **El portátil de la demo es el de Alfonso, y en él no se ha medido nada:** en la defensa
hay que decir "en el portátil de desarrollo".

### Cómo se construyen las 10.000
- Son los 500 PDFs de la Caja repetidos en round-robin, así que la mezcla es exacta: 9.360 por plantilla
  (93,6 %), 580 escaneadas (5,8 %) y 60 con texto sin plantilla (0,6 %).
- Cada copia lleva un comentario PDF añadido al final (`%% albertitos-escala copia=NNNNN`). Su sha256 es
  distinto, así que nuestra caché no la reconoce y se procesa entera. PyMuPDF la lee igual.
- Las 640 copias que irían al LLM **no se mandan al LLM en esta pasada**. El caos `llm_down` está activo en el
  fichero de caos del banco:
  - su render sí se mide (PDF → PNG a 150 dpi, lo mismo que pagan en producción antes de la llamada);
  - después reciben sus hechos reales de `hechos_caja.jsonl`, re-etiquetados como haría `hechos import`;
  - el tiempo de LLM de esos caminos se mide aparte, en el §4.
- **Artefacto que hay que saber leer:** las copias repiten pedido, así que `marcar_duplicados` marca las
  10.000 y `decide` da 9.820 ESCALAR y 180 NO_PAGAR. Eso es correcto con estos datos y **no dice nada de la
  precisión**. Para el tiempo da igual: las 6 reglas se evalúan siempre todas.
  - `marcar_duplicados` reescribe aquí los 10.000 hechos. Es su peor caso de escritura.

## 2. El pipeline real a 10.000, por etapa (MEDIDO)

`uv run python scripts/bench_escala.py --n 10000 --etiqueta 10k --workers 1,8` → 3 min 39 s de pared,
pico de 653 MB (`/usr/bin/time -v`). **JSONL de 10.000 líneas APTO** según el validador de la entrega.

Cada etapa corre en su propio proceso. RSS base de cada proceso tras los imports: 58 MB.

| Etapa | n | Tiempo | ficheros/s | ms/factura | RSS pico | 500 → 10.000 |
|---|---:|---:|---:|---:|---:|---|
| generar copias (sólo banco) | 10.000 | 0,94 s | 10.589 | 0,09 | 66 MB | — |
| **ingest** (sha256 + info PDF + fila + evento) | 10.000 | **12,4 s** | 808 | 1,24 | 87 MB | 0,61 s → 12,4 s (lineal) |
| **extract, 1 hilo** | 10.000 | **86,3 s** | 116 | 8,6 | 411 MB | 4,53 s → 86,3 s (lineal) |
| · de ello, 9.360 por plantilla | 9.360 | 10,3 s dentro del hilo | — | p50 1 · p95 2 | | |
| · de ello, render de las 640 que van al LLM | 640 | 66,4 s | — | p50 49 · p95 316 | | |
| extract, 8 hilos | 10.000 | 89,7 s | 111 | — | 638 MB | ver §3 |
| hechos de las 640 (equivale a `hechos import`) | 640 | 0,04 s | — | — | 69 MB | — |
| maestro (Excel) | 516 pedidos | 0,05 s | — | — | 86 MB | fijo |
| ERP `pull` completo | 516 asientos | 3,8 s | — | — | 78 MB | fijo: 31 consultas, 3 ORA-00600 superados |
| marcar_duplicados | 10.000 | 0,62 s | 16.075 | 0,06 | 135 MB | 0,01 s → 0,62 s |
| **decide** (norma v3) | 10.000 | **20,3 s** | 493 | 2,03 | 87 MB | **0,07 s → 20,3 s (×280)** · §5 |
| package + validación (todo o nada) | 10.000 | 0,19 s | 53.262 | 0,02 | 102 MB | 0,01 s → 0,19 s |
| validar sólo el JSONL | 10.000 | 0,05 s | 195.220 | 0,005 | 72 MB | — |

- **BD final: 36,7 MB** (3,7 KB por factura): decisiones 13,6 MB · hechos 11,6 MB · eventos 5,6 MB
  (30.671 eventos) · ficheros 1,3 MB. **PDFs: 128 MB** (12,8 KB de media).
- **Camino determinista completo, sin el render del camino LLM: 57,1 s por 10.000** (5,7 ms por factura).
  Es la suma de ingest, plantillas, maestro, ERP, duplicados, decide y package.
  - Con el índice del §5, decide pasa de 20,3 s a 1,7 s y el total queda en **38,6 s (3,9 ms por
    factura)**. Esta cifra está medida etapa a etapa sobre copias de la misma BD; lo que no se ha ejecutado
    es una pasada entera con el índice.

## 3. Extract con 1 y con 8 hilos: 8 hilos no ganan nada

| Hilos | Tiempo | Plantilla, latencia en el hilo | Render del camino LLM | RSS pico |
|---:|---:|---|---|---:|
| 1 | 86,3 s | p50 1 ms · p95 2 ms · máx 4 ms | p50 49 ms · p95 316 ms | 411 MB |
| 8 | 89,7 s | p50 5 ms · **p95 57 ms · máx 2.969 ms** | p50 156 ms · p95 754 ms | 638 MB |

**Veredicto (MEDIDO): el camino determinista no escala con hilos en un proceso.** Con 8 hilos tarda lo mismo
que con 1 (+4 %) y usa un 55 % más de RAM. Hay dos causas y no las he separado con una medida:
- el GIL: el render y el parseo son trabajo de CPU en Python o PyMuPDF;
- el escritor único de SQLite: `_extraer_uno` hace un commit por factura con una conexión por hilo.
  - Las esperas de hasta 3 s en una factura que tarda 1 ms tienen la firma del bloqueo de escritura
    (`busy_timeout` de 30 s en `db.conectar`), no la del GIL.

Consecuencias:
- **Para el camino determinista, 1 hilo.** Si hiciera falta más, la palanca son **procesos**, cada uno con su
  lote, y un único escritor. Más hilos no sirven.
- **Para el camino LLM, más hilos sí ayudan:** ahí el hilo espera a la red, no a la CPU. En el §4, 8 hilos ganan a
  4 en texto (1,80 frente a 1,30 f/s) y en visión (0,106 frente a 0,065). B2 recomendaba 4 por una cola de 94 s
  con 8 hilos que esta noche no apareció.
- El ensayo a 500 da lo mismo: 4,53 s con 1 hilo y 4,74 s con 8.

## 4. Caminos de LLM medidos de verdad (sin la caché del gateway)

`bench_escala.py --n 0 --etiqueta llm --llm-vision 24 --llm-texto 12 --workers-llm 4,8`, a la 01:00.

**Cómo se evita la caché del gateway.** Helmcode devuelve la misma respuesta a un cuerpo de petición idéntico
(B2 §4). Cada copia lleva una marca única que cambia ese cuerpo:
- escaneadas: dos puntos grises cuya posición y tono salen de un hash de la marca, dentro del recorte de la
  segunda lectura;
- texto sin plantilla: una línea al pie.

Las copias se generan de nuevo para cada número de hilos. Pasan por **el `extraer()` real**: doble lectura de
las escaneadas (página a 150 dpi + recorte superior a 200 dpi) y reconciliación con el maestro. Comprobación de
que es LLM de verdad:
- 0 respuestas por debajo de 1,7 s en texto y de 6,7 s en visión;
- 60 lecturas en `cache_llm` por tanda (12 de texto + 24 × 2 de visión): las dos lecturas se hicieron.

| Camino | Hilos | n | Pared | **ficheros/s** | p50 | p95 | máx | reintentos | tokens/factura (entrada / salida) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| texto (`deepseek-v4-flash`) | 4 | 12 | 9,2 s | **1,30** | 2,4 s | 3,6 s | 3,6 s | 0 | 1.136 / 485 |
| texto | 8 | 12 | 6,7 s | **1,80** | 3,3 s | 4,1 s | 4,1 s | 0 | 1.136 / 709 |
| visión (`qwen3.6`, 2 lecturas) | 4 | 24 | 371,6 s | **0,065** | 31,4 s | 128 s | 200 s | 1 | 5.877 / 2.107 |
| visión | 8 | 24 | 227,5 s | **0,106** | 51,5 s | 167 s | 176 s | 2 | 5.876 / 4.094 |

Qué dice esto:
- **Texto:** coincide con B2 (1,28 f/s con 4 hilos) y sube a 1,80 con 8. Esta vez sin la cola de 94 s.
- **Visión:** con 8 hilos la tanda termina antes (0,106 frente a 0,065 f/s), pero la latencia de cada
  petición sube (p50 de 31 a 52 s). Es la firma de un límite de concurrencia del proveedor (Helmcode publica 5
  por modelo): pasado ese límite, las peticiones esperan en su lado.
  - En régimen estable, la suma de latencias entre los hilos da 0,095 (4) y 0,121 (8) f/s. Una tanda de 24 la
    alarga su factura más lenta: en la de 4 hilos, `scan_023` tardó 200 s.
- **Corrección a lo que hoy dicen los documentos.** RESILIENCIA-Y-COSTE §4 (y a partir de ahí
  `docs/benchmark.md` de Miguel) extrapolan con **0,22 f/s de visión**. Esa cifra sale de `bench_llm.py`, que
  hace **una** lectura por escaneada. El camino real hace **dos** (ADR-0003), así que su capacidad medida es
  **0,065-0,106 f/s**, entre 2 y 3,4 veces menos.
  - B2 ya tenía la pista: su §2 da 35,3 s de media por escaneada con doble lectura, y 4 hilos / 35 s ≈
    0,11 f/s, no 0,22.
- **Calidad (no es el objeto de este banco, pero se ve):** en la tanda de 4 hilos, la reconciliación con el
  maestro corrigió NIF o IBAN mal leídos en 7 de 24, y 4 quedaron con `discrepancia_extractores`. Es el
  comportamiento de ADR-0003.

## 5. El cuello de botella del lado determinista: un índice que falta (MEDIDO)

La sospecha era `ErpSnapshot.por_pedido()`: `regla_5_erp` lo reconstruye por factura. **Se midió y no es eso,
hoy.** A 10k, `por_pedido()` suma 0,45 s de los 20,3 s de `decide` (lo cronometra un envoltorio en el banco,
sin tocar `src/`).

**La causa es `db.guardar_decision`.** Hace `UPDATE decisiones SET vigente=0 WHERE sha256=? AND vigente=1` y
`decisiones` no tiene índice sobre `sha256`. Cada decisión recorre la tabla entera, y eso es cuadrático.
Experimento sobre copias de la BD de 10k (`--decide-variantes`):

| Variante (10.000 decisiones) | Plan de SQLite | Tiempo |
|---|---|---:|
| tabla vacía, sin índice (lo que hace hoy `run`) | `SCAN decisiones` | **20,3 s** |
| **reprocesado** con 10.000 decisiones previas, sin índice | `SCAN decisiones` | **67,8 s** |
| tabla vacía, con `CREATE INDEX … ON decisiones(sha256, vigente)` | `SEARCH … USING INDEX` | **1,70 s** |
| reprocesado con 10.000 previas, con índice | `SEARCH … USING INDEX` | **2,28 s** |

- **Crece con cada reprocesado.** El historial no se borra (es a propósito: es el "antes/después" de ADR-0005),
  así que cada `reprocess` hace la tabla más grande y el siguiente más lento. Sin índice se recalcula peor
  cuanto más se ha recalculado.
- A la escala de la Caja no se nota: 540 decisiones en 0,07 s. Por eso no lo había visto nadie.
- **Extrapolado a 100.000 sin índice**, con el exponente medido entre 500 y 10.000 (×280 por ×20, n^1,9):
  unos 34 min la primera pasada y más cada reprocesado. **Con índice**, lineal: unos 17 s.
- **Pedido a Miguel** (`core/schema.sql`, una línea idempotente que no cambia ningún resultado):
  `CREATE INDEX IF NOT EXISTS ix_decisiones_sha ON decisiones(sha256, vigente);`

`por_pedido()` sí será un cuello cuando el ERP crezca. Micro-benchmark de una llamada según el número de
asientos:

| Asientos del ERP | ms por llamada | × 10.000 facturas | × 100.000 facturas |
|---:|---:|---:|---:|
| 516 (hoy) | 0,028 | 0,3 s (medido: 0,45 s) | 2,8 s |
| 5.000 | 0,99 | 9,9 s | 99 s |
| 50.000 | 28,2 | 4,7 min | **47 min** |

(Llamada medida; los productos son EXTRAPOLADOS.) **Pedido a Mónica y Miguel:** construir el índice por
pedido una vez por `decide` y pasarlo a la regla, o cachearlo en el snapshot. Hoy es el 2 % de `decide`.

## 6. RAM: lo que crece con N (MEDIDO a 500 y a 10.000; EXTRAPOLADO a 100k y 1M)

| Etapa | Qué carga entero | Pico sobre la base, 500 → 10.000 | ~por factura | 100.000 | 1.000.000 |
|---|---|---|---:|---:|---:|
| `marcar_duplicados` | todos los `InvoiceFacts` | 11 → 77 MB | 7 KB | ~0,7 GB | ~7 GB |
| `package.empaquetar` | todas las filas y los `Outcome` | 8 → 43 MB | 3,7 KB | ~0,4 GB | ~4 GB |
| `decide` | `fetchall()` de los `hechos_json` | 11 → 29 MB | 1,9 KB | ~0,2 GB | ~2 GB |
| `validar_jsonl` | `read_bytes()` del JSONL | 5 → 13 MB | 0,9 KB | ~0,1 GB | ~1 GB |
| extract, 1 hilo | caché de MuPDF (acotada) + candidatos | 193 → 353 MB | no lineal | no medido | no medido |

Todo cabe en un portátil hasta 1M facturas. Desde ~1M, `marcar_duplicados` y `package` deben ir por
cursor o streaming en vez de cargarlo todo: es un cambio de código, no de infraestructura. El dato de
extract es el pico del proceso y lo domina la caché de MuPDF; no crece como las demás y no lo extrapolo.

## 7. T(N): tiempo de 10.000 y 100.000 facturas

```
T(N) = c_det · N  +  N · p_txt / f_txt  +  N · p_vis / (f_vis · k)
```

| Parámetro | Valor | Origen |
|---|---|---|
| p_plantilla · p_txt · p_vis | 0,936 · 0,006 · 0,058 | la Caja (468 · 3 · 29 de 500), MEDIDO |
| c_det: todo el camino determinista por factura (ingest, plantilla, maestro, ERP, duplicados, decide, package) | **5,7 ms** hoy · **3,9 ms** con el índice del §5 | MEDIDO a 10.000 (§2) |
| f_txt | 1,80 f/s (8 hilos) · 1,30 (4) | MEDIDO en tanda de 12 (§4) |
| f_vis por key del gateway | 0,106 f/s (8 hilos) · 0,065 (4) | MEDIDO en tanda de 24 (§4) |
| k | nº de keys del gateway (hoy 1) | — |

La suma es conservadora: en `run`, las plantillas y la visión comparten el pool de hilos y en parte se solapan.

| Tramo | 10.000 facturas | ¿Medido? | 100.000 facturas | ¿Medido? |
|---|---:|---|---:|---|
| Determinista, hoy | **57 s** | **MEDIDO a 10k** | ~34 min (sólo `decide` crece como n^1,9) | EXTRAPOLADO |
| Determinista, con índice | **39 s** | MEDIDO por etapas a 10k | **~6,5 min** (lineal) | EXTRAPOLADO |
| LLM texto (60 / 600) | 33 s | EXTRAPOLADO de 12 | 5,6 min | EXTRAPOLADO |
| **LLM visión (580 / 5.800), 1 key** | **~1 h 30 min** (rango 1 h 20 min-2 h 30 min) | EXTRAPOLADO de 24 | **~15 h** (13-25 h) | EXTRAPOLADO |
| **Total, 1 key** | **~1,5-2,5 h** | | **~16 h** | |
| Total con 3 keys (visión / 3) | ~30-50 min | | ~5,5 h | EXTRAPOLADO, suponiendo límites por key |

**Lectura:** el 93,6 % de las facturas (las de plantilla) cuesta **menos de un minuto por cada 10.000**. El 5,8 %
(las escaneadas) se lleva **más del 97 % del tiempo**. La cifra de "10.000 en ~45 min" de RESILIENCIA §4 es
optimista unas 2-3 veces por el motivo del §4.

## 8. Coste por factura

- **Marginal: 0 €.** `deepseek-v4-flash` y `qwen3.6` son modelos abiertos, incluidos en la suscripción plana de
  Helmcode. Los frontier dan `402` sin crédito prepago (RESILIENCIA-Y-COSTE §1, consultado el 18/09/2026).
  Todas las tandas de este banco imprimen `coste_eur = 0`.
- **Tokens medidos:**
  - una escaneada, con dos lecturas: 5.877 de entrada y 2.107-4.094 de salida (~8-10 K);
  - una de texto: 1.136 de entrada y 485-709 de salida;
  - 10.000 facturas con la mezcla de la Caja: ~5,3 M tokens.
  - La cuota Starter, 5.000 M al mes, da para ~940 lotes de 10.000. **La cuota no limita.**
- **Lo que sí se paga es la suscripción, amortizada** (Starter, 399 €/mes, B2 §1). El euro por factura depende
  del volumen mensual, no del proceso:

| Facturas/mes | Keys necesarias | €/factura |
|---:|---|---:|
| 500 (Alberto hoy) | 1 | 0,80 |
| 10.000 | 1 (580 escaneadas/mes ≪ ~9.000 escaneadas/día por key) | 0,040 |
| 100.000, repartidas en el mes | 1 (5.800 escaneadas/mes) | 0,004 |
| 100.000 **en una noche de 8 h** | ~2-3 (visión ~15 h con 1 key) | 0,008-0,012 |

- **Hardware:** el portátil. 0 € adicionales; la electricidad no está medida.
- **La palanca de coste es la misma que la de tiempo:** cada escaneada que deja de ir al LLM ahorra ~40-65 s
  del cupo de concurrencia. El euro no cambia hasta que hace falta otra key.

## 9. Umbrales de infraestructura, cada uno con la medida que lo dispara

**La frase que sostiene el proyecto, ahora medida:**
- 10.000 facturas del camino determinista son **39-57 s en un solo núcleo**;
- las 580 escaneadas de esas mismas 10.000 son **~1,5 h de gateway**;
- **para 10× no hace falta más máquina: hace falta que menos facturas lleguen al LLM** (o más keys).

| Pieza | Hoy | Umbral que la dispara | Medida en que se apoya |
|---|---|---|---|
| **Postgres en vez de SQLite** | SQLite WAL, un proceso | **Más de un proceso o máquina escribiendo a la vez** (varios extractores, la consola con acciones, alta disponibilidad). El tamaño no es el disparador | Un escritor aguanta **≥116 commits/s** (extract a 1 hilo, un commit por factura), con esperas de hasta **3 s** en cuanto hay 8 escritores (§3). La BD ocupa **3,7 KB por factura** → 1M son 3,7 GB, nada para SQLite |
| **Almacén de objetos (S3/MinIO) en vez del disco** | `data/caja/facturas` en local | Cuando los workers estén en **más de una máquina** (necesitan ver los mismos PDFs) o la retención pase del disco. Con 1 TB de disco, esto último es a unos 50-80 M de PDFs | **12,8 KB por PDF de media** → 1M son 12,8 GB y 10M son 128 GB |
| **Cola de trabajo** | La tabla `ficheros` hace de cola (pendiente = sin hechos; idempotente por sha256; reanudar es volver a ejecutar) | Cuando haya **varios consumidores** o **entradas continuas de varias fuentes** (email, SFTP, API) y una ráfaga supere el camino de visión de un proceso. Con Postgres, `SELECT … FOR UPDATE SKIP LOCKED` es la cola; un broker aparte sólo con consumidores heterogéneos | Visión: **~0,106 f/s por key → ~9.000 escaneadas/día → ~158.000 facturas/día por key** con la mezcla de la Caja. Por debajo, un proceso con la tabla como cola basta |
| **Spark** | — | **Nunca para este problema.** La parte cara (LLM) es latencia de una API externa con límite de concurrencia: Spark no acelera una API limitada. El cruce con el ERP cabe en memoria: un ERP de 50.000 asientos son 144 MB de pico (micro-benchmark, §5), ~1,7 KB por asiento. Haría falta un ERP de más de ~10 M de asientos (~17 GB) para que no cupiera, y aun así la respuesta es un índice en Postgres, no un clúster | Determinista **39 s por 10k en un núcleo** → 1 M ≈ 65 min en un núcleo, o ~7 min con 10 procesos (EXTRAPOLADO lineal) |
| **Procesos en vez de hilos** (antes que cualquier pieza nueva) | `ThreadPoolExecutor` en extract | Cuando el determinista necesite más de ~250 f/s de un proceso | 8 hilos = 1 hilo en el camino determinista (§3) |

**Qué cambia de verdad primero, por orden y con su cifra:**
1. El índice de `decisiones(sha256)` (§5): de cuadrático a lineal. Una línea.
2. `por_pedido()` una vez por `decide`, cuando el ERP pase de ~5.000 asientos (§5).
3. Más keys o menos escaneadas por LLM, cuando hagan falta más de ~9.000 escaneadas al día.
4. Postgres y almacén de objetos, sólo el día que haya más de una máquina.

## 10. Qué NO está medido
- **Ninguna pasada de 10.000 con el LLM real.** Los tramos de LLM a 10k y 100k son extrapolaciones de tandas
  de 12 (texto) y 24 (visión). Las 580 escaneadas de 10k llevarían horas de gateway; no se lanzaron.
- **El portátil de la demo (Alfonso).** Todo es del portátil de Javier.
- **El ERP con latencia real** (`make erp`): aquí, sin latencia. El pull es fijo (una vez por ejecución, no por
  factura) y no escala con N.
- **Una pasada entera con el índice de `decisiones`.** Medido sólo `decide` sobre copias (§5).
- **Varios procesos en paralelo** sobre el camino determinista: sólo hilos (§3). La palanca propuesta, procesos
  con un único escritor, no está medida.
- **Separar GIL y bloqueo de SQLite** en el resultado de 8 hilos (§3). La firma apunta al bloqueo; no está
  aislado.
- **Un 429 real del gateway:** 0 en las tandas de este ciclo, como en B2.
- **La calidad de las lecturas de visión de las copias marcadas.** No se compara con la Caja: se miden
  tiempo y tokens. Las marcas son dos puntos grises de 2×2 pt en la franja superior (y ≤ 48 pt).

## Reproducir
```bash
(make erp-fast > /tmp/erp.log 2>&1 &)                   # bridge en :8009
uv run python scripts/bench_escala.py --n 500 --etiqueta ensayo --workers 1,8          # 18 s
uv run python scripts/bench_escala.py --n 10000 --etiqueta 10k --workers 1,8           # 3 min 40 s
uv run python scripts/bench_escala.py --n 0 --etiqueta 10k-decide --bd dist/escala/escala-10k-w8.db --decide-variantes
uv run python scripts/bench_escala.py --n 0 --etiqueta llm --llm-vision 24 --llm-texto 12 --workers-llm 4,8
```
El banco borra los PDFs generados al terminar (`--conservar` para no hacerlo). Cada tanda de LLM genera
copias con marca nueva (sufijo con la hora): repetirla vuelve a medir de verdad.
