# Reparto del backend (viernes 21:00 → domingo 02:00)

Tres personas, cada una con **directorios propios** (nadie edita los de otro; si hace falta, se pide en el canal)
y con tareas escritas para que las ejecute un agente. Frontend (`console/`) y el PDF del plan siguen con
Alejandro y Alfonso (ver `CLAUDE.md`). Miguel mergea.

## Propiedad de ficheros

| Persona | Escribe SÓLO en | Lee todo lo demás |
|---|---|---|
| **Javier** | `src/albertitos/sources/**` · `src/albertitos/extract/**` · `tests/test_{erp,excel,snapshot,extract,plantillas,llm}.py` · `scripts/inventario_trampas.py` · `docs/trampas.md` · `data/fixtures/{hechos_muestra.jsonl,anomalias.csv,erp_lote2_simulado.csv}` · `docs/agentes/**` | |
| **Mónica** | `src/albertitos/rules/**` · `tests/test_rules*.py` · `data/fixtures/esperado_muestra.csv` · `docs/adr/*frontera*` · `docs/adr/*norma-v4*` · `docs/adr/*duplicados*` | |
| **Miguel** | `src/albertitos/core/**` · `src/albertitos/pipeline/**` · `src/albertitos/cli.py` · `tests/test_{db,linaje,validar,pipeline,contracts}.py` · `Makefile` · `.github/**` · `docs/adr/0001*`, `docs/adr/*formato*`, `docs/adr/*sqlite*`, `docs/adr/*linaje*` · `docs/entregas.log` · `docs/benchmark.md` | |

Interfaces ya congeladas en `core/contracts.py` + dos nuevas de hoy:
- `extract.etapa.extraer(conn, *, solo_pendientes, fixture, workers) -> ResumenExtraccion` (Javier implementa; pipeline/cli ya la llaman).
- `albertitos hechos export/import <jsonl>`: hechos reales sin LLM para Mónica y Miguel. Javier publica `data/fixtures/hechos_muestra.jsonl` en cuanto tenga las 21 de la muestra.

## Javier — ingesta de datos (sources/ + extract/)
Plan de 3 agentes en paralelo: `docs/agentes/PLAN-01.md`. Entregables:

| Hora | Entregable | Cómo se comprueba |
|---|---|---|
| Vie 23:30 | `hechos_muestra.jsonl` (21 facturas por LLM real, revisadas 5 a mano) · `trampas.md` v2 con cifras · `anomalias.csv` | `uv run albertitos hechos import data/fixtures/hechos_muestra.jsonl` carga 21 |
| Sáb 02:00 | 500/500 con hechos o PENDIENTE con `error_codigo` (repliegue 1 de `docs/hitos.md`) | `uv run albertitos status` → 0 sin hechos |
| Sáb 12:00 | Plantillas para las 3-5 mayores, con cobertura medida (`N de 471`) · caos ensayado | `uv run albertitos bench` y bitácora |
| Sáb 18:30 | Lote 2 ingerido, `erp pull --tag v2`, `erp diff v1 v2` | `/lote2` pasos 1-2 |

## Mónica — la norma como código (rules/)
Tareas para agente (cada una = un fichero o dos, sin pisarse con Javier ni Miguel):

| # | Tarea | Ficheros | Aceptación |
|---|---|---|---|
| M1 | **Muestra etiquetada.** Abrir los 21 PDFs de `data/fixtures/muestra.txt` (con `pdftotext` o el visor) y rellenar `esperado_monica` en `esperado_muestra.csv` con PAGAR/NO_PAGAR/ESCALAR y motivo, aplicando la Norma v3 a mano cruzando Excel y ERP (`make erp-fast` + `make -C data/caja erp-login`). Alfonso rellena `esperado_alfonso` por su cuenta; donde discrepen → `pregunta_mentor` | `data/fixtures/esperado_muestra.csv` | 21 filas con `acordado` relleno antes del sáb 10:00 |
| M2 | **Validar `norma_v3.py` contra la muestra.** Cuando exista `hechos_muestra.jsonl`: `albertitos hechos import` + `maestro` + `erp pull` + `decide` + comparar `outcomes` con `acordado`. Cada discrepancia: ¿regla mal, hecho mal (→ Javier) o etiqueta mal? Ajustar reglas SÓLO si la norma literal lo respalda | `src/albertitos/rules/norma_v3.py`, `tests/test_rules.py` | 21/21 coinciden o cada discrepancia tiene dueño y anotación |
| M3 | **Políticas abiertas** (con mentor, ADR cada una): frontera NO_PAGAR/ESCALAR · dos PDFs del mismo pedido (¿el primero PAGAR y el resto ESCALAR? ¿todos ESCALAR?) · 20 pedidos sin NIF en el Excel (¿R2 por `ProveedorID`?) · IVA ≠ 21 % (nota de Sonia) · "pedido anulado" según el PDF pero ABIERTO en Excel/ERP. Implementar lo decidido en `norma_v3.py` con tests de frontera | `docs/adr/000N-frontera-no-pagar-escalar.md`, `docs/adr/000N-duplicados.md`, `norma_v3.py`, `test_rules.py` | ADRs con respuesta del mentor citada (hora) y test por política |
| M4 | **Tabla de tests completa**: por regla, caso ok / ko / frontera (±0,01, fecha = corte, PAGADA, IBAN con espacios, NIF con guion, pedido de otro proveedor) | `tests/test_rules.py` | `uv run pytest tests/test_rules.py -q` verde; ≥ 3 casos por regla |
| M5 | **Sábado 18:00: norma v4.** Copiar `norma_v3.py` → `norma_v4.py`, cambiar sólo lo que cambie, `REGISTRO["v4"]`, tests de lo nuevo, ADR con el diff v3→v4 y qué decisiones toca (Miguel lo usa para `reprocess --impacted --norma v4`) | `norma_v4.py`, `__init__.py`, `test_rules_v4.py`, `docs/adr/000N-norma-v4.md` | `decide --norma v4` corre; ADR lista las reglas cambiadas |

