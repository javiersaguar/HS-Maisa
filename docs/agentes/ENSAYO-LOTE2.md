# Ensayo E3 · ciclo 5 · 19/09/2026

**Ensayo aislado:** `dist/ensayo/ensayo.db` (backup SQLite de la real), salida `dist/ensayo/entrega`, material `data/fixtures/lote2_sim`. Las 500 decisiones de partida eran 443 PAGAR / 48 ESCALAR / 9 NO_PAGAR. E3 no ha escrito en la BD real, su entrega ni data/. La comparación global detecta cambios concurrentes, detallados al final.

El flujo íntegro se ha medido: 10 nuevos hechos, 20 marcas de duplicado, nueve originales pasan a ESCALAR; el diff posterior de ERP recalcula sólo dos facturas. **La primera auditoría sale ROJO por el `"None"` heredado de scan_025**. Se detiene package final, se prueba la recuperación en la copia y se registra debajo; eso no autoriza una entrega real ni resuelve la política de Mónica.

Los tiempos siguientes son de pared por comando, incluyendo inicio de Python/CLI. **Ensayo caliente: 8 plantillas y 2 escaneadas ya cacheadas, 0 tokens nuevos / 0 EUR.** No compararlo como si las 2 escaneadas se hubieran vuelto a leer por red. Para visión fría, D1 midió 0,065–0,106 facturas/s con doble lectura en `ESCALA-10K.md`.

## Tiempos comparados con el ciclo 2

| Paso | Ciclo 2 (B1) | Ciclo 5 (E3) | Resultado medido |
|---|---:|---:|---|
| Preflight E1 + backup de copia | No existía | 0,174 s | exit 0; 500 lote 1, sin fantasmas, ERP v1 y segundo bridge vivos; ámbar por carpeta del simulado con 10 PDFs |
| Verificador, directorio simulado | No existía | 0,350 s | 10 PDF APTO; muestra README como dato; no hay CSV dentro de ese directorio |
| Verificador, ZIP simulado con CSV | No existía | 0,429 s | Hash cotejado; 10 PDF, 3 asientos nuevos, 2 modificados |
| caja verify con --dir | No disponible | 0,070 s | 10 PDFs OK; no escribe manifiesto |
| ingest | 0,31 s | 0,233 s | 10 nuevos en lote 2 |
| run completo, ERP v1 comprobado | No ejecutado | 1,380 s | 10 extraídos, 0 pendientes, duplicados +20, 510 decisiones |
| extract del ensayo anterior | 68 s, visión nueva | Incluido en run | 8 plantillas + 2 caché; 0 tokens |
| ERP pull v2-sim | ~4 s | 3,969 s | 519 asientos, 31 consultas, 3 reintentos |
| ERP diff | 0,17 s | 0,135 s | 3 altas, 2 cambios, 5 pedidos afectados |
| reprocess --impacted | 0,50 s; 510/510 | 0,220 s; **2/510** | 2 cambian, 508 sin impacto; proceso interno 0,04 s |
| inventario --con-hechos | 0,07 s; sólo texto | 0,393 s | 15 filas, 10 ficheros; 11 filas desde hechos |
| auditoría E2 antes de package | No existía | 0,244 s | exit 1; único tipo rojo: evidencia falsa de scan_025 (2 incidencias del mismo fichero) |
| Alternativa extract sin pendientes | — | 0,268 s | 0/0, 0 tokens |
| Alternativa reprocess --todo --erp v2-sim | — | 0,918 s | 510 recalculadas, 0 cambios: equivalente disponible con ERP explícito |

Los pasos de la primera pasada suman **7,597 s** incluyendo las dos verificaciones de material. No incluyen pausas de inspección, arranque de bridges ya vivos, recuperación ni la alternativa complementaria. Registro literal de cada comando, inicio, duración y código en `dist/ensayo/e3-medidas.json`; stdout/stderr en `dist/ensayo/e3-*.log` (artefactos locales, no se versionan).

## Resultado: separar duplicados de cambios ERP

El run agrega los 10 simulados a las 500 facturas. Todos son copias con SHA distinto, por construcción. Se marcan 20 documentos, pero **sólo nueve decisiones previas cambian de resultado**; el original `F26-2201_transportes.pdf` ya escalaba.

