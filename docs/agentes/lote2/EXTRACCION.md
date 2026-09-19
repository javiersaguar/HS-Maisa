# Lote 2 · extracción de los 40 y auditoría de divisas (Javier · agente B · sábado 19/09 23:30)

Qué hay aquí: cómo se leyeron los 40 PDF del lote 2, la comprobación de la subida de facturas por la consola
(lo que pidió Miguel) y la auditoría de divisas de los **540** ficheros. Todo medido, no estimado. La BD de la
entrega no se tocó en ningún momento: las pruebas van sobre copias (`dist/demo/`, `/tmp`).

## 1. Extracción de los 40

23 por plantilla y 17 por el LLM (`llm_texto`, `deepseek-v4-flash`, `p-0.4`), 40/40 sin pendientes. Los hechos
están en `data/fixtures/hechos_lote2.jsonl` (exportados con `hechos export`).

Comprobado a mano, PDF a PDF:

- **Dos páginas con «Suma y sigue»** (`2026-08-05_P005.pdf` 6.827,57 y `factura_1221.pdf` 6.668,98): se toma el
  total de la última página, no el arrastre.
- **Fechas en 7 idiomas** (15 de las 18 `e*` traen la fecha en letra: ES, EN, CA, PT, FR, IT, DE): las 15
  correctas. `e07` dice «sette agosto duemilaventisei» → 2026-08-07. No hizo falta tocar el parser de `formatos`.
- **Manuscritas**: `e16` (sólo la fecha), `e17` (entera) y `e18` (total tachado y corregido a mano) salen con
  `anotacion_a_mano`, que R6 escala. `e18` es la peligrosa: la capa de texto la da por limpia (1.815,00) y el
  papel dice 18.150,00.
- **Identificadores extranjeros** (`formatos.py`, commit `7e4d94c`): IVA alemán, francés, CNPJ brasileño y número
  corporativo japonés ya no son `NIF_INVALIDO`; el IBAN se valida por país. Sin esto, `e08_P012` (alemana, todo
  cuadra) escalaba. Los avisos de los 523 hechos que ya había no cambian.

