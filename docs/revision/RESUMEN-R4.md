# RESUMEN R4 · portabilidad y demo · 15:53–15:58

## Huellas
- al empezar: BD 8501d9975c38 · outcomes 1ec4be206089   ·   al terminar: BD 8501d9975c38 · outcomes 1ec4be206089

## Comprobaciones (una fila por comprobación)
| # | Qué comprobé | Comando exacto | Resultado (OK / FALLA / RARO) | Salida literal que lo demuestra |
|---|---|---|---|---|
| 1 | Huellas al empezar | `sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl \| cut -c1-12` | OK | `8501d9975c38` / `1ec4be206089` |
| 2 | Clon limpio | `git worktree add dist/ensayo/r4/limpio HEAD --detach` | OK | `Preparing worktree (detached HEAD a5a8366)` |
| 3 | `./bootstrap.sh` en el clon | `time ./bootstrap.sh` (cwd limpio) | OK | `Listo. Siguiente: make erp-fast …` · **2.270 s** · crea `.env` desde `.env.example` y BD vacía |
| 4 | Empaquetar kit (BD de revisión, sólo lectura) | `uv run python scripts/kit_demo.py empaquetar --origen dist/albertitos.db --salida dist/kit --entrega dist/entrega` | OK | `kit: dist/kit/albertitos-kit-20260919-1555.tar.gz · 1.4 MB` · `ficheros {'1': 500}` · `decisiones {'ESCALAR': 53, 'NO_PAGAR': 9, 'PAGAR': 438}` · `caché LLM 881` · **0.486 s** |
| 5 | Instalar kit en el clon | `uv run python scripts/kit_demo.py instalar …1555.tar.gz --sin-status` | OK | `VEREDICTO: instalado` · `outcomes.jsonl 1ec4be206089` · **0.219 s** |
| 6 | `status` en el clon | `uv run albertitos status` | OK | `ficheros por lote: {1: 500} · decisiones vigentes: {'ESCALAR': 53, 'NO_PAGAR': 9, 'PAGAR': 438} · caché LLM: 881` · `sin decisión vigente: 0` · **0.330 s** |
| 7 | `trace` en el clon | `uv run albertitos trace F26-2201_transportes.pdf` | OK | `1 HECHOS` … `6 RESULTADO   ESCALAR · v3.R6` · **0.235 s** |
| 8 | Demo sin red en el clon | `uv run python scripts/demo_caos.py --sin-red` | OK | paso 1 `run → exit 1 · entrega escrita: no` y las 3 `extract pendiente (LLM-DOWN) → decide skip → emit pendiente · decisión: NINGUNA`; paso 2 `run → exit 0 · outcomes.jsonl 1ec4be206089`; paso 3 `(igual: True)` · `Demo: 3.7 s` / pared **3.838 s** |
| 9 | `--listar` en el clon | `uv run python scripts/dato_en_vivo.py --listar` | OK | primer pedido `PO-2026-0001 · 9221.75 EUR · … ['F26-9865_ofimática.pdf']` · **0.191 s** |
| 10 | `--pagada` del primero listado | `uv run python scripts/dato_en_vivo.py --pagada PO-2026-0001` | OK | `1 de 500 recalculadas · 1 cambian` · `F26-9865_ofimática.pdf: PAGAR → NO_PAGAR` · **0.657 s** |
| 11 | Bonus en el clon | `uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000` | OK | `"decisiones_pagar": 438` · `"calendario_total_eur": "2428159.06"` · `Calendario: dist/bonus/calendario.html` · **0.228 s** |
| 12 | Chat se niega en local | `uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf"` | OK | `"estado": "solo_lectura"` · `"modelo": "sin_modelo"` · `"latencia_ms": 0` · **0.255 s** |
| 13 | `scripts/smoke.sh` en la carpeta de revisión | `bash scripts/smoke.sh` | OK | `VEREDICTO: OK` · **2.474 s** (docs/revision/r4/smoke-revision.log) |
| 14 | `scripts/smoke.sh` en el clon | `cp scripts/smoke.sh dist/ensayo/r4/limpio/scripts/ && bash scripts/smoke.sh` | OK | `VEREDICTO: OK` · **2.962 s** (docs/revision/r4/smoke-clon.log) |
| 15 | Quitar el clon | `git worktree remove dist/ensayo/r4/limpio --force` | OK | el worktree ya no está en `git worktree list` |
| 16 | Huellas al terminar | `sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl \| cut -c1-12` | OK | `8501d9975c38` / `1ec4be206089` (iguales que al empezar) |

