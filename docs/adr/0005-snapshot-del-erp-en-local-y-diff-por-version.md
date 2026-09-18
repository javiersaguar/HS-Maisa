# ADR-0005 · El ERP de 2009 se descarga entero una vez, versionado, y el cambio se cuenta con un diff

- **Estado:** propuesto
- **Fecha:** 2026-09-18 23:55 · **Dueño:** Javier · **Módulos:** sources/, pipeline/

## Contexto
El ERP de Alberto es un bridge HTTP instalado en 2009 (`data/caja/MANUAL_ERP_2009.md`). Sus condiciones reales, no
supuestas:

- XML en **ISO-8859-1**, fechas `DD/MM/AAAA`, importes `12.874,40`.
- Token que caduca a los **300 usos o 15 minutos** (`SES-401`).
- **`ORA-00600` (HTTP 500) cada 10ª consulta autenticada.** El manual lo dice sin pudor: "Es del año de
  instalación. **Reintentar la misma consulta.** Funciona. No llame a Mantenimiento."
- `ERP-429` por encima de 10 req/s, con `Retry-After`.
- 516 asientos servidos de 20 en 20: **26 páginas**.

Enfrente hay 500 facturas que hay que cruzar, y el sábado llega una actualización del ERP con la que hay que
demostrar **qué decisiones cambian y por qué**.

## Alternativas consideradas
1. **Consultar el ERP por factura** (`GET /erp/asientos/AS-…` cuando la norma lo necesita). Es lo natural si se
   piensa en "una factura, una decisión". Se descarta por dos motivos, y el segundo es el de fondo: (a) son ~500
   consultas autenticadas, o sea **~50 `ORA-00600`** que reintentar, más la latencia real del bridge en cada
   decisión; (b) la decisión dejaría de ser **reproducible**, porque el ERP puede cambiar entre dos facturas y no
   habría forma de decir con qué estado del ERP se decidió cada una.
2. **Raspar la consulta web `/erp/consulta`.** Devuelve HTML pensado para personas. El manual la reserva a
   administración y el propio bridge redirige; es frágil y además nos saltaríamos la interfaz que el cliente
   soporta. Descartada.
3. **Caché local por pedido, sin versionar.** Quita la latencia pero no resuelve lo importante: sin versión no se
   puede responder "¿esta decisión se tomó antes o después de la actualización?", que es exactamente la pregunta
   del sábado y del domingo.
4. **Descarga completa, versionada por tag, y diff entre versiones (elegida).**

## Decisión
`ClienteERP.descargar_todo(tag)` recorre las 26 páginas **una sola vez** y construye un `ErpSnapshot` que se guarda
en la tabla `snapshots` con su tag (`v1`, `v2`, `v2-sim`). El cliente absorbe las averías del bridge como parte de su
trabajo, no como excepciones: renueva el token a los 250 usos o 13 minutos (antes de que caduque), reintenta
`ORA-00600` hasta 5 veces con backoff corto, respeta `Retry-After` en los 429 y se limita por debajo de 10 req/s.
**Cada consulta emite un `Event`** con latencia, intento y `error_codigo`: los reintentos reales son parte de la
traza que se enseña en la defensa.

A partir de ahí, la norma trabaja **en local** (`ErpSnapshot.por_pedido()`): ninguna regla toca la red. La versión
del ERP entra en `Decision` y en el linaje, así que `reprocess --impacted` sabe exactamente qué recalcular cuando
llega `v2`, y `snapshot.diff_erp(v1, v2)` dice qué asientos son nuevos, cuáles cambiaron y **qué pedidos quedan
afectados**.

## Consecuencias aceptadas
- **El snapshot puede quedar viejo.** Es el precio de no consultar en vivo. Se mitiga con la versión en la decisión:
  una decisión tomada con `v1` se distingue de una tomada con `v2` y el linaje la recalcula sola.
- **`linaje.impactados` recalculaba todas las decisiones cuando cambiaba la versión del ERP**, aunque sólo cambiaran 2.
  Corregido por Miguel en el ADR-0006: ahora el diff decide qué se recalcula (**2 de 500, 0,04 s**; antes, 510 de 510 en 0,5 s). Se
  acepta porque cuesta **0,5 s** y porque la alternativa (deducir qué facturas dependen de qué asiento) es
  complejidad que hoy no compra nada. En la demo se cuenta tal cual: *"recalculadas 510, cambian 2, y son
  exactamente las que referencian los asientos modificados"*.
