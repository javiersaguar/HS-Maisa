# Ensayo de fuentes · un Excel o un ERP con otra forma no nos paran · J2, 19/09 12:36-12:50

A las 18:00 llega material nuevo: un Excel (la regla nueva, un proveedor, un IBAN) o un CSV del ERP. Hasta hoy el
loader se había probado con **un** fichero, el de la Caja, y leía las columnas **por posición**. Este documento es el
inventario de lo que suponía, lo que ahora tolera, y las cifras del ensayo con una copia de la BD real.

**Resumen en una línea:** el Excel real sigue dando el mismo maestro (`80911e429c6c`, 11 proveedores, 516 pedidos,
41 avisos) y `reprocess --impacted` no cambia nada; las **ocho** formas distintas que probamos tampoco cambian nada;
los **cuatro** cambios de contenido cambian lo que tienen que cambiar, en menos de un segundo.

## 1 · Qué suponía el loader (y por qué importaba)

El Excel real, medido (`dist/ensayo/j2/inventario.py`): 14 hojas; `Proveedores` con cabecera
`ID · Razon Social · NIF · IBAN · Ciudad · Condiciones` y 12 filas de datos (P007 repetido); `Pedidos_2026` con
`Pedido · ProveedorID · NIF · Importe_Total · Estado · Fecha_Pedido` y 516 filas; **cero** filas vacías; `Estado` es
`ABIERTO` en las 516; los importes son 502 `float` y 14 `int` (nunca texto); las fechas, 516 cadenas ISO (nunca fecha
de Excel). Sobre eso, lo que el loader daba por hecho:

| Suponía | Si el sábado no se cumple | Hoy |
|---|---|---|
| Las hojas se llaman exactamente `Proveedores` y `Pedidos_2026` | `KeyError` seco: la cadena para y nadie sabe por qué | Se buscan por nombre normalizado (sin tildes, mayúsculas ni separadores) y se avisa del nombre real |
| Cada campo está en su columna: `fila[0]`…`fila[5]` | **El fallo peligroso**: con las columnas movidas, el IBAN entra como ciudad y el NIF como razón social. No revienta: **corrompe en silencio** y decide con datos cruzados | Se busca por cabecera normalizada, con alias por campo |
| La cabecera está en la fila 1 | Con un título encima, la cabecera se lee como un proveedor y se pierde una fila real | Se busca la cabecera en las 6 primeras filas y se avisa de en qué fila estaba |
| Una fila está vacía si su primera celda es `None` | Una fila con datos pero sin identificador entraba como proveedor `''` | Se salta si está entera vacía; si tiene datos y no identificador, se avisa con el número de fila |
| Sólo existen las hojas conocidas | Una hoja nueva caía en «hojas ignoradas» junto al ruido de Alberto: **la regla de las 18:00 pasaría desapercibida** | Una hoja que suene a norma sale como `REGLA NUEVA?: la hoja «X» parece una norma y nadie la lee` |
| Las columnas son exactamente seis | Una columna nueva en medio desplaza todo lo que viene detrás | Las que no se reconocen se nombran en un aviso y no estorban |

Lo que **no** cambia: el contenido sigue siendo estricto. Un importe ilegible descarta el pedido con su aviso, un NIF
que no cuadra con el del proveedor se avisa, los duplicados conservan la primera fila y explican el conflicto.

## 2 · La regla de las 18:00 puede venir dentro del Excel

`hojas_norma(xlsx)` lista las hojas que suenan a norma (`norma`, `regla`, `politica`, `pagos`). Con el Excel de hoy
devuelve sólo `['Norma_Pagos_v3']`, la vigente, y no avisa de nada. Si el sábado aparece `Norma_Pagos_v4` o
`Regla nueva`, sale en `avisos_calidad` **con su nombre**, y se lee con
`leer_norma(xlsx, 'Norma_Pagos_v4')` (el nombre también se busca normalizado: vale `norma pagos v4`).
Esto avisa; **no** decide: la norma la escribe Mónica en `rules/`, como siempre.

