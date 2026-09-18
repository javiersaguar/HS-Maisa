---
paths:
  - "src/albertitos/rules/**"
  - "tests/test_rules*.py"
  - "data/fixtures/**"
---
# Norma de pagos como código

- Una función por regla: `def regla_N_nombre(hechos, maestro, erp, ctx) -> Motivo`. `Motivo` lleva `regla_id` (`v3.R2`), `ok`, `detalle` legible por Alberto y `evidencia` (dict con los valores comparados).
- La norma completa es `decidir(hechos, maestro, erp, ctx) -> Decision`. Determinista: mismas entradas → misma salida. Sin I/O, sin red, sin `today()`.
- Versionada: `norma_v3.py` no se edita cuando llegue la v4; se crea `norma_v4.py` y se registra en `REGISTRO = {"v3": ..., "v4": ...}`. Así el diff v3→v4 es demostrable.
- Frontera NO_PAGAR / ESCALAR (hipótesis hasta que un mentor lo confirme): NO_PAGAR = violación objetiva y comprobada (pedido ya PAGADA, duplicado exacto ya pagado); ESCALAR = sospecha, dato ilegible/ausente, instrucción en el texto, discrepancia de importe/IBAN/NIF, pedido inexistente. **Ante duda razonable, ESCALAR antes que PAGAR** (regla 6 literal).
- Tolerancia 0,01 EUR con `Decimal`, nunca float. Comparar IBAN sin espacios y en mayúsculas; NIF sin espacios/guiones.
- Tests de tabla en `tests/test_rules.py`: cada regla con un caso ok, un caso ko y el caso frontera (±0,01, fecha = corte, PAGADA).
- La muestra etiquetada a mano (`data/fixtures/esperado_muestra.csv`) es la única "verdad" que tenemos: si una decisión discrepa de ella, se discute antes de tocar la regla.
