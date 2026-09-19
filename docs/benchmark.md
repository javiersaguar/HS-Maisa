# Benchmark (sólo cifras medidas; lo extrapolado se dice)

Medido el 19/09/2026 a las 00:14 (Madrid) sobre el commit `5b5c1c0` (`miguel/pipeline`). Las cifras salen
de la tabla `eventos` (`albertitos bench --desde <inicio>`) y de `time`. Se usaron BD aparte (`dist/bench.db`,
`dist/bench2.db`); la BD de la entrega no se tocó.

## Condiciones
| Hardware | SO | Lote | ERP | % que toca el LLM | Modelos | Caché | Workers |
|---|---|---|---|---|---|---|---|
| Intel i5-1235U (10 núcleos / 12 hilos), 7,7 GB RAM | Windows 11 Pro · Python 3.12.13 | Caja, lote 1: 500 PDFs | bridge local `:8009` sin latencia (`make erp-fast`) | 6,4 % (32 de 500): 29 escaneadas (visión) y 3 sin plantilla (texto) | visión `qwen3.6` (doble lectura) · texto `deepseek-v4-flash`, vía gateway Helmcode | vacía (BD nueva) | 4 |

## Cifras
| Métrica | Valor | De dónde sale |
|---|---|---|
| **Pasada completa, caché vacía** | **204,0 s · 500 ficheros · 2,5 ficheros/s** (3 min 24,9 s de `time`) · entrega APTO | `time albertitos run` sobre BD nueva |
| **Reprocesado con la caché llena** (BD nueva, sólo la caché copiada) | **15,0 s · 33,4 ficheros/s** · 0 tokens | `time albertitos run` sobre `bench2.db` |
| Segunda pasada sin cambios | 1,3 s (2,3 s de `time`) · 0 nuevos · 0 llamadas al LLM | `run` otra vez |
| `reprocess --impacted` con ERP v1→v2-sim | 2 de 500 recalculadas · 0,04 s (0,51 s de CLI) | ADR-0006 |
| `reprocess --todo` (500 decisiones) | 0,43 s (0,93 s de CLI) | ADR-0006 |
| `reprocess --todo` con el índice `decisiones(sha256, vigente)` (esquema v2) | **0,11 s** con 1.000 decisiones en el historial (antes 0,35 s) · **0,16 s** con 4.500 (antes 2,34 s: sin índice crecía ~0,3 s por pasada) | 19/09 01:45, copia de la BD real, 8 pasadas antes y 8 después |
| `reprocess --todo` a **10.000** (los 500 hechos reales ×20 con sha256 distinto) | sin índice **160,6 s** (tabla vacía) y **297,6 s** (10.000 decisiones previas) · con índice **4,08 s** y **3,97 s** | 19/09 01:48-01:55, `pipeline.run.reprocesar(todo=True)` en BD aparte (`dist/ensayo-10k/`); las copias comparten pedido, así que salen duplicadas (como en ESCALA-10K §1) |
| Demo de resiliencia (`make demo-caos`) | 21,9 s (3 `run` y 3 lecturas del LLM) | ADR-0007 |
| extract · plantilla (468) | p50 3 ms · p95 11 ms · 0 tokens | `bench` + `hechos.metodo` |
| extract · LLM texto (3) | p50 3,3 s · 1.123 / 509 tokens por factura | ídem |
| extract · LLM visión (29) | p50 17,3 s · p95 46,3 s · máx. 85,4 s · 5.876 / 1.308 tokens por factura | ídem |
| enrich ERP | 28 consultas · p50 4 ms · p95 8 ms · **3 reintentos ORA-00600** superados | `bench` (reintentos) |
| ingest (500 PDFs, primera vez) | ~1,5 s (325 ficheros/s); después, 0 eventos nuevos | `bench` |
| decide (500) | < 1 ms por factura | `bench` |
| Tokens totales · EUR | 173.773 de entrada / 39.461 de salida · **0,00 EUR** | `bench` |

