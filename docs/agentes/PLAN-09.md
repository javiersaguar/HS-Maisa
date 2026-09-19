# PLAN-09 · ciclo 9 · sábado 19/09 ~11:35 → ~13:30 · rama `javier/ingesta` · dos agentes

**Dónde estamos (11:25).** `javier/ingesta` = `59ca8a7`, con `main` dentro: 418 tests en verde y 5 xfail. Entrega
publicada `232bb76` (438/53/9, `1ec4be206089`). Miguel tiene P0-1, P0-4 y la trazabilidad en `miguel/pipeline`, sin
mergear a `main`, y validados con lo de H1 (bitácora 11:10). Mónica no ha subido la muestra (0 de 21).

**Por qué este ciclo.** Nada de lo que queda es construir. Son las dos cosas que pueden dejarnos NO APTO y que caen en
lo de Javier:

1. **El lote 2 de las 18:00 es de Javier, y su último ensayo es anterior a casi todo.** E3 lo ensayó a las 01:52.
   Desde entonces han cambiado la ingesta (tabla `identidades`), `run --erp`, `package --aceptar-rojo`, `trace`,
   `status` y la auditoría dentro de `package`. Además, hay un riesgo sin probar: **P0-5**, un PDF del lote 2 con el
   mismo nombre que uno del lote 1 y distinto contenido. **I1 hace el ensayo general con el código que habrá a las
   18:00**, cronometrado, y deja la receta y una chuleta de una página al día.
2. **La validación es binaria, y hay decisiones del lote 1 que dependen de preguntas que el mentor no ha contestado.**
   La norma escala siempre un texto que ordena la decisión (`TEXTO_INSTRUCCION` está en `ANOMALIAS_HUMANO`), y la Caja
   tiene 31. Hay más preguntas en el aire: el pedido «anulado según el PDF», la frontera NO_PAGAR/ESCALAR, los
   «documentos de prueba del evaluador» y el duplicado `PO-2026-0492`. Si la referencia lee alguna de otra manera,
   varias líneas no se aceptan. Nadie ha medido cuántas. **I2 mide cuántas decisiones del lote 1 cambiarían con cada
   respuesta posible**: sin tocar `rules/`, con la norma real simulada en memoria. Así Mónica llega al mentor con
   números y la palanca preparada.

| Agente | Misión | Lo que hay al terminar |
|---|---|---|
| **I1** | Ensayo general del lote 2 contra `javier/ingesta` + `miguel/pipeline`, con ERP v2 en otro puerto; P0-5 reproducido | tiempos por paso · `.claude/skills/lote2/SKILL.md` al día · `docs/agentes/CHULETA-LOTE2.md` (una página) · sección nueva en `ENSAYO-LOTE2.md` · fixture y test xfail de P0-5 (sin parche) |
| **I2** | Mapa de las decisiones del lote 1 que dependen de una política abierta | `scripts/mapa_politicas.py` (sólo lectura) + tests · `MAPA-POLITICAS.md` (método y recuentos por pregunta) · la lista por fichero, **fuera del repo** hasta que Mónica cierre la muestra |

## Antes de lanzar (Javier, 3 min)
```bash
cd /home/javier/proyectos/HackSpain && git switch javier/ingesta && git pull --ff-only && make check   # 418 + 5 xfail
curl -s http://127.0.0.1:8009/erp/estado | grep asientos        # 516: es el de todos, nadie lo para
uv run python scripts/auditoria_entrega.py                       # VERDE
sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl | cut -c1-12
mkdir -p dist/ensayo/i1 dist/ensayo/i2
```
**Dos líneas antes de lanzar:**
- **A Miguel:** «I1 ensaya el lote 2 contra tu rama en un worktree. De P0-5 prepara sólo un fixture y un test xfail;
  parche no. Si ya lo estás haciendo tú, dímelo y lo quito».
- **A Mónica:** «I2 cuenta cuántas decisiones del lote 1 dependen de cada pregunta abierta del mentor. Te da los
  números, pero la lista por fichero no, hasta que cierres la muestra».

Durante el ciclo **ningún agente escribe en `dist/albertitos.db`, `dist/entrega/` ni `../HS-Maisa-Entrega`**, ni para el
bridge de :8009.