| Original del lote 1 | Antes | Tras run con v1 |
|---|---|---|
| 2026-01-08_P001.pdf | PAGAR | ESCALAR |
| 2026-01-14_P002.pdf | PAGAR | ESCALAR |
| 2026-01-15_P003.pdf | PAGAR | ESCALAR |
| 2026-01-16_P004.pdf | PAGAR | ESCALAR |
| 2026-01-24_P009.pdf | PAGAR | ESCALAR |
| 2026-01-25_P001.pdf | PAGAR | ESCALAR |
| 2026-01-26_P007.pdf | PAGAR | ESCALAR |
| scan_002.pdf | PAGAR | ESCALAR |
| scan_004.pdf | PAGAR | ESCALAR |

Después del run: lote 1 = **434 PAGAR / 57 ESCALAR / 9 NO_PAGAR**; lote 2 = **10 ESCALAR**. La política sobre duplicados entre lotes, especialmente si el original ya se entregó, corresponde a Mónica/mentor (ADR-0006).

El pull posterior produce este diff, ya comprobado también por el verificador del ZIP:

| Asiento | Cambio |
|---|---|
| AS-SIM-00001, AS-SIM-00002, AS-SIM-00003 | Nuevos; pedidos PO-SIM-0001/2/3, sin facturas asociadas |
| AS-00001 | PENDIENTE → PAGADA; PO-2026-0001 |
| AS-00002 | 10325.90 → 10449.35; PO-2026-0002 |

`reprocess --impacted --erp v2-sim` cambia **sólo** `F26-9865_ofimática.pdf` (PAGAR→NO_PAGAR) y `2026-06-27_P001.pdf` (PAGAR→ESCALAR). Quedan 508 decisiones conservadas por el diff. Lote 1 antes de recuperar scan_025: **432 PAGAR / 58 ESCALAR / 10 NO_PAGAR**. Lote 2: 10 ESCALAR.

## Bloqueo y recuperación de la auditoría

Salida inicial literal:

```text
ROJO      2  Motivo o evidencia falsos ("None", cita que no está en el PDF, cita vieja)
  - scan_025.pdf: texto_sospechoso = 'None' (ESCALAR)
  - scan_025.pdf: el motivo de R6 cita 'None'
VEREDICTO: ROJO · 1 comprobación(es) en rojo: NO entregar
```

El control funcionó: no había fantasmas, pagos dobles, duplicados sin marcar con PAGAR, PAGAR incoherentes ni decisiones contra otros hechos. Sí había ámbar esperado por 10/10 simuladas ESCALAR, cinco PAGAR de confianza 0,6 y el JSONL preliminar anterior al diff.

La reparación de hechos se ensaya sólo en la copia con el extractor de E2 y la caché existente. Una auditoría verde comprueba coherencia con la norma implementada; **no ratifica la política DOCUMENTO_SUPERPUESTO**. Su posible paso a PAGAR requiere decisión de Mónica antes de tocar la BD/entrega real.

Recuperación ejecutada con el extractor E2 (b678cfd), sin modificar su código. En el proceso de extracción se sustituyó temporalmente `ClienteLLM._api` por una función que lanza error: un fallo de caché no podía contactar al proveedor. No se activó caos.

```bash
printf 'scan_025.pdf\n' > dist/ensayo/e3-recuperar.txt
uv run python - <<'PY'
import sys
from albertitos.extract.llm import ClienteLLM
def sin_red(self):
    raise RuntimeError("ENSAYO: falta cache; no contactar al proveedor")
ClienteLLM._api = sin_red
from albertitos.cli import app
sys.argv = ["albertitos", "extract", "--no-solo-pendientes", "--fixture",
            "dist/ensayo/e3-recuperar.txt", "--workers", "4"]
app()
PY
uv run albertitos reprocess --impacted --erp v2-sim --fecha-corte 2026-09-18
uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos --dir-lote1 data/caja/facturas --dir-lote2 data/fixtures/lote2_sim/facturas --entrega dist/ensayo/entrega
```

Medidas: extracción **5,478 s** (1/1 caché, 0 pendientes, tokens 0/0, 0 EUR); reproceso **1,591 s**, **1 de 510 recalculada**, scan_025 ESCALAR→PAGAR; primera auditoría recuperada **2,257 s**, VERDE. Con la auditoría definitiva de E2 se repitió antes de package (**0,386 s**): VERDE con ámbar explícito en DOCUMENTO_SUPERPUESTO.

Package por API: **0,163 s**, ambos **APTO**: lote 1 **500 líneas, 433 PAGAR / 57 ESCALAR / 10 NO_PAGAR**; lote 2 **10 líneas, todas ESCALAR**. Auditoría posterior **0,381 s**, VERDE, cero líneas desfasadas. Quedan tres avisos ámbar: documento superpuesto pagable, las diez copias escaladas y cinco lecturas reconciliadas de confianza 0,6. Es resultado del ensayo bajo v3, no autorización de entrega real.

