# Decisiones de norma pendientes · dossier para Mónica · 19/09/2026 01:30 (D2)

Cada política abierta con **los ficheros concretos a los que afecta hoy** y lo que la norma hace ahora mismo, para que
decidir cueste minutos. Datos sobre los 500 hechos del lote 1 y sus decisiones vigentes (`norma v3`, maestro
`80911e429c6c`, ERP `v1`): **443 PAGAR · 48 ESCALAR · 9 NO_PAGAR**.

## Lo que ya he tocado en `rules/norma_v3.py` (revísalo y revierte si no estás de acuerdo)
| Cambio | Por qué | Impacto medido |
|---|---|---|
| R6: la evidencia se recorta a **300** caracteres en vez de 120 | el tramo de `F26-2201` mide 127 y la demo enseñaba media orden ("…bajo revisión…" sin "Debe escalarse cualquier factura suya") | ninguna decisión cambia; sólo el texto del motivo |
| `Aviso.NIF_INVALIDO` entra en `ANOMALIAS_HUMANO` | un NIF con forma imposible es anomalía que un humano debe ver | **0 facturas** hoy; protege el lote 2 |

Falta el test de ambas en `tests/test_rules.py` (tu fichero, no lo toco).

## Hallazgo que sí cambia resultados: el mismo pedido facturado dos veces
`marcar_duplicados` (paso de `run`) **nunca se había ejecutado** sobre la BD: ningún hecho tenía el aviso. Al ejecutarlo:

| file_id | Nº factura | Fecha | Importe | Pedido | Antes | Ahora |
|---|---|---|---|---|---|---|
| `factura_41082.pdf` | F26-0233 | 2026-04-07 | 1.512,50 | PO-2026-0492 | PAGAR | ESCALAR |
| `2026-0233-A_catering.pdf` | 2026/0233-A | 2026-04-11 | 1.512,50 | PO-2026-0492 | PAGAR | ESCALAR |

Mismo proveedor (P005), mismo importe que el pedido, el ERP tiene un único asiento `AS-00492` PENDIENTE. El sufijo "-A"
y la fecha posterior sugieren una reemisión. **Sin este paso pagábamos dos veces**, que es lo único que la norma prohíbe
por escrito ("Nunca pagar dos veces el mismo pedido").
**Tu decisión:** ¿las dos ESCALAR (lo que hace ahora) o una PAGAR (la primera por fecha) y la otra NO_PAGAR? Recomendación:
las dos ESCALAR — la referencia privada esperará como mínimo que una no sea PAGAR, y "ante duda razonable, escalar".

## Políticas abiertas, con los ficheros afectados
| # | Política | Hoy | Afecta a | Recomendación |
|---|---|---|---|---|
| 1 | `discrepancia_extractores` en escaneadas | R6 → ESCALAR | 5: `copia_2026_0518`, `fax_2026_0411`, `scan_016`, `scan_021`, `scan_023` | mantener: identificador ilegible o distinto del maestro (verificado a 220 dpi, `docs/trampas.md`) |
| 2 | Lecturas reconciliadas con el maestro (`confianza = 0,6`) | se paga si el resto cuadra | 6: `scan_006`, `scan_009`, `scan_011`, `scan_012`, `scan_017`, `fax_2026_0411` | ratificar o exigir ESCALAR; es lo que falta para aceptar el ADR-0003 |
| 3 | `fecha = None` (fecha imposible impresa) | R4 → ESCALAR | 3: `2026-03-19_P008`, `FA-1123_construcciones`, `FA-2967_seguridad` (las dos últimas ordenan sustituir la fecha) | mantener |
| 4 | Cuota de IVA que no sale del porcentaje impreso | R3 → ESCALAR | 6 | mantener |
| 5 | `texto_instruccion` | R6 → ESCALAR | 31 reales (+1 falso, ver abajo) | mantener |
| 6 | PDF que dice "pedido anulado / no procede pago" | R6 → ESCALAR | 2: `2026-23904_construcciones`, `FA-3388_ofimática` | mantener: el Excel y el ERP los dan por vivos; el documento no manda |
| 7 | Frontera NO_PAGAR vs ESCALAR | NO_PAGAR sólo si el ERP ya lo marcó PAGADA | 9 | confirmar con un mentor; es la pregunta abierta desde el viernes |
| 8 | 20 pedidos del Excel sin NIF | — | **0 facturas los referencian**: no urge para el lote 1 | dejarlo anotado por si el lote 2 los usa |
| 9 | Documento con otro superpuesto | no hay aviso honesto | 2: `scan_023` (manchas + factura detrás), `scan_025` (transparencia invertida con sello "URGENTE") | pedir `Aviso.DOCUMENTO_SUPERPUESTO` a Miguel y decidir si escala |

## Falso positivo pendiente de arreglar: `scan_025.pdf`
No tiene ninguna instrucción: el modelo devolvió la cadena `"None"` y el código la tomó por evidencia. Hoy **escala con el
motivo literal `el documento dice: "None"`**. El fallo está corregido en `extract/llm.py`, pero **no he reextraído ese
fichero**: sin el aviso pasaría probablemente a PAGAR, y la factura lleva otra transparentándose por detrás. Cuando exista
el aviso del punto 9, se reextrae y se decide con el motivo verdadero.

## Para el mentor (siguen abiertas desde el viernes)
1. ¿Cuándo es NO_PAGAR y cuándo ESCALAR?
2. Dos facturas del mismo pedido: ¿una PAGAR y otra NO_PAGAR, o las dos ESCALAR?
3. ¿Un escaneado con otro documento superpuesto se escala?
