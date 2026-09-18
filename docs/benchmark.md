# Benchmark (rellenar con `/benchmark`; sólo cifras medidas)

## Condiciones
| Hardware | SO | Lote | ERP latencia | % LLM | Modelo | Caché | Workers | Fecha/commit |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

## Cifras
| Métrica | Valor | De dónde sale |
|---|---|---|
| ficheros/s (pasada completa, caché vacía) | | `time uv run albertitos run` |
| ficheros/s (reprocesado, caché llena) | | ídem, segunda pasada |
| p50 / p95 extract (ms) | | `albertitos bench` |
| p50 / p95 enrich ERP (ms) · reintentos ORA-00600 | | `albertitos bench` |
| tokens in/out totales · EUR totales | | `albertitos bench` |
| EUR por factura · por 10.000 | | fórmula |

## Fórmula de coste
`coste = N · p_llm · (t_in · P_in + t_out · P_out) + N · p_vision · c_vision`
*(valores medidos y precios citados con fecha)*

## Límites medidos y evolución
*(cuello de botella, 10×, 100×, nuevos tipos de archivo)*
