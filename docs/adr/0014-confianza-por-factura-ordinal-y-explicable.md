# ADR-0014 · La confianza por factura es una puntuación ordinal y explicable, no una probabilidad

- **Estado:** propuesto (K3, PLAN-11). Lo aceptan Javier y Mónica; Alejandro decide cómo se enseña.
- **Fecha:** 2026-09-19 15:07 · **Dueño:** Javier (agente K3) · **Módulos:** `confianza/` (nuevo), `scripts/calibrar_confianza.py`

## Contexto
Alberto recibe 500 decisiones y no sabe por cuáles empezar a mirar. La validación de la entrega es binaria: basta una
línea que la referencia lea distinto para quedarse sin premio. Así que la pregunta útil no es «¿se paga?», sino
**«¿cuánta seguridad hay de que esta clasificación es la correcta?»**. El sistema ya sabe mucho de cada factura, pero lo
tiene disperso:
- el método de extracción: 468 por plantilla, 31 reproducidas desde la caché del LLM, 1 por texto;
- en `cache_llm`, la lectura de contraste de las 468 de plantilla y hasta 5 lecturas por escaneada;
- las reconciliaciones con el maestro (confianza 0,6) y los avisos de lectura;
- la evidencia de cada regla en `motivos_json`: importes, asiento, `no_pagar`;
- las cinco preguntas que el mentor no ha contestado y cuántas facturas dependen de cada una: 45 ficheros, mapa de I2.

Ninguna pieza lo juntaba. Además, no hay verdad etiquetada con que calibrar: la muestra de Mónica sigue abierta (0 de 21).

## Alternativas consideradas
1. **Probabilidad calibrada (regresión logística o isotónica)**. Descartada hoy: no hay etiquetas. Con 21 facturas y
   la muestra abierta, cualquier «87 %» sería inventado. Se puede hacer cuando haya muestra, y el script ya lo prepara.
2. **Que la dé el LLM («del 0 al 100, ¿cuánto te fías?»)**. Descartada: no es reproducible ni explicable, cuesta
   llamadas y mete el texto del PDF (que da órdenes) en el cálculo. Sólo entra como segunda opinión opcional, con
   esquema cerrado, y nunca decide. Jev (Score calibrado) sería el candidato natural si el equipo lo aprueba
   (ANALISIS-JEV.md §3 B). No se integra aquí.
3. **Mostrar la `confianza` de `InvoiceFacts`**. Descartada: sólo existe para las reconciliadas (0,6) y mide la
   lectura, no la clasificación.
4. **Puntuación ordinal determinista con pesos a la vista (elegida)**. Parte de 100 y resta una penalización por cada
   duda con nombre. Cada peso tiene una línea que lo justifica y cada factura, sus tres razones en castellano.

## Decisión
`albertitos.confianza` puntúa cada nombre entregado de 0 a 100. Bandas: **alta ≥ 80 · media ≥ 50 · baja < 50**.
- **Cómo se calcula:** lee la BD en sólo lectura y no importa `rules/` ni `extract/`. Una duda sólo pesa en la medida
  en que la decisión depende de ella:
  - **dudas de lectura, a la mitad** (factor 0,5) cuando la decisión ya la corroboran el maestro y el ERP (todo PAGAR)
    o la sostiene una causa clara (una orden en el PDF, un IVA mal calculado, el ERP la da por PAGADA);
  - **las dudas de lectura no cuentan** (factor 0) cuando son el propio motivo de escalar. Esa factura carga en su
    lugar `decision.escala_por_lectura` (55): si el original está limpio, lo correcto sería PAGAR;
  - en una escaneada, **si las lecturas no coinciden justo en el campo que hace fallar la regla**, ese fallo cuenta
    como de lectura y no como una causa clara;
  - **las preguntas abiertas del mentor** (Q1, Q2, Q3 y Q5) restan 25 cada una, con un tope de 30 entre todas;
  - **contingencia** (ADR-0009): como mucho 25.
- **Razones:** las tres que más restan. Si no restan, lo que sostiene la decisión y lo que la respalda.
- **Integración:** `puntuar(conn, file_id)` y `puntuar_todas(conn, lote)`; `rutas()` para el puente de la consola,
  con su misma firma. Contrato en `docs/api/confianza.md`.

