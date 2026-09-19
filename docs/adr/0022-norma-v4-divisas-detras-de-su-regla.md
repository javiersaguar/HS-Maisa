# ADR-0022 · La norma v4 es la v3 más una regla de moneda, y la divisa escala hasta que haya tipo de cambio

- **Estado:** propuesto (Miguel, 19/09 20:10). Lo revisa Mónica; se cierra cuando se publique la regla nueva.
- **Fecha:** 2026-09-19 · **Dueño:** Miguel (M3) · **Módulos:** rules/

## Contexto
El lote 2 trae "una regla nueva", pero a las 20:10 no está publicada ni en la web ni en el repo. Lo que sí traen
los datos (`docs/agentes/lote2/HIPOTESIS.md`) son 8 facturas en divisa (USD, GBP, CHF, BRL, MXN, JPY) contra
pedidos y asientos en EUR. El tipo implícito (pedido / total) es fijo en cada moneda: USD 0,92, GBP 1,17, CHF 1,05,
BRL 0,1613, MXN 0,0469, JPY 0,00617. Con la v3, esas 8 escalan por R2 con un motivo falso: "el total no coincide
con el pedido".

## Alternativas consideradas
1. **Esperar a la regla y no hacer v4** — a las 02:00 se congela. Si la regla llega tarde, no daría tiempo a
   escribirla y probarla.
2. **Suponer la regla (por ejemplo, convertir con los tipos implícitos)** — sería inventar la norma a partir de las
   facturas, justo lo que la chuleta prohíbe ("no la deduces de las facturas").
3. **Tratar la "factura anterior al pedido" como anomalía** — las 18 `e*` son anteriores a su pedido (del 14/09).
   Es la forma en que se generaron los datos, no una trampa, y escalaría las 5 `e*` limpias. Descartada.
4. **(elegida) v4 = v3 + R7 (moneda), con la tabla de tipos vacía.**
   - Sin tipo, la divisa escala con su motivo verdadero, y la evidencia lleva el tipo implícito.
   - Si la regla da tipos, se rellena `TIPOS_CAMBIO`, R2 y R5 comparan el importe convertido (con una tolerancia
     relativa del 0,1 % por el redondeo del tipo) y se hace `reprocess --todo --lote 2 --norma v4`.
   - Si la regla es otra cosa, se reescribe sólo R7.

## Decisión
- `rules/norma_v4.py`: reglas 1-6 de la v3 (la misma implementación, con el identificador `v4.Rn`) más
  `regla_7_moneda`, evaluada justo después de R1 para que su motivo sea el principal.
- EUR, o sin moneda (los hechos del lote 1), decide igual que la v3.
- Registrada en `REGISTRO`. Sólo se aplica al lote 2: `reprocess --lote 2 --norma v4` (ADR-0021).

## Consecuencias aceptadas
- **Sin tipos de cambio, las 8 en divisa salen ESCALAR,** como con la v3, pero con el motivo bueno.
- **Si se rellenan los tipos, falta hacer lo mismo en el auditor.** `comprobar_pagar` compara el total con el
  pedido sin convertir, así que un PAGAR en divisa daría rojo.
- `decidido_en` lo sella `core.db` y no la norma. La v3 lo ponía con el reloj, y el hook no lo deja en `rules/`.

## Evidencia
- `tests/test_rules_v4.py`:
  - en EUR y sin moneda, igual que la v3;
  - en divisa sin tipo, escala con motivo `v4.R7` y tipo implícito 0,92;
  - con tipo, PAGAR;
  - el redondeo del tipo se admite y un importe distinto no;
  - la anotación a mano y el pedido ya pagado deciden como en la v3.
