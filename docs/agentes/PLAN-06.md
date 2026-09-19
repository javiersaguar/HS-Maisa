# PLAN-06 · ciclo 6 · sábado 19/09 ~07:30 → ~09:30 · rama `javier/ingesta` · dos agentes

**Dónde estamos (07:15).** `main` = `javier/ingesta` = `8052396`, `make check` en verde (323). La **entrega de
seguro ya está publicada** en `HS-Maisa-Entrega` (`fdc76e8`: 500 líneas, 443/48/9, sha256 `5ec17aaa5045`). La
auditoría sale roja **sólo** por la evidencia «None» de `scan_025` (su resultado, ESCALAR, es el correcto), y eso
espera a que Mónica decida sobre `DOCUMENTO_SUPERPUESTO`. El reprocesado por linaje y la demo sin red están
ensayados (ENSAYO-REPROCESADO.md, RESILIENCIA §3 (f)).

**Por qué este ciclo.** Quedan tres momentos en los que no se puede improvisar: la **defensa**, ensayada a las 15:00
en el portátil de Alfonso; la entrega de las **17:30**; y el lote 2 de las **18:00**, seguido de la entrega final del
domingo a las **08:00**. Hoy, entregar son once comandos a mano copiados de una skill, y la auditoría es un paso que
hay que acordarse de mirar. Además, la demo sólo funciona en un portátil: el mío, que es el único que tiene
`dist/albertitos.db`. Este ciclo convierte los dos momentos en un comando cada uno, y los prueba donde van a
ocurrir: con un remoto real de pega y en un clon limpio.

| Agente | Misión | Lo que hay al terminar |
|---|---|---|
| **F1** | Entregar con un comando, con la auditoría como puerta | `make publicar` (en seco por defecto) · tests con remoto local · hook de inicio sin la cifra engañosa |
| **F2** | La defensa funciona en un portátil que no es el mío | `kit_demo.py` (empaquetar/instalar) · ensayo cronometrado en un clon limpio · chuleta del bloque 4 · 5 trazas revisadas |

## Antes de lanzar (Javier, 3 min)
```bash
cd /home/javier/proyectos/HackSpain && git switch javier/ingesta && git pull --ff-only && make check
make erp-fast            # en otra terminal: el preflight y los tests `erp` lo necesitan
uv run python scripts/preflight_lote2.py                   # todo verde
sha256sum dist/entrega/outcomes.jsonl | cut -c1-12         # 5ec17aaa5045
mkdir -p dist/ensayo
```
Durante el ciclo **ningún agente escribe en `dist/albertitos.db`, `dist/entrega/` ni `../HS-Maisa-Entrega`**. Si
Mónica decide mientras tanto, el arreglo de `scan_025` lo aplica Javier (final de AUDITORIA-ENTREGA.md), no un
agente, y lo apunta en la bitácora con el hash nuevo.

## Propiedad de ficheros (`plan.json`; `make agentes-check` lo verifica)
| F1 | F2 |
|---|---|
| `scripts/publicar_entrega.py` (nuevo) · `tests/test_publicar_entrega.py` (nuevo) · `.claude/skills/entrega/SKILL.md` · `Makefile` · `.claude/hooks/session_start.py` · `tests/test_hooks.py` | `scripts/kit_demo.py` (nuevo) · `tests/test_kit_demo.py` (nuevo) · `docs/agentes/KIT-DEFENSA.md` (nuevo) · `docs/demo/` |

Compartidos, sólo añadiendo al final: `docs/agentes/BITACORA.md`, `docs/agentes/PARTE.md` (cada uno su sección).
El `Makefile` es de F1: F2 le pide su objetivo con `PIDO A F1:` en la bitácora.

---

## Prompt F1 · Entregar con un comando, con la auditoría como puerta

