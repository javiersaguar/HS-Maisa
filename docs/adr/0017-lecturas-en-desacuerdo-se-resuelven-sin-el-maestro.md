# ADR-0017 · Cuando las lecturas de una escaneada no coinciden, decide una prueba independiente, no el maestro

- **Estado:** aceptado por Miguel (19/09), pendiente del visto bueno de Javier (extract/) y Mónica (ADR-0011).
  Hechos regenerados con una pasada nueva (ver Evidencia).
- **Fecha:** 2026-09-19 16:30 · **Dueño:** Miguel · **Módulos:** extract/ (acota el ADR-0003; complementa el ADR-0011)

## Contexto
Las 29 escaneadas se leen dos veces con visión (ADR-0003), y las dos lecturas pueden no coincidir.

**Identificadores.** En 10 de las 29, las dos lecturas no coinciden en NIF, IBAN o pedido. Hasta ahora decidía el
maestro: ganaba la lectura igual a la del proveedor del pedido, con `confianza 0,6`. El ADR-0011 vio el problema
(si el IBAN se eligió *porque* es el del maestro, la R1 ya no puede fallar) y escala esas facturas: 5 pasan de
PAGAR a ESCALAR. Pero en varias el documento se lee sin problema y lo que falló fue una lectura. Mirado a
300-600 dpi: `scan_009` y `scan_011` imprimen `ES93 6888 4400 1235 8890 0142` (la principal leyó `6998` y
`ES83…`); `scan_006` y `scan_012` imprimen `ES44 1465 …` y `NIF B98120774`.

**Importes.** Entre las dos lecturas no se comparaban importes. `scan_001` y `scan_014` escalaban por
`importe_ambiguo`, porque las líneas no sumaban la base. Es lo único que dispara ese aviso en toda la Caja: en las
468 con texto las líneas suman la base al céntimo. La causa era un dígito mal leído en una línea: `scan_001`
imprime `51,27` y se leyó `61,27`; `scan_014` imprime `896,03` y se leyó `898,03`.

En los dos casos, facturas limpias escalan por un fallo de nuestro lector, no del documento. Con validación binaria,
eso puede costar aciertos.

## Alternativas consideradas
1. **Mantener el ADR-0011 y escalar lo que no cuadra** — seguro, pero da por dudosas facturas que se leen bien.
   Se descarta: al menos 6 facturas verificadas a mano escalarían sin motivo en el documento.
2. **Volver al ADR-0003 (pagar lo reconciliado)** — se descarta por el mismo argumento del ADR-0011: elegir con
   el maestro y comprobar después contra el maestro no comprueba nada.
3. **Votar carácter a carácter** — se descarta con un caso real. En `scan_023` (NIF tapado por una mancha, trampa)
   las lecturas `B96233418`, `B68233419` y `B96233419` componen, dígito a dígito, el NIF del maestro. Pagaríamos
   una trampa.
4. **Tercera lectura del 55 % superior a 300 dpi para los identificadores** — medida y descartada: falló el IBAN
   de `scan_006` (repitió el `1485` erróneo de la segunda) y el de `scan_011`.
5. **Importes: votar línea a línea entre lecturas** — descartado. La propia factura trae la prueba: si las cuentas
   cuadran (las líneas suman la base, base + IVA = total, la cuota sale del porcentaje), esa lectura vale. No
   hace falta componer un resultado a partir de trozos.
6. **(elegida)** Identificadores: una tercera lectura (35 % superior, 300 dpi) y mayoría por valor entero.
   Importes: la lectura cuyas cuentas cuadran; si ninguna, una lectura más de la página entera a 200 dpi, que
   sólo vale si cuadra. En los dos casos, lo que no se resuelve sigue escalando.

## Decisión
Un desacuerdo entre lecturas se resuelve con una prueba independiente del maestro y del pedido. Así la R1 y la R2
siguen comprobando algo. Si esa prueba no alcanza, la factura escala: el sistema pregunta cuando no sabe.

Implementación en `extract/etapa.py`, llamada desde `_segunda_lectura`:
- **Identificadores (`_desempatar`):** si las dos lecturas no coinciden en NIF, IBAN o pedido, hay una tercera
  lectura del 35 % superior a 300 dpi (variante de caché `sup35_300`). En cada campo gana el valor entero que
  repiten dos de las tres lecturas. Lo que siga sin acuerdo va por el camino de antes: reconciliación con el
  maestro (`confianza 0,6`, escala por el ADR-0011) o `DISCREPANCIA_EXTRACTORES`. Parámetros: `TERCERA_LECTURA`
  (`ALBERTITOS_VISION_TERCERA`), `DPI_VISION_3`, `FRACCION_SUPERIOR_3`. Evidencia en el evento: `desempate=`.
