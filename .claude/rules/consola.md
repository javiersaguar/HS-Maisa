---
paths:
  - "src/albertitos/console/**"
---
# Consola (Streamlit, sólo lectura)

- Lee la SQLite directamente (`core.db.conectar(..., solo_lectura=True)`); no importa `rules/` ni `extract/`. Cero lógica de negocio: si un dato no está en la BD, se pide a Miguel un evento/columna, no se recalcula aquí.
- Tres vistas y ninguna más: **Escalados** (cola con motivo y evidencia), **Traza** (una decisión: input → hechos → maestro → asiento ERP → reglas → resultado, con eventos, latencias, reintentos, tokens y coste), **Panel** (contadores por etapa/estado, pendientes, ficheros/s, coste acumulado, versión de norma/ERP/maestro).
- Una única acción: botón "Reprocesar impactados" que lanza `albertitos reprocess --impacted` por subprocess y muestra el diff antes/después.
- Tiene que abrir en < 3 s con la BD de 540 ficheros y funcionar sin red (la demo corre en el portátil de Alfonso).
- Se prueba con `dist/albertitos.db`; si no existe, `make db && uv run albertitos ingest` da datos mínimos.
