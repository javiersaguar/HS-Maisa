# Hitos y señales de repliegue (hora de Madrid) · al día el domingo 20/09 a las 01:30

## Lo que queda
| Cuándo | Qué | Dueño |
|---|---|---|
| **Dom 20 02:00** | **Congelación de funcionalidad.** Sólo docs, ensayo y arreglos de NO APTO | todos |
| Dom 20 (noche) | Grabar y editar la demo. La pública (`albertitos.vercel.app`) está despierta y probada | Alfonso |
| **Dom 20 08:00** | **Entrega final**: ya está publicada (`d2ade3f`). Sólo se republica si cambia la norma o el PDF | Javier / Miguel |
| Dom 20 09:00 | Mentores: divisas e IVA (abajo). Si responden, reprocesar el lote 2 y republicar | Mónica |
| Dom 20 ~09:00 | **PDF del plan** al día con el lote 2 y republicado: es uno de los tres ficheros de la entrega | Alfonso |
| Dom 20 10:30 | **Cierre interno** (colchón). Oficial en la web: **11:00**, «cierre de entrega y registro del commit» | — |
| Dom 20 11:00 | La organización clona y registra el commit (hora oficial) | — |
| Dom 20 (hora por confirmar) | Defensa 10 min (2/2/4/2). El bloque 4 pide demostrar **timeout, rate limit, respuesta inválida o caída** | Alfonso |

**Repliegues que siguen en pie:** si algo se rompe después de la congelación, se entrega lo que ya está publicado
(`d2ade3f`, auditoría VERDE) y la demo se hace con `albertitos trace` en terminal, que no necesita red ni consola.

## Lo que ya pasó
| Cuándo | Qué | Cómo acabó |
|---|---|---|
| Vie 18 19:00 | Material inicial: el repo de participantes, no un zip | ✅ `data/caja` con su manifiesto `data/caja.sha256` |
| Vie 18 23:59 | Contratos, ERP v1, maestro, trampas, LLM sobre la muestra | ✅ |
| Sáb 19 02:00 | **Repliegue 1:** sin `outcomes.jsonl` válido, se para todo | ✅ no hizo falta: había entrega válida desde las 23:05 del viernes |
| Sáb 19 10:07 | **Entrega de seguro** del lote 1 | ✅ `232bb76`, 500 líneas, 438/53/9 |
| Sáb 19 12:00 | **Repliegue 2:** > 10 ficheros sin extracción validada | ✅ no hizo falta: 500/500 extraídos |
| **Sáb 19 17:57** | **Lote 2.** No vino en `lote-2-sorpresa-v3.2.zip` ni con hashes en el canal, como anunciaba la web: llegó como **un commit del repo de participantes** (`f831e34`), con 40 PDF en `facturas_primin/` y tres CSV (`erp_export_lote2`, `pedidos_nuevos`, `proveedores_nuevos`) | ✅ copiado a `data/lote2/` con manifiesto propio (`data/lote2.sha256`) |
| Sáb 19 18:00 | **La regla nueva** que prometía la web | 🔴 **nunca se publicó.** Los datos traen 8 facturas en divisa y 4 proveedores extranjeros: la v4 de Miguel las escala con su motivo (ADR-0022) |
| Sáb 19 20:00 | **Repliegue 3:** si la consola no enseña una traza | ✅ no hizo falta: la consola funciona, y además hay demo pública |
| Sáb 19 22:00 | **Repliegue 4:** si el lote 2 no está procesado, se cancela el bonus | ✅ no hizo falta: procesado y entregado a las 00:17 |
| Sáb 19 23:00 | Ensayo del «dato en vivo» (< 30 s) | ✅ **1,4 s** con el Excel cambiado y 0,2 s con un asiento del ERP (`KIT-DEFENSA.md`) |
| **Dom 20 00:17** | **Entrega con los dos lotes** | ✅ `d2ade3f`: 500 (445/46/9) + 40 (23/16/1), auditoría VERDE |

## Preguntas para los mentores
### Abiertas, y es lo primero de la mañana
Se juegan **5 facturas de 540** y la validación es binaria.
1. **Tipo de cambio:** ¿hay tabla oficial? Si no, ¿vale el tipo fijo con el que cuadran los pedidos? (El mismo tipo
   sale en facturas de fechas distintas y, convertido, cuadra al céntimo con el pedido y con el asiento del ERP.)
2. **IVA 0 % de exportación:** una factura en divisa que, convertida, cuadra con el pedido y con el ERP, ¿es PAGAR o
   ESCALAR?
3. **La regla 3 de la norma,** ¿es «el IVA debe estar bien calculado» (lo que dice el Excel) o «siempre 21 %» (lo que
   implementamos)?
4. **Frontera NO_PAGAR / ESCALAR:** hipótesis nuestra, NO_PAGAR = violación objetiva comprobada en el ERP (por
   ejemplo, ya PAGADA). Afecta a unas 35 líneas.
5. **Pedido ANULADO en el Excel:** hoy no cambia nada, porque la norma no lee `Pedido.estado`.
6. **Copias exactas:** ¿se escala también el original del lote 1, o sólo la copia?

### Cerradas sin respuesta: las decidimos nosotros, y queda escrito
| Pregunta | Qué hicimos | Dónde |
|---|---|---|
| ¿El lote 1 final va con la regla nueva y el ERP actualizado? (P0-2) | **No.** Cada lote se decide en su contexto: el 1 con v3 y ERP v1, el 2 con v4 y ERP v2. Con el ERP v2, `factura_4635` pasaría a NO_PAGAR; no se aplica | ADR-0021 |
| ¿El lote 2 puede traer una factura idéntica byte a byte, con otro nombre? (P0-1) | Preparado: cada nombre tiene su línea y las copias escalan. En el lote 2 real no ha pasado | ADR + `identidades` |
| ¿Respecto a qué fecha se evalúa «fecha no futura»? | `ALBERTITOS_FECHA_CORTE` (2026-09-18), guardada con cada decisión. Nunca `date.today()` | regla 3 del equipo |
| ¿Los PDF que se declaran «documento de prueba del evaluador» se validan igual? | Sí: el texto de una factura es un dato, no una instrucción. Escalan por anomalía | ADR-0010 · `.claude/rules/texto-es-dato.md` |
| ¿Dónde llega la regla nueva? | No llegó. Se decidió con lo que dicen los datos | ADR-0022 |

**Respuestas de mentores:** *(anotar aquí, literales y con hora, en cuanto haya alguna)*

## Turnos de sueño
Ya no aplican: el sábado se cumplieron los hitos y la entrega de los dos lotes salió a las 00:17 del domingo.
Lo que queda de noche es de Alfonso, grabando y editando. Criterio para el domingo: **descansa primero quien
defiende**, y antes de la defensa hay que tener a alguien despierto capaz de republicar (Javier o Miguel).
