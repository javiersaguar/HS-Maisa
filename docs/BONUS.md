# Bonus: calendario, tesorería y borrador de remesa

Implementado por J5 (PLAN-10); tesorería, proveedores, programa con tope y rutas para la consola, por K1 (PLAN-11). Lee los PAGAR vigentes, los hechos de su linaje y el snapshot del maestro usado al decidir. No escribe en SQLite, no cambia decisiones, no genera outcomes y no conecta con bancos, ERP ni LLM.

## Lo nuevo de K1 (19/09 14:55)
- **Tesorería por semana**: lo que se paga cada semana ISO, lo acumulado y lo vencido a la fecha de corte
  (`tesoreria.json` y la sección «Tesorería» de `calendario.html`).
- **Por proveedor**: facturas, importe, vencidas y la primera y última fecha de pago (`proveedores.csv`).
- **Programa con tope** (`--tope-semanal 150000`): reparte la remesa por semanas desde la del corte, sin pasar del
  tope, y dice cuánto se tarda. Con la Caja: **al día con lo vencido en 16 semanas**, todo pagado en 17.
- **Cada pago lleva su lote**: el calendario incluye los PAGAR de todos los lotes vigentes.
- **Rutas GET para la consola**: `bonus.rutas()` → `/bonus/{resumen,calendario,proveedores,remesa,avisos,tesoreria}`.
  Contrato, ejemplos reales y propuesta de pantalla en [`docs/api/bonus.md`](api/bonus.md). Alejandro las registra
  con una línea.

Frase añadida para la defensa: «Si Alberto sólo puede pagar 150.000 € a la semana, en 16 semanas está al día con lo
vencido. Es un cálculo sobre las decisiones, no una decisión nueva».

## Defensa en 30 segundos

Desde la raíz del repo, con la copia del ensayo ya preparada:

```bash
uv run python -m albertitos.bonus --db dist/ensayo/j5/bonus.db --salida dist/ensayo/j5/bonus/
```

Abrir `dist/ensayo/j5/bonus/calendario.html`. El comando tardó **0,184 s** en este portátil con WSL/Ubuntu, Python 3.12, 438 PAGAR y sin red (19/09/2026). La apertura y la explicación no están cronometradas.

Frase para la defensa: «Hay 438 facturas PAGAR por 2.428.159,06 euros. Al corte del 18 de septiembre, 431 están vencidas y 2 vencen esa semana. El calendario aplica los plazos del maestro. La remesa lleva las 438, pero marcadas: los once IBAN de esta Caja son sintéticos y no pasan el dígito de control, así que un banco las rechazaría. En modo estricto la remesa sale vacía, y lo decimos. No hemos cambiado ninguna decisión ni ninguna cuenta».

Enseñar el calendario, abrir `avisos.csv` (11 avisos `IBAN_SIN_CONTROL`, uno por proveedor) y señalar en `resumen.json` `remesa_numero: 438` junto a `remesa_iban_sin_control: 438`. **No decir “438 transferencias listas”**: es un borrador con las cuentas marcadas. `--estricto` da lo que aceptaría un banco: 0. La generación con IBAN válido se demuestra con `uv run pytest -q tests/test_bonus.py`, sin sustituir los IBAN reales de la Caja.

El comando general solicitado también está disponible:

```bash
uv run python -m albertitos.bonus --salida dist/bonus/
```

Lee `ALBERTITOS_DB` si está definido; por defecto `dist/albertitos.db`, siempre mediante conexión de sólo lectura. En PLAN-10 se ha ejecutado exclusivamente con la copia `dist/ensayo/j5/bonus.db`, creada con `sqlite3.Connection.backup`.

## Ficheros y controles

| Fichero | Contenido |
|---|---|
| `calendario.html` | Vista local, sin servidor ni recursos de red; semana ISO, vencimiento, importe, vencido y aptitud para remesa |
| `calendario.csv` | Una fila por PAGAR con vencimiento calculable, también si su IBAN impide incluirlo en remesa |
| `remesa.csv` | Sólo filas preparables; cabecera incluso si no hay ninguna |
| `avisos.csv` | `file_id;codigo;detalle`, una fila por incidencia; una factura puede tener varias |
| `resumen.json` | Recuentos, sumas decimales en texto, exclusiones únicas, vencidos, semana del corte y totales por semana |

