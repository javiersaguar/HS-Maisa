# Mapa de políticas abiertas · lote 1 · I2 · 19/09

**La pregunta con más facturas en juego es Q3 (frontera NO_PAGAR/ESCALAR): 35 líneas hoy ESCALAR pasarían a NO_PAGAR; 28 fuera de la muestra.**

## Método
1. BD real en **sólo lectura**. Hechos + decisiones vigentes del lote 1, maestro y ERP `v1` desde snapshots.
2. Decisión en memoria con `REGISTRO["v3"].decidir`, fecha de corte `2026-09-18` (la misma que `pipeline.etapas.decide`).
3. **Control:** sin variante reproduce **438 PAGAR · 53 ESCALAR · 9 NO_PAGAR**, fichero a fichero (500/500). Si no, el script para.
4. Cada variante se aplica con `unittest.mock.patch` (o un `decidir` local) y se deshace al salir. **No se edita `rules/`.**
5. Comprobación a mano de las candidatas Q1/Q2 contra maestro, ERP v1 y PDF: `dist/ensayo/i2/comprobacion.csv` (fuera del repo publicado). Veredicto: 6 LIMPIA (Q1) · 2 OTRA_REGLA (Q2, siguen con `TEXTO_INSTRUCCION`) · 0 DATO.
6. Mientras la muestra de Mónica esté abierta, este documento **no lista** file_id de `muestra.txt`. La lista completa está en `dist/ensayo/i2/`.

```bash
uv run python scripts/mapa_politicas.py --excluir-muestra --markdown
uv run python scripts/mapa_politicas.py --por-fichero --salida dist/ensayo/i2/por_fichero.csv
```

## Recuentos (todos / sin los 21 de la muestra)

| Pregunta | Variante | Cambian (todos) | Sin muestra | Transiciones (todos) |
|---|---|---:|---:|---|
| **Q1** texto que ordena | Quitar `TEXTO_INSTRUCCION` de `ANOMALIAS_HUMANO` → ¿PAGAR? | **6** de 31 con el aviso | **0** | ESCALAR→PAGAR 6 |
| **Q2a** pedido «anulado» según PDF | Quitar `PEDIDO_ANULADO_SEGUN_PDF` → ¿PAGAR? | **0** de 2 | 0 | — (las 2 siguen ESCALAR por `TEXTO_INSTRUCCION`) |
| **Q2b** | Forzar NO_PAGAR si trae el aviso | **2** | **0** | ESCALAR→NO_PAGAR 2 |
| **Q3** frontera | Fallo objetivo R1–R4 → NO_PAGAR (hoy ESCALAR) | **35** | **28** | ESCALAR→NO_PAGAR 35 |
| **Q4** docs del evaluador | Inventario (sin cambio de norma) | **2** (hoy ESCALAR) | **0** | — |
| **Q5** duplicado PO-2026-0492 | Primero por fecha PAGAR, el otro NO_PAGAR | **2** | **2** | ESCALAR→PAGAR 1 · ESCALAR→NO_PAGAR 1 |

**Q1 · tipos de orden** (las 6 que pasarían a PAGAR): escalar/bloquear 3 · evaluador 2 · no_pagar 1. Las otras 25 con el aviso **no** cambian: fallan por R1–R5 u otra R6.

**Q5 · fuera de la muestra (sí se nombran):** `factura_41082.pdf` (2026-04-07) → PAGAR · `2026-0233-A_catering.pdf` (2026-04-11) → NO_PAGAR. Hoy las dos ESCALAR por `DUPLICADO_SOSPECHOSO`.

