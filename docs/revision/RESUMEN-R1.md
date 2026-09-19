# RESUMEN R1 · Lote 2 y entrega · 15:52–16:05

## Huellas
- al empezar: BD 8501d9975c38 · outcomes 1ec4be206089   ·   al terminar: BD 8501d9975c38 · outcomes 1ec4be206089

## Comprobaciones (una fila por comprobación)
| # | Qué comprobé | Comando exacto | Resultado (OK / FALLA / RARO) | Salida literal que lo demuestra |
|---|---|---|---|---|
| 1 | Rama y HEAD | `git branch --show-current && git rev-parse --short HEAD` | OK | `revision/grok` · `a5a8366` |
| 2 | Ensayo general lote 2 | `bash scripts/ensayo/lote2-ensayo.sh` | FALLA | Resumen: `total: 26.676 s` · `run-erp-v1 exit=1` · `huellas iguales: sí`. Log: `extract: 8 extraídos · sin hechos: 2 → ['L2-scan_002.pdf', 'L2-scan_004.pdf']` · `LLM claude-sonnet-5 intento 3/3: "Could not resolve authentication method…"` · `NO APTO · … falta 'L2-scan_002.pdf' falta 'L2-scan_004.pdf'` |
| 3 | ERP v1 vivo (:8009) | el propio ensayo, `curl http://127.0.0.1:8009/erp/estado` | OK | `<asientos>516</asientos>` · `actualizacion_cargada>NO` · al terminar `activo_segundos>31042` |
| 4 | ERP v2 ensayo (:8011) + pull | pasos `erp-8011-arranca` y `erp-pull-v2` | OK | `<asientos>519</asientos>` · `actualizacion_cargada>SI` · `erp v2: 519 asientos · 30 consultas · 2 reintentos · lote2=True` |
| 5 | Diff + reprocess | `erp diff v1 v2` · `reprocess --impacted --erp v2` | OK | `2 de 510 recalculadas · 2 cambian` · `2026-06-27_P001.pdf: PAGAR → ESCALAR` · `F26-9865_ofimática.pdf: PAGAR → NO_PAGAR` |
| 6 | Desvío rojo `--aceptar-rojo` | `package` y `package --aceptar-rojo "…"` | RARO | Los dos salen 1 por las 2 líneas que faltan, no por `texto_sospechoso`. `--aceptar-rojo` no entrega: `NO APTO · falta 'L2-scan_002.pdf'`. Eventos `%ROJA%`: ninguno |
| 7 | Contingencia en seco | `scripts/contingencia.py --db … --lote 2` | OK | exit 1 · `2 ficheros del lote 2 sin decisión vigente` · `L2-scan_002.pdf` / `L2-scan_004.pdf` · `LLM-TypeError` · `sin respaldo configurado` |
| 8 | Desvío P0-5 | `bash scripts/ensayo/lote2-desvio-p05.sh` | RARO | `verificar-antes-del-merge exit=0` · `AVISO: nombre coincide con lote 1 y el contenido es otro: facturas/2026-01-16_P004.pdf` · `git merge … Already up to date.` · `make check` 562 passed, 4 skipped, 2 deselected in 41.00s · package FALLA por las mismas 2 escaneadas · en BD: `('2026-01-16_P004.pdf', 1)` y `('./2026-01-16_P004.pdf', 2)` |
| 9 | Preflight sobre la copia-tratada-como-real | `uv run python scripts/preflight_lote2.py` | OK | `Puedes seguir con el lote 2. 1 aviso(s) en ámbar.` · ámbar: `copia de la BD no hay copia` · decisiones `{'ESCALAR': 53, 'NO_PAGAR': 9, 'PAGAR': 438}` |
| 10 | Auditoría sobre la copia-tratada-como-real | `uv run python scripts/auditoria_entrega.py` | OK | `VEREDICTO: VERDE · se puede empaquetar` · lote 1 `500 decisiones · {'ESCALAR': 53, 'NO_PAGAR': 9, 'PAGAR': 438}` |
| 11 | Órdenes de la chuleta vs `--help` | `uv run albertitos <cmd> --help` / `uv run python <script> --help` (log en `docs/revision/r1/helps.txt`) | OK | Todas las opciones de la chuleta existen (tabla debajo). `make publicar` no se ejecutó (regla: no GitHub); `publicar_entrega.py --help` tiene `--publicar --aceptar-rojo --sin-gh --destino --db --plan` |
| 12 | Resumen de una pantalla | el propio `lote2-ensayo.sh` al terminar | OK | imprimió total, 10 exits ≠ 0 (1 marcado esperado), `huellas iguales: sí` |