## 3 · Los fixtures: `data/fixtures/maestro_cambiado/generar.py`

Doce copias del Excel real (el original no se toca), ocho de **forma** y cuatro de **contenido**. Los `.xlsx` no van a
git (son doce copias de ~90 KB del mismo fichero): se generan al vuelo, los tests los piden en `tmp_path` y a mano:

```bash
uv run python data/fixtures/maestro_cambiado/generar.py dist/ensayo/j2/maestro_cambiado
```

| Forma (no cambia el dato) | Contenido (sí lo cambia) |
|---|---|
| `columnas_reordenadas` · IBAN antes del NIF, fecha antes del importe | `proveedor_nuevo` · P099 con su pedido PO-2026-0999 |
| `columna_nueva` · una columna desconocida insertada en medio | `iban_cambiado` · P001 cambia de banco |
| `cabeceras_distintas` · `CÓDIGO`, `N.I.F.`, `Condiciones de pago`, `N.º Pedido` | `pedido_anulado` · PO-2026-0001 pasa a ANULADO |
| `filas_vacias` · huecos intercalados y una fila sin identificador | `importe_cambiado` · PO-2026-0002 al importe que da el ERP del lote 2 |
| `titulo_encima` · la cabecera baja a la fila 3 | |
| `hoja_renombrada` · `PEDIDOS 2026` y `Maestro Proveedores` | |
| `importes_como_texto` · `9.221,75 EUR` y fechas `dd/mm/aaaa` | |
| `hoja_norma_v4` · una hoja que parece la regla del sábado | |

Cada una tiene su test en `tests/test_excel.py` (35 en total, antes 12). El invariante que más vale:
**las ocho de forma dan un maestro idéntico dato a dato al del Excel real, y la misma versión `80911e429c6c`.**

## 4 · Ensayo «maestro cambiado» sobre una copia de la BD real

Copia fresca con la API de backup de SQLite por variante, `ALBERTITOS_DB` apuntando a ella, y
`albertitos maestro --ruta <fixture>` → `reprocess --impacted --erp v1`
(`dist/ensayo/j2/ensayo_maestro.sh`, salidas en `dist/ensayo/j2/salidas/`):

| Variante | versión del maestro | recalculadas | cambian | maestro | reprocess |
|---|---|---|---|---|---|
| las 8 de **forma** y el original | `80911e429c6c` (la misma) | 0 de 500 | **0** | 0,46-0,72 s | 0,22-0,36 s |
| `iban_cambiado` | `5ae91d9c6a5e` | 47 | **43** PAGAR → ESCALAR | 0,56 s | 0,33 s |
| `importe_cambiado` | `dcef6398a62f` | 1 | **1** PAGAR → ESCALAR | 0,61 s | 0,36 s |
| `proveedor_nuevo` | `88a8b3e41192` | 0 (500 sin impacto por diff) | 0 | 0,52 s | 0,30 s |
| `pedido_anulado` | `423855e9d29e` | 1 | **0** | 0,63 s | 0,31 s |

Las dos filas que hay que leer despacio:

- **`iban_cambiado` recalcula 47 y deja 453 fuera**: el linaje hace su trabajo, sólo toca las facturas del proveedor
  cuyo IBAN cambió, y las 43 que pagaban pasan a ESCALAR con el motivo nombrando las dos versiones del maestro
  (`maestro 80911e429c6c→5ae91d9c6a5e: NIF B46102331`). Es el ensayo del cambio que más probable es el sábado.
- **`pedido_anulado` recalcula 1 y no cambia nada**, y eso es un hallazgo, no un acierto: ver abajo.

Huellas de `dist/albertitos.db` y `dist/entrega/outcomes.jsonl` antes y después: `c66d00e45be3` / `1ec4be206089`.

## 5 · Hallazgo para Mónica: el estado del pedido en el Excel no entra en la decisión

