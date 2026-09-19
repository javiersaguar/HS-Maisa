# ADR-0012 · Calendario y remesa de sólo lectura

Estado: implementado en PLAN-10, J5. Fecha: 19/09/2026.

## Contexto

El bonus aporta hasta 10 puntos y es el tercer desempate. Ya hay 438 PAGAR: Alberto necesita conocer cuándo vencen y preparar su pago. El maestro contiene plazos de 30/45/60 días. El bonus debe poder enseñarse en 30 segundos sin alterar la clasificación oficial ni la entrega.

## Alternativas consideradas

1. Calendario y CSV de preparación: reutiliza decisiones, hechos y maestro; se puede mostrar localmente sin servicios ni credenciales nuevos.
2. SEPA pain.001: más cercano a banca, pero faltan cuenta ordenante, perfil bancario y validación contra su esquema. No prometer una remesa importable sin ellos.
3. Otro bonus (predicciones o recordatorios): necesita datos o integraciones nuevos y es menos inmediato para Alberto.

## Decisión

Implementar `python -m albertitos.bonus` sin modificar la CLI principal. Abre SQLite con `mode=ro` y una transacción de lectura consistente. Toma sólo PAGAR vigentes, verifica el hash de sus hechos y utiliza la versión del maestro guardada en cada decisión. No añade eventos a la BD: la evidencia del bonus está en sus propios ficheros y en la bitácora del ensayo.

Suma con Decimal. Calcula vencimientos en días naturales y grupos de semana ISO; el corte es explícito o el de las decisiones, nunca el reloj. El CSV propone ejecutar en el vencimiento o en el corte si ya venció. Genera calendario HTML/CSV, remesa CSV, avisos por fichero y resumen con controles de número y suma.

Un IBAN sin forma de IBAN, una discrepancia con los hechos, la ausencia de plazo, los datos incompletos o los duplicados impiden entrar en remesa. Un IBAN con forma válida que no pasa el mod-97 (los once de la Caja son sintéticos) entra **marcado** (`iban_control_ok=false`), con un aviso por proveedor; `--estricto` lo excluye, como haría un banco (revisado por Javier a las 13:20: excluirlos dejaba la remesa en 0 pagos). No se corrigen cuentas ni se cambian decisiones para conseguir 438 filas. Las rutas de entrega y Caja quedan excluidas como destino.

## Consecuencias aceptadas

El resultado es un borrador financiero en EUR, no una transferencia. No hay envío bancario, pain.001, gestión de festivos, conciliación, pagos parciales ni persistencia de pagos ejecutados. Volver a exportar no acredita que una factura esté aún impagada: se deben actualizar ERP/maestro y reprocesar por el flujo normal antes de usar datos nuevos. Leer el maestro histórico conserva trazabilidad, pero no certifica una cuenta actual.

La Caja contiene once IBAN que no pasan mod-97: por defecto la remesa tiene 438 filas, todas marcadas; con `--estricto`, ninguna. Es un resultado defendible y explícito, no se debilita la validación para aparentar pagos preparados. Los casos positivos se prueban con datos sintéticos en tests.

## Evidencia

- `uv run pytest -q tests/test_bonus.py`: 16 tests pasan; incluye suma exacta, IBAN, plazos, exclusión de ESCALAR/NO_PAGAR, duplicados y CLI repetible sin cambios de BD.
- Ensayo con `sqlite3.Connection.backup`, salida `dist/ensayo/j5/bonus/`: 438 facturas, 2.428.159,06 EUR, 431 vencidas, 2 vencen en semana del corte 2026-09-18. Exactamente 438 avisos individuales por IBAN_INVALIDO.
- CLI sobre copia: 0,184 s en WSL/Ubuntu, Python 3.12, sin red ni LLM; hash de la copia antes/después idéntico. Evidencia: `dist/ensayo/j5/medicion.json`.
- Receta demostrable y límites: [BONUS.md](../BONUS.md).

## Resumen para el plan (5 líneas)
El bonus convierte los PAGAR en un calendario de vencimientos y un CSV de preparación de pagos, sin tocar decisiones ni entrega.
Usa los hechos y el maestro del linaje, plazos en días naturales, semanas ISO y dinero Decimal.
Cada exclusión queda en avisos por factura; los IBAN deben superar el control existente, sin corregir datos de la Caja.
La copia real produce 438 vencimientos por 2.428.159,06 EUR en 0,184 s; la remesa excluye los 438 por IBAN inválido.
El alcance acaba en el borrador: no ejecuta transferencias, no certifica un formato bancario ni registra pagos realizados.
