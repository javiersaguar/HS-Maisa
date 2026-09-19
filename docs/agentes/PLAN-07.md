# PLAN-07 · ciclo 7 · sábado 19/09 ~08:45 → ~10:45 · rama `javier/ingesta` · dos agentes

**Dónde estamos (08:40).** F1 y F2 cerrados y comprobados: `make check` 359 en verde, `agentes-check` limpio,
`make publicar` en seco sale rojo **sólo** por `scan_025` (0,7 s, no toca nada), el hook de inicio dice
«ficheros sin decisión=0», y el kit de la demo se instala en un clon limpio, donde la demo sin red tarda ~4 s. La
entrega de seguro publicada (`fdc76e8`) sigue siendo la buena. Pendiente de Mónica: `DOCUMENTO_SUPERPUESTO` y los
5 PAGAR reconciliados.

**Por qué este ciclo.** Queda un agujero que nos deja sin premio y no depende de nosotros: **si a la hora de
entregar un solo PDF del lote 2 no tiene decisión** (el LLM caído a las 18:00, una escaneada ilegible, un 429 que
no se va), `package` se niega. Eso es lo correcto, porque nunca se paga a ciegas, pero entonces **no hay
`outcomes_lote2.jsonl`, y sin él la entrega es NO APTA**: son 540 de 540 o nada. Hoy la única salida sería escribir
líneas a mano, y el hook lo bloquea con razón. Hace falta una salida prevista: **ESCALAR explícito, registrado y
reversible**, que es lo que la propia norma haría con una factura que nadie ha podido leer.

El segundo frente es lo que el tribunal va a preguntar en la traza (20 pts) y en escala (25 pts). F2 encontró que los
reintentos ORA-00600 que promete el guion **no salen en ninguna traza**, que `erp pull` sin ERP escupe un traceback
de 92 líneas, y el plan de Alfonso aún dice que la visión va a **0,22 f/s**, la cifra que ya corregimos (con doble
lectura son 0,065-0,106). Todo eso es de `sources/` y de las cifras: es mío.

| Agente | Misión | Lo que hay al terminar |
|---|---|---|
| **G1** | Ningún fichero sin línea: contingencia para el lote 2 | `scripts/contingencia.py` (en seco por defecto) · auditoría que la enseña · paso en `/lote2` · ADR-0009 propuesto · ensayo de punta a punta con el LLM caído |
| **G2** | Lo que el tribunal pregunta: de dónde sale cada reintento y cada cifra | `erp pull` sin traceback · resumen del ERP listo para la traza · `docs/CIFRAS.md` con la fuente de cada cifra · `cifras_check.py` que caza las cifras obsoletas |

## Antes de lanzar (Javier, 5 min)
1. **Pregunta en el canal a Mónica y a Miguel** (G1 la construye igual, pero no se usa sobre la BD real sin su sí):
   > «Si a la hora de entregar un fichero no tiene hechos validados (LLM caído, PDF ilegible), proponemos decidirlo
   > como ESCALAR con el motivo "sin hechos validados: lo revisa una persona", registrado como contingencia y
   > revertido solo en cuanto lleguen los hechos. Nunca PAGAR ni NO_PAGAR. ¿OK?»
2. Lo de siempre:
```bash
cd /home/javier/proyectos/HackSpain && git switch javier/ingesta && git pull --ff-only && make check
make erp-fast                                              # en otra terminal, si no está
uv run python scripts/preflight_lote2.py                   # todo verde
sha256sum dist/entrega/outcomes.jsonl | cut -c1-12         # 5ec17aaa5045 (o el nuevo, si ya se aplicó lo de Mónica)
```
Durante el ciclo **ningún agente escribe en `dist/albertitos.db`, `dist/entrega/` ni `../HS-Maisa-Entrega`**. Si
Mónica decide mientras tanto, el arreglo de `scan_025` lo aplica Javier (final de AUDITORIA-ENTREGA.md) y lo apunta
en la bitácora.