### Tabla de pesos (generada desde `modelo.PESOS`)
| Señal | Fuente | Puntos | Por qué |
|---|---|---:|---|
| `pdf.plantilla_sin_contraste` | pdf | 5 | La plantilla es determinista, pero sin la lectura del LLM al lado no se descarta un error del parser. |
| `pdf.contraste_difiere` | pdf | 30 | Dos extractores independientes (plantilla y LLM) leen distinto un campo que decide. |
| `pdf.llm_texto` | pdf | 10 | Una sola lectura, del LLM, sobre la capa de texto: no hay segundo extractor que la contraste. |
| `pdf.vision` | pdf | 15 | Escaneada: sólo hay imagen y la leyó la visión, la vía con más errores (17 desacuerdos en 29). |
| `pdf.una_lectura` | pdf | 10 | De la imagen hay una sola lectura: nada con qué contrastarla. |
| `pdf.lecturas_discrepan` | pdf | 20 | Las lecturas independientes de la imagen no coinciden en un campo que decide. |
| `pdf.reconciliada` | pdf | 30 | Las lecturas no coincidían y se eligió la que cuadra con el maestro (confianza 0,6, ADR-0003/0011). |
| `pdf.discrepancia_extractores` | pdf | 30 | La extracción marcó que sus lecturas no coinciden y no pudo reconciliarlas. |
| `pdf.superpuesto` | pdf | 30 | Hay otro documento encima o transparentándose (ADR-0010): la lectura es frágil. |
| `pdf.parcial` | pdf | 15 | Faltan campos o hay un importe ambiguo: la norma decide con menos datos (15 por aviso, hasta 30). |
| `pdf.respaldo` | pdf | 5 | La leyó el modelo de respaldo, no el principal: menos historia medida. |
| `maestro.calidad` | maestro | 10 | El maestro avisa de un problema con ese pedido (p. ej. sin NIF en el Excel): el cruce es más débil. |
| `maestro.sin_snapshot` | maestro | 25 | No está el maestro con el que se decidió: no se puede comprobar el cruce. |
| `erp.sin_snapshot` | erp | 25 | No está el ERP con el que se decidió: no se puede comprobar el asiento. |
| `erp.varios_asientos` | erp | 10 | El pedido tiene más de un asiento en el ERP: la norma mira el primero. |
| `decision.escala_por_lectura` | decision | 55 | Se escala sólo porque no se pudo leer con seguridad, no porque la factura esté mal: si el original está limpio, lo correcto sería PAGAR. |
| `decision.cerca_del_limite` | decision | 15 | El importe se queda a menos de 1 € de lo que se esperaba: puede ser un redondeo o una mala lectura. |
| `decision.contingencia` | decision | 75 | Decidida por la contingencia (ADR-0009), sin hechos validados: confianza baja por definición. |
| `decision.sin_hechos` | decision | 100 | No hay hechos extraídos: no hay nada que respalde la clasificación. |
| `politica.q1_texto` | politica | 25 | Lo único que la frena es un texto que ordena qué hacer; si el mentor dice que manda la norma, sería PAGAR (Q1). |
| `politica.q2_anulado` | politica | 25 | El PDF dice que el pedido está anulado y el Excel y el ERP no: sin política confirmada (Q2). |
| `politica.q3_frontera` | politica | 25 | Falla una comprobación objetiva; hoy es ESCALAR, pero sería NO_PAGAR si el mentor fija así la frontera (Q3). |
| `politica.q5_duplicado` | politica | 25 | Comparte pedido o factura con otro PDF y la política de duplicados no está confirmada (Q5). |
| `revisor.desacuerdo` | revisor | 15 | Una segunda opinión del LLM no ve coherente la clasificación con los hechos (sólo una señal). |

Umbrales y topes, en código: `UMBRAL_ALTA = 80`, `UMBRAL_MEDIA = 50`, `FACTOR_CORROBORADA = 0.5`,
`TOPE_POLITICA = 30`, `TOPE_CONTINGENCIA = 25`, `MARGEN_CERCA = 1,00 €`. Por qué `escala_por_lectura` vale 55: deja
en banda baja (45) a la que sólo se escala por lectura, aunque no tenga ninguna otra duda. Es el grupo «revisar
primero»: si el original está limpio, la referencia esperaría PAGAR.

## Consecuencias aceptadas
- **No es una probabilidad**, y la pantalla tiene que decirlo: «confianza en la clasificación, no probabilidad de
  pago». Los pesos son juicio experto documentado, no aprendidos. Cambiarlos es cambiar este ADR.
