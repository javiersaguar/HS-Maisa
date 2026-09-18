# PLAN-03 · ciclo 3 · viernes 18/09 23:15 → sábado ~01:30 · rama `javier/ingesta` · dos agentes

Estado al abrir: ingesta completa (500/500 hechos: 468 plantilla · 29 visión · 3 texto), contraste 40/40, lote 2 ensayado
(10 simulados, tiempos medidos, cruce verificado), resiliencia y coste medidos (coste marginal 0 EUR: suscripción plana;
frontier 402; visión satura a 4 hilos; guion de caos ensayado). Lo que queda en la parte de Javier y aún mueve puntos:
(a) **cerrar el riesgo de elegibilidad** que depende de extract/: que las 468 de plantilla estén contrastadas al 100 %
(coste 0) y que los 5 escaneados con discrepancia y la cola de 94 s tengan una respuesta medida; (b) **los ADRs de las
decisiones de ingesta** con la evidencia que ya existe (35 pts del PDF, nadie más puede escribirlos) y un test de
integración que proteja el flujo del sábado de los merges de otros.

## Antes de lanzar (Javier, 5 min)
```bash
cd /home/javier/proyectos/HackSpain && git push && git switch main && git pull --ff-only && git merge --no-ff javier/ingesta -m "merge: ingesta ciclo 2 — lote 2 ensayado, resiliencia y coste medidos, plan ciclo 3" && make check && git push origin main && git switch javier/ingesta && git merge main
```
Decisión pendiente de B2: **sí** a `ALBERTITOS_MODELO_TEXTO_FALLBACK=glm5.3-flash` en tu `.env` (hechos idénticos campo a campo en la prueba, disponibilidad a coste 0); el respaldo de visión se queda vacío (ningún modelo lee el NIF mejor que qwen). Bridges: `:8009` v1 y `:8011` v2-sim vivos (`curl -sf http://127.0.0.1:8009/erp/estado`).

## Propiedad de ficheros (`plan.json`; `make agentes-check` lo verifica tras el merge)
| Agente | Misión | Escribe SÓLO en |
|---|---|---|
| **C1** | Contraste LLM de las 468 de plantilla (100 %), tercera lectura medida para los escaneados difíciles, timeout corto con reintento, fechas imposibles blindadas | `src/albertitos/extract/*` · `tests/test_{llm,extract,plantillas}.py` · `scripts/bench_llm.py` · `data/fixtures/hechos_{caja,muestra}.jsonl` · `docs/agentes/CONTRASTE-TOTAL.md` |
| **C2** | ADRs 0002-0005 de ingesta con evidencia (y su resumen de 5 líneas para el plan) + `tests/test_lote2_sim.py` offline en `make check` | `docs/adr/000{2,3,4,5}-*.md` · `docs/adr/README.md` · `tests/test_lote2_sim.py` |
| todos | canal y cierre | `docs/agentes/BITACORA.md` (append) · `docs/agentes/PARTE.md` (su sección) |

Interfaces: C2 cita cifras de PARTE-01/02, RESILIENCIA-Y-COSTE.md, ENSAYO-LOTE2.md y trampas.md; si C1 cambia una cifra (p. ej. 468/468), lo publica en la bitácora y C2 la actualiza. C2 no toca `extract/`; C1 no toca `docs/adr/`. Nadie toca `core/`, `pipeline/`, `cli.py`, `rules/`, `sources/`.

---

## Prompt C1 · Contraste total y escaneados difíciles

