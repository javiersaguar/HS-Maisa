> **SUPERADO (20/09 01:25). Esto es la lectura a ciegas del sábado por la tarde, no el resultado.** Lo que de
> verdad salió está en [`EXTRACCION.md`](EXTRACCION.md): los 40 extraídos, la auditoría de divisas de los 540 y
> las decisiones (23 PAGAR · 1 NO_PAGAR · 16 ESCALAR). Este fichero se conserva porque es la evidencia que citan
> el ADR-0022 y `rules/norma_v4.py`: se escribió **antes** de decidir nada, para poder etiquetar a ciegas.

# Lote 2 · primera lectura de los 40 PDFs (Javier, sábado 19/09 19:00) · hipótesis, no etiquetas

**L5: no leas esto hasta terminar tu etiquetado a ciegas.**

Lectura de la capa de texto de los 40, más render de las 3 manuscritas, cruzada con el Excel, los tres CSV nuevos y
la BD del lote 1, sin tocar nada. Material: commit `f831e34` de `ikurotime/500-sombras-de-alberto`
(`facturas_primin/`). Aquí los resultados son **lo que previsiblemente toca con la norma v3**, sin conocer la regla
nueva.

## Generales
- Los 40 tienen capa de texto, con ReportLab y sin imágenes. Ninguno es escaneado.
- Ningún nombre coincide con los del lote 1 ni hay copias exactas de facturas del lote 1. Todos los nombres están en
  NFC, dos de ellos con tilde.
- `proveedores_nuevos.csv` trae P012 (DE), P013 (FR), P014 (BR) y P015 (JP). Hay ciudades como «Tokyo, España», un IBAN
  JP (Japón no usa IBAN) y un IBAN BR que acaba en `493C1`.
- El ERP v2 añade 39 asientos nuevos, más `AS-90001`: `PO-2026-0071` pasa a **PAGADA**. En el lote 1, `factura_4635.pdf`
  (el mismo pedido, 951,89 €) salió PAGAR.

## Serie de agosto (22 facturas, pedidos PO-2026-05xx del Excel nuevo, más una del lote 1)
| Fichero | Proveedor | Pedido | Total | Cuadra con pedido y ERP | Trampa | Hipótesis |
|---|---|---|---|---|---|---|
| 2026-08-05_P005.pdf | P005 | 0532 | 6.827,57 | sí | 2 páginas, «Suma y sigue» 3.047,09 | PAGAR |
| 2026-08-09_P001.pdf | P001 | 0534 | 9.457,00 | sí | formato «Invoice #» | PAGAR |
| 2026-08-22_P010.pdf | P010 | **0071** | 951,89 | ERP: **PAGADA** | pedido del lote 1 ya pagado | NO_PAGAR (R5) |
| 2026-08-26_P010.pdf | P010 | 0517 | 4.047,50 | sí | — | PAGAR |
| 2026-08-27_P007.pdf | P007 | 0520 | 3.662,83 | sí | «FACTURA SIMPLIFICADA» de 3.662 € | PAGAR (¿regla nueva?) |
| 2026-27450_suministros.pdf | P001 | 0523 | 4.905,29 | sí | — | PAGAR |
| 2026-42111_construcciones.pdf | P009 | 0529 | 3.496,74 | sí | — | PAGAR |
| 2026-72452_suministros.pdf | P001 | 0531 | 2.211,67 | sí | — | PAGAR |
| FA-3955_electricidad.pdf | P006 | 0536 | 943,80 | sí | **IBAN ES14 0049…** ≠ maestro, más «Actualizacion datos bancarios adjunta» | NO_PAGAR/ESCALAR (R1) |
| FA-5103_electricidad.pdf | P006 | 0528 | 1.008,01 | sí | — | PAGAR |
| FA-6217_transportes.pdf | P002 | 0500 | 3.139,66 | sí | — | PAGAR |
| FA-7357_papelería.pdf | P007 | 0518 | 6.070,03 | sí | fecha en letra | PAGAR |
| FA-7532_informática.pdf | P010 | 0537 | 15.596,90 | sí | **IBAN ES71 0182…** ≠ maestro, más «Ruegan tomen nueva cuenta» | NO_PAGAR/ESCALAR (R1) |
| factura_1210.pdf | P003 | 0512 | 3.679,88 | sí | — | PAGAR |
| factura_1221.pdf | P002 | 0533 | 6.668,98 | sí | 2 páginas, «Suma y sigue» 3.307,05 | PAGAR |
| factura_2923.pdf | P004 | 0530 | 6.778,69 | sí | — | PAGAR |
| factura_6932.pdf | P010 | 0535 | **2.674,10** | **no** (pedido y ERP: 2.120,10) | total distinto del pedido | NO_PAGAR (R2) |
| factura_6990.pdf | P006 | 0504 | 6.483,85 | sí | — | PAGAR |
| factura_7036.pdf | P003 | 0524 | 3.625,60 | sí | — | PAGAR |
| factura_7495.pdf | P003 | 0509 | 5.347,84 | sí | — | PAGAR |
| factura_7713.pdf | P007 | 0519 | 2.041,79 | sí | — | PAGAR |
| factura_9660.pdf | P001 | 0526 | 5.861,75 | sí | — | PAGAR |

