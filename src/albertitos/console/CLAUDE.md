# console/ — Streamlit de sólo lectura · dueño: Alejandro (Cursor)

`app.py` ya abre con tres pestañas (Escalados, Traza, Panel) y un botón de reprocesado. Lee `dist/albertitos.db`
directamente; **no importa `rules/` ni `extract/`**, no recalcula nada.

## Arranque
```
make db && uv run albertitos ingest      # datos mínimos (ficheros + eventos)
make console                             # http://localhost:8501
```
Con `make run` completo verás decisiones y trazas de verdad.

## Qué mejorar (en este orden)
1. **Escalados**: filtro por regla incumplida y por lote; contador arriba; la evidencia del `Motivo` legible sin JSON (tabla clave/valor).
2. **Traza**: pintar el camino input → hechos → maestro → asiento ERP → reglas → resultado como pasos, con latencias de los eventos al lado. Es lo que se enseña 4 minutos en la defensa.
3. **Panel**: ficheros/s (desde eventos `ingest`/`extract`: nº / (max ts − min ts)), coste acumulado, % que tocó el LLM, reintentos ORA-00600, versión de norma/ERP/maestro. Un "antes/después" tras el botón de reprocesado (`pipeline.linaje.diff_decisiones`).
4. Bonus, sólo si el resto está verde y el equipo lo aprueba: calendario de vencimientos (condiciones del maestro: 30/45/60 días) para los PAGAR.

## Reglas del módulo
- Todo dato viene de la BD. Si falta un dato, pídele a Miguel una columna/evento; no lo calcules aquí.
- Abrir en < 3 s con 540 ficheros: `@st.cache_data` en las consultas pesadas, nada de cargar `hechos_json` de todos los ficheros a la vez.
- Sin red: la demo corre en el portátil de Alfonso. Nada de CDN ni componentes externos.
- Cursor no ejecuta los hooks: antes de commitear, `make check` a mano y no toques nada fuera de `console/` sin avisar.
