# PLAN-10 · ciclo 10 · sábado 19/09 ~12:30 → ~14:30 · rama `javier/ingesta` · cinco agentes

**Dónde estamos (12:20).** `main` = `javier/ingesta` = `990a75d`. `make check`: 443 en verde y 1 xfail estricto (P0-5,
que espera la rama de Miguel). Auditoría VERDE. Entrega publicada `232bb76` (438/53/9, `1ec4be206089`). En `main` ya
están P0-1 (copias exactas), P0-4 (`--aceptar-rojo`) y la traza legible de Miguel. El ensayo de integración de todas las
ramas sale limpio (444 en verde). Quedan fuera de `main`, a propósito: P0-5 (`miguel/p0-5-nombre-repetido`, se mergea
a las 18:00 sólo si hace falta) y la presentación de Alfonso.

**Por qué este ciclo.** Quedan tres momentos, y en los tres manda Javier: la **defensa** (ensayo a las 15:00), el
**lote 2** a las 18:00 y la **entrega final** del domingo. Nada de lo que falta es el sistema; son **ensayos con el
código de verdad** y **redes de seguridad** que hoy no existen:
1. El lote 2 **no se ha ensayado con el código que habrá a las 18:00**. I1 se quedó sin terminal y la chuleta es un
   borrador sin ejecutar.
2. Las escaneadas del lote 2 **dependen de un solo modelo de visión**: el respaldo de visión está vacío por defecto.
3. Nadie ha probado qué pasa si el Excel o el ERP del sábado **cambian de forma** (columnas, hojas, formato), además
   de cambiar de contenido.
4. El domingo el tribunal cambia un dato en vivo, y ese número todavía no está medido (hitos, sáb 23:00).
5. El bonus (+10, tercer desempate) sigue sin empezar, y a las 16:30 ya es tarde.

| Agente | Misión | Lo que hay al terminar |
|---|---|---|
| **J1** | Ensayo general del lote 2 con `main`, cronometrado | Skill `/lote2` y `CHULETA-LOTE2.md` **ejecutadas**, con tiempos reales; P0-5 ensayado con la rama de Miguel; `--aceptar-rojo` y la contingencia probados |
| **J2** | Que un Excel o un ERP cambiados de forma no nos paren | loader del Excel tolerante y con avisos; ensayo «maestro cambiado» → `reprocess --impacted`; `ENSAYO-FUENTES.md` |
| **J3** | Las escaneadas del lote 2 no dependen de un solo modelo | modelos de visión candidatos medidos contra el gateway; recomendación de respaldo con cifras; `RESPALDO-VISION.md` |
| **J4** | La defensa con el código de hoy, y el dato en vivo del domingo | kit nuevo; chuleta del bloque 4 re-cronometrada; `scripts/dato_en_vivo.py` con su tiempo medido |
| **J5** | Bonus (+10): remesa y calendario de pagos | `albertitos.bonus` (sólo lectura: nunca cambia una decisión ni la entrega) + tests + ADR-0012 |

## Antes de lanzar (Javier, 5 min)
```bash
cd /home/javier/proyectos/HackSpain && git switch javier/ingesta && git pull --ff-only && make check   # 443 + 1 xfail
make erp-fast                                              # en otra terminal (el v1 en :8009)
uv run python scripts/preflight_lote2.py && uv run python scripts/auditoria_entrega.py    # verde / VERDE
sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl | cut -c1-12
mkdir -p dist/ensayo/j1 dist/ensayo/j2 dist/ensayo/j3 dist/ensayo/j4 dist/ensayo/j5
```
**Reglas del ciclo, las cinco a la vez:**
- **Nadie escribe en `dist/albertitos.db`, `dist/entrega/`, `../HS-Maisa-Entrega` ni `data/caja/`.** Cada agente trabaja
  en copias propias, hechas con `sqlite3.Connection.backup`, dentro de `dist/ensayo/jN/`.