## Propiedad de ficheros (`plan.json`; `make agentes-check` lo verifica)
| G1 | G2 |
|---|---|
| `scripts/contingencia.py` (nuevo) · `tests/test_contingencia.py` (nuevo) · `scripts/auditoria_entrega.py` · `tests/test_auditoria.py` · `docs/agentes/AUDITORIA-ENTREGA.md` · `.claude/skills/lote2/SKILL.md` · `docs/adr/0009-*.md` (nuevo) · `docs/adr/README.md` | `src/albertitos/sources/erp.py` · `src/albertitos/sources/snapshot.py` · `tests/test_erp.py` · `tests/test_snapshot.py` · `src/albertitos/sources/CLAUDE.md` · `docs/CIFRAS.md` (nuevo) · `scripts/cifras_check.py` (nuevo) · `tests/test_cifras.py` (nuevo) · `docs/agentes/RESILIENCIA-Y-COSTE.md` · `docs/agentes/ESCALA-10K.md` |

Compartidos, sólo añadiendo al final: `docs/agentes/BITACORA.md` y `docs/agentes/PARTE.md` (cada uno en su sección).
Ninguno toca `pipeline/`, `cli.py`, `core/`, `rules/`, `console/`, `docs/plan/` ni `docs/guion-defensa.md`: lo
que haga falta ahí se pide con `PIDO A Miguel:` / `PIDO A Mónica:` / `PIDO A Alejandro:` / `PIDO A Alfonso:`, con
el parche propuesto en la bitácora.

---

## Prompt G1 · Ningún fichero sin línea: contingencia para el lote 2

