# RESUMEN R2 · Documentación: cifras, comandos, ADRs y enlaces · 15:53–15:57

## Huellas
- al empezar: BD 8501d9975c38 · outcomes 1ec4be206089   ·   al terminar: BD 8501d9975c38 · outcomes 1ec4be206089

## Comprobaciones (una fila por comprobación)
| # | Qué comprobé | Comando exacto | Resultado (OK / FALLA / RARO) | Salida literal que lo demuestra |
|---|---|---|---|---|
| 1 | `cifras_check` (formas obsoletas del catálogo) | `uv run python scripts/cifras_check.py` | OK | `OK: ninguna forma obsoleta del catálogo en los cuatro documentos.` |
| 2 | Decisiones vigentes lote 1 | `uv run albertitos status` | OK | `decisiones vigentes: {'ESCALAR': 53, 'NO_PAGAR': 9, 'PAGAR': 438}` · `ficheros por lote: {1: 500}` · `caché LLM: 881` |
| 3 | C1 de CIFRAS.md (BD sólo lectura) | SQL de `docs/CIFRAS.md` §C1 | OK | `[(500,)]` ficheros · `[('cache', 31), ('llm_texto', 1), ('plantilla', 468)]` · `[('ESCALAR', 53), ('NO_PAGAR', 9), ('PAGAR', 438)]` |
| 4 | Totales del bonus | `uv run python -m albertitos.bonus --salida dist/ensayo/r2/bonus` | OK | `decisiones_pagar: 438` · `calendario_total_eur: "2428159.06"` · `vencidos: 431` · `tesoreria.json`: `vencido_importe_eur=2383400.88` · `en_plazo_importe_eur=44758.18` |
| 5 | «16 semanas» con tope 150000 | `uv run python -m albertitos.bonus --salida dist/ensayo/r2/bonus-tope --tope-semanal 150000` | OK | `semanas_para_ponerse_al_dia 16` · `semanas_para_pagarlo_todo 17` |
| 6 | Hash de la entrega citada | `sha256sum dist/entrega/outcomes.jsonl \| cut -c1-12` | OK | `1ec4be206089` (igual que ESTADO-BACKEND, KIT-DEFENSA y CIFRAS) |
| 7 | `438/53/9`, `2.428.159,06`, `2.383.400,88`, `16 semanas`, `1ec4be206089` en mis docs y en KIT/CLAUDE | búsqueda literal | OK en las cifras de negocio; ver hallazgos por el recuento de tests y de ADRs | ESTADO L8 `438/53/9` + `1ec4be206089`; BONUS L29/L70 `2.428.159,06`; api/bonus.md L48 `2.383.400,88` y L50 `16 semanas`. CLAUDE.md no las cita. CIFRAS L13 marca `443/48/9` como «Antes de ADR-0011». |
| 8 | Comandos citados: `albertitos {run,status,trace,reprocess,bench}` y `python -m albertitos.{bonus,chat,confianza.revisor,console.api}` | `--help` de cada uno | OK | Todos existen. Opciones usadas (`--salida`, `--fecha-corte`, `--erp`, `--impacted`, `--desde`, `--db`, `--tope-semanal`, `--servidor`, `--maximo`) salen en el help. Salida: `docs/revision/r2/helps.txt` |
| 9 | Índice de ADRs vs `docs/adr/*.md` | `ls docs/adr/` frente a `docs/adr/README.md` | RARO | 14 ficheros 0001–0014, todos en el índice. Plantilla 0000 fuera, como debe. **0012: fichero dice «implementado», índice dice «aceptado»**. 0013 índice añade «(14/15 + 1 parcial)» al «implementado y evaluado» del fichero. |
| 10 | Enlaces relativos del repo | `uv run python scripts/enlaces_check.py` | FALLA (6 rotos, ninguno en mis ficheros) | ver §Hallazgos y `docs/revision/r2/enlaces.txt` |
| 11 | Tests del comprobador | `uv run pytest -q tests/test_enlaces.py` | OK | `4 passed in 0.06s` |