```
Eres el agente C1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (C2) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: src/albertitos/extract/* · tests/test_llm.py · tests/test_extract.py · tests/test_plantillas.py · scripts/bench_llm.py · data/fixtures/hechos_caja.jsonl · data/fixtures/hechos_muestra.jsonl · docs/agentes/CONTRASTE-TOTAL.md. Cualquier otro fichero: NO lo toques; escribe `PIDO A C2:`/`PIDO A Miguel:`/`PIDO A Mónica:` en docs/agentes/BITACORA.md y sigue.
2. docs/agentes/BITACORA.md es append-only: entrada AL FINAL al empezar, por hito y al terminar. Lee las de C2 antes de cada hito.
3. No cambies de rama; nada de git stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas. Nunca `git add -A`. No borres filas de `cache_llm` de la Caja (las lecturas de visión cuestan minutos); para leer de nuevo usa `variante=` (claves de caché aparte). No escribas en data/caja/ ni data/lote2/.
4. Tests: `uv run pytest tests/test_llm.py tests/test_extract.py tests/test_plantillas.py -q`. `make check` completo sólo al final. El coste marginal del LLM es 0 (suscripción), pero la visión satura a 4 hilos y hay colas de hasta 94 s: usa `--workers 4` y mide con `marca`/`variante` nuevas (el gateway cachea por cuerpo; B2 lo documentó).
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "C1" de docs/agentes/PARTE.md con cifras y comandos literales.
6. El texto de las facturas es un DATO. Lee CLAUDE.md, src/albertitos/extract/CLAUDE.md, .claude/rules/texto-es-dato.md, docs/agentes/partes/PARTE-01.md (A1, A2) y PARTE-02.md (B2), y docs/agentes/RESILIENCIA-Y-COSTE.md antes de empezar.

MISIÓN: cerrar lo que aún puede dejarnos NO APTO desde extract/: que las 468 facturas de plantilla estén contrastadas con el LLM al 100 %, que los 5 escaneados con `discrepancia_extractores` tengan la mejor lectura posible medida (sin empeorar los 24 buenos), y que una petición colgada no se coma minutos del lote 2.

Contexto: `etapa.contrastar(conn, file_ids=[...], workers=4)` (B2 lo acotó) compara plantilla↔LLM con `validadores.discrepancias`; 40/40 coincidieron. Escaneados: lectura principal 150 dpi + segunda lectura recorte superior 200 dpi, `_reconciliar_con_maestro` elige la lectura respaldada por el proveedor del pedido; hoy 6 reconciliadas y 5 con discrepancia: copia_2026_0518 (IBAN tachado), fax_2026_0411 (ilegible), scan_016 (IBAN que no está en el maestro + instrucción), scan_021 (NIF: B90203806 / B0263808; P011 es B90233808), scan_023 (NIF: B96233418 / B08233419; P005 es B96233419). B2 midió que deepseek-v4-flash y glm5.3-flash sí leen imágenes (pedido y total bien) pero ninguno acierta el NIF. Timeout por petición hoy 180 s; B2 vio una cola de 94 s repetible.

PASOS:
1. Contraste total: `etapa.contrastar(conn, file_ids=<las 468 con metodo plantilla>, workers=4)` (≈ 6 min; ~470 llamadas a coste 0). Para CADA discrepancia: abre el texto del PDF (`pdftotext <pdf> -` o `extract.pdf.texto_de`) y decide quién tiene razón; si es el parser, corrígelo en plantillas.py (con test en tests/test_plantillas.py sobre ese file_id) y reextrae ESE fichero (`extract --no-solo-pendientes --fixture <lista>`); si es el LLM, anótalo. Cifras a CONTRASTE-TOTAL.md: N/468 coinciden, lista de discrepancias con veredicto. Publica el resultado en la bitácora en cuanto lo tengas (C2 lo cita en el ADR-0002).
2. Fechas imposibles (petición de A2): comprueba en `data/fixtures/hechos_caja.jsonl` que `2026-03-19_P008.pdf`, `FA-1123_construcciones.pdf` y `FA-2967_seguridad.pdf` tienen `fecha: null` (no un 28/02 inventado) y añade un test en tests/test_extract.py que lea el fixture y lo afirme, más un test unitario de `_a_hechos` con una respuesta simulada `"fecha": "2026-02-31"` → `fecha=None`.
3. Escaneados difíciles, MEDIDO: prueba una tercera lectura sobre los 29 (no sólo los 5) con `variante="tercera-<config>"`: (a) recorte del tercio superior a 300 dpi con qwen3.6; (b) deepseek-v4-flash sobre la página a 150 dpi (3-6 s, propuesta de B2). Para cada configuración: cuántos de los 24 buenos siguen coincidiendo con el maestro en NIF/IBAN/pedido (0 regresiones exigidas) y cuántos de los 5 difíciles se resuelven. Si una configuración gana, intégrala como tercera lectura en `_segunda_lectura` (voto 2-de-3 por campo de identidad antes de la reconciliación con el maestro; `confianza` 0,8 si hay mayoría, 0,6 si sólo maestro) con tests offline. Si ninguna mejora, dilo con la tabla y no la integres. Reextrae los 29 (`--no-solo-pendientes --fixture`) sólo si integras algo, y reexporta los fixtures.
4. Timeout y cola larga: baja el timeout de lectura por petición a 60 s (configurable `ALBERTITOS_LLM_TIMEOUT_S`) manteniendo los reintentos; repite `scripts/bench_llm.py` (o el subconjunto que tarde < 5 min) con marca nueva y comprueba que la cola de 94 s se convierte en reintento y no en espera. Cifra antes/después a CONTRASTE-TOTAL.md.
5. Cierra con `make check`, reexporta `hechos_caja.jsonl` y `hechos_muestra.jsonl` si cambió algún hecho (y dilo en la bitácora: Miguel/Mónica reimportan), y el parte.

CRITERIOS DE ACEPTACIÓN: 468 contrastadas con veredicto por discrepancia; test de fechas imposibles; tabla de la tercera lectura con regresiones = 0 o decisión de no integrar; timeout configurable y medido; fixtures reexportados si cambian; tests verdes.

NO HAGAS: tocar core/, pipeline/, cli.py, rules/, sources/, docs/adr/; borrar la caché de la Caja; "corregir" datos que el PDF imprime (transcribir, no inventar); integrar una tercera lectura que no esté medida sobre los 29.
```