| Fichero | Método | Moneda | Base | IVA | Total | Pedido | Decisión | Reglas que fallan | Avisos |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-05_P005.pdf` | plantilla | EUR | 5642.62 | 1184.95 | 6827.57 | PO-2026-0532 | **PAGAR** | — | — |
| `2026-08-09_P001.pdf` | plantilla | EUR | 7815.70 | 1641.30 | 9457.00 | PO-2026-0534 | **PAGAR** | — | — |
| `2026-08-22_P010.pdf` | plantilla | EUR | 786.69 | 165.20 | 951.89 | PO-2026-0071 | **NO_PAGAR** | R5 R6 | duplicado_sospechoso |
| `2026-08-26_P010.pdf` | plantilla | EUR | 3345.04 | 702.46 | 4047.50 | PO-2026-0517 | **PAGAR** | — | — |
| `2026-08-27_P007.pdf` | plantilla | EUR | 3027.13 | 635.70 | 3662.83 | PO-2026-0520 | **PAGAR** | — | — |
| `2026-27450_suministros.pdf` | plantilla | EUR | 4053.96 | 851.33 | 4905.29 | PO-2026-0523 | **PAGAR** | — | — |
| `2026-42111_construcciones.pdf` | plantilla | EUR | 2889.87 | 606.87 | 3496.74 | PO-2026-0529 | **PAGAR** | — | — |
| `2026-72452_suministros.pdf` | plantilla | EUR | 1827.83 | 383.84 | 2211.67 | PO-2026-0531 | **PAGAR** | — | — |
| `FA-3955_electricidad.pdf` | plantilla | EUR | 780.00 | 163.80 | 943.80 | PO-2026-0536 | **ESCALAR** | R1 | fecha_en_letra |
| `FA-5103_electricidad.pdf` | plantilla | EUR | 833.07 | 174.94 | 1008.01 | PO-2026-0528 | **PAGAR** | — | fecha_en_letra |
| `FA-6217_transportes.pdf` | plantilla | EUR | 2594.76 | 544.90 | 3139.66 | PO-2026-0500 | **PAGAR** | — | — |
| `FA-7357_papelería.pdf` | plantilla | EUR | 5016.55 | 1053.48 | 6070.03 | PO-2026-0518 | **PAGAR** | — | fecha_en_letra |
| `FA-7532_informática.pdf` | plantilla | EUR | 12890.00 | 2706.90 | 15596.90 | PO-2026-0537 | **ESCALAR** | R1 | — |
| `e01_P001.pdf` | llm_texto | EUR | 1240.00 | 260.40 | 1500.40 | PO-2026-1301 | **PAGAR** | — | — |
| `e02_P002.pdf` | llm_texto | USD | 2450.00 | 0.00 | 2450.00 | PO-2026-1302 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar |
| `e03_P002.pdf` | llm_texto | EUR | 780.00 | 163.80 | 943.80 | PO-2026-1303 | **PAGAR** | — | fecha_en_letra |
| `e04_P003.pdf` | llm_texto | EUR | 1180.00 | 247.80 | 1427.80 | PO-2026-1304 | **PAGAR** | — | — |
| `e05_P004.pdf` | llm_texto | EUR | 920.00 | 193.20 | 1113.20 | PO-2026-1305 | **ESCALAR** | R1 R2 R5 | fecha_en_letra |
| `e06_P013.pdf` | llm_texto | EUR | 1560.00 | 327.60 | 1887.60 | PO-2026-1306 | **ESCALAR** | R1 | — |
| `e07_P006.pdf` | llm_texto | EUR | 2340.00 | 491.40 | 2831.40 | PO-2026-1307 | **PAGAR** | — | — |
| `e08_P012.pdf` | llm_texto | EUR | 3120.00 | 655.20 | 3775.20 | PO-2026-1308 | **PAGAR** | — | — |
| `e09_P015.pdf` | llm_texto | JPY | 773000.00 | 77000.00 | 850000.00 | PO-2026-1309 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar iban_invalido |
| `e10_P006.pdf` | llm_texto | USD | 3450.00 | 0.00 | 3450.00 | PO-2026-1310 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar |
| `e11_P011.pdf` | llm_texto | GBP | 2900.00 | 0.00 | 2900.00 | PO-2026-1311 | **ESCALAR** | R1 R7 R2 R3 R5 | iva_no_estandar |
| `e12_P010.pdf` | llm_texto | CHF | 4200.00 | 0.00 | 4200.00 | PO-2026-1312 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar |
| `e13_P014.pdf` | llm_texto | BRL | 15500.00 | 0.00 | 15500.00 | PO-2026-1313 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar |
| `e14_P004.pdf` | llm_texto | MXN | 45800.00 | 9160.00 | 48800.00 | PO-2026-1314 | **ESCALAR** | R7 R2 R3 R5 | total_no_cuadra iva_no_estandar |
| `e15_P012.pdf` | llm_texto | CHF | 5400.00 | 0.00 | 5400.00 | PO-2026-1315 | **ESCALAR** | R7 R2 R3 R5 | iva_no_estandar |
| `e16_P011.pdf` | llm_texto | EUR | 520.00 | 109.20 | 629.20 | PO-2026-1316 | **ESCALAR** | R6 | anotacion_a_mano |
| `e17_P007.pdf` | llm_texto | EUR | 680.00 | 142.80 | 822.80 | PO-2026-1317 | **ESCALAR** | R6 | anotacion_a_mano |
| `e18_P001.pdf` | plantilla | EUR | 1500.00 | 315.00 | 1815.00 | PO-2026-1318 | **ESCALAR** | R6 | anotacion_a_mano |
| `factura_1210.pdf` | plantilla | EUR | 3041.22 | 638.66 | 3679.88 | PO-2026-0512 | **PAGAR** | — | — |
| `factura_1221.pdf` | plantilla | EUR | 5511.55 | 1157.43 | 6668.98 | PO-2026-0533 | **PAGAR** | — | — |
| `factura_2923.pdf` | plantilla | EUR | 5602.22 | 1176.47 | 6778.69 | PO-2026-0530 | **PAGAR** | — | — |
| `factura_6932.pdf` | plantilla | EUR | 2210.00 | 464.10 | 2674.10 | PO-2026-0535 | **ESCALAR** | R2 R5 | — |
| `factura_6990.pdf` | plantilla | EUR | 5358.55 | 1125.30 | 6483.85 | PO-2026-0504 | **PAGAR** | — | — |
| `factura_7036.pdf` | plantilla | EUR | 2996.36 | 629.24 | 3625.60 | PO-2026-0524 | **PAGAR** | — | — |
| `factura_7495.pdf` | plantilla | EUR | 4419.70 | 928.14 | 5347.84 | PO-2026-0509 | **PAGAR** | — | — |
| `factura_7713.pdf` | plantilla | EUR | 1687.43 | 354.36 | 2041.79 | PO-2026-0519 | **PAGAR** | — | — |
| `factura_9660.pdf` | plantilla | EUR | 4844.42 | 1017.33 | 5861.75 | PO-2026-0526 | **PAGAR** | — | — |

Reparto: **23 PAGAR · 1 NO_PAGAR · 16 ESCALAR** (norma v4, maestro `f504377103b2`, ERP v2, corte 2026-09-18).
La única NO_PAGAR es `2026-08-22_P010.pdf`: su pedido `PO-2026-0071` ya figura PAGADA en el ERP v2 (AS-90001),
el mismo pedido que en el lote 1 pagó `factura_4635.pdf`. En el ensayo de Miguel salían 22/1/17: la que cambia
es `e08_P012.pdf` (alemana), que con los validadores de identificadores extranjeros pasa a PAGAR.

## 2. Divisas: qué dicen los PDF, qué dice el ERP y qué hacemos (lo que preguntaba Miguel)

**Barrido de los 540 PDF** (`scripts` de un solo uso; método: texto de cada PDF contra símbolos, códigos ISO y
palabras de divisa en 7 idiomas, más «tipo de cambio», «exchange rate», «Währung», «moeda»…):

| | Resultado |
|---|---|
| PDF que nombran una divisa o un cambio | **8**, los 8 del lote 2, y la divisa extraída coincide en los 8 |
| PDF del lote 1 con cualquier rastro de divisa extranjera | **0** |
| PDF sin ningún símbolo de euro | 216 (208 del lote 1 + 8 del lote 2): números pelados, sin `€` |

- **Los 500 del lote 1 tienen `moneda` a null**: el campo se añadió el 19/09, después de extraerlos. La norma
  trata «sin moneda» como EUR, y el barrido dice que es verdad: ninguno menciona otra divisa. Los 216 sin `€`
  son las plantillas de la Caja, que imprimen el importe sin símbolo.
- **El Excel y el ERP de 2009 no tienen columna de moneda**: `pedidos_nuevos.csv` es `pedido,proveedor_id,nif,
  importe_total,estado,fecha_pedido` y `erp_export_lote2.csv` es `asiento_id,fecha_registro,proveedor_id,nif,
  pedido,importe_esperado,estado`. **Todo lo del ERP y del maestro está en euros**, siempre.
- **No convertimos**: `norma_v4.TIPOS_CAMBIO` está vacía a propósito (ADR-0022). Con una factura en divisa, R7
  escala y deja en la evidencia el importe del pedido en EUR y el tipo implícito. No da error ni se inventa un
  cambio: escala para que lo vea una persona.
- Los tipos implícitos (pedido EUR ÷ total en divisa) son fijos por moneda: USD 0,92 · GBP 1,17 · CHF 1,05 ·
  BRL 0,1613 · MXN 0,0469 · JPY 0,00617. Si la regla del reto publica una tabla, se rellena `TIPOS_CAMBIO` y
  `reprocess --todo --lote 2 --norma v4`: R2 y R5 pasan a comparar en euros, con tolerancia al redondeo.

Las 8 en divisa: `e02` USD 2.450 · `e09` JPY 850.000 · `e10` USD 3.450 · `e11` GBP 2.900 · `e12` CHF 4.200 ·
`e13` BRL 15.500 · `e14` MXN 48.800 · `e15` CHF 5.400. Las 8 escalan por R7.

**Arreglado en la consola** (`3e6cabe`): formateaba **todos** los importes en euros, así que `e10` se leía
«3.450,00 €» cuando son dólares. Ahora cada importe se pinta en su divisa (`3450,00 US$`) y los del maestro y
el ERP siguen en euros, que es lo que son. Comprobado en el navegador, en el listado y en la ficha.

## 3. Subir facturas por la consola: probado con las 3 categorías de los 2 lotes

Seis PDF **nuevos** (mismo contenido, bytes distintos, así que no valen ni la caché ni el atajo de copia
exacta) subidos por `POST /inbox` a una copia de la BD con los 540 dentro:

| Subido | Lote de origen | Resultado | Igual que el original |
|---|---|---|---|
| `nuevo-2026-01-08_P001.pdf` | 1 | PAGAR | sí |
| `nuevo-2026-03-28_P002.pdf` | 1 | NO_PAGAR (R5, ya pagada) | sí |
| `nuevo-2026-07-09_P010.pdf` | 1 | ESCALAR (R6, el PDF intenta instruir) | sí |
| `nuevo-2026-08-26_P010.pdf` | 2 | PAGAR | sí |
| `nuevo-2026-08-22_P010.pdf` | 2 | NO_PAGAR (R5, ya pagada) | sí |
| `nuevo-e10_P006.pdf` | 2 | ESCALAR (R7, factura en USD) | sí |

Los hechos extraídos coinciden campo a campo con los del original (número, fecha, NIF, IBAN, pedido, base, IVA,
total, moneda). El panel cuenta el lote 99 aparte y la ficha enseña el pedido y el asiento de verdad.

**Fallo encontrado y arreglado** (`23569d1`): la bandeja llamaba a `decide` sin `--norma`, y `decide` aplica la
v3 por defecto. Una factura en divisa subida a mano se decidía con una norma que no tiene R7: salía escalada
por «el total no coincide con el pedido», comparando dólares con euros, en vez de por la moneda. Ahora la
bandeja lee la norma de la decisión vigente más reciente de esa BD (la que enseña el panel) y se la pasa.

## 4. Dos cosas que son de Miguel (no las toco)

1. **`texto_instruccion` falso en una relectura de `e10_P006.pdf`.** Al reextraer, el LLM devolvió como
   `texto_sospechoso` la línea «Divisa de facturación: USD ($) — proveedor factura en USD sin IVA
   (exportación).», que no ordena nada, y la ficha acaba diciendo «el documento intenta instruir». La primera
   extracción del mismo PDF no lo hizo: es variabilidad del modelo. En la entrega no afecta (los 31 avisos de
   la Caja son instrucciones de verdad y ninguna `e*` lo lleva), pero en una factura limpia subida en la demo
   convertiría un PAGAR en ESCALAR. Está en `extract/etapa.py` (`_evidencia_de_lecturas`) y `extract/llm.py`.
2. **La bandeja no marca duplicados.** Hace `ingest → extract → decide`, nunca `reprocess`, así que no pasa
   `marcar_duplicados`: si Alberto sube otra vez una factura ya pagada, R5 la caza por el ERP, pero un
   duplicado cuyo pedido no esté pagado no sale marcado. Una copia byte a byte sí se detecta (mismo sha256) y
   devuelve la decisión que ya tenía.