```
Eres el agente F1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (F2) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/publicar_entrega.py (nuevo) · tests/test_publicar_entrega.py (nuevo) · .claude/skills/entrega/SKILL.md · Makefile · .claude/hooks/session_start.py · tests/test_hooks.py. Cualquier otro fichero: NO lo toques; escribe `PIDO A F2:` o `PIDO A Miguel:` en docs/agentes/BITACORA.md y sigue.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar. Escríbela con un heredoc con comillas simples (<<'EOF'), no con echo: las comillas de la shell ya rompieron una entrada. Lee las de F2 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push: lo hace Javier al cerrar.
4. No escribas en la BD real (`dist/albertitos.db`), en `dist/entrega/` ni en `../HS-Maisa-Entrega`, y NUNCA hagas push a GitHub desde tus pruebas: todo contra repos locales en `dist/ensayo/` o `tmp_path`. Nunca leas `.env`.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "F1" de docs/agentes/PARTE.md.
6. Antes de empezar, lee CLAUDE.md, .claude/skills/entrega/SKILL.md, docs/agentes/AUDITORIA-ENTREGA.md, scripts/auditoria_entrega.py (sólo para llamarlo: no es tuyo), .claude/hooks/guard_bash.py y tests/test_hooks.py (el hook distingue el repo de entrega por `git -C`), y docs/entregas.log.

MISIÓN: que a las 17:30 y a las 08:00 entregar sea UN comando que no puede subir algo que la auditoría ve mal, que deja el registro escrito y que por defecto no publica nada.

A · scripts/publicar_entrega.py  (objetivo `make publicar`; `make publicar ARGS=--publicar` publica de verdad)
Pasos, en este orden. Cada uno, si falla, para con el motivo y el comando que lo arregla (como hace scripts/preflight_lote2.py):
  1. `albertitos package`, y después `albertitos validate` del lote 1 y, si existe, del lote 2. Si existe data/lote2/facturas con PDFs y NO hay outcomes_lote2.jsonl con una línea por PDF → rojo: una línea ausente es NO APTO. Llama a la CLI como subproceso: no dupliques lógica de pipeline/.
  2. scripts/auditoria_entrega.py como subproceso. ROJO → para. Única salida: `--aceptar-rojo "<motivo>"`, que publica igual pero deja el motivo literal en docs/entregas.log y en el mensaje del commit. (Es exactamente lo que hizo Javier a las 07:10 con scan_025: que quede como opción explícita y registrada, no como costumbre.)
  3. Repo de entrega: `ENTREGA_REPO` (por defecto javiersaguar/HS-Maisa-Entrega) y `--destino` (por defecto ../HS-Maisa-Entrega). Comprueba con `gh repo view … --json visibility` que es PUBLIC (desactivable con `--sin-gh`, para los tests). Si no está clonado, lo clona.
  4. Copia outcomes.jsonl, outcomes_lote2.jsonl (si existe) y albertitos_plan.pdf. Después, `ls -A` del destino tiene que ser EXACTAMENTE .git más esos ficheros. Cualquier otro fichero (README, .gitignore…) → rojo, NO lo borres tú: dilo.
  5. Si no hay diferencias con lo último publicado, dilo y termina en verde, sin commit vacío.
  6. En seco (lo que hace por defecto): enseña el diff de nombres y los sha256, y ejecuta `git -C <destino> push --dry-run`. Con `--publicar`: commit `entrega <fecha> · lote1 N (P/E/NP) [· lote2 M] · norma X · erp Y`, `git -C <destino> push -u origin HEAD:main`, y añade la línea a docs/entregas.log con su formato (fecha | commit | líneas | líneas lote2 | norma | erp | quién). La norma y el ERP se sacan de las decisiones vigentes, no se escriben a mano.
  7. Avisos por la hora (hora de Madrid, `zoneinfo`): después del domingo a las 10:30, rojo salvo `--despues-del-cierre`; entre las 02:00 (congelación) y las 10:30, ámbar.
  Usa SIEMPRE `git -C <destino>`, nunca `cd`: el hook guard_bash sólo reconoce el otro repo por `git -C`.
  El registro en docs/entregas.log lo escribe el script. Ese fichero no es de nadie del ciclo: es el registro del equipo.

B · tests/test_publicar_entrega.py, sin red: un `git init --bare` en tmp_path hace de GitHub y un clon suyo de destino. `package`, `validate` y la auditoría se sustituyen por scripts de mentira mediante variables de entorno o parámetros que sólo existen para los tests (documentado en el docstring), porque el pipeline de verdad necesita la BD real. Casos, como mínimo: en seco no crea commits en el remoto; `--publicar` crea uno con los ficheros exactos; auditoría roja → no publica, y con `--aceptar-rojo` sí, dejando el motivo en el log; un README en el destino → rojo; lote 2 presente pero sin su JSONL → rojo; dos publicaciones seguidas sin cambios → la segunda no hace commit; el hook guard_bash deja pasar los comandos que genera el script (reutiliza `decidir()` de tests/test_hooks.py importándolo, sin cambiarlo de sitio).
Después, un ensayo de verdad en seco contra el repo real: `make publicar` sin `--publicar`. Tiene que salir rojo por scan_025 y decir exactamente eso. Pega la salida en tu parte.

C · Skill /entrega: el paso 3 pasa a ser `make publicar` (en seco), leerlo y `make publicar ARGS=--publicar`. Los comandos manuales se quedan en un apartado «si el script falla», no se borran. Añade el apartado «Aceptar un rojo», con el caso de scan_025 como ejemplo.

D · Hook de inicio de sesión (.claude/hooks/session_start.py): hoy dice «eventos pendientes=7», y son 7 eventos ANTIGUOS de ficheros que después se extrajeron bien y tienen decisión (copia_2026_0518, fax_2026_0411, scan_001, reimpresion_0712, scan_018, scan_021: pruebas de caos del 18/09). Asusta a quien abre sesión y no dice nada útil. Cambia la cifra por «ficheros sin decisión=N» (N = ficheros sin decisión vigente) y, si N > 0, los primeros 3 file_id. Sigue sin dependencias: sólo stdlib y sqlite3 en modo `?mode=ro`, y si falla no puede romper el arranque. Añade el test en tests/test_hooks.py.

CRITERIOS DE ACEPTACIÓN: `make publicar` en seco contra el repo real sale rojo sólo por scan_025, lo explica y no toca nada; los tests pasan sin red y sin la BD real; la skill manda al script; el hook dice «ficheros sin decisión=0» con la BD real; `make check` y `make agentes-check` verdes.

NO HAGAS: tocar pipeline/, cli.py, core/, rules/ ni scripts/auditoria_entrega.py (si la auditoría necesita algo, `PIDO A Miguel:` o a Javier); push a GitHub; borrar nada del repo de entrega; editar outcomes a mano (el hook lo bloquea con razón).
```