**Salvedad sobre la visión.** La p50 de 17,3 s por escaneada de esta pasada está MEDIDA, con las dos
lecturas que hace el pipeline (ADR-0003). Pero pudo pegar en la caché del gateway: Helmcode devuelve la
misma respuesta a un cuerpo de petición idéntico, y estas 29 ya se habían leído con el mismo prompt y
modelo. A posteriori no se puede separar qué lectura salió de su caché. **No la usamos para extrapolar.**

Para extrapolar usamos lo que midió D1 con copias marcadas que el gateway no puede reconocer y el
`extraer()` real con doble lectura (`docs/agentes/ESCALA-10K.md` §4, portátil de Javier, tandas de 24):

| Hilos | ficheros/s | p50 por escaneada | p95 | reintentos |
|---:|---:|---:|---:|---:|
| 4 | **0,065** | 31,4 s | 128 s | 1 |
| 8 | **0,106** | 51,5 s | 167 s | 2 |

La cifra que usábamos antes, 0,22 ficheros/s con 4 hilos (`RESILIENCIA-Y-COSTE.md` §4), sale de
`scripts/bench_llm.py`, que hace **una** lectura por escaneada. Sobreestima la capacidad real entre 2 y
3,4 veces.

## Fórmula de coste
`coste = N · p_llm · (t_in · P_in + t_out · P_out) + fijo`

Con lo medido:
- p_llm = 32/500 = 0,064;
- t_in = 5.430 y t_out = 1.233 tokens por factura que toca el LLM;
- P_in = P_out = **0 €** (modelos abiertos incluidos en la suscripción; los modelos frontier dan 402 sin
  crédito, según RESILIENCIA-Y-COSTE §1).

**Coste marginal: 0 € por factura y 0 € por 10.000.** El dinero está en el `fijo`: la suscripción
Starter, a 399 €/mes (consultada el 18/09). Amortizada sale a 0,80 € por factura con 500 facturas al
mes, 0,040 € con 10.000 y 0,004 € con 100.000. La cuota de 5B tokens al mes no limita: da para unas
560.000 escaneadas.

Palancas: más plantillas (baja p_llm, que aquí es sobre todo exposición a fallos) y la caché por sha256.
Reprocesar no vuelve a pagar tokens: 15 s y 0 tokens con la caché llena.

## Determinismo: la entrega sale de hechos congelados, no de una relectura
La pasada en frío volvió a leer las 29 escaneadas con el LLM. **6 de 29 cambiaron de resultado** frente
a la entrega oficial, que usa la lectura congelada (`hechos_caja.jsonl` / caché):

| Factura | Oficial → relectura | Por qué |
|---|---|---|
| `scan_012` | PAGAR → ESCALAR | total 877,83 frente a 877,63; base + IVA = 877,63: la relectura se equivoca |
| `scan_017` | PAGAR → ESCALAR | NIF `S46102331` frente a `B46102331` |
| `scan_027` | PAGAR → ESCALAR | `texto_instruccion` sin fragmento; en la imagen no hay instrucción |
| `scan_028` | PAGAR → ESCALAR | `texto_instruccion` = "RECIBIDO CONTABILIDAD", un sello |
| `scan_015` | PAGAR → ESCALAR | `importe_ambiguo` sólo en la relectura |
| `scan_014` | ESCALAR → PAGAR | `importe_ambiguo` sólo en la lectura oficial |

Consecuencia: **no se relee nada en frío antes de una entrega.** La caché por sha256 es lo que hace
reproducible el resultado: con la caché llena, dos pasadas dan el mismo JSONL byte a byte. Las 6 van
a Mónica para revisarlas a mano.

## Límites medidos y evolución
- **Cuello de botella: la visión con doble lectura.** De los 204 s, unos 189 son de extract, y casi
  todo son las 29 escaneadas (MEDIDO). Plantillas, ERP, decide y package juntos suman unos 15 s
  (MEDIDO: la pasada con la caché llena). A 10.000 facturas la proporción es la misma: el camino
  determinista son 57 s y las 580 escaneadas ~1,5 h con una key, más del 97 % del tiempo (ESCALA-10K §7:
  57 s MEDIDO a 10.000 en el portátil de Javier; 1,5 h EXTRAPOLADO de la tanda de 24 a 0,106 f/s).