Controles finales actualizados: verificador ZIP **0,358 s** (10 PDF, 3 altas y 2 cambios); preflight **0,135 s**, exit 0, con directorio simulado explícito y ERP esperado v2-sim. Las diferencias de fixture frente a esta copia son esperables: no se reexportan los hechos simulados a data/.


## Receta reproducible del ensayo

No ejecutar este bloque sobre la BD real. Los bridges `:8009` (v1) y `:8011` (CSV `data/fixtures/erp_lote2_simulado.csv`) deben estar vivos. No detener otro servicio si ocupa el puerto.

```bash
set -euo pipefail
export ALBERTITOS_DB=dist/ensayo/ensayo.db
export ALBERTITOS_FECHA_CORTE=2026-09-18
export ALBERTITOS_WORKERS=4

# Guardar huellas y crear una copia coherente nueva, sin cp ni borrar caché.
uv run python - <<'PY'
import hashlib, json, sqlite3
from pathlib import Path
raiz = Path("dist/ensayo")
raiz.mkdir(parents=True, exist_ok=True)
destino = raiz / "ensayo.db"
if destino.exists():
    raise SystemExit("Ya existe ensayo.db: conserva el ensayo anterior antes de repetir.")
rutas = [Path("dist/albertitos.db"), *Path("dist/entrega").rglob("*"), *Path("data").rglob("*")]
huellas = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in rutas if p.is_file()}
(raiz / "e3-hashes-antes.json").write_text(json.dumps(huellas, indent=2))
src = sqlite3.connect("file:dist/albertitos.db?mode=ro", uri=True)
dst = sqlite3.connect(destino)
src.backup(dst)
src.close()
dst.close()
PY

uv run python scripts/preflight_lote2.py --db "$ALBERTITOS_DB" --dir-lote2 data/fixtures/lote2_sim/facturas --erp-esperado v1 --erp-lote2 http://127.0.0.1:8011 --respaldar
export ALBERTITOS_DIR_LOTE2=data/fixtures/lote2_sim/facturas
uv run python scripts/verificar_material.py data/fixtures/lote2_sim --esperados 10
uv run albertitos caja verify --lote 2 --dir data/fixtures/lote2_sim/facturas --esperados 10
uv run albertitos ingest --dir data/fixtures/lote2_sim/facturas --lote 2

# CLI actual: esta alternativa incluye marcar_duplicados y fija ERP.
if uv run albertitos run --help | grep -q -- '--erp'; then
  uv run albertitos run --erp v1 --norma v3 --fecha-corte 2026-09-18 --salida dist/ensayo/entrega
else
  uv run albertitos maestro
  uv run albertitos extract --workers 4
  uv run albertitos reprocess --todo --erp v1 --norma v3 --fecha-corte 2026-09-18
fi

ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2-sim
uv run albertitos erp diff v1 v2-sim
uv run albertitos reprocess --impacted --erp v2-sim --fecha-corte 2026-09-18
uv run python scripts/inventario_trampas.py --con-hechos --facturas data/fixtures/lote2_sim/facturas --erp-tag v2-sim --salida dist/ensayo/anomalias_lote2.csv --sin-docs --solo-resumen
uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos --dir-lote1 data/caja/facturas --dir-lote2 data/fixtures/lote2_sim/facturas --entrega dist/ensayo/entrega
```

Con la BD actual, se detiene en el rojo de scan_025. Ejecutar únicamente la recuperación documentada arriba, repetir auditoría y, si pasa, continuar:

```bash
# API de package: la CLI no admite raíz alternativa del lote 2.
uv run python -c 'from pathlib import Path; from albertitos.core import db; from albertitos.pipeline.package import empaquetar; c=db.conectar("dist/ensayo/ensayo.db"); salidas=empaquetar(c,Path("dist/ensayo/entrega"),Path("data/caja"),Path("data/fixtures/lote2_sim"),con_traza=True); c.close(); [print(informe.texto()) for _,informe in salidas]'
uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos --dir-lote1 data/caja/facturas --dir-lote2 data/fixtures/lote2_sim/facturas --entrega dist/ensayo/entrega
uv run python - <<'PY'
import hashlib, json
from pathlib import Path
antes = json.loads(Path("dist/ensayo/e3-hashes-antes.json").read_text())
cambios = [p for p,h in antes.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
actuales = {str(p) for raiz in ("data", "dist/entrega") for p in Path(raiz).rglob("*") if p.is_file()}
nuevos = sorted(actuales - set(antes))
assert not cambios and not nuevos, (cambios, nuevos)
print("BD, entrega real y data: hashes intactos; cero ficheros nuevos.")
PY
```

