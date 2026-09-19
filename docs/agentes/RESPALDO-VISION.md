# Respaldo de visión · medido contra el gateway (J3 · 19/09/2026, 12:4x-13:0x)

**Recomendación: `ALBERTITOS_MODELO_VISION_FALLBACK=deepseek-v4-flash`.** No lee mejor que el
principal — ninguno lo hace —, pero es el único candidato que **no añade un riesgo nuevo**: contesta
en 4,3 s de mediana (el principal, 12,0 s), nunca falló, y no se dejó ni un `pedido`, ni un `total`,
ni una `fecha` de las ocho. `glm5.3-flash` queda **descartado** para visión.

Sin respaldo (lo de hoy), si `qwen3.6` se cae o da 429 a las 18:00 las escaneadas del lote 2 quedan
PENDIENTES y su única salida es la contingencia manual (ESCALAR, ADR-0009). Con respaldo, se leen.

## Qué se midió, y qué no

    10|`uv run python scripts/bench_vision_respaldo.py --modelos qwen3.6,deepseek-v4-flash,glm5.3-flash --facturas 8 --max-llamadas 30 --sufijo j3a`

- **24 llamadas reales** (3 modelos × 8 escaneadas), de un tope de 30. 6 min 46 s en total. 0 desde
  caché, 0 errores. Portátil de Javier, dpi 150 (el de producción), un hilo.
- Muestra: las 8 escaneadas del lote 1 con pedido en el maestro (`copia_2026_0518`, `fax_2026_0411`,
  `reimpresion_0712`, `scan_001`…`scan_005`). Las tres primeras son los casos sucios de la Caja.
- **Una lectura por factura**, no la doble de `extract/etapa.py`: esto mide el modelo, no el pipeline.
- `qwen3.6` va como **control**, medido a la vez y en las mismas condiciones. Las cifras de §5 de
  RESILIENCIA (18/09) eran de tres facturas y otra tanda; éstas las sustituyen para estos ocho ficheros.
- La caché se escribió en `dist/ensayo/j3/bench.db`. La BD real se abrió en sólo lectura: su sha256 y
    20|  el de `dist/entrega/outcomes.jsonl` son los mismos antes y después.
- **No medido:** 429 real, concurrencia, y el respaldo dentro del pipeline entero (eso es de J1).

## Resultados

| Modelo | ok | p50 | máx | tokens (in/out) | pedido | total | fecha | NIF ✓ | IBAN ✓ |
|---|---|---|---|---|---|---|---|---|---|
| `qwen3.6` (principal) | 8/8 | **12,0 s** | 25,8 s | 23.864 / 16.258 | **8/8** | 8/8 | **8/8** | **5/5** | **5/5** |
| `deepseek-v4-flash` | 8/8 | **4,3 s** | **8,9 s** | **15.168 / 4.156** | **8/8** | 8/8 | **8/8** | 4/5 | 3/5 |
| `glm5.3-flash` | 8/8 | 15,3 s | **81,2 s** | 28.576 / 4.827 | 7/8 | 8/8 | 7/8 | 3/5 | 3/5 |

    30|NIF e IBAN se cuentan **sólo sobre las cinco escaneadas limpias** (`scan_001`…`scan_005`), contra el
Excel: es la única verdad independiente del sistema que hay sin etiquetar a mano. En las otras tres el
IBAN impreso **no es** el del maestro (es la trampa que R1 caza: las tres leyeron lo mismo los tres
modelos), así que ahí un «fallo» contra el maestro no mide al modelo. La tabla del script, que no hace
esa separación, sale 7/8 · 5/8 · 5/8 y **no** es la que hay que citar.

Coste: **0 EUR**. Los tres son modelos abiertos del gateway, incluidos en la suscripción plana
(RESILIENCIA §1); no cobran por token.

## Por qué `deepseek-v4-flash` y no `glm5.3-flash`

    40|1. **Latencia frente al timeout.** `glm5.3-flash` tardó **81,2 s** en el fax contra un
   `TIMEOUT_VISION_S` de 90 s. Un respaldo que roza el timeout en una factura difícil, y que se usa
   justo cuando el proveedor va mal, no es un respaldo: es un segundo fallo. `deepseek` no pasó de
   8,9 s, o sea 10× de margen.