Los CSV usan UTF-8, separador `;`, fechas ISO y euros con punto y dos decimales. Campos de pagos: `file_id`, `decision_id`, `proveedor_id`, `beneficiario`, `iban`, `referencia`, `importe_eur`, `fecha_factura`, `vencimiento`, `fecha_ejecucion`, `semana`, `vencido`, `maestro_version`, `apto_remesa`. Se antepone apóstrofo a texto que pudiera interpretarse como fórmula de hoja de cálculo. El HTML escapa los datos.

Es un **CSV de preparación y revisión**, sin homologación a un banco específico; no es XML SEPA pain.001 ni una orden ejecutada. No incluye cuenta ordenante, firma, envío, conciliación o bloqueo contra repetir una transferencia en ejecuciones futuras. Repetir el comando produce el mismo borrador si no cambian los datos ni el corte.

## Cálculo y exclusiones

- Vencimiento = fecha de factura + días naturales de condiciones del proveedor. Agrupación por semana ISO (lunes a domingo). No hay ajuste de festivos ni fines de semana.
- Vencido significa vencimiento **anterior** al corte. Fecha de ejecución propuesta = máximo entre vencimiento y corte. No se emplea la fecha del sistema. Por defecto se usa el único corte de las decisiones; si hay varios o la BD está vacía, se exige `--fecha-corte AAAA-MM-DD`.
- `--fecha-corte 2026-09-21` permite ver el calendario del lunes; no revalida las decisiones ni el ERP a esa fecha. El informe refleja los snapshots guardados, no garantiza que el proveedor o su cuenta sigan vigentes al efectuar una transferencia.
- Los importes se suman con Decimal. Falta de proveedor/plazo/fecha/referencia/importe deja aviso y excluye de calendario y remesa. Un IBAN inválido o discrepante deja el vencimiento visible, pero excluye de remesa.
- Nunca entran ESCALAR ni NO_PAGAR. Hechos nuevos con hash distinto exigen reprocesado. Falta de maestro histórico, copias exactas y referencias duplicadas entre PAGAR también impiden preparar el pago.
- Los totales de calendario sólo incluyen filas calculables; `sin_vencimiento_calculable` muestra cualquier diferencia. `excluidos_remesa` cuenta facturas, no avisos.

## Evidencia sobre la copia real

Corte 2026-09-18, maestro del linaje, 438 PAGAR vigentes:

| Control | Resultado |
|---|---:|
| Calendario | 438 facturas · 2.428.159,06 EUR |
| Vencidos | 431 |
| Vencen en semana 2026-W38 | 2 · 14.518,10 EUR |
| Sin vencimiento calculable | 0 |
| Remesa (por defecto) | 438 pagos · 2.428.159,06 EUR, **todos marcados `iban_control_ok=false`** · 11 avisos `IBAN_SIN_CONTROL` |
| Remesa `--estricto` | 0 pagos · 438 `IBAN_INVALIDO` (lo que aceptaría un banco) |

**Cambio de las 13:20 (Javier):** los once IBAN del maestro tienen forma de IBAN, pero son sintéticos y ninguno pasa el mod-97. El propio `formatos.iban_valido` lo avisa: «es un Aviso, no una regla». Excluirlos dejaba el bonus en «0 pagos» con 438 PAGAR, así que ahora entran marcados y `--estricto` conserva el criterio original de J5. Un IBAN sin forma de IBAN, o distinto del de la factura, se sigue excluyendo siempre. `avisos.csv` contiene exactamente los 438 `file_id` distintos excluidos, sin excepciones ni cuentas corregidas artificialmente. La comprobación individual y el tiempo están en `dist/ensayo/j5/medicion.json`; los totales por semana, en `resumen.json`.

Los tests cubren inclusión y suma con IBAN válido, las exclusiones, decisiones no PAGAR, corte y frontera semanal, linaje, duplicados, exportación segura y CLI repetible. ADR: [0012](adr/0012-calendario-remesa-solo-lectura.md).
