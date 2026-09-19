# Parte de fin de ciclo · ciclo 7

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2 · 05: E1-E3 · 06: F1-F2).

## G1 · Ningún fichero sin línea: contingencia para el lote 2
_(pendiente)_

## G2 · Lo que el tribunal pregunta: de dónde sale cada reintento y cada cifra
- Estado: **terminado** (el agente se quedó a medias con todo sin commitear; lo cerró Javier: revisión, tests, un añadido a cifras_check y los commits).
- Commits: `645ecd5` ERP-NO-RESPONDE y enlace de eventos por descarga · `5c55a63` resumen_erp · `0860459` CIFRAS.md + cifras_check · `67451fe` sources/CLAUDE.md, RESILIENCIA y ESCALA remiten a CIFRAS.
- **A · `erp pull` sin ERP:** `ErrorERP("ERP-NO-RESPONDE", …)` con la URL, `make erp`/`make erp-fast`, `ALBERTITOS_ERP_URL` y el aviso de que el snapshot anterior sigue sirviendo. Con los valores por defecto: 8 consultas, 7 reintentos, **5,619 s** (no es instantáneo: se conserva el backoff). Test con 2 intentos, < 2 s. **El traceback sigue** hasta que Miguel aplique en `cli.py` el bloque de la bitácora («ERP medido»).
- **B · `resumen_erp(conn, version)`** sobre la BD real:
  `v1 · 2026-09-18T19:55:36Z · 516 asientos · 31 consultas · 3 reintentos · {"ORA-00600": 3} · 35 ms HTTP · atribución inferida_por_ventana` (eventos 3213-3243). `v2-sim`: 519 asientos, 30 consultas, 2 reintentos. La latencia es la suma HTTP, sin el ritmo ni el backoff. Las descargas nuevas quedan enlazadas de forma exacta (`atribucion: explicita`).
- **C · `docs/CIFRAS.md`:** 25 cifras con qué miden, fuente, comando (C1-C7), fecha y límites. Las que no se reproducen hoy con un comando lo dicen (contraste 468/468, linaje 40/500, benchmark del i5).
- **D · `scripts/cifras_check.py`:** busca las formas obsoletas del catálogo en el plan, el guion, KIT-DEFENSA y el benchmark; sale 1 si encuentra alguna y sólo informa. Menciones históricas declarables (fichero + trozo literal). Salida hoy:
```text
docs/plan/albertitos_plan.md:98: reprocesar 500 decisiones, 0,04 s → 2 de 500 en 0,04 s; total 500 depende del banco (7,06 s en ensayo de Javier) · fuente: docs/benchmark.md, Cifras; docs/agentes/ENSAYO-REPROCESADO.md, Qué salió
1 coincidencia(s).
```
  El 0,22 del plan ya lo corrigió Miguel; el de `benchmark.md:44` es la frase histórica, declarada.
- Verificado: `make check` → **389 passed, 1 skipped**; `cifras_check` 8 tests; BD real y `outcomes.jsonl` (`5ec17aaa5045`) sin cambios.
- Necesito de otros: **Miguel**: captura de ErrorERP en `erp pull` y la línea de `resumen_erp` en `trace` (parches en la bitácora). **Alfonso**: plan:98 (texto propuesto en la bitácora, 09:40) y enseñar los reintentos con C6.
- Riesgo: si en la defensa se enseñan los reintentos con `status`, salen 122 eventos y 11 reintentos que son **de todas las descargas**, no de v1. Hay que usar C6 o la línea de `trace` cuando exista.