- **Hilos: 8 mejor que 4 en el camino LLM.** En visión, 8 hilos dan 0,106 f/s frente a 0,065 con 4, y en
  texto 1,80 frente a 1,30 (MEDIDO, ESCALA-10K §4). Cada petición espera más (p50 de 31 a 51 s): el
  límite de concurrencia está en el proveedor (Helmcode publica 5 por modelo), pero la tanda acaba
  antes. La recomendación de 4 hilos venía de una cola de 94 s con 8 hilos en texto (RESILIENCIA §4)
  que en las tandas de D1 no apareció. **Recomendación: `ALBERTITOS_WORKERS=8` cuando haya escaneadas
  nuevas que leer** (`run` usa 1 por defecto). Más de 8 no está medido. En el camino determinista los
  hilos no ganan nada: 8 tardan lo mismo que 1 (MEDIDO, ESCALA-10K §3).
- **Cola de latencia.** Una lectura tardó 85 s en esta pasada, y en la demo de caos una petición se
  colgó 87 s antes de un `LLM-RED`. Javier vio 94 s dos veces. El arreglo son timeouts por modalidad,
  60 s para texto y 90 s para visión (ciclo 3, rama `javier/ingesta`, sin mergear a esta rama al medir).
- **A 10×** (5.000 facturas, misma mezcla; todo EXTRAPOLADO):
  - visión: ~290 escaneadas a 0,106 f/s (8 hilos, MEDIDO en tanda de 24) → **~46 min**; con 4 hilos
    (0,065) → ~74 min;
  - texto: ~30 a 1,80 f/s → ~17 s;
  - el resto, ~2,5 min (lineal desde los 15 s MEDIDOS con la caché llena en esta máquina).
  - Lo que escala sin coste es subir la cobertura de plantillas: cada escaneada que deja de ir al LLM
    ahorra ~9-15 s de pared (1 / 0,106 = 9,4 s con 8 hilos; 1 / 0,065 = 15,4 s con 4).
- **A 100×** (50.000 facturas; todo EXTRAPOLADO):
  - visión: ~2.900 escaneadas → **~7,6 h con una key** a 0,106 f/s (~12,4 h a 0,065). Con 3 keys,
    ~2,5 h, suponiendo que el límite es por key (no medido). 399 €/mes por key;
  - determinista: 3,9 ms por factura con el índice de `decisiones` (MEDIDO por etapas a 10.000 por D1, portátil de Javier) → ~3,3 min;
  - `decide` y `reprocess` son lineales **gracias al índice `decisiones(sha256, vigente)`** (esquema v2,
    19/09). Sin él eran cuadráticos y empeoraban con cada reprocesado: a 10.000, `reprocess --todo`
    tardaba 160,6 s la primera vez y 297,6 s la segunda; con él, 4,1 s y 4,0 s (MEDIDO en esta
    máquina). A 50.000, ~20 s (EXTRAPOLADO lineal desde los 4,0 s a 10.000).
- **Nuevos tipos de archivo:** un email, un Excel o más escaneados son un conector nuevo en `extract/`
  que produce el mismo `InvoiceFacts`; `rules/`, `core/` y `pipeline/` no cambian (RESILIENCIA-Y-COSTE
  §6). Un Excel no necesita LLM; un email va por el camino de texto; los escaneados son el único caso
  caro.

Qué **no** está medido:
- ERP con latencia real (`make erp`);
- 10.000 facturas con el LLM real: D1 midió el camino determinista a 10.000 y el LLM en tandas de 24
  (ESCALA-10K §10);
- la visión sin la caché del gateway en esta máquina (la tabla de la salvedad es del portátil de Javier);
- más de 8 hilos, o más de una key;
- un 429 real del gateway.