## Propiedad de ficheros (`plan.json`; `make agentes-check`)
| I1 | I2 |
|---|---|
| `.claude/skills/lote2/SKILL.md` · `docs/agentes/ENSAYO-LOTE2.md` · `docs/agentes/CHULETA-LOTE2.md` (nuevo) · `data/fixtures/lote2_nombre_repetido/*` (nuevo) · `tests/test_nombre_repetido.py` (nuevo) · `scripts/verificar_material.py` · `tests/test_material.py` · `scripts/preflight_lote2.py` · `tests/test_preflight.py` · `docs/CIFRAS.md` (sólo filas nuevas) | `scripts/mapa_politicas.py` (nuevo) · `tests/test_mapa_politicas.py` (nuevo) · `docs/agentes/MAPA-POLITICAS.md` (nuevo) |

Compartidos, sólo añadiendo al final: `docs/agentes/BITACORA.md` y `docs/agentes/PARTE.md`. Nadie toca `core/`, `pipeline/`,
`cli.py` ni `rules/`, ni `data/caja/`, ni `data/fixtures/esperado_muestra.csv`, ni `docs/trampas.md`: la lista por
fichero de I2 contaminaría a Mónica.

---

## Prompt I1 · Ensayo general del lote 2 con el código de las 18:00

```
Eres el agente I1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (I2) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas, EN EL ÁRBOL PRINCIPAL: .claude/skills/lote2/SKILL.md · docs/agentes/ENSAYO-LOTE2.md · docs/agentes/CHULETA-LOTE2.md (nuevo) · data/fixtures/lote2_nombre_repetido/ (nuevo) · tests/test_nombre_repetido.py (nuevo) · scripts/verificar_material.py · tests/test_material.py · scripts/preflight_lote2.py · tests/test_preflight.py · docs/CIFRAS.md (sólo añadir filas medidas por ti). Cualquier otra cosa: `PIDO A Miguel:` / `PIDO A Mónica:` en docs/agentes/BITACORA.md.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar, siempre con heredoc de comillas simples (<<'EOF'). **Pon la hora con `TZ=Europe/Madrid date +%H:%M`, nunca calculada.** Lee las de I2 antes de cada hito.
3. En el árbol principal: no cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. NUNCA escribas en la BD real (`dist/albertitos.db`), `dist/entrega/` ni `../HS-Maisa-Entrega`. **No pares ni reinicies el bridge de :8009 (lo usa todo el equipo)**: el tuyo va en :8010. Nunca leas `.env`. data/caja/ es inmutable.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "I1" de docs/agentes/PARTE.md.
6. Lee antes: CLAUDE.md, docs/ESTADO-BACKEND.md, .claude/skills/lote2/SKILL.md (la receta que vas a ensayar), docs/agentes/ENSAYO-LOTE2.md (el ensayo de E3, 01:52: tus tiempos se comparan con los suyos), docs/agentes/P0-1-IDENTICOS.md, la entrada «19/09 10:55 · Miguel» de la bitácora (lo que cambió en su rama y el riesgo P0-5), dist/ensayo/p01/e2e.log (el ensayo de P0-1 de las 11:04), data/caja/MANUAL_ERP_2009.md y `uv run albertitos --help` en el worktree.

EL CÓDIGO QUE SE ENSAYA ES EL DE LAS 18:00, no el de tu rama: `javier/ingesta` + `origin/miguel/pipeline`. Móntalo en un worktree desechable:
  git worktree add --detach dist/ensayo/i1/wt HEAD && cd dist/ensayo/i1/wt && git merge --no-edit origin/miguel/pipeline
Ése es el ÚNICO sitio donde puedes hacer merge. Si Miguel mergea a main o sube algo durante el ciclo, `git fetch` y rehaz el worktree. Dentro del worktree, `uv run` usa su propio src. Ejecutas allí; editas en el árbol principal.
  - BD de ensayo: copia de la real con `sqlite3.Connection.backup` (nunca cp con WAL) en el worktree; `ALBERTITOS_DB` y `ALBERTITOS_CHAOS` apuntando a ficheros del worktree.
  - ERP v2: `uv run python data/caja/alberto_erp.py --puerto 8010 --lote2 data/fixtures/erp_lote2_simulado.csv` en segundo plano, y `ALBERTITOS_ERP_URL=http://127.0.0.1:8010`. Apágalo al terminar (sólo el tuyo).
  - Material: `data/lote2/facturas` DEL WORKTREE con lote2_sim (10) + lote2_identicos (4) + el caso P0-5 (abajo). Así, a las 18:00, lo único nuevo es el ZIP.