- **Importes (`_importes_que_cuadran`):** si alguna cuenta de la principal falla
  (`validadores.cuentas_fallan`; que falte el detalle no cuenta como fallo), se toma el bloque base, IVA %, IVA,
  total y líneas de otra lectura cuyas cuentas cuadran (`validadores.cuentas_cuadran`, que exige líneas). Si
  ninguna cuadra, hay una lectura más de la página entera a 200 dpi (variante `pag200`), que sólo se usa si
  cuadra. Parámetros: `IMPORTES_POR_CUENTAS` (`ALBERTITOS_IMPORTES_POR_CUENTAS`), `DPI_VISION_IMPORTES`.
  Evidencia en el evento: `importes_de=`, con los importes de antes.
- **El IBAN también se desempata** (`CAMPOS_DESEMPATE`). El 19/09 se probó a no hacerlo (alternativa 2 del
  ADR-0011, sólo para el IBAN) porque Miguel leía `ES83` en `scan_011` donde dos lecturas leían `ES93`. Pero así
  escalaban `scan_006` y `scan_009`, dos facturas limpias en las que una lectura falló un dígito. Revisada de
  nuevo, `scan_011` puede ser un 93. Sobre las 26 escaneadas con respuesta conocida: con mayoría también en el
  IBAN, 26/26; sin ella, 23/26. Se vuelve a la mayoría.
- Ninguna de las dos baja `confianza`, porque el criterio no sale del maestro. Las lecturas extra son opcionales,
  como la segunda: si fallan, decide el camino de antes.
- **`validadores.revalidar`:** los avisos que `validar` deduce de los campos se recalculan después de cambiarlos.
  Antes, un `importe_ambiguo` o un `nif_invalido` del valor mal leído sobrevivía al valor bueno, y ya pasaba con
  la reconciliación. Conserva el orden, porque el orden entra en el hash de los hechos. Sobre los 500 hechos de
  `hechos_caja.jsonl` no cambia ninguno.

## Consecuencias aceptadas
- **Dos lecturas pueden coincidir en el mismo error.** Pasó en el ensayo con el recorte del 55 % (el `1485` de
  `scan_006`). Si el error da un valor distinto del maestro, la R1 escala y no se paga nada mal. Para pagar mal,
  dos lecturas tendrían que coincidir exactamente en el IBAN del maestro sin haberlo visto nunca. El riesgo que
  queda es un IBAN fraudulento que se diferencia del bueno en un solo dígito ambiguo, y lo aceptamos.
- **Unas cuentas que cuadran pueden no ser las impresas**, si varios errores se compensan al céntimo. No se ha
  visto: en el ensayo, todas las lecturas que cuadraron tenían los valores correctos, y todas las que leyeron mal
  un importe dejaron de cuadrar. Aun así, R2 y R5 siguen comparando el total con el pedido y con el ERP.
- **Más visión, sólo cuando hace falta.** Identificadores: 10 lecturas más en la Caja (media qwen3.6: 3.788
  tokens de entrada y 3.561 de salida). Importes: una lectura más sólo si las dos primeras fallan las cuentas (media
  de página a 200 dpi: 4.621 de entrada y 1.582 de salida). Coste marginal 0 con el gateway de suscripción plana.
  En el ensayo, 20 lecturas a 300 dpi con 4 hilos tardaron 3 min 40 s, y 22 de importes, 3 min 9 s.
- **La evidencia sólo queda en el evento.** `InvoiceFacts` no tiene dónde guardarla (core/ congelado). Al importar
  hechos desde `hechos_caja.jsonl` la traza la pierde, igual que ya pierde la reconciliación.
- **`EXTRACTOR_VERSION` no sube.** Al reimportar los hechos, el linaje los recalcula por la marca de tiempo
  (`_posterior` en `pipeline/linaje.py`, igual que en el ADR-0011).
- **Las lecturas son de otra pasada.** Los hechos ya no salen de la caché de Javier (`hechos_caja.jsonl`, que
  no está en esta máquina), sino de una pasada nueva con p-0.2, cuyas lecturas quedan en la caché de la BD. Cada
  pasada tiene su propio ruido; los mecanismos de este ADR están para absorberlo, y se midió contra las etiquetas.
  El fixture hay que reexportarlo desde esta BD.
- **`scan_017` depende de la pasada**: bajo una mancha, unas lecturas dan `B46102331` (lo impreso) y otras `S…`
  o `G…`. En la pasada vigente gana `B46102331` por mayoría y paga; en otras, escala.

