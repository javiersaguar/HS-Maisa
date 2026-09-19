# ADR-0003 · Las escaneadas se leen dos veces y el desacuerdo se resuelve con el maestro, no con el modelo

- **Estado:** aceptado, **acotado por el ADR-0011** (Mónica, 19/09): la reconciliación con el maestro sigue
  eligiendo qué lectura vale, pero una lectura reconciliada (confianza < 1) ya no basta para pagar: R6 la escala.
  Las 5 escaneadas que se pagaban así (`scan_006/009/011/012/017`) pasan a ESCALAR.
- **Fecha:** 2026-09-18 23:45 · **Dueño:** Javier · **Módulos:** extract/

## Contexto
29 de las 500 facturas no tienen capa de texto (`copia_`, `fax_`, `reimpresion_`, `scan_*`), con calidades que van
de **80 dpi a 450 dpi** (`docs/trampas.md`, sección `sin_texto`). Sólo se pueden leer con visión.

Lo que hay que leer bien no es el total: es la **identidad**. `NIF` e `IBAN` son las entradas de la R1 (¿es este
proveedor y es su cuenta?) y el `pedido` la de la R2/R5. Y ahí es justo donde los modelos fallan. Medido por B2
sobre el gateway real (`RESILIENCIA-Y-COSTE.md` §5):

| Fichero | qwen3.6 | deepseek-v4-flash | glm5.3-flash | Verdad (maestro) |
|---|---|---|---|---|
| `scan_002` | `B88125774` | `89812077W` | — | `B98120774` |
| `scan_004` | `B60233808` | `B90233805` | `B00233858` | `B90233808` |

`pedido` y `total` salen casi siempre; el NIF, casi nunca, y **ningún candidato es mejor que otro**. Un dígito mal en
el IBAN es una transferencia a una cuenta equivocada; un dígito mal en el NIF es pagar a un proveedor que no es. Con
una sola lectura no hay ninguna señal de que eso ha pasado.

## Alternativas consideradas
1. **Una sola lectura por escaneada.** Es lo barato (35 s pasarían a ~18 s). Se descarta: un dígito mal sale como
   un hecho perfectamente válido, la norma lo aplica y el resultado es PAGAR a quien no es. No hay aviso posible
   porque no hay con qué contrastar.
2. **Segunda lectura de la página entera a otra resolución.** Probado: a **130 dpi la segunda lectura es peor que
   la primera** (leía `B99…` por `B98…` y `51,27` por `61,27`) y generaba discrepancias falsas; a **200 dpi la página
   entera dispara los tokens y qwen se pierde**. Descartadas por medición, no por criterio.
3. **Corregir siempre el NIF/IBAN contra el maestro**, coincidan o no las lecturas. Descartada por seguridad: eso
   convertiría cualquier NIF impreso mal a propósito en un NIF correcto, que es exactamente una de las trampas de la
   Caja (`nif_distinto_pedido`, 2 ficheros). La corrección sólo se permite cuando **ya hay un desacuerdo** que
   resolver.
4. **Cambiar de modelo de visión.** Probados cuatro (§5 de B2): ninguno lee el NIF mejor que `qwen3.6`; `gemma4`
   además tarda 47 s por imagen y acierta menos. Un respaldo compra disponibilidad, no precisión (ADR-0004).
5. **Doble lectura + reconciliación con evidencia externa (elegida).**

## Decisión
Cada escaneada se lee **dos veces**: la página entera a **150 dpi** y un **recorte del 55 % superior a 200 dpi**
(donde están los identificadores), comparando sólo `nif_emisor`, `iban` y `pedido` (`CAMPOS_SEGUNDA_LECTURA`; los
importes ya los cruzan validadores, maestro y ERP). El recorte a 200 dpi cuesta lo mismo en tokens que la página a
150 y lee mejor.

Si las dos lecturas discrepan en un identificador, `_reconciliar_con_maestro` elige la que está respaldada por **dos
evidencias independientes**: el maestro del Excel y el proveedor del pedido. Cuando existe ese respaldo, el hecho se
guarda con `confianza = 0,6` y **las dos lecturas quedan en el evento**. Cuando no existe, el hecho se marca con
`Aviso.DISCREPANCIA_EXTRACTORES` y la norma lo escala: el sistema dice "no sé leer esto", que es la respuesta
honesta.