```
Eres el agente G1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (G2) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/contingencia.py (nuevo) · tests/test_contingencia.py (nuevo) · scripts/auditoria_entrega.py · tests/test_auditoria.py · docs/agentes/AUDITORIA-ENTREGA.md · .claude/skills/lote2/SKILL.md · docs/adr/0009-*.md (nuevo) · docs/adr/README.md. Cualquier otro fichero: NO lo toques; escribe `PIDO A G2:`, `PIDO A Miguel:` o `PIDO A Mónica:` en docs/agentes/BITACORA.md, con el parche propuesto, y sigue.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar, siempre con un heredoc con comillas simples (<<'EOF'). Lee las de G2 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. NUNCA escribas en la BD real (`dist/albertitos.db`), en `dist/entrega/` ni en `../HS-Maisa-Entrega`. Todo ensayo va en copias hechas con `sqlite3.Connection.backup` dentro de `dist/ensayo/g1/`, con `ALBERTITOS_DB` apuntando a la copia. El caos es por BD (`<db>.chaos.json`): enciéndelo sólo en la copia y apágalo al terminar. Nunca leas `.env`.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "G1" de docs/agentes/PARTE.md.
6. Antes de empezar, lee CLAUDE.md, src/albertitos/pipeline/CLAUDE.md, src/albertitos/pipeline/linaje.py (sobre todo `evaluar`), src/albertitos/pipeline/package.py, src/albertitos/core/contracts.py (Decision, Motivo, Event) y core/db.py (`guardar_decision`, `registrar_evento`), scripts/auditoria_entrega.py, docs/agentes/AUDITORIA-ENTREGA.md, .claude/skills/lote2/SKILL.md, docs/agentes/ENSAYO-LOTE2.md y tests/test_lote2_sim.py (el lote 2 simulado de 10 PDFs en data/fixtures/lote2_sim/).

CONTEXTO: la validación es binaria. Un outcome por cada PDF, 540 en total, o no hay premio. `package` se niega a escribir un JSONL si a algún fichero le falta la decisión vigente (regla 6: nunca pagar sin hechos validados). Es correcto, pero si a la hora de entregar el lote 2 un PDF sigue PENDIENTE porque el LLM está caído, porque es una escaneada ilegible o porque hay un 429 persistente, NO habrá outcomes_lote2.jsonl y la entrega entera será NO APTA. Hoy la única salida sería escribir líneas a mano, y el hook lo bloquea con razón. Hace falta una salida prevista, explícita, registrada y reversible.

MISIÓN
A · scripts/contingencia.py
  - `uv run python scripts/contingencia.py --lote 2` (EN SECO por defecto): lista los ficheros del lote sin decisión vigente, con el último evento de cada uno (etapa, estado, error_codigo, ts) y el porqué en una línea. No escribe nada. Sale 0 si no hay ninguno y 1 si hay alguno, diciendo el comando para aplicarla.
  - `--aplicar --motivo "<texto>"` (el motivo es obligatorio): para cada uno de esos ficheros, y SÓLO para ellos, guarda con `core.db.guardar_decision` una Decision con resultado **ESCALAR** (nunca otro), un Motivo `regla_id="contingencia.C1"`, `ok=False` y un detalle legible por Alberto ("sin hechos validados a la hora de entregar (<error>): lo revisa una persona"), con la evidencia del último error y el motivo que se ha dado. `hechos_hash="sin-hechos"`; la norma, el maestro, el ERP y la fecha de corte, los que están en vigor (los mismos que usaría `decide`: impórtalos de donde los saque pipeline, no los copies). Además, un Event de `decide` con estado ok y un detalle JSON `{"contingencia": true, "motivo": ...}`. Todo en una transacción.
  - Idempotente: si se ejecuta dos veces, no crea decisiones nuevas.
  - `--lote` es obligatorio. En el lote 1 (500/500) no debe haber nunca nada que aplicar; si lo hay, rojo con un mensaje que lo diga.
  - REVERSIBLE SIN HACER NADA: cuando lleguen los hechos, `hechos_hash` real ≠ "sin-hechos", así que `linaje.evaluar` lo clasifica como "hechos cambiados" y `reprocess --impacted` la sustituye por la de la norma. Compruébalo con un test; no lo des por hecho.
B · tests/test_contingencia.py (fixture `conn` de conftest; sin red ni LLM): en seco no escribe; con --aplicar sólo toca a los que no tienen decisión; todo lo que escribe es ESCALAR; es idempotente; `package` pasa de negarse a APTO; cuando llegan los hechos, `reprocess --impacted` la reemplaza y la contingencia queda con vigente=0; sin `--motivo` se niega.
C · Auditoría (scripts/auditoria_entrega.py y su test): comprobación nueva, "Decisiones de contingencia", en ÁMBAR con la lista y el motivo. No en rojo: es una salida prevista, pero quien entrega tiene que verla. Documéntala en la tabla de AUDITORIA-ENTREGA.md.
D · Skill /lote2: un paso nuevo, "Si a las 07:30 del domingo queda algún PENDIENTE", con la secuencia en seco → --aplicar con motivo → auditoría → make publicar, y la regla de que antes se intenta de verdad (chaos apagado, reintentar el extract de los pendientes, el modelo de respaldo). La contingencia es lo último, no un atajo.
E · ADR-0009, "Si a la hora de entregar no hay hechos, ESCALAR explícito y reversible", en estado **propuesto** (lo aceptan Mónica y Miguel): contexto (binario 540/540), alternativas (no entregar el lote 2; PAGAR por defecto; NO_PAGAR por defecto; ESCALAR con registro), decisión, consecuencias y evidencia (la de tu ensayo) + "Resumen para el plan (5 líneas)" como los demás. Añádelo a docs/adr/README.md.
F · ENSAYO DE PUNTA A PUNTA, en una copia de la BD real en dist/ensayo/g1/ con el lote 2 simulado (sigue lo que hace tests/test_lote2_sim.py y ENSAYO-LOTE2.md: el ERP simulado va en otro puerto; no toques el de :8009). Mide cada paso con `time`: chaos --llm-down → ingest+extract del lote 2 simulado → las escaneadas PENDIENTE → `package` se niega → contingencia en seco → --aplicar → auditoría (ámbar) → package APTO 510 → chaos --off → extract de pendientes → `reprocess --impacted` → las de contingencia sustituidas → auditoría. Pega las salidas literales en tu parte. Borra el caos de la copia al terminar.

CRITERIOS DE ACEPTACIÓN: sin --aplicar no escribe nunca; sólo escribe ESCALAR; se revierte sola con los hechos (probado con un test y en el ensayo); la auditoría la enseña en ámbar; la skill /lote2 la tiene como último recurso; ADR-0009 propuesto; `make check` y `make agentes-check` verdes; la BD real y dist/entrega, con el mismo sha256 antes y después (apúntalos).

NO HAGAS: tocar pipeline/, cli.py, core/ ni rules/ (si `package` o `decide` necesitan algo, PIDO A Miguel con el parche); aplicar la contingencia a la BD real; decidir PAGAR o NO_PAGAR por contingencia; borrar filas de la BD real.
```