TAREAS
A · ENSAYO GENERAL cronometrado, paso a paso como dice la skill /lote2, con `time` de pared por comando y su salida literal en dist/ensayo/i1/ensayo.log:
  preflight → verificar_material (directorio, y un ZIP con el CSV del ERP, `--hash` y `--esperados`) → ingest → `run --erp v1` (o extract + reprocess, lo que diga la skill, y si la skill está mal, corrígela) → status → `erp pull --tag v2` (contra :8010) → `erp diff v1 v2` → `reprocess --impacted --erp v2` → inventario → auditoría → package → validate ×2 → trace de tres casos: una copia exacta, uno que cambia por el diff del ERP y uno del lote 2 normal.
  - La regla nueva es de Mónica, no la escribas: deja su hueco marcado en la receta, con el comando que irá entonces (`reprocess --todo --norma v4 --erp v2`), y cronometra el mismo paso con `--norma v3` para saber cuánto tarda.
  - `--aceptar-rojo`: compruébalo en la copia forzando un rojo (p. ej. borrando una decisión en la copia) y escribe en la receta cuándo se usa: último recurso, con el motivo, y nunca por un JSONL inválido.
  - La contingencia (ADR-0009), sólo en seco: `scripts/contingencia.py --lote 2`, sin `--aplicar`.
  - Opcional, si el LLM contesta: las 2 escaneadas de lote2_sim en frío, en una BD sin su caché, para saber cuánto tarda la visión de verdad a las 18:00. Apunta tokens y tiempo; máximo 2 PDFs.
B · P0-5, el mismo nombre que un PDF del lote 1 y distinto contenido (bitácora de Miguel, 10:55). Hoy el verificador lo marca ROJO y la ingesta falla: NO APTO. Lo decide Miguel; tú no escribes parche.
  - `data/fixtures/lote2_nombre_repetido/facturas/`: un PDF de lote2_sim copiado con el nombre de un PDF del lote 1 que NO esté en data/fixtures/muestra.txt, más un README de tres líneas (qué es y sus sha256).
  - `tests/test_nombre_repetido.py`, sin red y con BDs temporales: lo que tendría que pasar (el lote 1 conserva su línea; el del lote 2 tiene la suya con SU decisión; validate APTO en los dos), con `@pytest.mark.xfail(strict=True, reason="P0-5: lo decide Miguel")`; y lo que pasa hoy, en un test normal. `make check` sigue verde.
  - En el ensayo: qué dice el verificador y qué hace la ingesta, literal. En la skill y en la chuleta, qué hacer a las 18:00 si aparece: parar, avisar a Miguel y no renombrar nunca un PDF oficial.
  - `PIDO A Miguel:` en la bitácora, con el fixture y el test, al empezar B (no al final).
C · LA RECETA Y LA CHULETA
  - `.claude/skills/lote2/SKILL.md`: al día con el CLI real del worktree (run --erp, trace legible, status, --aceptar-rojo, P0-1 y P0-5). Quita lo que ya no aplica («si aún no admite run --erp…»). Cada paso, con su tiempo medido.
  - `docs/agentes/CHULETA-LOTE2.md`, una página para Javier a las 18:00: los comandos en orden, lo que tiene que salir, cuánto tarda y qué hacer si no sale, y arriba las variables de entorno. Sin nada que no hayas ejecutado.
  - `docs/agentes/ENSAYO-LOTE2.md`: sección nueva «Ensayo I1 · ciclo 9», con la tabla de tiempos frente a los de E3 y lo que ha cambiado.
  - Si el preflight o el verificador no entienden la tabla `identidades` o dan un falso rojo con el código nuevo, arréglalo en tu script con su test. Si el fallo está en el código de Miguel, PIDO A Miguel.
  - `docs/CIFRAS.md`: sólo filas nuevas con lo que midas (población, máquina, fecha y comando), y `uv run python scripts/cifras_check.py` sin coincidencias nuevas.