## Hallazgos (lo que está mal o confunde), de más grave a menos
| # | Gravedad (alta/media/baja) | Dónde (fichero:línea o comando) | Qué pasa | Propuesta (parche en texto si es fuera de mis ficheros) |
|---|---|---|---|---|
| 1 | media | `docs/adr/0012-calendario-remesa-solo-lectura.md:3` vs `docs/adr/README.md` fila 0012 | El fichero dice «Estado: implementado»; el índice dice «aceptado». No es el mismo estado. | Fuera de mis ficheros. Unificar: o el README pasa a «implementado», o el ADR pasa a `- **Estado:** aceptado`. |
| 2 | media | `docs/agentes/partes/PARTE-10.md:44` | `[docs/agentes/ENSAYO-FUENTES.md](ENSAYO-FUENTES.md)` se resuelve a `docs/agentes/partes/ENSAYO-FUENTES.md`, que no existe. El fichero real es `docs/agentes/ENSAYO-FUENTES.md`. | Cambiar el destino a `../ENSAYO-FUENTES.md`. |
| 3 | baja | `docs/agentes/fix_invoice_detail_6009103d.plan.md:66,77,81` | Cinco enlaces `console-web/...` y `src/albertitos/console/api.py` relativos al plan (en `docs/agentes/`). Los ficheros sí están en la raíz del repo. | Prefijo `../../` (a `console-web/...` y `src/...`) o rutas desde la raíz documentadas como código, no como enlace. |
| 4 | baja | `docs/adr/README.md` candidatos | El pie sigue hablando de «qué hace la norma con DOCUMENTO_SUPERPUESTO» y de la frontera NO_PAGAR/ESCALAR como ADRs por crear: 0010 y 0011 ya existen. | Fuera de mis ficheros. Borrar esas dos líneas de «Candidatos». |
| 5 | baja | `docs/api/chat.md:114` | Cita `make check: 555 passed` (evaluación K2). Hoy es `574 passed, 1 skipped, 2 deselected`. | Marcarla como histórica: «K2, 19/09: 555 passed». No la toco: es el recuento de aquella pasada, no el de ahora. |
| 6 | baja | `docs/ESTADO-BACKEND.md:9,21` (ya pulido) | Decía **513 tests** como cifra vigente. `make check` en esta carpeta: **574 passed**. | Hecho: Linux → 574; Windows 513 queda como «último CI, no repetido». |

## Lo que he cambiado yo
| Commit | Ficheros | Qué y por qué | Cómo se prueba |
|---|---|---|---|
| (este ciclo) | `scripts/enlaces_check.py` · `tests/test_enlaces.py` | Comprobador de enlaces relativos y sus 4 tests | `uv run pytest -q tests/test_enlaces.py` · `uv run python scripts/enlaces_check.py` |
| (este ciclo) | `docs/ESTADO-BACKEND.md` | 12 ADRs → 14; 513 tests de Linux → 574 medidos aquí; Windows 513 marcado como CI no repetido | `grep -n '14 ADRs\\|574 passed\\|windows-latest' docs/ESTADO-BACKEND.md` |
| (este ciclo) | `docs/revision/RESUMEN-R2.md` · `docs/revision/r2/*` · `docs/revision/BITACORA-R.md` | Resumen, salidas y bitácora | lectura |

## Lo que he añadido (la cosa sencilla)
- `scripts/enlaces_check.py`: recorre `docs/**/*.md`, `CLAUDE.md` y `README.md` si existe; extrae `[texto](ruta)` y `[texto](ruta#ancla)`; ignora `http(s)://`, `mailto:`, anclas solas, imágenes `![…](…)`, bloques ` ``` ` y el falso positivo `rutas()["/x"](conn, …)`. Imprime `fichero:línea → destino` y sale 1 si hay rotos. Sólo lee.
- Cómo se usa: `uv run python scripts/enlaces_check.py` (opcional `--raiz`).
- Test: `tests/test_enlaces.py` — árbol temporal con uno bueno, uno roto (`docs/no-existe.md#ancla`), uno `https://` y uno dentro de un fence; más el de `conn,`.
- Por qué ayuda: el tribunal y Alfonso saltan de un doc a otro; un enlace a `ENSAYO-FUENTES.md` desde `partes/` es un 404 silencioso.

## make check al final
- literal: `574 passed, 1 skipped, 2 deselected in 48.97s`

## Lo que no he podido hacer y por qué
- No he corrido el CI de Windows: no toco GitHub. El 513 de `windows-latest` queda como último CI, no como cifra de esta pasada.
- No he arreglado los 6 enlaces rotos: están en `docs/agentes/` (R1/bitácora/planes), fuera de mi lista.
- No he unificado el estado del ADR-0012: `docs/adr/` no es mío.