- **El ERP de `:8009` sólo se lee.** Para el ERP v2, J1 usa `:8011`; ningún otro agente levanta bridges.
- **J3 es el único que llama al LLM**, con un tope: cuántas llamadas por modelo y un máximo total, apuntados en su parte.
- `make check` corre a la vez en cinco sesiones: un fallo por BD bloqueada se reintenta una vez antes de darlo por malo.

## Propiedad de ficheros (`plan.json`; `make agentes-check`)
| J1 | J2 | J3 | J4 | J5 |
|---|---|---|---|---|
| `.claude/skills/lote2/SKILL.md` · `docs/agentes/CHULETA-LOTE2.md` · `docs/agentes/ENSAYO-LOTE2.md` | `src/albertitos/sources/excel.py` · `tests/test_excel.py` · `data/fixtures/maestro_cambiado/*` (nuevo) · `docs/agentes/ENSAYO-FUENTES.md` (nuevo) | `scripts/bench_vision_respaldo.py` (nuevo) · `docs/agentes/RESPALDO-VISION.md` (nuevo) · `src/albertitos/extract/llm.py` y `tests/test_llm.py` (sólo si hace falta, al final) | `scripts/dato_en_vivo.py` (nuevo) · `tests/test_dato_en_vivo.py` (nuevo) · `docs/agentes/KIT-DEFENSA.md` · `docs/demo/*` | `src/albertitos/bonus/*` (nuevo) · `tests/test_bonus.py` (nuevo) · `docs/adr/0012-*` (nuevo) · `docs/BONUS.md` (nuevo) |

Compartidos, sólo añadiendo al final: `docs/agentes/BITACORA.md` y `docs/agentes/PARTE.md`. **Nadie toca** `core/`,
`pipeline/`, `cli.py` (Miguel), `rules/` (Mónica), `console/` (Alejandro) ni `docs/plan/`/`presentaciones/` (Alfonso).
Lo que necesiten de ellos se pide con `PIDO A <nombre>:` y el parche propuesto.

## Reglas comunes (van dentro de cada prompt)
```
REGLAS DE CONVIVENCIA (cinco agentes en el mismo árbol y en la misma rama `javier/ingesta`):
1. Sólo editas los ficheros de tu columna en docs/agentes/PLAN-10.md. Cualquier otro: `PIDO A <agente o persona>:` en docs/agentes/BITACORA.md, con el parche, y sigues.
2. BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar, siempre con heredoc de comillas simples (<<'EOF'). Lee las de los demás antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase en este árbol (para probar otra rama, usa un worktree en dist/ensayo/<tú>/ y quítalo al acabar); no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. Nunca escribas en dist/albertitos.db, dist/entrega/, ../HS-Maisa-Entrega ni data/caja/. Copias con sqlite3.Connection.backup dentro de dist/ensayo/<tú>/ y ALBERTITOS_DB apuntando a ellas. El caos es por BD: enciéndelo sólo en tu copia y apágalo al acabar. Nunca leas .env.
5. Apunta al empezar y al terminar el sha256 (12) de dist/albertitos.db y dist/entrega/outcomes.jsonl: tienen que coincidir.
6. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección de docs/agentes/PARTE.md: estado, commits, cifras con el comando que las da, hallazgos y lo que necesitas de otros.
7. Lee antes: CLAUDE.md, docs/ESTADO-BACKEND.md, la cola de BITACORA.md (desde «12:12 · Javier») y la documentación que diga tu prompt.
```

---

