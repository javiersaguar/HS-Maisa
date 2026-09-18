---
paths:
  - "src/albertitos/core/**"
  - "docs/contratos.md"
---
# Contratos congelados (core/)

- Dueño: Miguel. Cualquier cambio se anuncia en el canal ANTES de hacerlo con: qué campo/tabla, por qué, quién lo consume.
- Compatibilidad hacia atrás siempre: campos nuevos opcionales con default; nunca renombrar ni cambiar tipo.
- Dinero = `Decimal` (2 decimales), fechas = `date` ISO, versiones = strings cortos (`v3`, `ext-1.2`).
- Todo cambio en `contracts.py` va con su test en `tests/test_contracts.py` y con la línea correspondiente en `docs/contratos.md`.
- `schema.sql` es idempotente (`CREATE TABLE IF NOT EXISTS`) y sólo añade; las migraciones destructivas no existen en 36 h: si hace falta, `make clean && make db`.