No generar `caja manifest` en este ensayo: escribe en `data/lote2.sha256` aunque los PDF sean simulados. `caja verify --dir` sí se ejecutó y no escribe. `run` sólo ingiere la raíz fija del lote 2: por eso antes se usa `ingest --dir`; extract sí respeta `ALBERTITOS_DIR_LOTE2`. Package necesita su API para generar las 10 líneas del lote simulado.

La primera medida de `run` íntegro, sin `--erp` disponible, se hizo con comprobación explícita del último snapshot v1 antes y de `[('v1', 510)]` en las decisiones después. Se midió además la alternativa segura con destino explícito; no se ha inventado una opción de CLI. PIDO A Miguel registrado en bitácora.

## Integridad y aceptación

`make check` → **323 passed, 9 skipped, 2 deselected**, formato y lint correctos.
`make agentes-check` → **8 problemas ajenos a las rutas E3**: guard_bash.py, skill entrega, hechos_caja.jsonl, ENSAYO-REPROCESADO.md, PLAN-05.md, transcripcion-demo-caos.txt, demo_caos.py y test_hooks.py. Javier debe conciliar esas autorizaciones con plan.json.

**No se puede afirmar integridad global sin cambios.** El ensayo sólo escribió en dist/ensayo; durante el trabajo compartido cambiaron la BD real, el PDF real y el fixture de hechos. La reexportación del fixture está comunicada por E1 en bitácora; la causa de los otros dos cambios no está atribuida por E3. No se revierten. Cero archivos nuevos en data/ o entrega real; los otros 524 archivos de data/ conservan su hash.

| Archivo | SHA-256 antes | SHA-256 después |
|---|---|---|
| dist/albertitos.db | `8c163e859dd63022c10fa55bed116b7a694e026ab8bfc9b6b037bbb5bbf4bcc7` | `9ef061ed2fca79e82046fce4a78375b3d662d685a6ad05384c31ed88985170c0` |
| dist/entrega/outcomes.jsonl | `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3` | `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3` |
| dist/entrega/albertitos_plan.pdf | `eaeb1f1f5cf443c56a305ae91514f3d58d8f89b1fa93cb5476c128f925ad8797` | `a67e695b4e7990ba38fe09e9446eafb35af2482813334e0fb0543967cc4f5218` |
| data/fixtures/hechos_caja.jsonl | `fa23381e17a42dfbc1da1c0075e64303684f2be38af20d82562a300340512954` | `f3f937d824339b1ead23a7772392c794c23e78f783c21cc0050daa6ff79945c7` |

El JSONL oficial está intacto. Huellas completas: dist/ensayo/e3-hashes-{antes,despues}.json. PIDO A Javier: contrastar las escrituras concurrentes de BD/PDF antes de cerrar la integridad del ciclo.


Verificador: `uv run pytest tests/test_material.py -q` → **21 passed in 0.34s**, sin red. Casos: ZIP válido (2 PDF + CSV), hash incorrecto, PDF corrupto, NFD, colisión de nombre con lote 1 y entre carpetas, columnas/filas CSV, fechas/importes/estados ilegibles, asiento repetido, adjuntos de regla txt/xlsx/pdf, rutas ZIP inseguras y BD ausente. La revisión independiente añadió cuatro regresiones: PDF idéntico renombrado respecto a lote 1, idéntico con dos nombres en el lote recibido, `.PDF` y subcarpetas omitidas por ingest. No se extraen ZIP ni se ejecutan adjuntos.

La revisión también cerró el riesgo de `unzip -n` sobre restos de un intento anterior: la skill exige que `data/lote2` esté vacío (incluido el CSV) antes de extraer. El preflight nuevo de E1 rechaza variables de ensayo; por eso la receta pasa la ruta simulada como argumento al preflight y exporta `ALBERTITOS_DIR_LOTE2` sólo después.

---

# Antecedente histórico · ciclo 2

Lo que sigue se conserva como evidencia del primer ensayo. Sus comandos y estimaciones NO sustituyen el runbook de ciclo 5 ni sus gates; la observación antigua «recalcula todo» quedó superada por ADR-0006.


# Ensayo en frío del lote 2 (viernes 18/09, 22:10-22:40) · B1

Objetivo: que el sábado a las 18:00 el lote 2 (40 facturas + `erp_export_lote2.csv` + una regla nueva; la web del 18/09 23:00 ya no habla de "norma v4" ni de un fichero) entre en ~15 minutos con
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
- [ ] **4 (Mónica)** regla nueva (fichero, canal o Excel) → `norma_v4.py` + tests + ADR
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
