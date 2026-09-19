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
- Estado: **A, B y D terminados; C espera a Mónica** (a las 10:41, `git fetch`: 0 de 21 en `monica/norma`, `monica/norma-v3`, `alfonso/plan-defensa` y `main`). Commits: `9f31b5f` (comparador + tests) · `19aaf99` (MUESTRA-CONTRASTE). Sin push. Aquí no va ninguna etiqueta.
- **A · tercera lectura, 21 de 21** (10:28 → 10:38), en `dist/ensayo/h2/` (gitignorado; Mónica, no lo abras): `esperado_muestra_agente.csv` (file_id, esperado_agente, motivo, comprobado, confianza, duda) y `notas.md` (método, criterio, contaminación).
  - Norma: hoja `Norma_Pagos_v3` del Excel (el README del reto no la trae). Todas las hojas leídas, incluida `notas_alberto`.
  - ERP: descarga propia del bridge (`bajar_erp.py`: login, 26 páginas, reintentos ORA-00600): **516 asientos, 0 diferencias con el snapshot `v1`**. Estados del ERP: 507 PENDIENTE y 9 PAGADA. El Excel tiene los 516 pedidos ABIERTO: **ninguna fuente puede expresar «pedido anulado»**.
  - PDFs: texto con PyMuPDF. Las 3 escaneadas, como imagen a 150/300/600 ppp; el IBAN del fax sólo se lee tras desenfocar la trama (`png/fax_iban_blur5.png`). `2026-01-25_P001.pdf`: 38 + 19 líneas sumadas = base 4.808,25, las dos páginas leídas.
  - Duplicados: índice del texto de los 500 PDFs (`caja_texto.json`). Pedido y número de factura buscados para las 21. Límite: las 26 escaneadas que no están en la muestra no tienen texto y no las he mirado.
  - Reparto y confianza (sin decir cuál es cuál): 11 alta · 7 media · 3 baja. Cada una con su duda concreta.
- **Contaminación, declarada al empezar** (bitácora 10:28 y `notas.md`). Antes de recibir el encargo, esta sesión había leído para dar contexto a Javier: la cola de BITACORA, ESTADO-BACKEND, la cabecera de CIFRAS, el índice de ADRs, `esperado_muestra.csv` (vacía), PLAN-MONICA y el guion de la defensa. De ahí sabía la decisión del sistema para **una** de las 21 (etiqueta marcada `CONTAMINADA` en el CSV) y la política NO_PAGAR del sistema (cinco etiquetas marcadas con «contaminación leve»). Durante la parte A no abrí nada de la lista prohibida; de la BD, sólo `snapshots` y el esquema.
- **B · `scripts/comparar_muestra.py`** + `tests/test_comparar_muestra.py` (10 tests, 0,06 s). Con la parte humana abierta no enseña ni el sistema ni al agente, y no abre la BD. Revelar antes exige `--motivo` y lo dice en la primera línea. Pares, discrepancias y tabla, también en `--markdown`. Salida real de hoy: `Muestra humana: abierta · acordado 0/21 · Mónica 0/21 · Alfonso 0/21` y las dos columnas ocultas. Con `--agente dist/ensayo/h2/…` no se cuela ninguna etiqueta: `grep -cE "PAGAR|ESCALAR"` → 0.
- **D · `docs/agentes/MUESTRA-CONTRASTE.md`:** método (qué vio y qué no vio cada lectura), el comando y los pasos para cuando Mónica cierre. Sin etiquetas.
- **Verificado:** `make check` → **417 passed, 2 deselected, 5 xfailed** (los xfail son de H1) en 31 s · `make agentes-check` OK · ruff limpio. BD real y entrega: sólo leídas (`snapshots` en modo `ro`), sin escrituras.
- **Mi fallo:** la entrada «11:20 · H2 · parte A cerrada» de la bitácora lleva la hora mal: fue a las 10:38. Lo corrige la entrada de las 10:42.
- **Necesito de otros:**
  - **Javier:** la regla 3 (sin push) deja estos commits en local; el push es tuyo al cerrar el ciclo. La bitácora tiene entradas mías sin commitear.
  - **Mónica:** avisar en el canal cuando suba su columna. Hasta entonces, no mirar `dist/ensayo/h2/`.
  - **Mónica y el mentor, hoy y sin esperar a la muestra:** la tercera lectura deja abierta una pregunta de política: qué hacer con una factura cuyos datos cuadran con el maestro, el pedido y el ERP, pero que trae un texto que ordena la decisión (escalar, bloquear o no pagar). Afecta a varias de las 21 y a más de la Caja. Es la pregunta 4 de `hitos.md` ampliada; no digo en qué sentido la leo para no contaminar la muestra.
- **Cuando Mónica cierre (C):** `cp dist/ensayo/h2/esperado_muestra_agente.csv data/fixtures/` + commit, `comparar_muestra.py --markdown`, y cada discrepancia con dueño (REGLA → Mónica · DATO → Javier · ETIQUETA → quién), antes de las 17:00. Lo puede hacer cualquier sesión: el método está en MUESTRA-CONTRASTE.md.
