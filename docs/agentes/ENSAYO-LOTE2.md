# Ensayo en frío del lote 2 (viernes 18/09, 22:10-22:40) · B1

Objetivo: que el sábado a las 18:00 el lote 2 (40 facturas + `erp_export_lote2.csv` + norma v4) entre en ~15 minutos con
comandos ya probados. Se ensayó con **`data/fixtures/lote2_sim/`** (10 PDFs derivados de la Caja con sha distinto: una
por cada una de las 6 plantillas de A2, una de dos páginas, una con instrucción inyectada, dos escaneadas) y el ERP
simulado de A3 (`data/fixtures/erp_lote2_simulado.csv` en `:8011`: 3 altas, 2 cambios). **Nada de esto es el lote real.**

## 1. Tiempos medidos (portátil de Javier, WSL2, 4 hilos)
| Paso | Comando | Resultado | Tiempo |
|---|---|---|---|
| ingest | `uv run albertitos ingest --dir data/fixtures/lote2_sim/facturas --lote 2` | 10 ficheros, lote 2 | 0,31 s |
| extract | `ALBERTITOS_DIR_LOTE2=data/fixtures/lote2_sim/facturas uv run albertitos extract --workers 4` | 10/10 · plantilla 8 · llm_vision 2 · 18.368 tokens · 0 pendientes | 68 s (plantillas ≈ 0; las 2 escaneadas con doble lectura ≈ 35 s cada una) |
| comprobación | `uv run albertitos status` + consulta de hechos | `ficheros por lote {1: 500, 2: 10}`; 10/10 con hechos; la de instrucción lleva `texto_instruccion`; la de fecha en letra, `fecha_en_letra`; las escaneadas, `sin_texto` | — |
| erp pull v2-sim | (hecho por A3) `ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2-sim` | 519 asientos · 30 consultas · 2 reintentos | ~4 s |
| erp diff | `uv run albertitos erp diff v1 v2-sim` | 3 nuevos (AS-SIM-00001..3) · 2 cambiados (AS-00001 PENDIENTE→PAGADA, AS-00002 10325.90→10449.35) · 5 pedidos afectados | 0,17 s |
| inventario | `uv run python scripts/inventario_trampas.py --facturas data/fixtures/lote2_sim/facturas --erp-tag v2-sim --salida <csv> --sin-docs --solo-resumen` | texto_instruccion 1 · sin_texto 2 · fecha_en_letra 1 · resto 0 | 0,07 s |
| reprocess (Miguel) | `uv run albertitos reprocess --impacted --erp v2-sim` | impactados 510 de 510 · **cambian 2** (ver §3) | 0,50 s |
| package (comprobación) | `uv run albertitos package` | lote 1 APTO (500 líneas); lote 2 omitido porque no existe `data/lote2/facturas` | 1 s |

Extrapolación para 40 facturas: ingest < 2 s; extract ≈ 5 s si todas salen por plantilla, **≈ 9 s por escaneada** con 4 hilos
(40 escaneadas ≈ 6 min; 4-5 escaneadas ≈ 1 min); pull + diff < 10 s; reprocess < 2 s. Cuello de botella: visión (qwen3.6 razona ~3.000 tokens por lectura, dos lecturas por escaneada).

## 2. Huecos del runbook encontrados (y qué se hizo)
| Hueco | Estado |
|---|---|
| `caja verify --lote 2` sólo mira `data/lote2/facturas` (ruta fija) y no hay manifiesto para el lote 2 | PIDO A Miguel: `caja verify --dir <ruta>` y `caja manifest --lote 2` (cli.py) |
| `extract` buscaba los PDF del lote 2 sólo en `data/lote2/facturas` | Hecho (plataforma): `ALBERTITOS_DIR_LOTE2` / `ALBERTITOS_DIR_CAJA` en `extract/etapa.py` |
| `run` usa la constante `data/lote2` | Vale para el lote real; para simulaciones se ejecutan los verbos sueltos (documentado en la skill) |
| `package` incluye TODO fichero con `lote=2` de la BD en `outcomes_lote2.jsonl` si existe `data/lote2/facturas` → los `L2-*` del simulado darían NO APTO ("sobra") | Paso 0 de la skill: borrar los `L2-*` de la BD antes del lote real (comando literal) |
| `make erp-lote2` arranca en :8009, ocupado por el v1 | Skill: segundo bridge en :8011 (`--puerto 8011 --lote2 …`) y `ALBERTITOS_ERP_URL` en el `pull`; :8010 está ocupado por otro servicio en el portátil de Javier |
| `scripts/inventario_trampas.py` barría sólo `data/caja/facturas` y **siempre** reescribía `docs/trampas.md` | Hecho: `--facturas`, `--erp-tag`, `--salida`, `--sin-docs`; el resumen por categoría sale siempre en pantalla |
| Las facturas que salen por plantilla no pasan por el LLM: una instrucción con redacción nueva sólo la cazan las regex de `instrucciones.py` | PIDO A B2: pasada de contraste LLM sobre el lote 2 (`contrastar` ya existe; falta poder limitarla a un lote / lista de file_id) para recoger `texto_sospechoso` también de las de plantilla |
| `linaje.impactados` recalcula todo (510) cuando cambia la versión del ERP | Aceptable (0,5 s); en la demo, la frase es "recalculadas 510, **cambian 2**, y son exactamente las que referencian los asientos modificados" |

