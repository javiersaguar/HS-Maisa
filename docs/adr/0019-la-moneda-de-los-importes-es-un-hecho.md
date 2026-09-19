# ADR-0019 · Los importes llevan su moneda, y el hash de lo ya guardado no cambia

- **Estado:** aceptado (Miguel, 19/09). **Fecha:** 2026-09-19 19:40 · **Dueño:** Miguel · **Módulos:** core/, extract/

## Contexto
En el lote 2 hay 8 facturas en divisa (e02 y e10 en USD, e11 en GBP, e12 y e15 en CHF, e13 en BRL, e14 en MXN,
e09 en JPY), y sus pedidos y asientos del ERP están en EUR. `InvoiceFacts` no tenía dónde decir la moneda. Un
total de 2.450 $ se habría comparado con el pedido como si fueran 2.450 €, y R2 lo habría escalado con un motivo
falso ("el total no coincide") en vez del verdadero ("la factura viene en dólares").

## Alternativas consideradas
1. **No hacer nada y dejar que R2 escale** — el resultado quizá coincida, pero el motivo es falso, y la regla
   nueva del lote 2 (probablemente de divisas) no tendría con qué trabajar.
2. **Convertir a EUR en la extracción** — el extractor no debe calcular: "tal como está impreso, sin recalcular"
   es la base del ADR-0001. Además, el tipo de cambio es una decisión de la norma.
3. **(elegida) Un campo `moneda` (ISO 4217) en los hechos, opcional**, y que la norma decida qué hacer con él.

## Decisión
- `InvoiceFacts.moneda: str | None = None`.
- **`hash()` excluye `moneda` cuando es None.** Los hechos anteriores al campo conservan su hash y el linaje no
  redecide el lote 1 por un cambio de esquema. Con moneda, entra en el hash: si cambia, se redecide.
- Plantillas: `EUR`, porque las 6 familias de la Caja imprimen € o EUR.
- LLM: `moneda` en el esquema de la herramienta. `llm.moneda_iso` acepta el código ISO y sólo los símbolos sin
  ambigüedad (€, £, R$, MX$, US$; "$" suelto no se adivina). `PROMPT_VERSION` p-0.4.

## Consecuencias aceptadas
- **Cambiar el esquema invalida la caché del LLM.** Las lecturas p-0.2 del lote 1 no se reutilizan si se fuerza
  una reextracción. Los hechos del lote 1 ya están guardados y no se reextraen.
- Un hecho con `moneda=None` no dice "EUR": dice que no consta. La norma decide cómo tratarlo.

## Evidencia
- `tests/test_contracts.py::test_moneda_nueva_no_cambia_el_hash_de_lo_ya_guardado`.
- Los 500 hechos de `dist/albertitos.db` conservan exactamente su `hechos_hash` guardado (500/500).
- `tests/test_llm.py::test_moneda_iso` y `::test_la_moneda_del_llm_llega_a_los_hechos`.
- `tests/test_plantillas.py`: las facturas reales por plantilla salen en EUR.
