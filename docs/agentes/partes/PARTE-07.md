# Parte de fin de ciclo · ciclo 7

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2 · 05: E1-E3 · 06: F1-F2).

## G1 · Ningún fichero sin línea: contingencia para el lote 2
- Estado: **A-F terminados y commiteados** (`820a9b6` contingencia + tests + ámbar en la auditoría · `f7abbf5` ADR-0009 y `/lote2` §6). **G listo como parche, sin activar**: la auditoría real sigue ROJA (scan_025) y `package` no tiene `--aceptar-rojo`. **La contingencia no se ha aplicado a la BD real.**
- **A · `scripts/contingencia.py`:** en seco por defecto; lista los ficheros del lote sin decisión vigente con sus intentos de extract (reales/simulados, último error). `--aplicar --motivo "…"` guarda ESCALAR con `hechos_hash="sin-hechos"`, un único Motivo `contingencia.C1` y un evento decide con `"contingencia": true`, en una transacción. Se niega (exit 1): `--lote 1` siempre; caos encendido en esa BD; fichero sin ningún intento real (los `caos:` y `LLM-CIRCUIT-OPEN`/`LLM-PRESUPUESTO`/`LLM-CONFIG` no cuentan), y dice qué lanzar antes. Sin `--motivo`, exit 2. Cada paso tarda 0,15-0,17 s.
- **B · Tests, uno o más por condición de Miguel** (12 en `tests/test_contingencia.py` con los PDF reales de `data/fixtures/lote2_sim`, sin red; +1 en `test_auditoria.py`): C1 `test_c1_sin_motivo_se_niega`, `test_c1_con_el_caos_encendido_se_niega`, `test_c1_sin_ningun_intento_real_no_se_toca` · C2 `test_c2_solo_escalar_y_solo_a_los_que_no_tienen_decision`, `test_c2_en_el_lote_1_se_niega_siempre` · C3 `test_c3_se_revierte_con_reprocess_impacted`, `test_c3_se_revierte_con_run_entero` · C4 `test_c4_package_pasa_de_negarse_a_apto_y_la_linea_lo_dice`, `test_c4_el_evento_decide_lo_dice`, `test_contingencia_es_ambar_y_con_hechos_sin_reprocesar_pasa_a_rojo`.
- **C · Auditoría:** ÁMBAR «Decisiones de contingencia (ESCALAR sin hechos, ADR-0009)». Si la contingencia ya tiene hechos y nadie reprocesa: ROJO en `decision_vieja` («contingencia (ADR-0009) y ya hay hechos»).
- **D · `/lote2`:** §5, mientras `package` no audite solo, `make publicar` en seco o `scripts/auditoria_entrega.py` son obligatorios antes de `/entrega`. §6, último recurso: reintentar → en seco → aplicar → auditoría → `make publicar`, con C1-C4 tal cual.
- **E · ADR-0009:** alternativas, decisión con C1-C4, consecuencias y evidencia. **Su estado dice «propuesto»**: lo escribí a las 09:08 sin ver `902ebfe` (09:02), donde Javier lo da por aceptado. Pendiente: «aceptado» en el estado, en la fila de `docs/adr/README.md` y en la última frase de `/lote2` §6. Intenté el cambio y el control de permisos lo denegó; espera la confirmación de Javier.
- **F · Ensayo de punta a punta** (copia de la BD real en `dist/ensayo/g1/ensayo.db`, lote 2 simulado; log entero en `dist/ensayo/g1/ensayo.log`):
```text
## 03 extract (proveedor caído, simulado)   (0.48 s, exit 0)
extract: 8/10 ok · 2 pendientes · 0 pdf ilegibles · métodos {'plantilla': 8} · errores {'LLM-DOWN': 2} · …
## 05 package: se niega   (0.17 s, exit 1)
  ✗ falta 'L2-scan_002.pdf'
  ✗ falta 'L2-scan_004.pdf'
## 07 contingencia --aplicar con el caos encendido   (0.15 s, exit 1)
ROJO  el caos está encendido en esta BD (llm_down): los fallos son simulados. Apágalo (…), reintenta el extract y vuelve.
## 09 extract con el proveedor caído de verdad (puerto cerrado)   (7.49 s, exit 0)
extract: 0/2 ok · 2 pendientes · 0 pdf ilegibles · métodos {} · errores {'LLM-RED': 2} · …
## 10 contingencia en seco   (0.15 s, exit 1)
     intentos de extract: 2 · reales 1 · simulados 1 · … · LLM-DOWN (caos)×1, LLM-RED×1
## 11 contingencia --aplicar   (0.16 s, exit 0)
OK    2 decisiones ESCALAR de contingencia (contingencia.C1) · norma v3 · maestro 80911e429c6c · erp v1 · corte 2026-09-18
## 12 contingencia otra vez (idempotente)   (0.17 s, exit 0)
OK    lote 2: ningún fichero sin decisión vigente. Nada que aplicar.
## 14 package: APTO   (0.17 s, exit 0)
APTO · dist/ensayo/g1/entrega/outcomes_lote2.jsonl · lote 2 · 10 líneas · {'ESCALAR': 10}
  {"file_id":"L2-scan_002.pdf","result":"ESCALAR","motivo":"sin hechos validados a la hora de entregar (LLM-RED): lo revisa una persona","norma_version":"v3","regla":"contingencia.C1"}
## 15 extract de los pendientes   (0.56 s, exit 0)
extract: 2/2 ok · 0 pendientes · 0 pdf ilegibles · métodos {'cache': 2} · …
## 16 reprocess --impacted: la contingencia se deshace   (0.23 s, exit 0)
4 de 510 recalculadas · 2 cambian · 0.02 s
```
  - Paso 13 (auditoría): ÁMBAR contingencia · 2. El único ROJO es scan_025, heredado.
  - Tras el 16, las dos contingencias quedan con `vigente=0` y la vigente es de la norma (R6); en el 18, la auditoría da `OK 0` en contingencia.
  - Los «2 cambian» son `scan_002.pdf` y `scan_004.pdf` del lote 1 (PAGAR → ESCALAR, `duplicados: +4`): los `L2-*` son copias suyas. Efecto del simulado, no de la contingencia.
  - BD real `bb8128d2c656` y `dist/entrega/outcomes.jsonl` `5ec17aaa5045`: el mismo sha256 antes y después.