## Consecuencias aceptadas
- **5 escaneadas quedan en discrepancia y se escalan**: `copia_2026_0518` (IBAN tachado con rayas en el propio PDF),
  `fax_2026_0411` (NIF e IBAN emborronados), `scan_016` (IBAN que no está en el maestro + instrucción inyectada),
  `scan_021` y `scan_023`. Son 5 revisiones humanas que Alberto tendrá que hacer. Es el precio de no inventar.
- **La reconciliación es un criterio de negocio, no de infraestructura.** Decide qué lectura se cree. Está pedida a
  Mónica para que la ratifique (bitácora 22:20); mientras no lo haga, el ADR queda en *propuesto*.
- `confianza = 0,6` es **una señal, no una decisión**: hoy la norma no la usa. Si Mónica decide que con 0,6 no se
  paga, es un cambio en `rules/`, no aquí.
- **Visión cuesta 35,3 s y ~8,9 K tokens por factura** con la doble lectura incluida (`RESILIENCIA-Y-COSTE.md` §2),
  y satura a 4 hilos: 40 escaneadas en el lote 2 serían ~6 min. Es el cuello de botella conocido del sábado.
- **Texto y visión no ven lo mismo, en los dos sentidos.** Hay 2 PDFs con la instrucción inyectada **tapada por un
  rectángulo blanco** (`FA-5590_ofimática.pdf`, `2026-07-09_P010.pdf`): quien abre el PDF no la ve, la capa de texto
  sí. Y hay 3 escaneadas cuya instrucción **sólo** aparece por visión. Por eso el total de `texto_instruccion` en los
  hechos es **32** y no las 29 del inventario por texto.

## Evidencia
- Conteo hecho hoy por C2 sobre `data/fixtures/hechos_caja.jsonl` (500 líneas): `confianza` = `{1.0: 468, 0.6: 6}`;
  `discrepancia_extractores` en **5** ficheros; `texto_instruccion` en **32**; `sin_texto` en 29.
- **6 escaneadas recuperadas** por la reconciliación (`PARTE-01.md`, A1): `scan_006`, `scan_012`, `scan_017` por NIF;
  `scan_009`, `scan_011` por IBAN; `fax_2026_0411` por pedido.
- Verificación manual contra la imagen: `scan_001` exacto en todos los campos (NIF `B98120774`, IBAN …4302211,
  1.025,49 + 215,35 = 1.240,84).
- Las resoluciones están razonadas en el propio código con la medición que las justifica
  (`extract/etapa.py`, constantes `DPI_VISION`, `DPI_VISION_2`, `FRACCION_SUPERIOR_2`, `CONFIANZA_RECONCILIADA`).
- Lecturas de NIF de tres modelos distintos sobre las mismas imágenes: `RESILIENCIA-Y-COSTE.md` §5, hallazgo 2.
- Tests offline (`tests/test_llm.py`): `test_escaneada_va_por_vision_con_doble_lectura`,
  `test_doble_lectura_discrepante_marca_aviso`, `test_reconciliacion_con_maestro_elige_la_lectura_respaldada`,
  `test_reconciliacion_sin_evidencia_mantiene_discrepancia`.
- Commits `3e217c0` (recorte superior a 200 dpi) y `ef4d441` (reconciliación con el maestro).

## Resumen para el plan (5 líneas)
Las 29 facturas escaneadas se leen **dos veces** —página a 150 dpi y recorte superior a 200 dpi— y sólo se comparan los tres campos que deciden quién cobra: NIF, IBAN y pedido.
Lo hacemos porque está medido que **ningún modelo de visión lee el NIF de forma fiable** (tres modelos, tres NIF distintos y ninguno correcto en la misma imagen): con una sola lectura, un dígito mal es un pago a otra cuenta sin ninguna señal.
Cuando las dos lecturas discrepan, no gana el modelo: gana la lectura respaldada por **dos fuentes independientes** (el maestro del Excel y el proveedor del pedido); el hecho queda con `confianza 0,6` y las dos lecturas en la traza.
Cuando ninguna lectura está respaldada, no se elige ninguna: 5 facturas quedan marcadas y la norma las **escala**, porque "no sé leerlo" es un resultado legítimo y "me lo invento" no.
Nunca se corrige un identificador contra el maestro sin que haya desacuerdo previo: eso convertiría un NIF falsificado en uno válido, que es justo una de las trampas de la Caja.
