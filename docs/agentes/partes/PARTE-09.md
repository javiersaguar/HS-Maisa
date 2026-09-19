# Parte de fin de ciclo · ciclo 9 (sin plan todavía)

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2 · 05: E1-E3 · 06: F1-F2 · 07: G1-G2 · 08: H1-H2).

## I1 · Javier · ensayo lote2 + P0-5 — BLOQUEADO (shell)

**Veredicto:** PARO documentado. Sin terminal usable no se pudo hacer el ensayo A, `make check`, huellas, worktree ni commits.

**Bloqueo:** el Shell de Cursor falla al arrancar PowerShell:
`spawn C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe ENOENT`
(también: sandbox `workspace_readwrite` no disponible en este host). Un `TZ=Europe/Madrid date` llegó a devolver `11:30` al inicio; luego todo shell murió. No se inventa hora → **BITACORA no se pudo appendar con hora válida** hasta recuperar el terminal (hay borrador al final con cabecera `¿¿:??`).

**Hecho offline (Write, sin shell):**
- `data/fixtures/lote2_nombre_repetido/facturas/2026-01-16_P004.pdf` (PDF mínimo distinto del de Caja; nombre lote1 **no** en `muestra.txt`)
- `data/fixtures/lote2_nombre_repetido/README.md` (sha256 12 chars pendiente de `sha256sum`; sustituir PDF por `cp` de `lote2_sim/L2-2026-01-16_P004.pdf` si se exige el sim)
- `tests/test_nombre_repetido.py` (fixture + 2 tests «hoy» + 1 xfail strict P0-5)
- `docs/agentes/CHULETA-LOTE2.md` (nuevo)
- skill `/lote2`: párrafo P0-5 + enlace a chuleta

**Pendiente al recuperar shell (orden):**
1. `TZ=Europe/Madrid date +%H:%M` → corregir BITACORA + **PIDO A Miguel** P0-5
2. Preflight del prompt (pull, curl :8009, huellas, `make check`)
3. Worktree `dist/ensayo/i1/wt` + merge `origin/miguel/pipeline`; ERP propio :8010; TAREA A → `ensayo.log`
4. Completar README sha256; ENSAYO-LOTE2 § I1 ciclo 9; CIFRAS filas medidas
5. `make check` + `agentes-check`; huellas iguales; apagar sólo :8010; `git worktree remove --force`
6. Commits rutas explícitas; PARTE I1 final

**No tocado:** `:8009`, `dist/albertitos.db`, `dist/entrega/`, `core/`, `pipeline/`, `rules/`, parche P0-5, `make publicar`.

## I2 · Javier · mapa de políticas lote 1 — HECHO

**Veredicto:** HECHO. CONTROL OK 438/53/9 fichero a fichero. Script + tests + MAPA-POLITICAS.md.

**Recuentos (todos / sin muestra):** Q1 6/0 · Q2a 0/0 · Q2b 2/0 · Q3 35/28 · Q4 2/0 · Q5 2/2. Avisos: TEXTO_INSTRUCCION=31 · PEDIDO_ANULADO=2. Comprobación manual Q1/Q2: 6 LIMPIA · 2 OTRA_REGLA · 0 DATO (detalle en `dist/ensayo/i2/`, fuera del repo publicado).

**Comandos:** `uv run python scripts/mapa_politicas.py --excluir-muestra` · `make check` → 425 passed, 6 xfailed · `uv run pytest tests/test_mapa_politicas.py -q` → 4 passed. Huellas: c66d00e45be3 / 1ec4be206089.

**PIDO A Mónica:** lleva los números al mentor; lista por fichero de la muestra cuando cierres.

**No tocado:** `rules/`, `core/`, `pipeline/`, BD real, entrega.