## Prompt J1 · Ensayo general del lote 2 con `main`, cronometrado
```
Eres el agente J1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). [Pega aquí las REGLAS DE CONVIVENCIA de PLAN-10.md.] Tus ficheros: .claude/skills/lote2/SKILL.md · docs/agentes/CHULETA-LOTE2.md · docs/agentes/ENSAYO-LOTE2.md.
Lee además: .claude/skills/lote2/SKILL.md entera, docs/agentes/CHULETA-LOTE2.md (borrador de I1 SIN EJECUTAR), docs/agentes/ENSAYO-LOTE2.md, docs/agentes/partes/ (PARTE-05, E3) y el PARTE.md del ciclo 9 (I1: lo que no pudo hacer), docs/agentes/P0-1-IDENTICOS.md y la entrada de Miguel de las 11:40 sobre P0-5.

MISIÓN: a las 18:00 Javier ejecuta /lote2 con el código de main (990a75d). El último ensayo completo es de las 01:52, anterior a identidades, --aceptar-rojo, trace legible, status nuevo y la auditoría dentro de package. Ensáyalo entero, tal como está escrito, y deja la receta y la chuleta con tiempos REALES.

A · Ensayo general, en una copia de la BD real (dist/ensayo/j1/ensayo.db). Usa como lote 2 data/fixtures/lote2_sim/ (10 PDFs, 2 escaneadas; para las escaneadas usa la caché o el caos: NO llames al LLM, eso es de J3). El ERP v2 va en :8011 (el comando está en data/fixtures/lote2_sim/README.md). Sigue la skill paso a paso, desde el paso 0, y mide cada paso con `time`:
   verificar_material → ingest → extract → erp pull del v2 → diff → inventario → (regla nueva: simula un cambio in situ trivial SOLO en tu copia en memoria, o sáltalo apuntándolo; rules/ no se toca) → reprocess → auditoría → package → make publicar EN SECO con ENTREGA_REPO apuntando a un repo bare local de dist/ensayo/j1/ (nunca al real).
   Apunta lo que falle, lo que confunda y lo que la skill no diga.
B · Tres desvíos, cada uno en su propia copia:
   (1) P0-5: con data/fixtures/lote2_nombre_repetido/, en un worktree con `git merge origin/miguel/p0-5-nombre-repetido`, sigue la instrucción de Miguel (bitácora 11:40) y cronometra desde que verificar_material avisa hasta tener package APTO.
   (2) Auditoría roja: fuerza un rojo en tu copia (por ejemplo, un texto_sospechoso "None" como el de scan_025) y comprueba `package --aceptar-rojo "<motivo>"`: evento AUDITORIA-ROJA-ACEPTADA y el emit con el motivo.
   (3) Contingencia (ADR-0009): LLM caído con el caos en tu copia → contingencia en seco → --aplicar → package APTO → vuelta atrás. Sólo el tiempo; la mecánica ya la probó G1.
C · Reescribe CHULETA-LOTE2.md (UNA página): cada paso con su comando literal, qué se ve si va bien, cuánto tardó y qué hacer si falla. Pon la skill al día con lo que encuentres. Añade a ENSAYO-LOTE2.md una sección «19/09 · ensayo general con main 990a75d» con las salidas literales.
CRITERIOS: todo ejecutado (nada «debería»), tiempos por paso, los tres desvíos medidos, la chuleta en una página, BD real y entrega intactas, make check verde.
NO HAGAS: tocar código (si algo falla, PIDO al dueño con la salida literal); llamar al LLM; usar el puerto :8009 para el v2; publicar en el repo de entrega real.
```