### Tabla chuleta · orden · ¿existe? · ¿opciones correctas?
| Orden en CHULETA-LOTE2.md | ¿existe? | ¿opciones correctas? | Nota |
|---|---|---|---|
| `scripts/preflight_lote2.py --respaldar` | sí | sí `--respaldar` | no lo ejecuté con `--respaldar` sobre esta BD |
| `scripts/auditoria_entrega.py` + `--db --lote --dir-lote1 --dir-lote2 --entrega` | sí | sí | `--lote {1,2,ambos}` |
| `scripts/verificar_material.py --hash --esperados` | sí | sí `--hash --db --lote1-dir --esperados` + posicional `material` | |
| `albertitos caja manifest --lote 2` | sí | sí `--lote` | no ejecutado (escribe manifiesto) |
| `albertitos caja verify --lote 2` | sí | sí `--lote --dir --esperados` | |
| `albertitos ingest --dir --lote` | sí | sí | sólo --help |
| `albertitos run --erp --norma --fecha-corte --salida` | sí | sí; también `--aceptar-rojo --sin-auditoria --sin-extraer` | |
| `albertitos status` | sí | sí (`--historico` existe, la chuleta no lo usa) | |
| `data/caja/alberto_erp.py --puerto --lote2` | sí | sí; también `--rapido` | |
| `albertitos erp pull --tag` | sí | sí | |
| `albertitos erp diff v1 v2` | sí | sí, argumentos posicionales `a` `b` | |
| `albertitos reprocess --impacted --erp --norma --fecha-corte` | sí | sí; `--todo` existe | |
| `scripts/inventario_trampas.py --con-hechos --facturas --erp-tag --salida --sin-docs --solo-resumen` | sí | sí (`--erp-tag` alias de `--erp`; `--salida` alias de `--csv`) | |
| `albertitos package --salida` / `--aceptar-rojo` | sí | sí | |
| `albertitos extract --workers` | sí | sí | |
| `albertitos chaos --off` | sí | sí | |
| `scripts/contingencia.py --lote 2` / `--aplicar --motivo --fecha-corte` | sí | sí; `--db` existe | |
| `scripts/publicar_entrega.py` (`make publicar`) | sí | `--publicar --aceptar-rojo --sin-gh --destino --db --plan` | skill `/entrega` usa `make publicar` y `ARGS=--publicar` / `--aceptar-rojo`; coincide |
| `albertitos validate --lote` | sí | sí | |
| `reprocess --norma v4` | flag existe | v4 no está en el registro | no ejecutado (Mónica) |

### Tiempos vs chuleta (solo pasos con exit 0; umbral 50 %)
| Paso | Chuleta 13:12 | R1 15:54 | Δ |
|---|---:|---:|---|
| preflight | 0,3 s | 0,365 s | +22 % |
| verificar dir | 1,1 s | 1,989 s | **+81 %** |
| verificar ZIP | 0,4 s | 1,191 s | **+198 %** |
| caja verify | 0,2 s | 0,324 s | **+62 %** |
| ingest | 0,3 s | 0,372 s | +24 % |
| erp pull v2 | 3,9 s | 4,078 s | +5 % |
| erp diff | 0,2 s | 0,215 s | +8 % |
| reprocess --impacted | 0,2 s | 0,262 s | +31 % |
| reprocess --todo | 0,3 s | 0,336 s | +12 % |
| inventario | 0,4 s | 0,569 s | +42 % |
| P0-5 make check | 36 s | 42,153 s | +17 % |

No actualizo los tiempos de `run`/`package`/`validate`/`publicar`: en esta carpeta no llegaron a verde.