- **Ninguna ESCALAR sale en alta hoy.** Las 53 dependen de una duda de lectura o de una política sin confirmar. Es
  información (lo que hay que llevar al mentor), no un defecto. Si el mentor confirma una política, esas facturas
  suben de banda al cambiar la tabla de preguntas abiertas.
- **Esto contradice el ejemplo del PLAN-11,** que decía «un ESCALAR por una orden inyectada evidente tiene confianza
  ALTA». Con los datos, 6 de las 31 facturas con orden inyectada sólo se frenan por la orden: el resto de la factura
  está limpio (I2 lo comprobó a mano). Si el mentor dice que manda la norma, serían PAGAR. Por eso salen en media y
  no en alta. Las 25 restantes caen en otra pregunta abierta.
- **No comprueba que la evidencia sea literal en el texto del PDF:** abrir 500 PDFs costaría 1-2 s y rompería el
  objetivo de < 2 s. Queda para una versión 2, con caché.
- **Depende de lo que dejó el pipeline:** si se vacía `cache_llm`, las plantillas pierden su «confirmada por el LLM» y
  pasan a `pdf.plantilla_sin_contraste` (−2,5). Baja un poco, y lo dice.
- **El revisor LLM (opcional, apagado por defecto) no discrimina.** Se ensayó en vivo el 19/09 a las 15:13, sobre las 53
  facturas de banda media o baja: **53 llamadas** (tope 60), **52 «de acuerdo», 0 en desacuerdo y 1 `LLM-TIMEOUT`**, que
  se degradó bien (esa factura se quedó sin opinión). Latencia p50 1,5 s y máxima 8,4 s, con `deepseek-v4-flash`.
  Razona con los datos (cita importes, la confianza de 0,6, la superposición y el duplicado), pero juzga con la misma
  norma escrita que aplica el sistema. Así que confirma que ninguna clasificación contradice la norma; no resuelve las
  preguntas abiertas, porque para eso hace falta la referencia. Por eso un «de acuerdo» no suma puntos (sólo añade una
  frase a favor) y sólo un desacuerdo resta. Si el equipo aprueba Jev, entraría aquí con un Score calibrado.

## Evidencia
- **Tests:** `tests/test_confianza.py`, 27 tests en 0,9 s. Cubren la tabla de pesos, los casos por tipo, las rutas a
  través de `console.api.despachar`, que la BD no cambia ni un byte, y la **regla 5 del PLAN-11**: sobre una copia de
  la BD real, `package` antes y después de puntuar las 500 (y de llamar a las tres rutas) da el mismo `outcomes.jsonl`.
- **Rendimiento:** las 500 en 0,04-0,06 s; una factura, 0,33 ms. El calendario de K1 pide la de cada pago: 438 × 0,33 ms ≈ 0,15 s.
- **BD real (lote 1):** alta 447 (438 PAGAR, 9 NO_PAGAR) · media 40 · baja 13 (todas ESCALAR). Q1 6 · Q2 2 · Q3 35 · Q5 2,
  los mismos recuentos que MAPA-POLITICAS.md, y **los 45 ficheros coinciden uno a uno** con el mapa de I2.
- **Contraste plantilla↔LLM, factura a factura:** 468 de 468 coinciden en NIF, IBAN, pedido e importe (reproduce
  CONTRASTE-TOTAL §1).
- **Lo ya sabido dudoso:** las 10 de menor confianza y las 13 de banda baja lo estaban por los hechos o por el mapa de I2.
  Las 6 que I2 revisó limpias a mano salen en media.
- **Comando:** `uv run python scripts/calibrar_confianza.py [--markdown] [--salida dist/ensayo/k3]`.
- **Revisor:** `uv run python -m albertitos.confianza.revisor --maximo 60 --salida dist/ensayo/k3/revisor.json`; 10 tests sin red (esquema cerrado, texto delimitado como dato, tope, hora límite, caída, timeout, 429, respuesta inválida, sin key y opinión caducada).

## Resumen para el plan (5 líneas)
Confianza por factura: una puntuación ordinal 0-100 (no una probabilidad) con banda y tres razones, calculada con lo
que el sistema ya sabe de cada fuente (lecturas, maestro, ERP, decisión y políticas abiertas del mentor). Determinista,
con los pesos a la vista y justificados. Una duda pesa según cuánto dependa de ella la decisión. Las 500 en 0,05 s y
sin tocar la entrega (test). Hoy: 447 alta, 40 media y 13 baja. Ninguna ESCALAR en alta, porque todas dependen de una
duda de lectura o de una política sin confirmar.
