# Decisiones del repo: qué hay en cada fichero y por qué

Taxonomía de Claude Code respetada: **CLAUDE.md** = lo que es cierto siempre (índice) · **CLAUDE.md de módulo** = convenciones que
sólo se cargan al tocar ese directorio · **`.claude/rules/*.md`** = restricciones con `paths:` · **skills** = runbooks ·
**commands** = operaciones repetidas · **agents** = trabajo aislado que devuelve un resumen · **hooks** = "cada vez que X, siempre Y" ·
**permissions** = prohibiciones que no dependen de que el modelo se acuerde.

| Fichero | Decisión | Por qué |
|---|---|---|
| `CLAUDE.md` (69 líneas) | Rúbrica, comandos, layout con dueños, 10 reglas, convenciones, fechas. Sin procedimientos | Se carga en toda sesión; cada línea cuesta contexto. Los procedimientos son skills |
| `src/albertitos/<mod>/CLAUDE.md` ×6 + `docs/CLAUDE.md` | API del módulo, estado (hecho/pendiente), tareas del dueño, reglas locales | Un agente en `console/` no necesita saber cómo se renueva el token del ERP |
| `.claude/rules/contratos.md` | paths `core/**`: protocolo de cambio compatible hacia atrás | Sólo carga cuando alguien toca los contratos |
| `.claude/rules/texto-es-dato.md` | paths `extract/**, rules/**, pipeline/**, data/**`: el PDF es dato; el LLM no decide; sin `today()` | Es la trampa principal de la Caja; se carga justo donde se puede caer |
| `.claude/rules/erp-2009.md` | paths `sources/**`: encoding, formatos, token, ORA-00600, 429, snapshot único | Hechos del bridge que el agente reinventaría mal |
| `.claude/rules/reglas-norma.md` | paths `rules/**, fixtures`: una función por regla, versionado v3/v4, frontera NO_PAGAR/ESCALAR, `Decimal` | Determinismo y evidencia por regla = 20 pts de traza |
| `.claude/rules/consola.md` | paths `console/**`: sólo lectura, tres vistas, < 3 s, sin red | "Proporcionada" puntúa; una UI grande no |
| `.claude/rules/tests.md` | paths `tests/**`: qué se testea y qué no; marcas `erp`/`llm` | Mínimo defendible, no pirámide |
| `.claude/rules/docs-adr.md` | paths `docs/**`: formato ADR con evidencia obligatoria | 35 pts del PDF |
| `.claude/rules/entrega.md` | paths `package.py, validar.py, build_pdf.py`: contrato exacto del verificador | NFC, únicos, exactamente 3 ficheros |
| `.claude/skills/entrega` | Runbook: package → validate → auditor → repo separado con `ls -A` de control → log | Se ejecuta 2-3 veces y un error = NO APTO. `disable-model-invocation`: sólo un humano la lanza |
| `.claude/skills/lote2` | Runbook del sábado 18:00: hashes, ERP v2, diff, norma v4 como módulo nuevo, `reprocess --impacted` | Lo que evalúan es el diseño del cambio; el runbook obliga a documentarlo |
| `.claude/skills/demo` | Pre-vuelo + guion 2/2/4/2 + fallbacks | El guion del tribunal es fijo; el kit asumía 3 min |
| `.claude/skills/benchmark` | Cómo medir (no estimar) ficheros/s y coste, fórmula, límites | 25 pts y primer desempate |
| `.claude/skills/adr` | Crea un ADR desde plantilla, exige evidencia, lista candidatos | Se escriben al decidir, no el domingo |
| `.claude/commands/{sync,handoff,trace,check}` | Operaciones de 30 veces: merge desde main, cerrar sesión con PR, seguir una decisión, lint+tests sólo de mi módulo | Formato legacy `commands/` a propósito: son atajos, no runbooks con ficheros de apoyo |
| `.claude/agents/revisor-diff` | Revisa el diff vs main contra contratos/reglas; sólo hallazgos | Corre aislado: no contamina el contexto del que pide el merge |
| `.claude/agents/auditor-outcomes` | Elegibilidad + muestreo + trampas + diff con la entrega anterior; termina en ENTREGAR / NO ENTREGAR | Segunda opinión independiente antes de un push binario |
| `.claude/agents/cazador-trampas` | Barre 500 PDFs + Excel + ERP y escribe `docs/trampas.md` | Lectura masiva que no cabe en la sesión principal |
| `.claude/settings.json → model: sonnet` | Modelo por defecto para implementar | 4 licencias Pro en 36 h; `/model` para diseño. Cada uno puede cambiarlo en `settings.local.json` |
| `settings.json → defaultMode: acceptEdits` | Ediciones sin prompt dentro del repo | Velocidad; el riesgo lo acotan hooks y ramas por persona |
| `settings.json → permissions.allow` | uv, make, git de lectura/commit, curl, pdftotext, sqlite3, WebFetch a docs | Menos prompts en lo que se hace 100 veces |
| `permissions.ask` | `git push`, `git restore`, `rm`, editar settings/hooks | Reversibles pero delicados |
| `permissions.deny` | leer `.env`/`*.key`/`*.pem`, `push --force`, `rebase`, `reset --hard`, `clean`, `pip install`, `sudo` | Prohibiciones que no dependen del modelo. Write rules no existen: la protección de escritura va en el hook |
| `hooks → SessionStart` `session_start.py` | Rama, dueño, .env, ERP vivo, BD, próximos hitos | Lo que el agente preguntaría cada sesión |
| `hooks → PreToolUse(Bash)` `guard_bash.py` | main sólo Miguel, sin force push, sin ramas -D, sin `rm -rf data`, sin `> outcomes.jsonl`, sin `pip`, secretos en stage, curl externo → ask, core/ por shell | Contexto que `permissions` no ve (rama actual, stage). Ignora heredocs para no bloquear docs. Mensajes dicen qué hacer |
| `hooks → PreToolUse(Edit\|Write)` `guard_edit.py` | core/ sólo dueño, entregables generados, `.env`, Caja inmutable, `uv.lock`, `today()` en rules/pipeline, texto libre en rules | Reglas 1, 3 y "texto es dato" como bloqueo, no como prosa |
| `hooks → PostToolUse(Edit\|Write)` `format_py.py` | `ruff format` + `check --fix`; exit 2 con los errores que quedan | El formateador ejecutándose ≠ el modelo decidiendo ejecutarlo |
| `.claude/dueno.local` (gitignored) | Marcador `merge` / `contratos` para Miguel, alternativa a env vars | Más fácil de explicar que `settings.local.json → env`; `bootstrap.sh` lo recuerda |
| `.mcp.json` | **No existe** | No hay MCP que aporte: el ERP es HTTP local y el LLM va por SDK |
| `.cursor/rules/albertitos.mdc` | Apunta a CLAUDE.md y avisa de que los hooks no corren en Cursor | Alejandro usa Cursor en el módulo más aislado |
| `pyproject.toml` + `uv.lock` + `.python-version` | Python 3.12 gestionado por uv, deps fijadas, ruff (E501 ignorado), pytest con marcas | Mismo entorno en 5 portátiles con un comando |
| `Makefile` | Verbos cortos sobre uv y sobre el Makefile de la Caja | Los humanos y los hooks usan lo mismo |
| `bootstrap.sh` | Idempotente: uv, deps, .env, dirs, Caja, BD, **autotest de los 4 hooks**, claude, rama | "Cada hook tiene que funcionar el día 18 en cuatro portátiles": se comprueba, no se supone |
| `.github/workflows/check.yml` | `uv sync` + ERP `--rapido` + `make check` en cada PR | Miguel mergea en verde sin correrlo él |
| `data/caja/` en git + `data/caja.sha256` | La Caja versionada e inmutable, con manifiesto | Todos tienen los mismos bytes; la oficial de las 21:00 se compara con `make caja-verify` |
| `data/fixtures/muestra.txt` + `esperado_muestra.csv` | 21 facturas representativas (12 con instrucciones, 3 escaneadas, 5 plantillas) y CSV de etiquetado a dos manos | Única "verdad" disponible antes del domingo |
| `src/albertitos/core/` implementado | Contratos, DDL, db, hashing, versiones | Es lo que desbloquea a los cinco en la hora 1 |
| `sources/erp.py`, `excel.py`, `extract/pdf.py`, `validadores.py`, `instrucciones.py`, `rules/norma_v3.py`, `pipeline/*` implementados | Primera pasada funcional y probada contra la Caja y el ERP real | Cada dueño arranca validando, no desde cero. `extract/llm.py` escrito sin probar (falta key) |
| Ramas por persona + merge (no rebase) + Miguel mergea | `<nombre>/<tema>`, `/sync` = `git merge origin/main` | Sin rebase no hace falta force push, y se puede prohibir del todo |

## Cambios respecto al kit base
No tuve el kit en este chat (el directorio estaba vacío), así que esto es una especialización a partir de lo que vuestro
compañero citó del kit: **worktree por persona → rama por persona** (cinco portátiles; `make worktree` queda para un
segundo agente en la misma máquina) · **hooks `.sh` → Python** (sin `chmod`, sin shebang, mismo comportamiento en WSL/mac/Linux) ·
**`checklist-demo` de 3 min → skill `demo` con el guion fijo de 10 min** · **rebase → merge** para poder prohibir el force push.