## Hallazgos (lo que está mal o confunde), de más grave a menos
| # | Gravedad (alta/media/baja) | Dónde (fichero:línea o comando) | Qué pasa | Propuesta (parche en texto si es fuera de mis ficheros) |
|---|---|---|---|---|
| 1 | media | `uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000` | El comando sale 0 y escribe el calendario. En `semanas` hay `"2026-W35": {"numero": 19, "importe_eur": "184374.50"}`, por encima del tope 150000. El tope no recorta esas semanas en el JSON de `informe.resumen()`. | Fuera de mis ficheros (`src/albertitos/bonus/`). No lo he cambiado. Si el tope debe aplicar al calendario, que lo haga `tesoreria.programa` y que `resumen()` lo enseñe; si el tope sólo vale para la remesa programada, que `--help` lo diga. |
| 2 | baja | `docs/agentes/KIT-DEFENSA.md` (antes: `--pagada PO-2026-0003`) | `--listar` empieza por `PO-2026-0001` (`F26-9865_ofimática.pdf`). El PLAN-12 pedía `--pagada <el primer pedido que liste>`: lo he corrido así y cambia 1 de 500 a NO_PAGAR. La chuleta anterior usaba 0003 (`factura_8764.pdf`), que también está en la lista. | He dejado 0003 en la tabla histórica de la chuleta y he puesto 0001 en la cabecera, que es lo ejecutado. Los dos sirven. |
| 3 | baja | `scripts/kit_demo.py empaquetar` | El sha256 del fichero `dist/albertitos.db` es `8501d9975c38`; el de la BD **dentro** del kit es `c8639c8af1b6`. Los recuentos coinciden. `kit_demo.copiar_bd` hace `backup()` + `PRAGMA journal_mode=DELETE`. | No es un fallo de recuentos. No toco `kit_demo.py`. |

## Lo que he cambiado yo
| Commit | Ficheros | Qué y por qué | Cómo se prueba |
|---|---|---|---|
| (este ciclo) | `docs/agentes/KIT-DEFENSA.md` | Tiempos del clon de las 15:55; kit `1555`; `smoke.sh` antes de salir; demo ~3,7 s; una línea del bonus y otra del chat | Leer la chuleta; los comandos de las filas 4 y 5 de «En la sala» son los ejecutados en #11 y #12 |

## Lo que he añadido (la cosa sencilla)
- `scripts/smoke.sh` · desde la raíz: `bash scripts/smoke.sh` · no hay test en `tests/` (no está en mi lista de ficheros); la prueba es la ejecución #13 y #14 · 6 pasos de sólo lectura (status, auditoría, trace, bonus a `dist/smoke/`, `/confianza/resumen` por `despachar` en memoria, chat que se niega) y `exit 1` si alguno falla. 2,5 s en revisión y 3,0 s en el clon.

## make check al final
- literal: "574 passed, 1 skipped, 2 deselected in 57.75s"

## Lo que no he podido hacer y por qué
- El `instalar` del kit lo cronometré con `--sin-status` para separar el tiempo del paso 6 (`status`). El comando de la chuleta (`make kit-instalar KIT=…`) sí corre `status` al final. No he repetido el instalar sin `--sin-status`.
- No he repetido el breaker de RESILIENCIA §3 (b bis) ni abierto Streamlit: el PLAN-12 no los pedía en los pasos 2–3.
- No hay test pytest de `smoke.sh`: `tests/` no es mío en este plan.
