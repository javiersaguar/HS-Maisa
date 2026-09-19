# API del bonus: calendario de pagos y tesorería · contrato para la consola (K1, 19/09 14:55)

**Sólo lectura.** Estas rutas recalculan el calendario en cada petición a partir de las decisiones PAGAR vigentes: no
escriben en la BD ni cambian ninguna decisión (hay un test que lo comprueba contra una copia de la BD real). Tardan
~0,02 s con las 438 PAGAR de la Caja. **No es una orden bancaria**: es un borrador, y los IBAN de la Caja son
sintéticos (ver «Lo que la pantalla tiene que decir»).

## Cómo se registra (Alejandro, una línea en `src/albertitos/console/api.py`)
```python
from albertitos import bonus
RUTAS.update(bonus.rutas())
```
Mejor con import perezoso, para que el puente no caiga si el módulo no está:
```python
try:
    from albertitos import bonus
    RUTAS.update(bonus.rutas())
except ImportError:
    logger.warning("sin rutas del bonus")
```
Cada handler tiene la firma del puente, `(conn, query) -> (status, body)`: `conn` es la de sólo lectura del puente y
`query` el dict de `parse_qs`. El puente sigue siendo sólo GET (un POST da 405).

## Convenciones
- **Importes**: string con 2 decimales (`"8107.54"`). No los conviertas a `number` para sumar: usa un decimal, o
  suma en céntimos. **Fechas**: ISO (`"2026-09-19"`). **Semana**: ISO (`"2026-W38"`).
- **Parámetro `estricto`** (en todas): `?estricto=true` excluye de la remesa los IBAN que no pasan el mod-97, como
  haría un banco. Con los datos de la Caja, la remesa queda vacía.
- **Errores**: `400 {"error": "…"}` si un parámetro está mal (`limite=-1`, `vencido=quizá`, `tope=abc`); `409 {"error":
  "…"}` si la BD no tiene decisiones o tiene cortes distintos. El mensaje es para una persona: se puede enseñar tal cual.

## Rutas
| Ruta | Parámetros | Devuelve | Ejemplo real |
|---|---|---|---|
| `GET /bonus/resumen` | `estricto` | totales: PAGAR, calendario y remesa (número y €), vencido y en plazo (€), vencidos, los que vencen en la semana del corte, avisos por código, lotes, número de proveedores y totales por semana | `ejemplos/bonus-resumen.json` |
| `GET /bonus/calendario` | `semana`, `proveedor` (id `P001` o razón social exacta), `lote`, `vencido` (`true`/`false`), `limite` (500 por defecto), `estricto`, `con_confianza` (`true`: cada pago lleva `confianza`, lo que devuelva la métrica de K3; `null` si K3 no está, con `confianza_nota` explicándolo) | `{filtros, total, mostrados, pagos: [Pago]}` ordenado por vencimiento | `ejemplos/bonus-calendario.json` |
| `GET /bonus/proveedores` | `estricto` | `{proveedores: [{proveedor_id, beneficiario, numero, importe_eur, vencidos_numero, vencidos_importe_eur, primera_ejecucion, ultima_ejecucion, lotes, iban_control_ok, en_remesa_numero}]}`, de mayor a menor importe | `ejemplos/bonus-proveedores.json` |
| `GET /bonus/remesa` | `limite`, `estricto` | `{tipo: "BORRADOR…", iban_sin_control, total, mostrados, pagos: [Pago]}` (sólo los que entran en la remesa) | `ejemplos/bonus-remesa.json` |
| `GET /bonus/avisos` | `estricto` | `{total, avisos: [{file_id, codigo, detalle}]}` | `ejemplos/bonus-avisos.json` |
| `GET /bonus/tesoreria` | `tope` (€ por semana, opcional), `estricto` | `{fecha_corte, semana_corte, numero, importe_eur, vencido_numero, vencido_importe_eur, en_plazo_numero, en_plazo_importe_eur, semanas: [{semana, desde, numero, importe_eur, acumulado_eur, vencidos_numero, vencidos_importe_eur, en_remesa_numero}]}` y, con `tope`, `programa: {tope_semanal_eur, semanas_para_ponerse_al_dia, semanas_para_pagarlo_todo, sin_programar_numero, semanas: [{semana, desde, numero, importe_eur, supera_tope, arrastrado_numero, arrastrado_importe_eur}]}` | `ejemplos/bonus-tesoreria.json` (con `tope=150000`) |

**`Pago`** (un objeto por factura PAGAR): `file_id`, `lote`, `decision_id`, `proveedor_id`, `beneficiario`, `iban`,
`referencia` (nº de factura), `importe_eur`, `fecha_factura`, `vencimiento` (fecha + días de pago del maestro),
`fecha_ejecucion` (el vencimiento o, si ya pasó, el día de corte), `semana`, `vencido`, `maestro_version`,
`apto_remesa`, `iban_control_ok`. Con `file_id` se abre la traza, igual que en el resto de la consola.

**Ojo con las dos listas de semanas de `/bonus/tesoreria`** (lo confundió R4 en la revisión): `semanas` es el calendario
**natural**, por vencimiento y **sin tope** (la 2026-W35, a finales de agosto, suma 184.374,50 €). El reparto con tope está en
`programa.semanas`, que empieza en la semana del corte y nunca pasa del tope (con 150.000 €, el máximo es 149.999,99 €), salvo un pago que por sí solo lo supera
(`supera_tope: true`). En pantalla, que no se pinten las dos con el mismo título.

## Las cifras de hoy (copia de la BD real, corte 2026-09-18)
438 PAGAR · **2.428.159,06 €** · vencido **2.383.400,88 €** (431 facturas) · en plazo 44.758,18 € · 2 vencen en la semana
del corte · 11 proveedores · remesa 438, todas con `iban_control_ok=false` · 11 avisos `IBAN_SIN_CONTROL` (uno por
proveedor). Con `tope=150000`: al día con lo vencido en **16 semanas**, todo pagado en 17.

## Lo que propongo para la pantalla (la decide Alejandro)
1. **Cabecera** (con `/bonus/resumen`): «438 facturas a pagar · 2.428.159,06 € · 2.383.400,88 € vencidos». Y un aviso
   siempre visible: **«Borrador: los IBAN de esta Caja son sintéticos y un banco los rechazaría. No se ha ejecutado
   ningún pago.»**
2. **Calendario semanal** (con `/bonus/tesoreria`): una barra por semana con el importe, la parte vencida en rojo y la
   línea del acumulado. Un campo «tope semanal (€)» que repite la petición con `?tope=` y pinta el programa: «al día
   en N semanas».
3. **Tabla por proveedor** (con `/bonus/proveedores`): al pulsar una fila, `/bonus/calendario?proveedor=P00X`.
4. **Lista de pagos** (con `/bonus/calendario`): filtros de semana, lote y vencido; cada `file_id` enlaza a la traza.
5. **Avisos** (con `/bonus/avisos`): plegados, con el código y el detalle.

## Cómo probarlo sin la consola
```bash
uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000   # CSV + JSON + calendario.html
uv run python -c "from albertitos.core import db; from albertitos import bonus; print(bonus.rutas()['/bonus/resumen'](db.conectar('dist/albertitos.db', solo_lectura=True), {})[1]['calendario_total_eur'])"
```