- **Conviven dos bridges** (v1 en `:8009`, v2 en `:8011`) y el tag se pasa a mano: un `--tag` equivocado contamina
  el linaje. Por eso el ensayo usa siempre `v2-sim` y la skill lo repite.
- Si el bridge muere a mitad de descarga, el snapshot queda **incompleto y se marca como tal** en vez de guardarse a
  medias.

## Evidencia
- **Descarga real** (`PARTE-01.md`, A3): 516 asientos · ~27-30 consultas · 2-3 reintentos `ORA-00600` superados ·
  **~4 s**. Cruce Excel↔ERP v1: 0 pedidos sin asiento, 0 asientos sin pedido, 0 diferencias de importe, **9 asientos
  PAGADA** y **17 `ProveedorID` distintos** entre los 20 pedidos sin NIF en el Excel.
- **Ensayo completo del cambio del sábado** (`ENSAYO-LOTE2.md` §1 y §3), con el ERP simulado de A3
  (3 altas + 2 cambios): `erp pull --tag v2-sim` ~4 s · `erp diff v1 v2-sim` **0,17 s** → 3 nuevos, 2 cambiados,
  5 pedidos afectados · `reprocess --impacted --erp v2-sim` → **2 de 500 recalculadas en 0,04 s, cambian las 2**
  (ADR-0006; en el ensayo original, antes del diff, eran 510 de 510 en 0,5 s):
  `F26-9865_ofimática.pdf` PAGAR→NO_PAGAR (R5: el pedido ya figura PAGADA) y `2026-06-27_P001.pdf` PAGAR→ESCALAR
  (R5: el ERP espera otro importe, aunque con el Excel cuadre). Volver a `--erp v1` las devuelve a PAGAR, con el
  historial conservado en `decisiones` (`vigente=0`).
- **Tests** (`tests/test_erp.py`, 9): descarga completa contra `<meta>.total`, token caducado, renovación proactiva
  por usos y por tiempo, 429 con `Retry-After`, 429 agotado sin reintento ficticio, dos clientes concurrentes,
  conexión rechazada, página fuera de rango. Se saltan solos si el bridge no responde (marca `erp`).
- **Tests del diff** (`tests/test_snapshot.py`, 10), incluido el caso que destapó un **bug real**: `diff_erp` omitía
  los pedidos afectados por asientos eliminados y el pedido anterior al reasignar un asiento
  (`test_diff_afecta_pedido_eliminado_y_ambos_de_asiento_reasignado`).
- **Test de integración offline** de este ciclo (`tests/test_lote2_sim.py`): reconstruye v1 y v2 desde los datos
  embebidos del bridge + `data/fixtures/erp_lote2_simulado.csv` y comprueba el diff **sin levantar el bridge**, para
  que el flujo del sábado no dependa de que alguien tenga un puerto abierto.
- Commit `bf24010` (cliente ERP, cruce, diff del lote 2 simulado).

## Resumen para el plan (5 líneas)
El ERP del cliente es un bridge de 2009 que devuelve XML en ISO-8859-1, caduca el token a los 300 usos y **falla con `ORA-00600` cada diez consultas** —su propio manual dice que se reintente—, así que tratamos sus averías como datos: reintento, renovación proactiva, límite de ritmo y un evento por consulta.
Se descarga **entero una vez** (26 páginas, ~4 s, 2-3 reintentos) a un snapshot versionado en SQLite, y la norma consulta en local: ninguna regla toca la red, y así 500 decisiones no son 500 consultas a un sistema que se cae una de cada diez.
La versión del ERP viaja **dentro de la decisión**, de modo que siempre se puede responder con qué estado del sistema se decidió cada factura.
Cuando el ERP se actualiza, `erp diff v1 v2` dice qué asientos cambiaron y qué pedidos tocan, y `reprocess --impacted` recalcula sólo lo afectado: en el ensayo, **2 decisiones de 500 en 0,04 s**, las dos que referencian los asientos modificados, cada una con su regla y su motivo.
El historial no se borra: la decisión anterior queda marcada como no vigente, así que el cambio del sábado —y el dato que el tribunal cambie el domingo— se pueden enseñar como un antes y un después.