Con PO-2026-0001 puesto a `ANULADO` en el Excel, el linaje recalcula su factura (`F26-9865_ofimática.pdf`) y
**se queda en PAGAR**. La norma v3 sólo mira el estado del **asiento del ERP** (`norma_v3.py:183-198`, `PAGADA` y
`PENDIENTE`); `Pedido.estado` del Excel no lo lee ninguna regla. Hoy da igual porque el Excel trae `ABIERTO` en las
516 filas, pero si el sábado llega con pedidos anulados, **los pagaríamos**. Es la otra cara del Q2 que I2 midió
(allí el «anulado» venía dicho en el PDF; aquí viene en el maestro). Decisión de norma, no de loader.

## 6 · El ERP con otra forma (`dist/ensayo/j2/ensayo_erp_forma.py`)

Barato y sin levantar ningún bridge (el de `:8009` sólo se lee). Las dos capas ya aguantan:

| Capa | Otro orden | Columna/etiqueta nueva | Renombrada o ausente |
|---|---|---|---|
| CSV incremental del bridge (`alberto_erp._cargar_asientos_csv`, de la organización) | OK, 5 asientos | OK (y con BOM también) | `SystemExit`: «no parece un export del ERP (faltan columnas)» |
| Nuestro parseo del XML legacy (`sources/erp._asiento_de_xml`) | OK | OK, se ignora | `ERP-FORMATO: asiento AS-00001: fecha=None importe=9.221,75` |

El CSV se lee con `csv.DictReader` y se comprueba que estén los siete nombres (`asiento_id`, `fecha_registro`,
`proveedor_id`, `nif`, `pedido`, `importe_esperado`, `estado`): **el orden es irrelevante y las columnas de más se
admiten**, pero los nombres tienen que estar escritos igual, en minúsculas con guión bajo. Nosotros parseamos por
nombre de etiqueta, así que una etiqueta nueva en el XML no nos rompe y una que falte da un error con el asiento
dentro. No hay nada que arreglar aquí; lo que sí conviene saber a las 18:00:

- `make erp-lote2` apunta a `data/lote2/erp_export_lote2.csv`, que hoy sólo tiene un `.gitkeep`: si el CSV real llega
  con otro nombre o a otra carpeta, el bridge sale con error de fichero inexistente. Se salva con
  `make -C data/caja erp-lote2 LOTE2_ERP=<ruta>`.
- La fusión es por `asiento_id`: los que ya existen se **actualizan** y los nuevos se añaden. El fixture
  `data/fixtures/erp_lote2_simulado.csv` cambia el importe de PO-2026-0002 (10 325,90 → 10 449,35), que es
  justo el caso de `importe_cambiado`.

## 7 · Comprobar todo esto en dos minutos

```bash
uv run pytest tests/test_excel.py -q                                    # 35 passed
uv run python dist/ensayo/j2/comprobar.py                               # 80911e429c6c OK · 11 · 516 · 41
uv run python data/fixtures/maestro_cambiado/generar.py dist/ensayo/j2/maestro_cambiado
bash dist/ensayo/j2/ensayo_maestro.sh                                   # la tabla del §4
uv run python dist/ensayo/j2/ensayo_erp_forma.py                        # la tabla del §6
```

## 8 · Lo que sigue sin cubrir

- Un Excel con las hojas de datos **partidas en dos** (`Pedidos_2026_A`/`_B`) o con los pedidos en varias pestañas por
  trimestre: hoy se leería sólo la primera que coincida y las otras saldrían en «hojas ignoradas». Si pasa, se ve en
  el recuento (menos de 516 pedidos) y hay que decidir en caliente.
- Un `.xls` antiguo o un CSV en vez de `.xlsx`: `openpyxl` no los abre. Se convierte a mano antes.
- Que el ERP sirva el XML con una **etiqueta renombrada** se detecta, pero deja el snapshot sin bajar: eso es
  `ERP-FORMATO` y lo gestiona la política de reintentos, no el loader.
