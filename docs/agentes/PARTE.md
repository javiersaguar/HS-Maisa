# Parte de fin de ciclo · ciclo 10

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (… · 08: H1-H2 · 09: I1-I2).

## J1 · Ensayo general del lote 2 con `main`, cronometrado
_(pendiente)_

## J2 · Que un Excel o un ERP cambiados de forma no nos paren
_(pendiente)_

## J3 · Las escaneadas del lote 2 no dependen de un solo modelo
_(pendiente)_

## J4 · La defensa con el código de hoy, y el dato en vivo del domingo
_(pendiente)_

## J5 · Bonus (+10): remesa y calendario de pagos
_(pendiente)_


### Cierre J5 · implementado, comprobación global pendiente de formato ajeno
- Commit: 8e8301d (código, 16 tests, ADR-0012 y docs/BONUS.md). Sin push.
- Comando medido: `uv run python -m albertitos.bonus --db dist/ensayo/j5/bonus.db --salida dist/ensayo/j5/bonus/`: 0,184 s. Calendario 438 / 2.428.159,06 EUR, 431 vencidos, 2 en semana 2026-W38; remesa 0 / 0,00 EUR. Las 438 diferencias están identificadas en avisos.csv como IBAN_INVALIDO: los 11 IBAN de proveedores fallan mod-97.
- `uv run pytest -q tests/test_bonus.py`: 16 passed. `uv run pytest -q`: 459 passed, 2 deselected, 1 xfailed en 39,33 s. Ruff propio y `make agentes-check` OK.
- `make check` final se detiene en formato de sources/excel.py (J2 en edición; antes ficheros de J4). No toco esos ficheros; repetir al cerrar cambios concurrentes. Logs en dist/ensayo/j5/.
- BD / outcomes al inicio y fin: c66d00e45be3 / 1ec4be206089. Copia hecha con SQLite backup, sin LLM ni red; ningún cambio en decisiones o entrega.
- PIDO A Alejandro: conectar calendario.csv, avisos.csv y resumen.json si lo quiere en consola. Calendario HTML ya enseñable; CSV es borrador, no orden bancaria. La remesa con IBAN válido está probada sólo con datos sintéticos de tests.