## 3. Cruce ERP v2-sim ↔ Excel ↔ facturas (lo que el reprocesado debe cambiar)
| Pedido afectado | Excel | ERP v2-sim | Facturas que lo referencian (lote 1) | Vigente con v1 | Esperado con v2-sim | Confirmado |
|---|---|---|---|---|---|---|
| PO-2026-0001 | P003 · 9.221,75 · ABIERTO | AS-00001 **PAGADA** 9.221,75 | `F26-9865_ofimática.pdf` | PAGAR | **NO_PAGAR** (R5: ya pagada) | ✓ |
| PO-2026-0002 | P001 · 10.325,90 · ABIERTO | AS-00002 PENDIENTE **10.449,35** | `2026-06-27_P001.pdf` | PAGAR | **ESCALAR** (R5: el ERP espera otro importe; R2 con el Excel sí cuadra) | ✓ |
| PO-SIM-0001/2/3 | no existen | AS-SIM-00001..3 PENDIENTE | ninguna | — | — | ✓ (nada cambia) |

`reprocess --impacted --erp v2-sim` → `510 recalculadas · 2 cambian: 2026-06-27_P001.pdf PAGAR→ESCALAR · F26-9865_ofimática.pdf PAGAR→NO_PAGAR`. Después `reprocess --impacted --erp v1` devuelve ambas a PAGAR (historial conservado en `decisiones` con `vigente=0`).
Con el lote real, la misma tabla se construye con `erp diff v1 v2` + `hechos` (consulta en `docs/agentes/partes/PARTE-02.md` cuando exista, o el bloque de §4).

## 4. Checklist del sábado 18:00 (tiempos del ensayo)
- [ ] **0 (antes, 2 min)** `status` → si hay `{2: 10}`, limpiar `L2-*` de la BD (comando en la skill). `make package` de seguro. Mentor: ¿lote 1 con v3/v1 o con v4/v2?
- [ ] **1 (2 min)** `sha256sum` del zip vs. canal · `unzip -o … -d data/lote2/` · `ls -R data/lote2` · `uv run albertitos caja verify --lote 2` (40, NFC) · `git add data/lote2 && git commit`
- [ ] **2 (1 min)** bridge v2 en :8011 con `--lote2 data/lote2/erp_export_lote2.csv` · `curl …/erp/estado` → `SI` · `ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2` · `uv run albertitos erp diff v1 v2` → pegar en `docs/reprocesado-lote2.md`
- [ ] **3 (2-6 min)** `ingest --dir data/lote2/facturas --lote 2` · `extract --workers 4` · `status` (0 sin hechos; si quedan PENDIENTE, repetir `extract --workers 4`: los reintentos cambian el texto y suelen entrar) · inventario `--facturas data/lote2/facturas --erp-tag v2 --sin-docs --solo-resumen` → frases nuevas a B2/A2
- [ ] **3b (B2, 1-2 min)** contraste LLM del lote 2 para `texto_sospechoso` en las de plantilla (cuando exista la opción)
- [ ] **4 (Mónica)** norma v4 → `norma_v4.py` + tests + ADR
- [ ] **5 (Miguel, 1 min)** `reprocess --impacted --norma v4 --erp v2` → `docs/reprocesado-lote2.md` con "recalculadas N, cambian K" y la lista cruzada de §3 construida con el diff real
- [ ] **6** `/entrega` → `outcomes.jsonl` + `outcomes_lote2.jsonl` (40 líneas exactas) + `albertitos_plan.pdf`

Bloque para construir la tabla de §3 con el lote real (léelo, es sólo lectura):
```
uv run python - <<'PY'
from albertitos.core import db; from albertitos.core.contracts import InvoiceFacts; from albertitos.sources import snapshot
c = db.conectar("dist/albertitos.db", solo_lectura=True); d = snapshot.diff_erp(snapshot.cargar_erp_bd(c, "v1"), snapshot.cargar_erp_bd(c, "v2"))
dec = {r["file_id"]: r["resultado"] for r in c.execute("select file_id, resultado from decisiones where vigente=1")}
for r in c.execute("select f.file_id, h.hechos_json from hechos h join ficheros f on f.sha256=h.sha256"):
    h = InvoiceFacts.model_validate_json(r["hechos_json"])
    if h.pedido in d["pedidos_afectados"]: print(h.pedido, r["file_id"], "vigente:", dec.get(r["file_id"]))
PY
```