---

## Prompt G2 · Lo que el tribunal pregunta: de dónde sale cada reintento y cada cifra

```
Eres el agente G2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (G1) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: src/albertitos/sources/erp.py · src/albertitos/sources/snapshot.py · tests/test_erp.py · tests/test_snapshot.py · src/albertitos/sources/CLAUDE.md · docs/CIFRAS.md (nuevo) · scripts/cifras_check.py (nuevo) · tests/test_cifras.py (nuevo) · docs/agentes/RESILIENCIA-Y-COSTE.md · docs/agentes/ESCALA-10K.md. Cualquier otro fichero: NO lo toques; escribe `PIDO A G1:`, `PIDO A Miguel:`, `PIDO A Alfonso:` o `PIDO A Alejandro:` en docs/agentes/BITACORA.md, con el parche o el texto propuesto, y sigue.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar, siempre con un heredoc con comillas simples (<<'EOF'). Lee las de G1 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. La BD real (`dist/albertitos.db`) sólo se LEE. No escribas en `dist/entrega/`. Si necesitas bajar un snapshot del ERP, hazlo en una copia en `dist/ensayo/g2/` (ALBERTITOS_DB) y nunca con la etiqueta v1 ni v2 sobre la BD real. Nunca leas `.env`.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "G2" de docs/agentes/PARTE.md.
6. Antes de empezar, lee CLAUDE.md, src/albertitos/sources/CLAUDE.md, sources/erp.py y sources/snapshot.py, el `erp pull` de src/albertitos/cli.py (no es tuyo), docs/agentes/partes/PARTE-06.md (sección F2: hallazgos 3 y 6), docs/demo/trazas/README.md, docs/agentes/KIT-DEFENSA.md, docs/agentes/ESCALA-10K.md, docs/agentes/RESILIENCIA-Y-COSTE.md, docs/benchmark.md, docs/plan/albertitos_plan.md y docs/guion-defensa.md (estos dos últimos son de Alfonso: sólo se leen).

MISIÓN: que nada de lo que el tribunal pregunte sobre el ERP o sobre una cifra nos pille sin respuesta.

A · `erp pull` SIN ERP, en una línea. Hoy son 92 líneas de traceback (F2, hallazgo 6). En sources/erp.py: si no se puede conectar, reintenta lo que ya reintentes y después lanza un ErrorERP con código `ERP-NO-RESPONDE` y un mensaje que diga la URL, qué hacer (`make erp` / `make erp-fast` en otra terminal, o `ALBERTITOS_ERP_URL`) y que el snapshot anterior sigue sirviendo para decidir. El traceback lo imprime cli.py porque no captura la excepción: ese fichero es de Miguel. Déjale en la bitácora el parche exacto (≈4 líneas: capturar ErrorERP, imprimir el mensaje, typer.Exit(1)) con PIDO A Miguel. Test sin ERP (URL a un puerto cerrado): la excepción sale con ese código y ese mensaje, y rápido (mide cuánto).
B · LA TRAZA DEL ERP. Los reintentos ORA-00600 / 429 / SES-401 que promete el guion no salen en `trace`, porque la descarga es por snapshot y no por fichero (F2, hallazgo 3). Eso es el diseño (ADR-0005), no un fallo, pero la traza tiene que poder contarlo. En sources/snapshot.py, `resumen_erp(conn, version) -> dict` con: versión, descargado_en, asientos, consultas, reintentos y, sacados de los eventos de la descarga, los errores por código y la latencia total. Pura, en sólo lectura, con test. Después, PIDO A Miguel con el parche de UNA línea que `trace` imprimiría: "ERP v1 · bajado 18/09 19:55 · 516 asientos · 540 consultas · 24 reintentos (ORA-00600×19, ERP-429×5)" (con los números de verdad de la BD real, que lees tú). Y a Alfonso: cómo responder a "¿dónde se ven los reintentos?" con el comando que ya funciona hoy.
C · docs/CIFRAS.md: UNA tabla con cada cifra que vamos a decir en la defensa o que está escrita en el plan, el guion o la chuleta: la cifra, qué mide, la fuente (fichero §) y el comando que la reproduce, la fecha de medición y si sigue vigente. Como mínimo: 500/500 extraídos; 468/468 contraste; 93,6 % por plantilla; 443/48/9; escala 10k (tiempo del camino determinista); visión 0,065-0,106 f/s con doble lectura (NO 0,22, que es de una sola lectura); coste marginal; linaje 40/500 en 0,78 s y 500 en 7 s (ENSAYO-REPROCESADO); demo sin red ~4 s; breaker 5 fallos → 60 s; timeouts 60/90 s. Si una cifra no la puedes reproducir hoy con un comando, dilo en la tabla: no la inventes ni la redondees.
D · scripts/cifras_check.py (+ tests/test_cifras.py): lee docs/CIFRAS.md, donde cada cifra obsoleta tiene su forma escrita (p. ej. "0,22 ficheros/s"), y busca esas formas en docs/plan/albertitos_plan.md, docs/guion-defensa.md, docs/agentes/KIT-DEFENSA.md y docs/benchmark.md. Imprime fichero:línea, la cifra vieja y la vigente con su fuente. Sale 1 si encuentra alguna. Sólo lee: NO corrige los ficheros de otros. Ejecútalo contra el repo y pon la salida en tu parte. Ya sabemos que docs/plan/albertitos_plan.md:60 dice "0,22 ficheros/s": que salga. Después, PIDO A Alfonso con cada línea y el texto de sustitución.
E · Tus documentos al día: sources/CLAUDE.md (ERP-NO-RESPONDE, resumen_erp), RESILIENCIA-Y-COSTE y ESCALA-10K enlazando a CIFRAS.md como fuente única, sin duplicar tablas.

CRITERIOS DE ACEPTACIÓN: sin ERP, `erp pull` falla con un mensaje de una línea en cuanto Miguel aplique el parche (y el test de sources lo fija ya); `resumen_erp` sobre la BD real da los números reales; CIFRAS.md tiene cada cifra con su fuente y su comando; cifras_check.py encuentra el 0,22 del plan; los PIDO con su parche en la bitácora; `make check` y `make agentes-check` verdes; la BD real y dist/entrega con el mismo sha256 antes y después.

NO HAGAS: tocar cli.py, pipeline/, core/, docs/plan/, docs/guion-defensa.md, docs/agentes/KIT-DEFENSA.md (es de F2, ya cerrado: pide a Javier) ni la consola; bajar un snapshot sobre la BD real; cambiar el formato de los snapshots (lo leen linaje y el preflight); inventar o redondear cifras.
```

---

## Cierre del ciclo (Javier)
```bash
make agentes-check && make check && git push origin javier/ingesta
sha256sum dist/entrega/outcomes.jsonl | cut -c1-12      # igual que al empezar
uv run python scripts/contingencia.py --lote 1           # 0: nada que aplicar en el lote 1
uv run python scripts/cifras_check.py                    # lo que quede es de Alfonso: pásaselo
make publicar                                            # en seco
```
Después: los PIDO A Miguel (el parche de `erp pull` y la línea del ERP en `trace`) y la respuesta de Mónica y Miguel
sobre la contingencia (si es sí, ADR-0009 pasa a aceptado). Si ya se aplicó lo de `scan_025`: `make kit-demo` y el
kit nuevo a Alfonso, y `make publicar ARGS=--publicar`.