CRITERIOS DE ACEPTACIÓN: el ensayo de punta a punta con el código de las 18:00 llega a package APTO en los dos lotes, o se para donde tiene que pararse y lo dice; cada paso de la skill está ejecutado y cronometrado; P0-5 reproducido con fixture y xfail estricto; chuleta de una página; `make check` y `make agentes-check` verdes en el árbol; la BD real y dist/entrega con el mismo sha256 antes y después (apúntalos); el bridge de :8009 vivo al terminar; worktree quitado (`git worktree remove --force`).

NO HAGAS: editar core/, pipeline/, cli.py ni rules/; tocar el bridge de :8009; escribir en la BD real o en la entrega; escribir un parche para P0-5; ejecutar `make publicar` (ni en seco: toca GitHub).
```

---

## Prompt I2 · El mapa de las decisiones que dependen de una política abierta

```
Eres el agente I2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (I1) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/mapa_politicas.py (nuevo) · tests/test_mapa_politicas.py (nuevo) · docs/agentes/MAPA-POLITICAS.md (nuevo) · lo que necesites dentro de dist/ensayo/i2/ (gitignorado). Cualquier otra cosa: `PIDO A …:` en docs/agentes/BITACORA.md.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar, siempre con heredoc de comillas simples (<<'EOF'). **Pon la hora con `TZ=Europe/Madrid date +%H:%M`, nunca calculada.**
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. La BD real, SÓLO en modo lectura (`db.conectar(ruta, solo_lectura=True)`), o una copia hecha con `sqlite3.Connection.backup` en dist/ensayo/i2/. No escribas en dist/entrega/ ni en ../HS-Maisa-Entrega. **No edites src/albertitos/rules/**: la política es de Mónica. Tú mides. Nunca leas `.env`.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "I2" de docs/agentes/PARTE.md.
6. **La muestra de Mónica sigue abierta.** Mientras no suba su columna (`git fetch && git show origin/monica/norma-v3:data/fixtures/esperado_muestra.csv`), NINGÚN resultado por fichero de los 21 de data/fixtures/muestra.txt va al repo, a la bitácora ni al parte. La lista por fichero, completa, va a dist/ensayo/i2/. En el repo, sólo método y recuentos por pregunta. No abras dist/ensayo/h2/.
7. Lee antes: CLAUDE.md, la hoja Norma_Pagos_v3 del Excel (data/caja/FINAL_v7_DEFINITIVO_ahorasi.xlsx), src/albertitos/rules/__init__.py y norma_v3.py (ANOMALIAS_HUMANO, R1-R6, cómo se decide NO_PAGAR), pipeline/etapas.py (`decide`: cómo se llama a `REGISTRO[v].decidir(hechos, maestro, erp, ctx)`), docs/adr/0010 y 0011, docs/hitos.md (preguntas a los mentores), docs/agentes/DECISIONES-NORMA.md y docs/trampas.md («texto_instruccion · 29 ficheros» y la actualización D2: 31).

LA PREGUNTA: la validación es binaria. Cada factura cuya decisión depende de una política que la referencia podría leer distinto es un riesgo de NO APTO. ¿Cuántas son, cuáles, y qué pasaría con cada respuesta del mentor?

A · scripts/mapa_politicas.py, de sólo lectura:
  - Carga, de la BD (por defecto ALBERTITOS_DB), los hechos vigentes, el maestro y el ERP v1 del lote 1, y decide en memoria con la MISMA función que usa `decide` (`REGISTRO["v3"].decidir`), con fecha de corte 2026-09-18.
  - **Control:** sin variante reproduce exactamente las decisiones vigentes (438/53/9, fichero a fichero). Si no, para y dilo.
  - Una variante por pregunta. Se aplica en memoria (p. ej. `unittest.mock.patch` de `ANOMALIAS_HUMANO` o de una regla dentro del script) y se deshace al salir. Nunca edites rules/. Por cada variante: cuántas decisiones cambian, de qué a qué y cuáles.
  - Las preguntas, como mínimo:
    Q1 · texto que ordena la decisión (TEXTO_INSTRUCCION) en una factura que cumple R1-R5 → hoy ESCALAR; ¿y si fuera PAGAR? Separa por tipo de orden: empuja a escalar/bloquear, empuja a pagar o a relajar un control, empuja a no pagar, o va dirigida «al evaluador».
    Q2 · «pedido anulado» según el PDF (PEDIDO_ANULADO_SEGUN_PDF), con el pedido ABIERTO en el Excel y PENDIENTE en el ERP → hoy ESCALAR; ¿y si fuera PAGAR? ¿Y si fuera NO_PAGAR?
    Q3 · frontera NO_PAGAR/ESCALAR: un fallo objetivo de R1-R4 (NIF de otro proveedor, IVA mal calculado, total distinto del pedido, fecha futura) → hoy ESCALAR; ¿y si fuera NO_PAGAR?
    Q4 · «documentos de prueba del evaluador» (pregunta 4 de hitos.md): cuáles son y qué decide hoy la norma.
    Q5 · el duplicado PO-2026-0492 (dos ESCALAR hoy) frente a «el primero PAGAR y el otro NO_PAGAR».
  - Salida: una tabla de recuentos por pregunta y variante; con `--por-fichero`, la lista (file_id, decisión hoy, decisión con la variante, regla, tipo de orden); con `--markdown`, lista para pegar. Con `--excluir-muestra` quita los 21 de muestra.txt de la salida: ése es el modo para el repo.
B · COMPROBACIÓN A MANO de las que cambiarían con Q1 y Q2 (unas 30). Que el sistema diga «cumple R1-R5» no basta: comprueba desde las fuentes que es verdad. PDF con PyMuPDF (las escaneadas, como imagen), Excel y ERP (snapshot v1 de la BD o el bridge de :8009, sólo lectura). Si un hecho está mal extraído, la factura no es «limpia»: apúntala como DATO, con el campo y el valor, para Javier. Resultado en dist/ensayo/i2/comprobacion.csv.
C · docs/agentes/MAPA-POLITICAS.md, en una página: el método (control incluido), una tabla por pregunta con los recuentos (sin file_id de la muestra; los que no son de la muestra, sí), las preguntas para el mentor redactadas de forma neutra, y para cada respuesta posible, qué cambiaría: la palanca en la norma, en palabras (la decide y la escribe Mónica), cuántas líneas se mueven y el coste (reprocess --todo ≈ 7 s + auditoría + publicar). Arriba, una línea: cuál es la pregunta con más facturas en juego.
D · tests/test_mapa_politicas.py, con hechos construidos a mano y una BD temporal: la variante no deja la norma cambiada al salir, el control detecta una diferencia, y `--excluir-muestra` no enseña ningún file_id de muestra.txt.

CRITERIOS DE ACEPTACIÓN: el control reproduce 438/53/9 fichero a fichero; las cinco preguntas, con recuentos y lista por fichero en dist/ensayo/i2/; las candidatas de Q1 y Q2 comprobadas a mano contra las fuentes; nada por fichero de la muestra en el repo, la bitácora ni el parte; `make check` y `make agentes-check` verdes; la BD real y dist/entrega con el mismo sha256 antes y después.

NO HAGAS: editar rules/ ni proponer allí un cambio (para eso está la bitácora: «PIDO A Mónica»); escribir en la BD real; decidir una política; publicar la lista por fichero antes de que Mónica cierre la muestra.
```

---

## Mientras tanto, Javier
- Mensajes pendientes: a Mónica (no mirar `dist/ensayo/h2/`, subir la muestra, P0-2 y la confirmación de R3) y el kit
  de las 10:07 a Alfonso.
- **Cuando Miguel mergee `miguel/pipeline` a `main`:** `/sync`, `git apply dist/ensayo/p01/tests-identicos-sin-xfail.patch`
  en el mismo commit, `make check`, PR de `javier/ingesta` y `make kit-demo` otra vez (la BD pasa al esquema 3).
- 15:00: ensayo de la defensa en el portátil de Alfonso.

## Cierre del ciclo (Javier)
```bash
make agentes-check && make check && git push origin javier/ingesta
sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl | cut -c1-12       # las de antes de lanzar
curl -s http://127.0.0.1:8009/erp/estado | grep asientos                     # 516, vivo
```
Después: la chuleta de I1 a mano para las 18:00. Con Mónica, los números de I2 antes de hablar con el mentor. La lista
por fichero, cuando cierre la muestra. Y a Miguel, P0-5 con el fixture y el test de I1.