---

## Prompt F2 · La defensa funciona en un portátil que no es el mío

```
Eres el agente F2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otro agente (F1) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/kit_demo.py (nuevo) · tests/test_kit_demo.py (nuevo) · docs/agentes/KIT-DEFENSA.md (nuevo) · docs/demo/ (lo que hay y lo nuevo). Cualquier otro fichero: NO lo toques; escribe `PIDO A F1:` (el Makefile es suyo), `PIDO A Miguel:`, `PIDO A Alejandro:` (consola) o `PIDO A Alfonso:` (guion) en docs/agentes/BITACORA.md y sigue.
2. docs/agentes/BITACORA.md es append-only: una entrada AL FINAL al empezar, otra por hito y otra al terminar. Escríbela con un heredoc con comillas simples (<<'EOF'), no con echo. Lee las de F1 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas (nunca `git add -A`), con mensaje `modulo: qué y por qué` y SIN trailer `Co-Authored-By` ni ninguna mención a Claude o a una IA. No hagas push.
4. La BD real (`dist/albertitos.db`) sólo se LEE, y la copia se hace con `sqlite3.Connection.backup`, NUNCA con cp: el WAL deja copias incoherentes (ADR-0008). No escribas en `dist/entrega/`. Todo lo que ensayes va en `dist/ensayo/` o `dist/kit/`. Nunca leas `.env`.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "F2" de docs/agentes/PARTE.md.
6. Antes de empezar, lee CLAUDE.md, docs/guion-defensa.md (es de Alfonso: no lo toques), docs/agentes/RESILIENCIA-Y-COSTE.md §3 (sobre todo (b bis) y (f)), scripts/demo_caos.py, scripts/preflight_lote2.py (cómo hace `--respaldar`) y la skill .claude/skills/demo/SKILL.md.

MISIÓN: la defensa (10 min: 2/2/4/2; el bloque 4 pide demostrar una caída del LLM) se ensaya a las 15:00 en el portátil de Alfonso, que NO tiene `dist/albertitos.db` (7,7 MB, gitignorada; sólo existe en el de Javier). Sin ella no hay demo, ni traza, ni consola con datos. Quiero que pasar el material a otro portátil sea un comando, y haberlo probado en un clon limpio antes de que lo pruebe Alfonso.

A · scripts/kit_demo.py
  `empaquetar`: copia de la BD real con backup() → `dist/kit/albertitos-kit-<fecha>.tar.gz` con la BD y un `MANIFIESTO.json`: commit de git, sha256 de la BD copiada, recuentos (ficheros por lote, decisiones por resultado, filas de cache_llm), sha256 de dist/entrega/outcomes.jsonl y versiones de norma/maestro/ERP vigentes. Imprime el tamaño y el comando para instalarlo.
  `instalar <tar>`: comprueba el manifiesto (sha256 de la BD y que el commit exista en el git local; si el código es más viejo que el kit, ámbar con el `git pull` que falta). Instala en `dist/albertitos.db` SÓLO si no existe; si existe, exige `--forzar` y antes hace backup a `dist/albertitos.db.antes-del-kit`. Después, `albertitos status` y comprueba que los recuentos coinciden con el manifiesto.
  El caos es por BD (`<db>.chaos.json`): el kit NO lo copia y, al instalar, avisa si en destino hay uno encendido.
  Tests en tests/test_kit_demo.py con BD temporales: ida y vuelta con los recuentos iguales; una BD modificada → el manifiesto falla; sin `--forzar` no pisa; con `--forzar` deja la copia `.antes-del-kit`.
  Pide a F1 el objetivo del Makefile: `make kit-demo` (empaquetar) y `make kit-instalar KIT=<tar>`.

B · ENSAYO EN UN CLON LIMPIO, cronometrado (es la prueba de verdad: así estará el portátil de Alfonso)
  `git worktree add dist/ensayo/limpio HEAD --detach`. Dentro: `./bootstrap.sh`, instalar el kit y después, midiendo cada paso con `time`:
  1. `uv run albertitos status` y `uv run albertitos trace scan_025.pdf`;
  2. `uv run python scripts/demo_caos.py --sin-red` (39,5 s en el de Javier);
  3. el comando del breaker de RESILIENCIA §3 (b bis), tal cual está escrito;
  4. la consola: `uv run streamlit run src/albertitos/console/app.py --server.headless true --server.port 8599` en segundo plano, `curl -sf http://127.0.0.1:8599/_stcore/health`, y pararla. Sólo compruebas que arranca con datos: la consola es de Alejandro;
  5. sin el ERP levantado (así puede estar la sala): ¿qué comandos de la demo fallan y qué mensaje dan? Apúntalo.
  Todo lo que falle en el clon limpio y no en el repo de Javier es un hallazgo: dependencias sin declarar, rutas absolutas, ficheros que sólo existen aquí. Apúntalo con el comando y la salida literal. Si el arreglo es tuyo, arréglalo; si no, PIDO A <dueño>.
  Al terminar: `git worktree remove dist/ensayo/limpio --force`. Nada de `rm -rf` (el hook lo bloquea en data/ con razón; en dist/ensayo no hace falta).

