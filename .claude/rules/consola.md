---
paths:
  - "src/albertitos/console/**"
---
# Consola (Streamlit, sólo lectura)

- Lee la SQLite directamente (`core.db.conectar(..., solo_lectura=True)`); no importa `rules/` ni `extract/`. Cero lógica de negocio: si un dato no está en la BD, se pide a Miguel un evento/columna, no se recalcula aquí.
- Tres vistas y ninguna más: **Escalados** (cola con motivo y evidencia), **Traza** (una decisión: input → hechos → maestro → asiento ERP → reglas → resultado, con eventos, latencias, reintentos, tokens y coste), **Panel** (contadores por etapa/estado, pendientes, ficheros/s, coste acumulado, versión de norma/ERP/maestro).
- Acciones, siempre por la CLI en un subprocess y nunca escribiendo en la BD desde aquí (ADR-0007):
  - botón "Reprocesar impactados" (Streamlit): lanza `albertitos reprocess --impacted` y muestra el diff antes/después;
  - bandeja (`POST /inbox`, `bandeja.py`, consola Next): `ingest --lote 99` → `extract` → `decide --fixture`. Sólo con el puente arrancado con `--bandeja` (BD `dist/bandeja.db`, nunca la de la entrega) y sólo desde el origen de la consola. Cada PDF subido se sigue por el `file_id` que ingest le dio (sha256), nunca por su nombre.
- Tiene que abrir en < 3 s con la BD de 540 ficheros y funcionar sin red (la demo corre en el portátil de Alfonso).
- Se prueba con `dist/albertitos.db`; si no existe, `make db && uv run albertitos ingest` da datos mínimos.
