# ADR-0021 · Cada lote se decide en su contexto, y el lote 2 no reabre el lote 1

- **Estado:** aceptado por Miguel (19/09). Pregunta abierta al mentor (P0-2): ¿el lote 1 debe reprocesarse con
  el ERP del sábado? **Fecha:** 2026-09-19 20:40 · **Dueño:** Miguel · **Módulos:** pipeline/, cli

## Contexto
El ERP del sábado (v2) registra como PAGADA (asiento AS-90001, 01/09) el pedido PO-2026-0071. Es justo el pago
que el lote 1 decidió para `factura_4635` (PAGAR). En el lote 2, `2026-08-22_P010` vuelve a facturar ese pedido.
Hay dos formas de estropear lo ya entregado:
1. **Reprocesar el lote 1 con el ERP v2 o la norma v4.** `factura_4635` pasaría a NO_PAGAR, porque R5 vería un
   asiento PAGADA, y la entrega del lote 1 dejaría de ser la que se validó. La chuleta lo hacía en su paso 3
   (`reprocess --impacted --erp v2`, sin `--lote`), y `run` y `decide` deciden todos los lotes con un solo
   contexto.
2. **Marcar duplicados entre lotes.** `marcar_duplicados` agrupaba por pedido en todos los lotes: al ingerir el
   lote 2, `factura_4635` recibía `DUPLICADO_SOSPECHOSO` y R6 la escalaba. Es lo mismo que pasó el 18/09 con el
   lote simulado.

## Alternativas consideradas
1. **Reprocesar todo con el contexto más nuevo** — refleja el mundo de hoy, pero cambia una entrega ya validada
   y le da la vuelta a una decisión correcta (el pago que el ERP registra es el nuestro). Descartada salvo que el
   mentor diga lo contrario.
2. **Confiar en que nadie se equivoque de orden** — ya estaba mal escrita en la chuleta. Descartada.
3. **(elegida) Cada lote se decide en su contexto.** La norma y el ERP de un lote son los de sus decisiones
   vigentes; cambiarlos exige nombrar el lote. Y un duplicado entre lotes marca sólo al posterior.

## Decisión
- `linaje.contextos_vigentes` y `linaje.choques_de_contexto`.
- `reprocess` sin `--norma` ni `--erp` reprocesa cada lote con los suyos. Con ellos y sin `--lote`, **se niega**
  si cambiarían el contexto de un lote ya decidido. `run` y `decide` se niegan igual.
- `grupos_duplicados(..., lotes)`: una factura sólo se marca por otra de su lote o de uno anterior. El auditor
  aplica la misma regla, y `pago_doble` sigue cazando dos PAGAR en cualquier combinación de lotes.
- Chuleta: los pasos 3, 4 y 6 llevan `--lote 2`.

## Consecuencias aceptadas
- **Para cambiar el ERP del lote 1** (el cambio de dato del domingo, si lo toca) hay que decirlo:
  `reprocess --lote 1 --erp v3`. Es intencionado.
- **Una copia exacta entre lotes** (el mismo PDF, P0-1) comparte hechos, así que la marca de duplicado le llega a
  las dos líneas. En este lote 2 no hay ninguna copia exacta.
- Si el mentor dice que el lote 1 se reprocesa con el v2, es `reprocess --lote 1 --erp v2` y se vuelve a
  entregar: el linaje dice qué cambia (`factura_4635`).

## Evidencia
- **Tests:**
  - `tests/test_linaje.py::test_una_factura_del_lote_2_no_marca_la_del_lote_1` (el lote 1 ni se marca ni se
    redecide) y `::test_cada_lote_se_decide_en_su_contexto`;
  - `tests/test_auditoria.py::test_duplicado_entre_lotes_sin_marca_en_el_anterior_no_es_rojo` y
    `::test_duplicado_entre_lotes_pagado_dos_veces_sigue_siendo_rojo`.
- **En una copia de `dist/albertitos.db`:**
  - `reprocess --impacted --erp v2` se niega ("el lote 1 está decidido con la norma v3 y el ERP v1… usa --lote N");
  - `reprocess --impacted` sin opciones: lote 1, 0 de 500 recalculadas.