## Evidencia
- **Identificadores.** Ensayo del 19/09 sobre una copia de `dist/bench.db`, con las dos primeras lecturas en caché
  y sólo la tercera por red. Las 10 escaneadas con desacuerdo; "maestro" significa que coincide con el del
  proveedor del pedido:

  | Fichero | Campo en desacuerdo | Principal / segunda | Tercera (35 %, 300 dpi) | Resultado |
  |---|---|---|---|---|
  | `scan_006` | NIF · IBAN | `B66…`/`B98…` · `1465`/`1485` | `B98…` · `1465` | los dos por mayoría = maestro |
  | `scan_009` | IBAN | `6998`/`6888` | `6888` | mayoría = maestro |
  | `scan_011` | IBAN | `ES83…3589`/`ES93…3588` | `ES93…3588` | mayoría = maestro |
  | `scan_012` | NIF | `B88…`/`B98…` | `B98…` | mayoría = maestro |
  | `scan_017` | NIF | `S46…`/`B45…` | `B46…` | sin mayoría → reconciliada → ESCALAR |
  | `scan_016` (trampa) | IBAN | `…336846`/`…338846` | `…338846` | mayoría ≠ maestro → R1 escala |
  | `scan_023` (trampa) | NIF | `B96233418`/`B68233419` | `B96233418` | mayoría ≠ maestro → R1 escala |
  | `scan_021` (trampa) | NIF | `B00203806`/`B0263808` | `None` | sin mayoría → escala |
  | `fax_2026_0411` (trampa) | NIF · IBAN · pedido | tres valores distintos en NIF e IBAN | — | pedido por mayoría; NIF/IBAN escalan |
  | `copia_2026_0518` (trampa) | IBAN | dos valores | un tercero distinto | sin mayoría → escala |

  Ninguna trampa pasa a coincidir con el maestro.
- **Importes.** Ensayo sobre 11 escaneadas: las 4 con importes mal leídos en alguna pasada (`scan_001`,
  `scan_012`, `scan_014`, `scan_015`) y 7 de control, entre ellas `reimpresion`, `fax` y `copia` por su maquetación.
  - `scan_001`: la principal leyó `61,27` y la segunda `912,89`. Ninguna cuadra. La página a 200 dpi lee
    `912,69 · 61,53 · 51,27`, que es lo impreso, y cuadra.
  - Las lecturas extra que se equivocaron (`scan_002`: total `1.664,38`; `scan_005`: una línea `68,49`) no
    cuadran. En esos casos la principal ya cuadraba, así que ni se habrían pedido.
  - Regenerando las 29 escaneadas desde esa caché, sólo cambian tres facturas y ninguna otra:
    - `scan_001`, por la lectura extra;
    - `scan_012` (total `877,83` → `877,63`) y `scan_015` (`1.823,58` → `1.823,98`), por la segunda lectura, que
      llega a los mismos valores que el fixture de Javier, sacado de otra pasada.
- **Verificación visual** (recortes a 200-600 dpi): `scan_001` `51,27`, `scan_014` `896,03`, `scan_006` y
  `scan_012` `ES44 1465 0100 9517 0430 2211` y `B98120774`, `scan_009` y `scan_011` `ES93 6888 4400 1235 8890
  0142`, `scan_017` `B46102331` bajo una mancha.
- **Efecto sobre la entrega** (medido al regenerar): respecto al ADR-0011 solo (438/53/9) pasan a PAGAR
  `scan_001`, `006`, `009`, `011`, `012`, `014` y `017`, y queda en 445/46/9.
- **BD regenerada (19/09)** con este código y el B' del ADR-0018, sobre una pasada nueva de visión con p-0.2
  (las lecturas quedan en su caché): **445 PAGAR · 46 ESCALAR · 9 NO_PAGAR**, auditoría APTO. Entre medias se
  promovió la variante sin mayoría en el IBAN (442/49/9), que se abandonó por lo dicho arriba.
- **Etiquetado a ciegas** de 17 escaneadas por Miguel (`data/fixtures/hechos_escaneadas.csv`,
  `scripts/comparar_hechos.py`, sin líneas), completado con 9 escaneadas de respuesta conocida por imagen, por el
  inventario de trampas o por los ADR:
  - esta versión: 26/26;
  - la entrega del 18/09: 23/26;
  - con el ADR-0011 solo: 20/26.

  Las 471 facturas con texto deciden igual en todas las versiones.
- **Tests:** `tests/test_llm.py`, sección "escaneadas: tercera lectura e importes". Tres de ellos fallan sin el
  cambio: `::test_tercera_lectura_desempata_por_mayoria`, `::test_importes_de_la_lectura_cuyas_cuentas_cuadran` y
  `::test_si_las_dos_fallan_una_lectura_mas_de_la_pagina`. Otros protegen contra corregir de más:
  `::test_si_ninguna_lectura_cuadra_el_aviso_se_queda`, `::test_una_lectura_sin_lineas_no_corrige_las_lineas` y
  `::test_sin_lineas_no_es_un_fallo_de_cuentas`.

## Resumen para el plan (5 líneas)
Si las dos lecturas de una escaneada no coinciden, no decide el maestro: decide una prueba independiente. Para
NIF, IBAN y pedido, una tercera lectura y mayoría por valor entero; para importes, la lectura cuyas cuentas cuadran
(y si ninguna, una más de la página). Así la R1 y la R2 siguen comprobando algo, y no se escala una factura legible
por un dígito mal leído (`scan_009`: `6998` donde pone `6888`; `scan_001`: `61,27` donde pone `51,27`). Lo que no
se resuelve escala. En el ensayo, ninguna de las 5 trampas cambió de resultado.