## Prompt J2 · Que un Excel o un ERP cambiados de forma no nos paren
```
Eres el agente J2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). [REGLAS DE CONVIVENCIA de PLAN-10.md.] Tus ficheros: src/albertitos/sources/excel.py · tests/test_excel.py · data/fixtures/maestro_cambiado/ (nuevo) · docs/agentes/ENSAYO-FUENTES.md (nuevo).
Lee además: sources/excel.py, sources/CLAUDE.md, pipeline/linaje.py (diff_maestro y evaluar: no son tuyos), tests/test_excel.py, docs/trampas.md (la parte del Excel) y docs/hitos.md (la regla nueva «puede venir en el zip, en el canal o en el Excel»).

MISIÓN: a las 18:00 puede llegar un Excel nuevo (la regla nueva, un proveedor, un IBAN cambiado) o un CSV del ERP con otra forma. Hoy el loader se ha probado con UN fichero. Si falla a las 18:05, la cadena entera espera. Que no falle, y que si algo no se entiende, lo diga.
A · Inventario: qué supone hoy excel.cargar_maestro (nombres de hoja, cabeceras, orden, tipos, filas vacías, NIF con espacios, importes con coma o punto, fechas como texto o como fecha de Excel). Escríbelo en ENSAYO-FUENTES.md.
B · Fixtures en data/fixtures/maestro_cambiado/ (copias del Excel real modificadas con openpyxl; el original NO se toca): columnas reordenadas; una columna nueva desconocida; una hoja nueva (p. ej. «Norma_Pagos_v4» o «Regla nueva»); un proveedor nuevo; un IBAN cambiado; un pedido anulado; cabeceras con mayúsculas o tildes distintas; filas vacías intercaladas. Añade uno o dos más que se te ocurran viendo el fichero real.
C · El loader tolerante a la FORMA (por nombre de cabecera normalizado, no por posición) y estricto con el CONTENIDO. Lo que no entienda va a MasterSnapshot.avisos_calidad con una frase clara (no revienta, no se lo calla). Una hoja nueva que parezca una norma se AVISA con su nombre: puede ser la regla de las 18:00. Un test por fixture. La versión del maestro (hash del contenido útil) NO cambia si sólo cambia la forma: compruébalo con un test contra el Excel real.
D · Ensayo del «maestro cambiado», en una copia de la BD: `albertitos maestro` con cada fixture de contenido (IBAN, proveedor, pedido anulado) → `reprocess --impacted` → cuántas decisiones cambian y cuáles, con el tiempo. Pon las cifras en ENSAYO-FUENTES.md.
E · El CSV del ERP del lote 2 (data/fixtures/erp_lote2_simulado.csv y lo que lee el bridge): haz lo mismo sólo si sale barato (columnas reordenadas o nuevas). El bridge es de la organización y no se toca: si hay problema, dilo.
CRITERIOS: con el Excel real, el maestro sale con la MISMA versión que hoy (80911e429c6c) y la BD real reprocesada no cambia nada; cada fixture tiene su test; los avisos son legibles; make check verde.
NO HAGAS: tocar data/caja/, pipeline/ o core/; cambiar la versión del maestro para el Excel real.
```

## Prompt J3 · Las escaneadas del lote 2 no dependen de un solo modelo
```
Eres el agente J3 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). [REGLAS DE CONVIVENCIA de PLAN-10.md.] Tus ficheros: scripts/bench_vision_respaldo.py (nuevo) · docs/agentes/RESPALDO-VISION.md (nuevo) · y, SÓLO al final y si hace falta, src/albertitos/extract/llm.py y tests/test_llm.py.
Lee además: extract/llm.py (_modelo_respaldo, VISION_DOBLE, timeouts, breaker, _con_modelos), extract/etapa.py (doble lectura y reconciliación), docs/agentes/RESILIENCIA-Y-COSTE.md §3 (e) y §5, docs/agentes/ESCALA-10K.md §4 y docs/CIFRAS.md.

MISIÓN: hoy ALBERTITOS_MODELO_VISION_FALLBACK está vacío. Si a las 18:00 qwen3.6 da 429 o se cae, las escaneadas del lote 2 se quedan PENDIENTES; con suerte acaban en contingencia (ESCALAR), pero sin premio en la precisión. El respaldo de texto se midió (glm5.3-flash, 3/3); el de visión, nunca. Mídelo.
A · Qué modelos de visión ofrece el gateway: GET /v1/models con httpx y la key que el propio código carga (llm.py lee .env con dotenv; tú NO lees .env). Descarta los claude-* (402). Lista los que aceptan imagen.
B · scripts/bench_vision_respaldo.py: para cada modelo candidato (tope: 3 modelos, 8 facturas cada uno, ≤ 30 llamadas en total; apúntalo), extrae las escaneadas de la Caja cuyos hechos buenos ya tenemos (los de la BD real, SÓLO LECTURA: tabla hechos). Compara campo a campo (NIF, IBAN, pedido, total, fecha): aciertos, latencia, tokens, si respeta el tool/esquema y cuántas veces devuelve basura. Usa la variante de caché que no pisa la principal (mira `variante` en llm.extraer) o, mejor, una BD de ensayo en dist/ensayo/j3/.
C · RESPALDO-VISION.md: la tabla de resultados, la recomendación (qué modelo, con qué timeout) y el riesgo: un respaldo peor que el principal puede decidir PAGAR con un NIF mal leído. Por eso la lectura del respaldo tiene que pasar igualmente la reconciliación con el maestro y la R1. Comprueba en el código que es así y dilo.
D · Sólo si hace falta tocar código (por ejemplo, un timeout distinto para el respaldo de visión, o que el respaldo de visión se salte la doble lectura): cambio mínimo en llm.py con su test, y avisa en la bitácora ANTES de commitear, porque J1 ensaya el pipeline a la vez. La variable de entorno la pone Javier a mano en .env: escríbele la línea exacta.
CRITERIOS: cifras medidas (no «parece»), el tope de llamadas respetado y apuntado, una recomendación con su riesgo, make check verde.
NO HAGAS: escribir en la caché de la BD real; tocar rules/ o etapa.py; leer .env; pasar de 30 llamadas.
```

