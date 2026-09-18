# ADR-0008 · SQLite (WAL, SQL a mano) como única fuente de verdad, con el log de eventos dentro

- **Estado:** aceptado
- **Fecha:** 2026-09-19 00:50 · **Dueño:** Miguel · **Módulos:** core/schema.sql, core/db.py, todos los que escriben

## Contexto
Hay 540 facturas. Cinco personas trabajan cada una en su portátil, sin servidor compartido, y la defensa es
en un portátil que puede estar sin red. Varias necesidades dependen de dónde guardemos el estado:
- **Trazabilidad (20 pts):** unir, por fichero, hechos, versiones de maestro y ERP, reglas y eventos.
- **Reprocesado del sábado:** guardar historial de decisiones, no sólo la última.
- **Idempotencia:** la clave es el sha256; repetir una etapa no debe duplicar nada.
- **Lectura concurrente:** la consola lee mientras la CLI escribe, y `extract` escribe desde 4 hilos.
- **Entrega reproducible:** tiene que poder regenerarse desde el estado guardado, no desde memoria.

## Alternativas consideradas
1. **PostgreSQL en Docker.** Concurrencia real y tipos ricos. Se descarta por la infraestructura: montarlo en
   cinco portátiles y en el de la demo cuesta tiempo, y nada de lo que hay con 540 facturas lo necesita.
2. **Un JSONL por etapa** (`hechos.jsonl`, `decisiones.jsonl`). Es sencillo y se ve bien en git. Se
   descarta porque no hay escrituras atómicas entre tablas ni lector concurrente, y los cruces de la traza y
   la idempotencia habría que programarlos a mano. Se conserva como **copia exportable**: 
   `data/fixtures/hechos_caja.jsonl` → `hechos import`.
3. **SQLite detrás de un ORM (SQLAlchemy).** Se descarta: son seis tablas, y el ORM añade una dependencia y
   una curva de aprendizaje para cinco personas, a cambio de nada que necesitemos.
4. **SQLite en modo WAL, esquema idempotente (`schema.sql`) y SQL a mano (elegida).**

## Decisión
`dist/albertitos.db` es la única fuente de verdad. Tiene seis tablas:
- `ficheros` (clave: sha256);
- `hechos` (por sha256 y versión del extractor, con `hechos_hash`);
- `snapshots` (maestro y ERP, versionados);
- `decisiones` (historial con `vigente`, que nunca se borra);
- `eventos` (el log: etapa, estado, intento, latencia, tokens, coste, error);
- `cache_llm`.

Cómo se trabaja con ella:
- El esquema sólo crece: `CREATE ... IF NOT EXISTS`, nunca migraciones destructivas.
- La consola y `bench` abren la BD en sólo lectura.
- Para copias en caliente (ensayos, demo) se usa la API de backup de SQLite, nunca `cp`.

## Consecuencias aceptadas
- **Un solo escritor a la vez.** Una transacción que queda abierta bloquea a los demás hilos, y ya nos pasó:
  en el ciclo 1, `_a_cache` no hacía commit antes de la siguiente llamada de red y daba `database is locked`
  con 4 hilos (PARTE-01, corregido con commit inmediato). La regla es hacer commit por fichero y no retener
  transacciones durante la red.
- **La BD no va a git** (`dist/` está en `.gitignore`). Si se pierde, se reconstruye con `hechos import` del
  JSONL exportado o con un `run` (la caché del LLM se perdería con ella).
- **El log de eventos crece con cada pasada.** Se contiene así: los eventos de estado sólo se escriben si el
  estado cambia (G4), e `ingest` no reabre lo ya registrado (G5). Antes, cada `run` añadía 500 eventos de ingest.
- **Sin migraciones:** para cambiar una columna hay que añadir otra o hacer `make clean && make db`.

## Evidencia
- `dist/albertitos.db` pesa 3,3 MB con 500 ficheros, 500 hechos, 1.000 decisiones y unos 4.000 eventos (18/09 23:05).
- Tiempos medidos: `reprocess --impacted` sobre 500 decisiones en 0,04 s dentro del proceso; `--todo` en 0,43 s.
- `tests/test_db.py::test_decision_nueva_desplaza_a_la_anterior`: la decisión nueva pasa a vigente y la
  anterior se conserva. `tests/test_linaje.py`: ida y vuelta de versiones con el historial intacto.
- Copias en caliente con backup: `dist/ensayo.db` y `dist/demo.db` (G3 y G4) se hicieron sin tocar
  `dist/albertitos.db`, que otra ventana podía estar usando.
- PARTE-01 (Javier): el `database is locked` con 4 hilos y su arreglo.