## Serie `e01`–`e18` (pedidos PO-2026-13xx, del 14/09; asientos del 15/09)
Son facturas fechadas **de enero a junio de 2026**, anteriores a su pedido. Casi todas en otro idioma.
| Fichero | Prov. | Idioma / fecha | Moneda | Total | Pedido (EUR) | Tipo implícito | Otras trampas |
|---|---|---|---|---|---|---|---|
| e01_P001 | P001 | ES, fecha en letra | EUR | 1.500,40 | 1.500,40 | — | — |
| e02_P002 | P002 | EN, fecha en letra | **USD** | 2.450,00 | 2.254,00 | 0,92 | IVA 0 % |
| e03_P002 | P002 | EN «03 Feb 2026» | EUR | 943,80 | 943,80 | — | — |
| e04_P003 | P003 | CA, fecha en letra | EUR | 1.427,80 | 1.427,80 | — | — |
| e05_P004 | P004 | PT | EUR | 1.113,20 | 1.113,20 | — | **razón social de P004 con el NIF de P011** (B90233808) |
| e06_P013 | P013 | FR, fecha en letra | EUR | 1.887,60 | 1.887,60 | — | **IBAN FR76 3000 6000…** ≠ `proveedores_nuevos` (FR76 3000 4000…) |
| e07_P006 | P006 | IT, fecha en letra | EUR | 2.831,40 | 2.831,40 | — | — |
| e08_P012 | P012 | DE, fecha en letra | EUR | 3.775,20 | 3.775,20 | — | todo cuadra (extranjero y en EUR) |
| e09_P015 | P015 | ES | **JPY** | 850.000 | 5.244,50 | 0,00617 | IVA 77.000 ≠ 21 % de 773.000; IBAN JP |
| e10_P006 | P006 | ES | **USD** | 3.450,00 | 3.174,00 | 0,92 | IVA 0 % |
| e11_P011 | P011 | ES | **GBP** | 2.900,00 | 3.393,00 | 1,17 | **IBAN GB29…** ≠ maestro (ES93…) |
| e12_P010 | P010 | ES | **CHF** | 4.200,00 | 4.410,00 | 1,05 | IVA 0 % |
| e13_P014 | P014 | PT | **BRL** | 15.500,00 | 2.500,00 | 0,1613 | IVA 0 %; IBAN BR con letras |
| e14_P004 | P004 | ES | **MXN** | 48.800,00 | 2.290,00 | 0,0469 | **45.800 + 9.160 ≠ 48.800** |
| e15_P012 | P012 | DE, fecha en letra | **CHF** | 5.400,00 | 5.670,00 | 1,05 | IVA 0 % |
| e16_P011 | P011 | ES | EUR | 629,20 | 629,20 | — | **fecha solo manuscrita** (15 de marzo de 2026) |
| e17_P007 | P007 | ES, entera manuscrita | EUR | 822,80 | 822,80 | — | la capa de texto sale letra a letra |
| e18_P001 | P001 | ES | EUR | 1.815,00 impreso | 1.815,00 | — | **total tachado y «15.000,00 / 18.150,00 corregido A.»** → no puede pagarse sin más |

Los tipos implícitos son iguales dentro de cada moneda: USD 0,92 · GBP 1,17 · CHF 1,05 · BRL 0,1613 · MXN 0,0469 ·
JPY 0,00617. Es decir, el pedido en EUR es el importe de la factura convertido a un tipo fijo. Lo más probable es que
la regla nueva vaya de divisas: o se escalan, o se convierten con una tabla dada.

## Resumen
- **Limpias con v3, si se leen bien: unas 26-27.** Incluye `e01`, `e03`, `e04`, `e07`, `e08`, `e16` y `e17`, si la
  fecha manuscrita se considera válida.
- **Dudosas o no pagables: unas 13-14.** 4 de la serie de agosto, 8 en divisa (de ellas, `e09` y `e14` con cuentas
  mal), más `e05`, `e06`, `e11` y `e18`.
- **Riesgo principal:** `e18`, que la capa de texto da por limpia; y que el lote 1 cambie por P0-2 (`factura_4635`).