## Prompt J4 · La defensa con el código de hoy, y el dato en vivo del domingo
```
Eres el agente J4 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). [REGLAS DE CONVIVENCIA de PLAN-10.md.] Tus ficheros: scripts/dato_en_vivo.py (nuevo) · tests/test_dato_en_vivo.py (nuevo) · docs/agentes/KIT-DEFENSA.md · docs/demo/*.
Lee además: docs/agentes/KIT-DEFENSA.md, docs/demo/ENSAYO-CLON-LIMPIO.md, docs/demo/trazas/README.md, scripts/kit_demo.py, scripts/demo_caos.py, docs/guion-defensa.md (de Alfonso: sólo se lee), docs/hitos.md («escenario del dato en vivo del domingo ensayado, reprocess --impacted < 30 s») y docs/agentes/ENSAYO-REPROCESADO.md.

MISIÓN: el ensayo de la defensa es a las 15:00 en el portátil de Alfonso. Desde el último kit, `trace` y `status` han cambiado (Miguel: trace legible, status sin histórico). Y el domingo el tribunal cambiará un dato delante de nosotros: hay que saber exactamente qué comando se teclea y cuánto tarda.
A · Kit nuevo, antes de las 14:00: `make kit-demo` (sólo lee la BD real) e instálalo en un clon limpio (`git worktree add dist/ensayo/j4/limpio HEAD --detach`, ./bootstrap.sh, `kit_demo.py instalar`). Ejecuta la chuleta de KIT-DEFENSA.md entera y cronometra cada paso: status, trace de las cinco trazas de docs/demo/trazas/ (con el formato nuevo), demo_caos --sin-red, el breaker de RESILIENCIA §3 (b bis) y la consola Streamlit (health). Regenera las cinco trazas de docs/demo/trazas/ con el `trace` de hoy. Pon KIT-DEFENSA.md al día con tiempos y salidas. Quita el worktree al acabar. Deja en la bitácora la ruta del kit para que Javier se lo pase a Alfonso.
B · scripts/dato_en_vivo.py, con tests: sobre una COPIA de la BD (nunca la real), aplica un cambio que el tribunal podría pedir y enseña, en menos de 30 s, qué decisiones cambian y por qué:
   `--erp-pagada <pedido>`: el asiento pasa a PAGADA (snapshot ERP nuevo derivado del vigente) → reprocess --impacted → la factura pasa a NO_PAGAR;
   `--iban <proveedor> <iban>`: el maestro cambia el IBAN → las facturas de ese proveedor pasan a ESCALAR;
   `--fecha-corte <fecha>`: todo se recalcula (--todo) y se dice cuántas cambian.
   Cada modo imprime: el cambio, «N de 500 recalculadas · M cambian · t s», las M con antes → después y el porqué, y el `trace` legible de una de ellas. Todo reversible: la copia se tira. Cronometra cada modo.
C · En KIT-DEFENSA.md, una sección «Si el tribunal cambia un dato»: el comando de cada modo, lo que se ve, el tiempo medido y la frase para decirlo: «el linaje recalcula sólo lo que el cambio toca».
CRITERIOS: kit nuevo instalado en un clon limpio con todos los pasos cronometrados; trazas regeneradas; dato_en_vivo con los tres modos, tests y tiempos (< 30 s cada uno); BD real y entrega intactas; make check verde.
NO HAGAS: tocar el guion de Alfonso, la consola, pipeline/ o core/; escribir en la BD real; dejar el worktree.
```