## Hallazgos (lo que está mal o confunde), de más grave a menos
| # | Gravedad | Dónde | Qué pasa | Propuesta |
|---|---|---|---|---|
| 1 | alta | `scripts/ensayo/lote2-ensayo.sh` paso `run-erp-v1` · esta carpeta sin `.env` | Las 2 escaneadas del simulado (`L2-scan_002.pdf`, `L2-scan_004.pdf`) no están en la caché de *esta* BD (hashes distintos de `scan_002`/`scan_004` de la Caja). Sin api_key el extract las deja PENDIENTE y `package` se niega. El ensayo de las 13:12 llegó a verde porque aquella copia ya tenía esas lecturas cacheadas. A las 18:00 sí hay `.env` en `HackSpain`. | No tocar extract/. En esta carpeta de revisión el ensayo no puede cerrar package APTO sin LLM. A las 18:00: si una escaneada nueva queda PENDIENTE, parar y no entregar. |
| 2 | media | `CHULETA-LOTE2.md` (antes) y `lote2-desvio-p05.sh` | P0-5 ya está en este código. El verificador **no para** (`APTO` + aviso). El script esperaba exit 1 antes del merge. `git merge origin/miguel/p0-5-nombre-repetido` → `Already up to date.` El file_id interno sí se crea: lote 2 `./2026-01-16_P004.pdf`. | Chuleta actualizada (fila del verificador). El script de P0-5 sigue midiendo el merge; no lo reescribo entero. |
| 3 | media | `package --aceptar-rojo` | Con líneas de lote 2 faltando, `--aceptar-rojo` no entrega. Coincide con el help: «nunca si … el JSONL es inválido». El desvío rojo de las 13:12 no se ha vuelto a ver: el evento `AUDITORIA-ROJA-ACEPTADA` no aparece. | Nada: es el contrato. El desvío rojo del ensayo no prueba `--aceptar-rojo` mientras falten las 2 escaneadas. |
| 4 | baja | verificar dir/ZIP | +81 % / +198 % frente a las 13:12, exit 0. Primera pasada en worktree frío (`Creating virtual environment at: .venv`). | No es un fallo. Cold start del `.venv` del worktree. |
| 5 | baja | `status` tras ingest de 14 PDFs | `ficheros por lote: {1: 500, 2: 10}` · `copias exactas con otro nombre, por lote: {2: 4}` | Las 4 de `lote2_identicos` van a `identidades`, no a `ficheros`. Confunde si se cuenta solo `ficheros`. Propuesta a Miguel: que `status` sume nombres de entrega. |

## Lo que he cambiado yo
| Commit | Ficheros | Qué y por qué | Cómo se prueba |
|---|---|---|---|
| (este) | `scripts/ensayo/lote2-ensayo.sh` | Resumen de una pantalla al final: total s, exits ≠ 0 (esperado: `desvio-rojo-package-niega`), huellas sí/no | `bash scripts/ensayo/lote2-ensayo.sh` → bloque `======== RESUMEN ENSAYO LOTE 2 ========` |
| (este) | `docs/agentes/CHULETA-LOTE2.md` | P0-5: aviso, no ROJO; nota R1 15:54 de los tiempos y del `.env` | leer la chuleta |
| (este) | `docs/revision/r1/tiempos.tsv` · `p05-tiempos.tsv` · `helps.txt` | Copias de lo ejecutado | — |

## Lo que he añadido (la cosa sencilla)
- Resumen de una pantalla al final de `scripts/ensayo/lote2-ensayo.sh`.
- Cómo se usa: sale solo al terminar el ensayo.
- Su test: ejecutado el 19/09 15:54; imprimió `total: 26.676 s`, la lista de exits y `huellas iguales: sí`.
- Por qué ayuda: a las 18:00 se ve en una ojeada si el ensayo cerró verde o qué paso rompió, sin leer el log.

## make check al final
- literal: `565 passed, 10 skipped, 2 deselected in 34.85s`

## Lo que no he podido hacer y por qué
- Llegar a `package` APTO en los dos ensayos: esta carpeta no tiene `.env` (PLAN-12) y las 2 escaneadas del simulado no están en caché.
- Repetir el desvío rojo de `texto_sospechoso = None` hasta el evento `AUDITORIA-ROJA-ACEPTADA`: `package` se para antes, por JSONL incompleto.
- `make publicar` contra GitHub: prohibido. Comprobado sólo `--help`.

