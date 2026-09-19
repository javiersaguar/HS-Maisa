# Parte de fin de ciclo · ciclo 8

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2 · 05: E1-E3 · 06: F1-F2 · 07: G1-G2).

## H1 · PDF idéntico con otro nombre: el caso entero, listo para Miguel
- Estado: **terminado**. Commits: `e9f4ca1` (fixture + tests) · `2fb5f76` (verificador) · `47c12d0` (documento para Miguel y skill /lote2). Sin push.
- **Reproducido** (`tests/test_identicos.py`, sin red; ERP v1 real y maestro real): hoy el lote 1 pierde su línea y `package` se niega. R1-R4 con **xfail estricto** (5); en cuanto entre el parche pasan a XPASS, que falla, y hay que quitar la marca. Controles que pasan hoy: el fixture es lo que dice, el renombrado dentro de un lote sigue funcionando, y sin copias no cambia nada.
- **Parche** `dist/ensayo/h1/identicos.patch` (sha256 `ede37b97d8fa`, 9 ficheros, +165 −46):
  - tabla aditiva `identidades` (ESQUEMA_VERSION 3);
  - en `ingest`, copia ≠ renombrado: es copia si el nombre original sigue existiendo;
  - `marcar_duplicados` cuenta las identidades → todas ESCALAR;
  - `decisiones_vigentes`, la auditoría, los eventos de `package` y `trace` devuelven cada nombre;
  - las BD de antes del parche se leen en solo lectura sin la tabla.
  - Detalle en `docs/agentes/P0-1-IDENTICOS.md`.
- **Verificado:**
  - Parche sobre un worktree limpio desde el HEAD `2fb5f76`: `make check` → **412 passed**.
  - R5 sobre una copia de la BD real: `500 de 500 recalculadas · 0 cambian`, `package` con auditoría → **438/53/9**, `outcomes.jsonl` **`1ec4be206089`**.
  - De punta a punta con la CLI (`dist/ensayo/h1/e2e.log`): `ingest` 4 nombres («copia exacta de 2026-01-08_P001.pdf (lote 1)») → `reprocess --impacted` con `duplicados: +5` → `package` **APTO lote 1 (500) y lote 2 (4, todas ESCALAR)** → `validate` APTO/APTO → `trace L2I-reenvio_…` con `mismo_pdf_que: ["2026-01-08_P001.pdf"]`.
  - `git apply --check` limpio sobre `47c12d0`.
- **Verificador:** `pipeline_admite_copias()` detecta `db.guardar_identidad`. Sin el parche da ROJO (con la ruta del documento); con él, AVISO. Los tests fijan los dos estados.
- **Hallazgos:**
  1. Dos copias en la **misma pasada** de ingest se renombraban entre sí, porque `conocidos` se calculaba una sola vez. Corregido en el parche.
  2. Las lecturas en **solo lectura** de una BD sin la tabla habrían dado «no such table» y habrían parado `make publicar`. Resuelto con `tiene_identidades` y un test.
  3. En el ensayo, el lote 1 cambia en 3 facturas: solo 1 por la copia exacta. Las otras 2 cambian porque el fixture reutiliza PDFs del lote 2 simulado, que repiten pedidos del lote 1; es el detector de siempre, no el P0-1.
- **BD real y entrega:** `dist/albertitos.db` `c66d00e45be3` → `c66d00e45be3`; `dist/entrega/outcomes.jsonl` `1ec4be206089` → `1ec4be206089`. Worktrees quitados.
- **Necesito de otros:**
  - Miguel: aplicar el parche antes de las 17:00 y quitar los xfail (el parche ya los quita).
  - Mónica: confirmar R3, que con el parche el original del lote 1 también sale ESCALAR.

## H2 · Tercera lectura de la muestra, a ciegas, y el contraste listo
_(pendiente; sin etiquetas ni resultados de la muestra hasta que Mónica suba las suyas)_
