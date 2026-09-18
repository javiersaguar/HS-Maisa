# ADR-0006 · Reprocesar sólo lo que el cambio toca, sin reescribir las decisiones que siguen valiendo

- **Estado:** aceptado
- **Fecha:** 2026-09-18 23:40 · **Dueño:** Miguel · **Módulos:** pipeline/linaje.py, pipeline/run.py, pipeline/etapas.py, cli.py

## Contexto
El sábado a las 18:00 llegan el ERP v2, la norma v4 y el lote 2. El domingo, "un dato en vivo". Cada cambio tiene que
recalcular lo afectado y explicar qué cambió. `linaje.impactados` comparaba la **versión entera** del snapshot: un
cambio de ERP recalculaba todo. En el ensayo de Javier (`docs/agentes/ENSAYO-LOTE2.md`) salieron 510 de 510 para que
cambiaran 2. El tiempo era bueno (0,5 s), pero la traza no decía por qué se había recalculado cada factura.

La norma v3 sólo lee dos cosas del maestro: el proveedor por el NIF de la factura (R1) y el pedido (R2). Del ERP sólo
lee los asientos del pedido de la factura (R5). Así que una decisión depende de:
- hechos;
- norma;
- fecha de corte;
- pedido y NIF de la factura en el maestro y en el ERP.

## Alternativas consideradas
1. **Seguir comparando la versión entera** (lo de antes). Correcto y rápido con 540 facturas. Se descarta porque
   recalcula todo ante cualquier cambio. "510 recalculadas, cambian 2" obliga a explicar a mano por qué son esas 2.
2. **Diff granular y actualizar la versión en las no afectadas** (`UPDATE decisiones SET erp_version=…`). Se descarta
   porque reescribe el historial. La decisión diría "ERP v2" y se calculó con v1. Rompe la regla de que las decisiones
   no se borran ni se editan.
3. **Diff granular y copiar la decisión** con la versión nueva, sin pasar por la norma. Se descarta por el ruido: unas
   500 filas de historial por pasada, y el "recalculadas" sería falso.
4. **Diff granular y tabla de confirmaciones** (`decision_id`, versión en la que se confirmó). Se puede auditar, pero
   cambia `core/schema.sql` a 18 h de la entrega y escribe una fila por fichero en cada pasada. Se descarta por
   tiempo y riesgo.
5. **Diff granular y no tocar las no afectadas (elegida).**

## Decisión
Una decisión se recalcula si cambian sus hechos, la norma o la fecha de corte, o si el diff entre la versión de
maestro/ERP con que se tomó y la de destino toca **su pedido o su NIF**. Las demás no se tocan.

Cómo se implementa:
- `linaje.evaluar()` agrupa las decisiones vigentes por la versión de origen. Hace un diff por versión:
  - ERP: `snapshot.diff_erp` → `pedidos_afectados`.
  - Maestro: `linaje.diff_maestro` → pedidos y NIF normalizados afectados.
- Devuelve `impactados` con el motivo de cada fichero, por ejemplo `erp v1→v2-sim: PO-2026-0002`.
- Las decisiones con otra versión cuyo pedido y NIF no toca el diff siguen con su versión real. Dejan un evento
  `decide/skip`, idempotente, del tipo `{"linaje":"sin impacto","decision":501,"erp":"v1→v2-sim"}`.
- Si el snapshot de origen ya no está en la BD, se recalcula por prudencia.
- Cambiar la fecha de corte recalcula todo. La evidencia de R4 la lleva en todas las decisiones, y la v4 puede usarla
  en más reglas (vencimientos).
- `run.reprocesar()` encadena `marcar_duplicados` → `evaluar` → `decide(solo=…, por=…)` → diff de esta pasada.
  Es lo que llama `albertitos reprocess --impacted`. `--todo` recalcula todo.
- `marcar_duplicados` recalcula la marca entera: la pone y la quita. Si no, borrar los `L2-*` de un ensayo dejaría
  escaladas las originales del lote 1.

