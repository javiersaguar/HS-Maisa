# ADR-0002 · Las plantillas deterministas extraen el 93,6 % de la Caja; el LLM es el resto, y además el control

- **Estado:** propuesto
- **Fecha:** 2026-09-18 23:40 · **Dueño:** Javier · **Módulos:** extract/

## Contexto
La Caja son 500 PDFs: **471 con capa de texto y 29 escaneadas** (`docs/trampas.md`, inventario de A3). La validación
de la organización es binaria, así que un campo mal extraído no cuesta décimas: cuesta el premio, porque la norma
decide con él y nadie lo revisa.

Al empezar creíamos que había "~30 plantillas" (así estaba escrito en el ADR-0001 y en `extract/CLAUDE.md`). Al
medirlo, la firma por las tres primeras líneas daba **313 formas distintas** —se fragmentaba por razón social— y la
firma por **anclas estructurales** (etiqueta de nº de factura + de pedido + de base + de total) dio **6 familias que
cubren las 471 sin resto**. Esto cambia la economía del problema: lo que parecía "hay que llamar al LLM para todo"
era "hay que escribir seis parsers".

El camino del LLM no es caro en dinero (coste marginal 0 EUR, ADR-0004) pero sí en tiempo y en exposición: **5 ms
por plantilla frente a 3,3 s por LLM de texto y 35,3 s por visión** (`RESILIENCIA-Y-COSTE.md` §2).

## Alternativas consideradas
1. **LLM para todas las facturas.** Es lo que hacía el andamiaje inicial y lo que haría cualquiera con prisa.
   Se descarta hoy porque: no es determinista (dos pasadas pueden discrepar y no podríamos explicar por qué cambió
   una decisión), 500 facturas por el camino de texto son ~27 min de reloj frente a 2,5 s, y deja el 100 % de la
   ingesta expuesta a que el proveedor caiga. No se descarta por "malo": se descarta como **camino principal**.
2. **Sólo parsers deterministas, sin LLM.** Máximo control. Imposible hoy: 29 facturas no tienen capa de texto
   (hay que verlas) y 3 con texto no caen en ninguna familia (`2026-03-19_P008.pdf`, `FA-1123_construcciones.pdf`,
   `FA-2967_seguridad.pdf`). Dejarlas fuera es entregar 32 líneas sin decisión = NO APTO.
3. **Plantillas primero, LLM para lo que no reconocen, y el LLM otra vez como control (elegida).**

## Decisión
`etapa.extraer` intenta `plantillas.extraer_por_plantilla(texto, file_id=…, sha256=…)`; si devuelve hechos, **no
llama al LLM**. El parser es deliberadamente conservador: si falta cualquier campo obligatorio devuelve `None` y el
fichero se va al LLM. Un campo inventado es peor que un campo ausente, porque el ausente lo ve la norma (R2/R3/R4
fallan y escalan) y el inventado no lo ve nadie.

Contra el riesgo propio de esta decisión —seis regex equivocándose **en bloque** sobre 468 facturas— se añade el
control: `etapa.contrastar(conn, file_ids=…, workers=4)` lee las mismas facturas con el LLM y las compara con
`validadores.discrepancias()`, que tolera formato (IBAN con espacios, NIF con guion, ±0,01 EUR) pero no diferencias
reales. Es barato (coste 0) y es la única forma de saber si un ancla casa donde no debe.

## Consecuencias aceptadas
- **Las facturas de plantilla no pasan por el LLM**, así que una instrucción inyectada con redacción nueva sólo la
  cazan las regex de `instrucciones.py`. Hueco conocido y documentado (`ENSAYO-LOTE2.md` §2); la respuesta es el
  contraste sobre el lote 2, no bajar la cobertura.
- **Las 6 plantillas son del lote 1.** Si el lote 2 del sábado trae maquetaciones nuevas, la cobertura cae y todo se
  va al LLM: eso es una degradación de tiempo, no de corrección, y `test_cobertura_medida` lo detecta en el acto.
- Mantener seis parsers cuesta trabajo cada vez que cambia un proveedor. A cambio, el 93,6 % de la Caja es
  reproducible sin red, que es lo que hace posible la demo del domingo con el proveedor caído.
- Un parser corregido **no recalcula solo** los hechos ya guardados: hay que reextraer con `--no-solo-pendientes`.

## Evidencia
- **6 familias, 471 de 471 clasificadas** (bitácora 21:20, A2): `moderna` 113 · `abono` 92 · `invoice` 91 ·
  `clasica` 73 · `mayusculas` 57 · `simplificada` 45. Las 22 facturas de dos páginas son todas de `moderna` y llevan
  el total en la página 2 (la 1 acaba en `Suma y sigue:`, que **no** es el total).
- **468 de 471 completas** = 99,4 % de las que tienen texto, **93,6 % de la Caja**. Verificado hoy por C2 contando
  `data/fixtures/hechos_caja.jsonl` (500 líneas): métodos `{plantilla: 468, cache: 29, llm_texto: 3}`.
- **En las 468, la suma de las líneas cuadra con la base al céntimo: 0 excepciones** (A2, `PARTE-01.md`).
- **10 facturas revisadas a mano** contra el PDF (semilla 20260918), 3 de ellas contra el PDF **renderizado**:
  0 campos incorrectos. La revisión encontró 1 defecto real (en `simplificada` el primer concepto se tragaba la
  cabecera de la tabla), corregido **antes** de medir la cobertura.
- **Contraste plantilla↔LLM: 468/468.** Las 468 facturas de plantilla releídas por el modelo, 0 discrepancias
  en los 8 campos clave y 0 fallos (717.188 tokens a coste 0, 472 s con 4 hilos; `CONTRASTE-TOTAL.md` §1).
  Antes se había medido sobre muestras: 18/18 en la muestra y 40/40 al azar (66.492 tokens, `PARTE-01.md`, A1).
- Tests que lo blindan (`tests/test_plantillas.py`): `test_las_seis_familias_estan_cubiertas`,
  `test_cobertura_medida` (falla si la cobertura baja), `test_las_lineas_suman_la_base`,
  `test_dos_paginas_toma_el_total_de_la_segunda`, `test_fecha_imposible_no_se_completa_ni_se_inventa`,
  `test_el_nif_del_cliente_no_se_cuela_como_emisor`.
- Commit `b2935dd` (plantillas, validadores, instrucciones).

## Resumen para el plan (5 líneas)
Medimos la Caja antes de elegir: sus 471 facturas con texto caen en **6 familias de maquetación**, no en treinta, y seis parsers deterministas extraen **468 (93,6 % de la Caja) en 5 ms cada una y sin tocar el LLM**.
El LLM queda para lo que los parsers no reconocen —29 escaneadas y 3 sin familia—, de modo que la ingesta no depende del proveedor para el 93,6 % del trabajo.
Los parsers son conservadores: si falta un campo obligatorio devuelven `None` y la factura se va al LLM, porque un campo inventado lo consume la norma sin que nadie lo vea.
El riesgo propio de esta decisión es equivocarse en bloque, así que el LLM vuelve como **control**: relee las mismas facturas y se comparan con tolerancia de formato (468/468 coincidieron: el 100 % de las facturas de plantilla).
Cobertura y coincidencia están clavadas en tests: si un parser deja de cubrir o empieza a mentir, `make check` se pone rojo ese día y no el domingo.