Lo que Mónica NO hace: leer texto de PDFs dentro de `rules/` (hook lo bloquea), tocar `core/` (pedir `Aviso` nuevos a Miguel), tocar `pipeline/etapas.marcar_duplicados` (proponer a Miguel).

## Miguel — contratos, pipeline, merge (core/ + pipeline/ + cli)
| # | Tarea | Ficheros | Aceptación |
|---|---|---|---|
| G1 | **Aceptar o corregir los contratos** (`core/contracts.py`, `schema.sql`): leer `docs/contratos.md`, decidir los `Aviso` que faltan (p. ej. `PEDIDO_SIN_NIF_MAESTRO`), anunciar cambios en el canal. Marcador `.claude/dueno.local` con `merge` y `contratos` | `src/albertitos/core/**`, `docs/contratos.md`, `tests/test_contracts.py` | Vie 23:30: "contratos v1 aceptados" en el canal |
| G2 | **`run` end-to-end sin LLM**: `hechos import` de `hechos_muestra.jsonl` (o, hasta que exista, 3 hechos escritos a mano en `tests/test_pipeline.py`) → `marcar_duplicados` → `decide` → `package` con `--con-traza`. Test de idempotencia: dos `run` → mismo JSONL | `src/albertitos/pipeline/**`, `cli.py`, `tests/test_pipeline.py` | `uv run albertitos run` termina; `make package` válido con los hechos que haya |
| G3 | **Reprocesado por linaje ensayado**: cambiar un asiento del ERP (CSV simulado de Javier: `data/fixtures/erp_lote2_simulado.csv` con `make -C data/caja erp-lote2 LOTE2_ERP=../fixtures/erp_lote2_simulado.csv`), `erp pull --tag v2`, `reprocess --impacted --erp v2` → "N de M recalculadas, K cambian". Cronometrar: < 30 s | `pipeline/linaje.py`, `cli.py`, `docs/adr/000N-linaje-reprocesado.md` | Sáb 23:00 según `hitos.md`, pero hacerlo el viernes si G2 va bien |
| G4 | **Caos integrado en `run`**: con `chaos --llm-down`, `extract` deja PENDIENTES, `decide` no toca esos ficheros, `package` se niega y lo dice; `chaos --off` reanuda. Evento por transición | `pipeline/etapas.py`, `cli.py`, `tests/test_pipeline.py` | Demo de 60 s reproducible (skill `demo`) |
| G5 | **Benchmark y coste**: `bench` con p50/p95 por etapa, ficheros/s de la ventana, EUR; `docs/benchmark.md` rellenado con hardware y condiciones tras el primer `run` completo | `pipeline/bench.py`, `docs/benchmark.md` | Cifras medidas, no estimadas |
| G6 | **Merge y entrega**: revisar PRs con `revisor-diff`, mergear en verde, `/entrega` de seguro sáb 17:30 y final dom 08:00, `docs/entregas.log` | — | Commits de entrega anotados |

Lo que Miguel NO hace: implementar `extract/` (Javier) ni reglas (Mónica); resolver conflictos de `core/` sin anunciarlos.

## Orden de dependencias (quién espera a quién)
1. **Vie 21:00–23:30:** los tres en paralelo sin depender de nadie (Javier: LLM + trampas; Mónica: M1; Miguel: G1 + G2 con hechos a mano).
2. **Vie 23:30:** Javier publica `hechos_muestra.jsonl` → Mónica M2, Miguel G2 con datos reales.
3. **Sáb 02:00:** Javier 500/500 hechos → Miguel `run` + `package` → **outcomes.jsonl válido** (repliegue 1).
4. **Sáb 10:00–12:00:** Mónica M3 con mentores → ajustes de reglas → Miguel `reprocess --impacted --norma v3` (los hechos no cambian; sólo cambia la norma: linaje lo detecta por `norma_version`... si la v3 cambia de comportamiento, Mónica sube la etiqueta a `v3.1` en `VERSION`).
5. **Sáb 17:30:** entrega de seguro. **18:00:** lote 2: Javier (datos + ERP v2) → Mónica (v4) → Miguel (reprocess + package).