- **G · La auditoría dentro de `package` (parche, sin activar):**
  - `src/albertitos/pipeline/auditoria.py` (nuevo), con la firma de `package.Auditor`: `auditar(conn, {lote: dir})`. `Informe.ok` = ningún ROJO; `Informe.rojos` = `{comprobación: [file_id]}`; `Informe.texto()`. Sin `entrega` no compara con los JSONL viejos (`package` la llama antes de sustituirlos). `scripts/auditoria_entrega.py` queda como su CLI: misma salida, mismo JSON y mismos códigos (0/1/2).
  - `tests/test_auditoria.py`, +4 de la puerta: encuentra el módulo; en verde entrega con `"auditoria": "verde"`; con un pago doble se niega, no pisa la entrega anterior y deja `AUDITORIA-ROJA` con los dos file_id; la contingencia en ámbar no bloquea. El test de contrato de Miguel deja de saltarse y pasa.
  - Parche: `dist/ensayo/g1/puerta-auditoria.patch` (sha256 `56e357574aa5`, 3 ficheros). `git apply --check` OK sobre `67451fe`. Aplicado en un worktree limpio sobre `67451fe`: `make check` → **394 passed, 2 deselected**.
  - Sobre una copia de la BD real (`dist/ensayo/g1/puerta.db`), `package` con la puerta: `VEREDICTO: ROJO · 1 comprobación(es) en rojo: NO entregar` en 0,13 s. Evento emit/error `AUDITORIA-ROJA` con `"rojos": {"evidencia_falsa": ["scan_025.pdf"]}` y emit/pendiente de scan_025.
  - Por qué no se activa: en cuanto existe `pipeline/auditoria.py`, `package` y `run` auditan solos. Con la BD real en ROJO, `make publicar` se pararía en su propio `package`, antes de su auditoría y de su `--aceptar-rojo`. `demo_caos.py` (llama a `run`) también se pararía.
  - Activarlo, cuando la auditoría real salga verde o Miguel añada `--aceptar-rojo`: `git apply dist/ensayo/g1/puerta-auditoria.patch && make check`, y commit de esos 3 ficheros.
- Verificado al cerrar (árbol compartido, `67451fe`): `make check` → **389 passed, 1 skipped, 2 deselected** (el skipped es el test de contrato: sin módulo, se salta). `make agentes-check` → `OK: cada fichero tiene un único dueño`.
- Necesito de otros:
  - **Javier:** confirmar el paso de ADR-0009 a «aceptado». Y que el evento de fallo de extract diga qué modelo falló y si se probó el respaldo (PIDO de las 09:05).
  - **Miguel:** `--aceptar-rojo "<motivo>"` en `package` y `run` (parche en la bitácora, 09:05).
  - **Mónica:** la respuesta A (`DOCUMENTO_SUPERPUESTO`) desbloquea scan_025, la auditoría verde y la puerta.
- Riesgo: si alguien aplica el parche con la BD real en ROJO, `package`, `run`, `make publicar` y la demo de caos se niegan hasta arreglar scan_025. Es lo que se pide a la puerta, pero sin salida de excepción.

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