## Prompt J5 · Bonus (+10): remesa y calendario de pagos
```
Eres el agente J5 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). [REGLAS DE CONVIVENCIA de PLAN-10.md.] Tus ficheros: src/albertitos/bonus/ (nuevo) · tests/test_bonus.py (nuevo) · docs/adr/0012-* (nuevo) · docs/BONUS.md (nuevo).
Lee además: CLAUDE.md (el bonus son +10 y es el tercer desempate; debe estar implementado y enseñado), docs/PLAN-SABADO.md (la idea: calendario de vencimientos con los 30/45/60 días del maestro + fichero de remesa para los PAGAR), core/contracts.py (Proveedor.condiciones_dias, iban), sources/excel.py, core/db.py (decisiones_vigentes) y docs/adr/ (el formato de los ADRs, con su «Resumen para el plan (5 líneas)»).

MISIÓN: lo que Alberto haría el lunes con nuestras 438 decisiones PAGAR. Pagarlas bien y a tiempo. SÓLO LECTURA sobre las decisiones: el bonus nunca cambia un resultado, una decisión ni la entrega.
A · src/albertitos/bonus/: a partir de las decisiones vigentes PAGAR, sus hechos y el maestro:
   - calendario de vencimientos: fecha de la factura + condiciones_dias del proveedor → fecha de pago; agrupado por semana; lo vencido a la fecha de corte, marcado; importes con Decimal;
   - fichero de remesa: SEPA pain.001 (XML) o, si no da tiempo, un CSV bancario claro, con IBAN (validado con formatos.py), importe, referencia de factura y fecha de ejecución; totales de control (número de pagos y suma);
   - lo que no se puede pagar bien (IBAN inválido, proveedor sin condiciones) va a una lista de avisos, no a la remesa;
   - un comando: `uv run python -m albertitos.bonus --salida dist/bonus/` (NO toques cli.py: es de Miguel; si quieres un subcomando, PIDO A Miguel con el parche).
B · Tests: sumas cuadran con las facturas; un IBAN inválido no entra; sin condiciones → aviso; sólo PAGAR (nunca ESCALAR ni NO_PAGAR); el XML, si lo haces, es válido contra la estructura básica de pain.001; sobre una copia de la BD real, la remesa tiene 438 pagos o explica cada diferencia.
C · docs/adr/0012-*.md: por qué este bonus y no otro, por qué de sólo lectura y qué queda fuera, con su «Resumen para el plan (5 líneas)». docs/BONUS.md: cómo se enseña en la defensa en 30 s (comando, qué se ve, una cifra: «438 pagos, X €, N vencen esta semana»).
D · Para la consola (de Alejandro), deja en la bitácora un PIDO A Alejandro con el fichero que generas y lo que podría enseñar.
CRITERIOS: implementado, probado sobre una copia de la BD real y enseñable en 30 s; nada cambia en decisiones ni en la entrega; make check verde.
NO HAGAS: tocar cli.py, pipeline/, rules/ o console/; escribir en la BD real.
```

---

## Cierre del ciclo (Javier, ~14:30)
```bash
make agentes-check && make check && git push origin javier/ingesta
sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl | cut -c1-12      # igual que al empezar
```
Antes de las 15:00: el kit de J4 a Alfonso, y un ensayo de 10 minutos de la defensa en su portátil. Antes de las 17:30: la
línea del respaldo de visión (J3) en `.env`, si J3 la recomienda. A las 18:00: la chuleta de J1. Con el bonus de J5 listo,
decidir con Alfonso si entra en el guion (30 s en el bloque 4 o en el cierre).