2. **Se dejó campos que el principal no falla.** `glm5.3-flash` leyó `PO-2026-0463` donde pone
   `PO-2026-0480` (`scan_004`) y `2026-04-17` por `2026-04-11` (el fax). Un `pedido` equivocado que
   **existe** en el Excel es el peor error posible: cruza contra otro pedido. No decide PAGAR (R2 exige
   que el pedido sea del NIF emisor), pero mueve la factura a un motivo falso.
3. **No concentrar el riesgo.** `glm5.3-flash` ya es el respaldo de TEXTO (RESILIENCIA §3 (e)). Si el
   respaldo de visión es el mismo modelo, un problema suyo nos deja sin las dos redes a la vez.
    50|4. `gemma4` no se midió: §5 ya lo descartó (47 s en imagen y acierta menos) y no valía gastar 8 de
   las 30 llamadas en confirmarlo.

Lo que `deepseek-v4-flash` falla son **dígitos sueltos**: `B60233808` por `B90233808`, un `9` por un
`0` en el IBAN. Es el mismo error que comete el principal, ni peor ni distinto.

## El riesgo, y por qué la norma ya lo tapa

Un respaldo peor que el principal podría, en teoría, hacer que se **pague** una factura con el NIF o el
IBAN mal leídos. **No puede**, y está comprobado en el código, no supuesto:

    60|- El respaldo devuelve un `InvoiceFacts` normal por el mismo camino (`llm.extraer` → `_a_hechos` →
  `validadores.validar`): no hay atajo que se salte nada.
- La **doble lectura sigue activa** (`etapa._segunda_lectura`): la segunda llamada vuelve a pasar por
  `llm.extraer`, así que si el principal está caído también la sirve el respaldo. Con `deepseek` eso
  cuesta ~8,6 s por escaneada, menos que las ~24 s que cuestan hoy las dos de `qwen3.6`.
- Si las dos lecturas no coinciden en NIF, IBAN o pedido, `_reconciliar_con_maestro` elige la que
  respalda el Excel **y** baja `confianza` a 0,6. Con `CONFIANZA_MINIMA = 1.0`, la R6 de la norma v3
  escala esa factura (ADR-0011): **una lectura reconciliada no se paga sola**.
- Si no se puede reconciliar, queda `DISCREPANCIA_EXTRACTORES`, que está en `ANOMALIAS_HUMANO`: R6
  escala igual.
    70|- Y aunque las dos lecturas coincidieran en un NIF mal leído, `regla_1_proveedor` pide que el NIF esté
  en el maestro y que el IBAN sea el de ese proveedor. `B60233808` no existe en el maestro → R1 en rojo.

**El peor caso del respaldo es un ESCALAR de más, nunca un PAGAR de menos rigor.** Ésa es la frase para
la defensa: el respaldo compra disponibilidad; la precisión la da la reconciliación con el maestro.

## Qué hay que hacer (Javier, antes de las 17:30)

Una línea en `.env` (los agentes no pueden escribirlo):

```
    80|ALBERTITOS_MODELO_VISION_FALLBACK=deepseek-v4-flash
```

No hace falta tocar código: `TIMEOUT_VISION_S` de 90 s le sobra (máximo observado 8,9 s), el respaldo ya
se salta el circuit breaker desde el arreglo de E1, y cachea con clave propia. Para comprobar que entra,
con el principal apuntado a un modelo que devuelve 402:

```bash
ALBERTITOS_MODELO_VISION=claude-sonnet-5 ALBERTITOS_MODELO_VISION_FALLBACK=deepseek-v4-flash \
ALBERTITOS_DB=dist/ensayo/j3/prueba.db uv run albertitos extract --fixture <una escaneada>
    90|# en el evento: modelo=deepseek-v4-flash respaldo=si
```

## Volver a medirlo

```bash
uv run python scripts/bench_vision_respaldo.py --listar      # qué ofrece el gateway hoy
uv run python scripts/bench_vision_respaldo.py --modelos qwen3.6,deepseek-v4-flash --facturas 8 \
    --max-llamadas 30 --sufijo <otro>                        # el sufijo, distinto: si no, sale de caché
```

   100|Con el mismo `--sufijo` las lecturas salen de la caché de ensayo y el script lo avisa por línea
(`DESDE CACHÉ: no vale`). Detalle campo a campo de esta tanda: `dist/ensayo/j3/resultados.json`.