**Q3 · 28 fuera de la muestra** (ESCALAR→NO_PAGAR):  
`2026-03-19_P008.pdf`, `2026-07-08_P010.pdf`, `F26-5240_ofimática.pdf`, `F26-6702_limpiezas.pdf`, `F26-6964_ofimática.pdf`, `F26-8801_suministros.pdf`, `F26-8812_electricidad.pdf`, `F26-9012_electricidad.pdf`, `FA-1123_construcciones.pdf`, `FA-2508_consultoría.pdf`, `FA-2967_seguridad.pdf`, `FA-4290_mensajería.pdf`, `FA-5044_mensajería2.pdf`, `FA-5077_electricidad.pdf`, `FA-5633_transportes.pdf`, `FA-7311_transportes.pdf`, `FA-9104_electricidad.pdf`, `factura_1936.pdf`, `factura_2018.pdf`, `factura_3184.pdf`, `factura_4485.pdf`, `factura_7265.pdf`, `reimpresion_0712.pdf`, `scan_016.pdf`, `scan_018.pdf`, `scan_021.pdf`, `scan_023.pdf`, `scan_029.pdf`.

## Preguntas para el mentor (neutras)
1. **Texto que ordena la decisión.** Si una factura cumple proveedor, pedido, IVA, fecha y ERP, pero el PDF dice qué decidir (escalar, pagar, no pagar, o «excluir del cómputo»), ¿manda el documento o la norma? Hoy: ESCALAR (`R6` + `TEXTO_INSTRUCCION`). **En juego:** 31 con el aviso; **6** pasarían a PAGAR si se ignorara sólo esa señal (las 6 están en la muestra etiquetada).
2. **Pedido «anulado» según el PDF**, ABIERTO en Excel y PENDIENTE en el ERP. ¿ESCALAR, PAGAR o NO_PAGAR? Hoy: ESCALAR. **En juego:** 2 (ambas también traen texto que ordena; quitar sólo el aviso de anulación no basta para pagar).
3. **Frontera NO_PAGAR / ESCALAR.** Hoy NO_PAGAR sólo si el ERP marca el pedido PAGADA. ¿Un fallo objetivo de NIF/IBAN, importe, IVA o fecha futura debe ser NO_PAGAR? **En juego:** 35 (28 fuera de la muestra).
4. **Documentos de prueba del evaluador** (el PDF pide marcarse ESCALAR y excluirse del acierto). ¿Se validan igual? Hoy: ESCALAR por el texto. **En juego:** 2 (en la muestra).
5. **Mismo pedido dos veces** (`PO-2026-0492`). ¿Las dos ESCALAR, o la primera PAGAR y la otra NO_PAGAR? Hoy: las dos ESCALAR. **En juego:** 2.

## Palanca (la escribe Mónica) y coste
| Si el mentor dice… | Qué tocaría en la norma (palabras) | Líneas | Coste |
|---|---|---:|---|
| Q1: el texto no manda → pagar si R1–R5 OK | Sacar `TEXTO_INSTRUCCION` de `ANOMALIAS_HUMANO`, o acotarlo | +6 PAGAR | `reprocess --todo` ≈ 7 s · auditoría · publicar |
| Q1: mantener ESCALAR | Nada | 0 | — |
| Q2: NO_PAGAR si el PDF anula | Tratar el aviso como `no_pagar` (como R5 PAGADA) | 2 ESCALAR→NO_PAGAR | ídem |
| Q2: PAGAR si Excel/ERP vivos | Sacar el aviso de `ANOMALIAS_HUMANO` **y** el `TEXTO_INSTRUCCION` asociado | hasta 2 | ídem |
| Q3: fallos R1–R4 → NO_PAGAR | Marcar esos `_ko` con `no_pagar=True` (o regla dedicada) | 35 | ídem |
| Q3: mantener ESCALAR | Nada (hipótesis actual) | 0 | — |
| Q4: excluir del cómputo / tratar distinto | Política + posible filtro en auditoría; hoy ya ESCALAR | 2 | según diseño |
| Q5: primero PAGAR, segundo NO_PAGAR | Política de duplicados por pedido (hoy `marcar_duplicados` → las dos ESCALAR) | 2 | ídem |

**PIDO A Mónica:** lleva estos recuentos al mentor. La lista por fichero de la muestra, cuando cierres `esperado_muestra.csv`.