## Consecuencias aceptadas
- **Las decisiones vigentes llevan versiones mezcladas.** Tras el ensayo quedan 498 con ERP v1 y 2 con v2-sim. A la
  pregunta "¿con qué ERP está decidida esta factura?" respondemos: con v1, y el diff v1→v2 demuestra que su pedido no
  cambió (evento `skip` en su traza).
- **La granularidad depende de una suposición sobre la norma:** que sólo lee el maestro y el ERP por el pedido y el
  NIF de la factura. Si la v4 lee acumulados por proveedor u otros pedidos, el linaje se quedaría corto.
  - Lo vigila `test_la_norma_solo_lee_su_pedido_y_su_nif`, que recorre cada norma del `REGISTRO` (la v4 entra sola al
    registrarse).
  - Si falla, hay que ampliar las claves en `linaje.py` o usar `--todo`.
- **El linaje ve versiones, no código.** Si alguien corrige `norma_v3.py` sin cambiar `"v3"`, `reprocess --impacted`
  no recalcula nada. `run` sí, porque decide todo cada vez. Regla: una norma publicada no se edita (la v4 es un
  módulo nuevo). Mientras Mónica valida la v3, usar `run` o `reprocess --todo`.
- Un evento `skip` por fichero confirmado (unas 500 filas la primera vez que cambia una versión). Repetir la pasada
  no los duplica.
- Hoy no ganamos tiempo: recalcular las 500 tarda 0,43 s. Ganamos traza: cada recálculo dice por qué, y cada no
  recálculo también.

## Evidencia
Ensayo sobre `dist/ensayo.db`, copia de `albertitos.db`: 500 facturas, v3, corte 2026-09-18. Portátil de Miguel
(Windows 11), commit base `4f0298b`. ERP simulado `data/fixtures/erp_lote2_simulado.csv` en `:8011`.

| Paso | Salida de `reprocess` | Tiempo (proceso / CLI) |
|---|---|---|
| Línea base, ERP v1 | 0 de 500 recalculadas | 0,03 s |
| ERP v1→v2-sim (3 altas, 2 cambios, 5 pedidos afectados) | **2 de 500 recalculadas · 2 cambian** · 498 sin impacto por diff: `2026-06-27_P001.pdf` PAGAR→ESCALAR (PO-2026-0002), `F26-9865_ofimática.pdf` PAGAR→NO_PAGAR (PO-2026-0001) | 0,04 s / 0,51 s |
| Repetir v2-sim | 0 de 500 · 0 cambian (antes: 510 de 510) | 0,04 s |
| Volver a v1 | 2 de 500 · 2 cambian, vuelven a PAGAR | 0,03 s |
| `--todo` con v2-sim | 500 de 500 · 0 cambian | 0,43 s / 0,93 s |
| + 10 `L2-*` (copias de facturas del lote 1) | duplicados +20 · 20 de 510 recalculadas · 9 cambian (originales del lote 1 PAGAR→ESCALAR) | 0,05 s |
| Borrar los `L2-*` (comando del README) | duplicados −10 · 10 de 500 · 9 vuelven a PAGAR | 0,04 s |
| Volver a v1 | resultados vigentes y `hechos_hash` **idénticos** a `albertitos.db` | — |

Tests: `tests/test_linaje.py`, 11 casos:
- ERP ida y vuelta;
- maestro por NIF y por pedido;
- norma, corte y `--todo`;
- hechos cambiados y fichero nuevo;
- snapshot de origen ausente;
- evento `skip` idempotente;
- duplicados que se ponen y se quitan;
- la suposición de la norma, en cada norma del REGISTRO.

Con una norma falsa que suma los pedidos del proveedor, el test de la suposición **falla** (comprobado a mano).
`make check`: 209 passed.

Pendiente de Mónica o un mentor: si una factura del lote 2 duplica una del lote 1 ya entregada como PAGAR, hoy las
dos pasan a ESCALAR por R6.
