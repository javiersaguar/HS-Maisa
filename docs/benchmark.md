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
| Demo de resiliencia (`make demo-caos`) | 21,9 s (3 `run` y 3 lecturas del LLM) | ADR-0007 |
| extract · plantilla (468) | p50 3 ms · p95 11 ms · 0 tokens | `bench` + `hechos.metodo` |
| extract · LLM texto (3) | p50 3,3 s · 1.123 / 509 tokens por factura | ídem |
| extract · LLM visión (29) | p50 17,3 s · p95 46,3 s · máx. 85,4 s · 5.876 / 1.308 tokens por factura | ídem |
| enrich ERP | 28 consultas · p50 4 ms · p95 8 ms · **3 reintentos ORA-00600** superados | `bench` (reintentos) |
| ingest (500 PDFs, primera vez) | ~1,5 s (325 ficheros/s); después, 0 eventos nuevos | `bench` |
| decide (500) | < 1 ms por factura | `bench` |
| Tokens totales · EUR | 173.773 de entrada / 39.461 de salida · **0,00 EUR** | `bench` |

**Salvedad sobre la visión.** Aquí sale una p50 de 17,3 s y Javier midió 35,3 s de media
(`docs/agentes/RESILIENCIA-Y-COSTE.md` §2). El gateway cachea por cuerpo de petición, y en esta
pasada algunas lecturas pueden haber salido de su caché. La cifra prudente es la de Javier:
0,22 ficheros/s con 4 hilos, con saturación en 4 (§4).

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
- **Cuello de botella: la visión.** De los 204 s, unos 189 son de extract, y casi todo son las 29
  escaneadas. Plantillas, ERP, decide y package juntos suman unos 15 s (la pasada con la caché llena).
- **Cola de latencia.** Una lectura tardó 85 s en esta pasada, y en la demo de caos una petición se
  colgó 87 s antes de un `LLM-RED`. Javier vio 94 s dos veces. El arreglo son timeouts por modalidad,
  60 s para texto y 90 s para visión (ciclo 3, rama `javier/ingesta`, sin mergear a esta rama al medir).
- **A 10×** (5.000 facturas, misma mezcla; esto es **extrapolación**): unas 290 escaneadas a 0,22
  ficheros/s dan ~22 min; el resto, ~2,5 min.
  - Más hilos no ayudan en visión (satura en 4).
  - Lo que sí escala sin coste es subir la cobertura de plantillas.
- **A 100×:** hacen falta más keys del gateway (399 €/mes por tramo, límites por key) y repartir extract
  entre procesos. `decide` y la BD no limitan: 500 decisiones en 0,43 s dan unos 43 s para 50.000
  (extrapolación lineal).
- **Nuevos tipos de archivo:** un email, un Excel o más escaneados son un conector nuevo en `extract/`
  que produce el mismo `InvoiceFacts`; `rules/`, `core/` y `pipeline/` no cambian (RESILIENCIA-Y-COSTE
  §6). Un Excel no necesita LLM; un email va por el camino de texto; los escaneados son el único caso
  caro.

Qué **no** está medido:
- ERP con latencia real (`make erp`);
- una ejecución de 10.000 facturas;
- un 429 real del gateway.