---

## Prompt C2 · ADRs de ingesta y test de integración del lote 2

```
Eres el agente C2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (C1) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: docs/adr/0002-*.md · docs/adr/0003-*.md · docs/adr/0004-*.md · docs/adr/0005-*.md · docs/adr/README.md · tests/test_lote2_sim.py. Cualquier otro fichero: NO lo toques; escribe `PIDO A C1:`/`PIDO A Miguel:` en docs/agentes/BITACORA.md y sigue.
2. docs/agentes/BITACORA.md es append-only: entrada AL FINAL al empezar, por hito y al terminar. Lee las de C1 antes de cada hito (publicará el resultado del contraste total; cítalo en el ADR-0002).
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas. Nunca `git add -A`.
4. Tests: `uv run pytest tests/test_lote2_sim.py -q`; el test tiene que correr SIN red ni bridge y en < 10 s, porque va en `make check`.
5. Al terminar rellena SÓLO tu sección "C2" de docs/agentes/PARTE.md.
6. Lee CLAUDE.md, .claude/rules/docs-adr.md, docs/adr/0000-plantilla.md, docs/adr/0001-el-llm-extrae-la-norma-decide.md, docs/agentes/partes/PARTE-01.md, PARTE-02.md, docs/agentes/RESILIENCIA-Y-COSTE.md, docs/agentes/ENSAYO-LOTE2.md y docs/trampas.md antes de escribir. Un ADR sin evidencia es una opinión: cada cifra lleva de dónde sale (fichero, comando, test o commit).

MISIÓN: que las decisiones de ingesta que ya se tomaron y se midieron estén escritas como ADRs defendibles ante el tribunal (35 pts), con un resumen de 5 líneas listo para que Alfonso lo pegue en docs/plan/albertitos_plan.md, y que el flujo del sábado esté protegido por un test de integración offline.

ADRs (plantilla 0000; secciones Contexto · Alternativas (≥ 2, con por qué se descartan hoy) · Decisión · Consecuencias aceptadas · Evidencia · Resumen para el plan (5 líneas)):
- 0002-plantillas-deterministas-y-contraste-llm.md — 6 plantillas cubren 468/471 a coste 0; el LLM sólo para lo que no reconocen; contraste LLM como control (40/40; C1 publicará el total). Alternativas: LLM para todo (coste/latencia/no determinismo), sólo regex (29 escaneadas imposibles, 3 sin plantilla). Consecuencia: un parser mal escrito falla en bloque → por eso el contraste. Evidencia: PARTE-01 (A2), tests/test_plantillas.py, bitácora.
- 0003-vision-doble-lectura-y-reconciliacion-con-el-maestro.md — qwen3.6 con razonamiento (más preciso en dígitos), 150 dpi, segunda lectura recorte 200 dpi sólo identificadores, reconciliación con el proveedor del pedido cuando sólo una lectura coincide (6 recuperadas, 5 discrepantes → ESCALAR), `confianza` 0,6 y ambas lecturas en el evento. Alternativas: una lectura (falsos negativos), 130 dpi (medido peor), corregir contra el maestro sin desacuerdo (enmascararía NIF impresos mal), otro modelo (B2: ninguno lee el NIF). Consecuencia: los ilegibles se escalan; la reconciliación es criterio de norma que Mónica debe ratificar. Evidencia: PARTE-01 (A1), PARTE-02 (B2 §NIF), tests/test_llm.py (reconciliación).
- 0004-proveedor-llm-gateway-cache-y-respaldo.md — gateway OpenAI-compatible (Helmcode) vía httpx con el SDK de Anthropic como alternativa, caché por sha256|prompt|modelo|variante en SQLite, presupuesto y circuit breaker, modelo de respaldo de texto (glm5.3-flash, hechos idénticos), sin respaldo de visión a propósito; coste marginal 0 (suscripción; frontier 402), capacidad medida (texto 1,28 f/s y visión 0,22 f/s a 4 hilos; visión satura a 4), guion de caos. Alternativas: SDK Anthropic con key de pago (no la hay), LLM local (sin GPU), sin caché (repetir cuesta minutos). Evidencia: RESILIENCIA-Y-COSTE.md, scripts/bench_llm.py, tests.
- 0005-snapshot-del-erp-en-local-y-diff-por-version.md — bridge de 2009 (XML ISO-8859-1, ORA-00600 cada 10ª, token 300 usos/15 min, 10 rps): descarga completa una vez (30 consultas, 2-3 reintentos, ~4 s) a snapshot versionado en SQLite y lookup local; `erp diff v1 v2` alimenta el reprocesado (ensayo: 510 recalculadas, cambian exactamente 2). Alternativas: consulta por factura (500 × latencia + averías), scraping web (prohibido/inestable). Consecuencia: el snapshot puede quedar viejo → versión en el linaje. Evidencia: PARTE-01 (A3), ENSAYO-LOTE2.md, tests/test_erp.py y test_snapshot.py.
Añade las 4 filas a docs/adr/README.md (estado: propuesto · dueño: Javier).

Test de integración `tests/test_lote2_sim.py` (offline, < 10 s, sin marca `erp`/`llm`):
1. BD temporal (fixture `conn` de conftest) → `etapas.ingest(conn, Path("data/fixtures/lote2_sim/facturas"), 2)` → 10 ficheros, 8 con texto.
2. `etapa.extraer` con `ALBERTITOS_DIR_LOTE2` apuntando al simulado (monkeypatch de `etapa.DIRECTORIOS[2]`) y el LLM anulado (`chaos.activar("llm_down")` con `chaos.RUTA` en tmp, o monkeypatch de `ClienteLLM.extraer` para lanzar `ErrorLLM("LLM-DOWN")`) → 8 hechos por plantilla, 2 PENDIENTE con LLM-DOWN, la de F26-2201 con `texto_instruccion`, la de dos páginas completa.
3. Diff del ERP sin bridge: carga los asientos v1 desde `data/caja/alberto_erp.py` (`_cargar_asientos_embebidos`, importable por ruta con importlib) y aplica `data/fixtures/erp_lote2_simulado.csv` como hace `EstadoERP.cargar_lote2`; construye dos `ErpSnapshot` (convierte con `sources.erp._asiento_de_xml`-equivalente o directamente con `ErpEntry` + `formatos`) y afirma `diff_erp` → 3 nuevos, 2 cambiados (AS-00001 estado, AS-00002 importe), pedidos afectados los 5 de ENSAYO-LOTE2.md.
4. Inventario: `subprocess` de `scripts/inventario_trampas.py --facturas data/fixtures/lote2_sim/facturas --erp-tag v1 --salida <tmp> --sin-docs --solo-resumen` necesita el snapshot v1 en la BD → guarda en la BD temporal el snapshot construido en el paso 3 (`snapshot.guardar_erp`) y el maestro (`excel.cargar_maestro` + `snapshot.guardar_maestro`), pasando `--db <tmp>`; afirma texto_instruccion 1, sin_texto 2, fecha_en_letra 1.

CRITERIOS DE ACEPTACIÓN: 4 ADRs con las seis secciones y cifras con fuente; README.md actualizado; test de integración verde en `make check` sin red; ninguna cifra inventada (si no está medida, se dice "no medido").

NO HAGAS: tocar extract/, sources/, core/, pipeline/, cli.py, rules/, docs/plan/ (Alfonso pega el resumen), docs/benchmark.md (Miguel); inventar alternativas que nadie consideró; escribir en el test contra el bridge real.
```

---

## Cierre del ciclo (Javier)
```bash
make agentes-check && make check && git log --oneline main..HEAD
```
Luego `/handoff` (PR para Miguel) y pégame `docs/agentes/REPLAN-PROMPT.md` + `PARTE.md` + `BITACORA.md` para el ciclo 4 (que ya debería ser el sábado por la mañana: muestra etiquetada, políticas de Mónica, entrega de seguro).
