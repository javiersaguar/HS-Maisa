# ADR-0020 · Lo escrito o tachado a mano en un PDF con texto lo mira una persona

- **Estado:** aceptado (Miguel, 19/09). **Fecha:** 2026-09-19 19:55 · **Dueño:** Miguel · **Módulos:** core/, extract/, rules/

## Contexto
Tres facturas del lote 2 son "las del café", y las tres tienen capa de texto:
- `e16`: la fecha está en blanco y escrita a mano ("15 de marzo de 2026").
- `e17`: la factura entera está a mano.
- `e18`: el total impreso está tachado y corregido a mano ("15.000,00 / 18.150,00, corregido A."). **Lo impreso
  (1.815 €) cuadra con el pedido y con el ERP**, así que el pipeline la habría pagado sin ver la corrección.

Todo lo que hicimos en los ADR-0017 y 0018 actúa sobre escaneadas, y aquí no hay ninguna.

## Alternativas consideradas
1. **Forzar la lectura por visión en todas las facturas con texto** — son 511 lecturas de visión más, y seguiría
   sin haber una señal de que algo está escrito a mano. Descartada por coste y porque no resuelve el problema.
2. **Pasar las tres por visión a mano** — no escala al lote siguiente ni a una factura nueva.
3. **(elegida) Detectar la escritura a mano en el propio PDF, sin LLM.** Lo escrito a mano va en tipografías
   manuscritas (BrushScript, BradleyHand, SnellRoundhand, MarkerFelt, alternadas letra a letra) y los tachados en
   trazos curvos.

## Decisión
- `pdf.rasgos_manuscritos(ruta)` devuelve las tipografías manuscritas, el texto escrito con ellas (recompuesto
  por líneas) y el número de trazos curvos. Si hay algo, `etapa._extraer_uno` añade `Aviso.ANOTACION_A_MANO`, y lo
  escrito queda en el evento (`manuscrito=`) como evidencia, no como hecho.
- La norma lo escala por R6 (`ANOMALIAS_HUMANO`), igual que un documento superpuesto.

## Consecuencias aceptadas
- **Es una heurística por nombre de tipografía y por trazo curvo.** Una firma escaneada como imagen, o una letra
  de mano con una tipografía de nombre neutro, no se detectaría. Las 471 facturas con texto del lote 1 no tienen
  imágenes, así que un "hay una imagen" sería la siguiente señal si hiciera falta.
- **Una factura con logotipo dibujado con curvas escalaría.** En la Caja no hay ninguna: ni una curva en 471.
- Lo escrito a mano no se usa para decidir: sólo se enseña. Decide una persona.

## Evidencia
- **Barrido de 540 PDF** (471 con texto del lote 1 y 40 del lote 2, con el material provisional del commit
  `f831e34`): positivos exactamente e16, e17 y e18, en 1,2 s. En el lote 1 no hay ninguna tipografía manuscrita
  ni ningún trazo curvo.
- **Lo que queda de evidencia:**
  - e16: "15de marzo de 2026";
  - e18: "15.000,00 / corregidoA. / 18.150,00" y 8 trazos;
  - e17: la factura entera ("PapeleríaRuzafa S.C. / NIFJ40112358 / …").
- **Tests:**
  - `tests/test_extract.py`: `::test_ninguna_factura_del_lote_1_tiene_escritura_a_mano`,
    `::test_fuentes_manuscritas`, `::test_un_trazo_curvo_a_mano_se_detecta`;
  - `tests/test_llm.py::test_escritura_a_mano_en_un_pdf_con_texto_da_aviso_y_evidencia`;
  - `tests/test_rules.py`: la escala por R6.