C · docs/agentes/KIT-DEFENSA.md: la chuleta de Alfonso para el bloque 4, UNA página:
  - antes de salir de casa: instalar el kit, comprobar con `status` los recuentos 443/48/9 y abrir la consola una vez;
  - en la sala, en orden: cada comando literal, lo que se ve en pantalla (una línea), cuánto tarda (lo medido en B) y la frase que hay que decir. La del `--sin-red` es obligatoria: «la vuelta la sirvo desde la caché para no depender del wifi».
  - el plan B si falla la sala: la transcripción de docs/demo/, y qué enseñar de la consola si la demo no arranca;
  - qué preguntas del tribunal responde cada paso (timeout, rate limit, respuesta inválida, caída; ¿y si el LLM se equivoca en vez de caerse? → la norma decide y la auditoría caza evidencias falsas).
  Sin cifras que no hayas medido tú o que no estén en RESILIENCIA/ESCALA con su fuente.

D · CINCO TRAZAS, que son 20 pts de la rúbrica: `albertitos trace` de un PAGAR de plantilla, un NO_PAGAR, un ESCALAR por instrucción inyectada, `PO-2026-0492` (el duplicado; las dos facturas) y `copia_2026_0518.pdf` (tiene eventos LLM-DOWN y LLM-INVALID de las pruebas del 18/09, seguidos de una extracción correcta). Para cada una: ¿se entiende sin saber el código por qué se decidió eso? Guarda las salidas literales en docs/demo/trazas/ y lo que no se entienda, con PIDO A Miguel (pipeline/trace) o a Alejandro (consola). No lo arregles tú.

CRITERIOS DE ACEPTACIÓN: el kit sale en un comando y se instala en un clon limpio, donde la demo `--sin-red`, el breaker, la traza y la consola funcionan, cada uno con su tiempo medido; la chuleta cabe en una página; las cinco trazas están guardadas y comentadas; `make check` verde.

NO HAGAS: tocar el guion de Alfonso, la consola, pipeline/, core/ ni el Makefile; copiar la BD con cp; llamar al LLM (todo el ensayo va sin red salvo el `bootstrap`); dejar el worktree creado.
```

---

## Cierre del ciclo (Javier)
```bash
make agentes-check && make check && git push origin javier/ingesta
sha256sum dist/entrega/outcomes.jsonl | cut -c1-12   # 5ec17aaa5045, o el nuevo si se aplicó lo de scan_025 (en la bitácora)
make publicar                                          # en seco: verde si ya se aplicó lo de Mónica
make kit-demo                                          # y el .tar.gz a Alfonso antes de comer
```
Si la auditoría está verde: `make publicar ARGS=--publicar` sustituye la entrega de seguro de las 07:10. Después,
que Miguel mergee a `main` y Alfonso y Mónica hagan `git pull`. Antes de las 18:00: skill `/lote2` desde el paso 0.
