# Parte de fin de ciclo · ciclo 6

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2 · 04: D1-D2 · 05: E1-E3).

## F1 · Entregar con un comando, con la auditoría como puerta
- Estado: **terminado**. Commits **626556b** (publicación, tests y Makefile) y **4881df5** (hook y tests); skill y este cierre en el commit que contiene el parte. Sin push a GitHub.
- Comando: `make publicar` en seco; `make publicar ARGS=--publicar` publica. Package y validate corren como subprocesos sobre backup SQLite y carpeta temporal; la BD real y dist/entrega nunca se escriben. La auditoría va después, antes de gh/destino. Un rojo sólo se acepta con `--aceptar-rojo "motivo"`, registrado en commit y docs/entregas.log. No permite saltar errores técnicos ni un JSONL inválido.
- Repo PUBLIC verificado; origin y pushurl cotejados con ENTREGA_REPO; destino limpio y al día, lista exacta de entregables + .git, sin borrar extras. En seco, clon temporal y push --dry-run, sin modificar el destino. Sin diferencias no crea commit. Tras un push confirmado registra versiones reales de decisiones, incluyendo mezclas por linaje. Si falla el push, no lo registra como publicado.
- Horario Madrid: ámbar desde domingo 02:00, rojo desde 10:30 salvo --despues-del-cierre explícito.
- Hook: cuenta ficheros sin decisión vigente, muestra hasta tres; sólo stdlib y SQLite modo ro, conexión cerrada, BD ilegible no rompe sesión. Ya no lee .env: informa sólo si existe.
- Skill /entrega: paso 3 con los dos comandos; excepción motivada; manual anterior conservado como recuperación, con auditoría obligatoria.
- Makefile: publicar; kit-demo y kit-instalar solicitados por F2; corregido erp-status para propagar fallo de curl. ERP vivo exit 0; puerto muerto :1 → curl (7), make Error 7, salida no cero.
- Verificado: **31 tests de publicación/hooks** (15 publicación y 16 hooks), offline, remoto bare local, sin BD real. Incluyen rojo/aceptación, visibilidad privada, faltante lote2, README, cambios locales, remoto de push distinto, fallo del push sin log, dos publicaciones sin cambios, destino nuevo con espacios y comandos Git aprobados por decidir() del hook.
- `make check` → **359 passed, 2 deselected in 32.51s**, lint/formato verdes; `make agentes-check` → **OK: cada fichero tiene un único dueño**.
- Ensayo real `make publicar`: **0,685 s**, package y validate APTO 500 (443/48/9), exit no cero esperado por scan_025. No se ejecutó gh ni Git contra el destino. Salida literal relevante:

```text
ROJO      2  Motivo o evidencia falsos ("None", cita que no está en el PDF, cita vieja)
  - scan_025.pdf: texto_sospechoso = 'None' (ESCALAR)
  - scan_025.pdf: el motivo de R6 cita 'None'
VEREDICTO: ROJO · 1 comprobación(es) en rojo: NO entregar
ROJO: Auditoría ROJA: NO se publica ni se accede al destino. Corrige los casos mostrados y repite make publicar; excepción explícita: --aceptar-rojo '<motivo>'.
```

- Hook real: `- BD: albertitos.db · ficheros=500 · decisiones vigentes=500 · ficheros sin decisión=0`.
- Registro completo del ensayo: dist/ensayo/f1-publicar-seco.log; hook: f1-session-start.log; huellas: f1-integridad.json. Todos los hashes comparados (BD, dist/entrega y archivos raíz del clon real) son iguales antes/después:
  - dist/albertitos.db: `9c812c30d51e7e834ddc7ec867631dadd2b062c25fc6240629448ccadcf9ee89` → `9c812c30d51e7e834ddc7ec867631dadd2b062c25fc6240629448ccadcf9ee89`.
  - dist/entrega/outcomes.jsonl: `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3` → `5ec17aaa50455f9459038520b14db8313cc1f1c8e2aeb787b9717023541d73a3`.
  - dist/entrega/albertitos_plan.pdf: `a67e695b4e7990ba38fe09e9446eafb35af2482813334e0fb0543967cc4f5218` → `a67e695b4e7990ba38fe09e9446eafb35af2482813334e0fb0543967cc4f5218`.

- Pendiente de otros: Mónica decide la política de scan_025; Javier ejecuta la publicación cuando corresponda. La excepción está implementada, no ejecutada sobre el repo real. Ningún pendiente de implementación F1.

## F2 · La defensa funciona en un portátil que no es el mío
- Estado: **terminado** (07:20 → 07:58). La demo, el breaker, la traza y la consola funcionan en un clon limpio con el kit. Falta el ensayo de verdad en el portátil de Alfonso (15:00), que es el que da las cifras de la sala.
- Hecho (con cifras):
  - **A · `scripts/kit_demo.py`** (`make kit-demo` / `make kit-instalar KIT=…`, objetivos añadidos por F1). `empaquetar`: copia con `backup()` (nunca cp), `.tar.gz` con la BD y `MANIFIESTO.json` (commit, sha256 de la BD, recuentos, versiones vigentes, sha256 de la entrega). `instalar`: comprueba sha256 y commit; no pisa una BD con datos sin `--forzar`; deja `.antes-del-kit` y nunca sobrescribe una copia anterior; borra el `-wal`/`-shm` de la BD vieja; avisa de un caos encendido; ejecuta `albertitos status`. La BD vacía que crea `./bootstrap.sh` se sustituye sin `--forzar` (con copia). 9 tests.
  - **Kit real:** `dist/kit/albertitos-kit-20260919-0722.tar.gz` · 1,2 MB · BD `697e3e13d6b8` · commit `b4f85c9a5` · `{'1': 500}` · 443/48/9 · caché LLM 881.
  - **B · ensayo en un clon limpio** (worktree en `dist/ensayo/limpio`, commit `184cb50`, ya quitado): bootstrap 1,6 s · instalar 0,3 s · status y trace 0,2 s · **demo `--sin-red` 4,7 s** (y 4,1 y 3,8 s al repetir) · breaker (b bis) tal cual `{'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3}` · consola `health ok` en 1,0 s · AppTest 1,3 s, 0 excepciones, 500/443/48/9. **Sin ERP**: status, trace, demo, reprocess y auditoría funcionan; `erp pull` falla con un traceback de 92 líneas; el preflight lo marca en rojo; `make erp-status` sale 0 aunque falle.
  - **C · `docs/agentes/KIT-DEFENSA.md`**: una página (45 líneas) con lo de casa, la sala en orden (comando, lo que se ve, lo que tardó, la frase, incluida la del `--sin-red`), el plan B y qué pregunta responde cada paso.
  - **D · cinco trazas** en `docs/demo/trazas/` con su comentario (README): PAGAR, NO_PAGAR y la instrucción inyectada se entienden; el duplicado no nombra a su pareja; la caída del LLM se ve entera en `copia_2026_0518`.
- Verificado con (comando → resultado literal):
  - `uv run python scripts/kit_demo.py empaquetar` → `kit: dist/kit/albertitos-kit-20260919-0722.tar.gz · 1.2 MB`; `dist/albertitos.db` `9c812c30d51e` y `outcomes.jsonl` `5ec17aaa5045` iguales antes y después (y tras cada paso con la BD real).
  - En el clon: `kit_demo.py instalar …` → `OK    la BD anterior (estaba vacía: la crea ./bootstrap.sh) queda en dist/albertitos.db.antes-del-kit` · `VEREDICTO: instalado`; `demo_caos.py --sin-red` → `run → exit 1 · entrega escrita: no` · `run → exit 0 · outcomes.jsonl 5ec17aaa5045` · `(igual: True)` · `Demo: 4.7 s`.
  - `make kit-instalar KIT=dist/kit/albertitos-kit-20260919-0722.tar.gz ARGS="--destino dist/ensayo/f2/instalado.db --sin-status"` → `VEREDICTO: instalado`.
  - `make check` → `359 passed, 2 deselected in 37.73s` · `make agentes-check` → `OK: cada fichero tiene un único dueño`.
- Ficheros tocados: `scripts/kit_demo.py`, `tests/test_kit_demo.py`, `docs/agentes/KIT-DEFENSA.md`, `docs/demo/ENSAYO-CLON-LIMPIO.md`, `docs/demo/trazas/` (6 salidas + README), `docs/agentes/BITACORA.md` (3 entradas), esta sección. Datos sólo en `dist/kit/` y `dist/ensayo/` (`f2/` con los logs literales del ensayo).
- Commits (hash · mensaje): `184cb50` kit_demo.py · `1d7adff` chuleta, ensayo y trazas · el de este parte.
- Descubierto:
  1. `./bootstrap.sh` crea una BD vacía: sin tratarla aparte, el kit habría exigido `--forzar` en todos los portátiles (resuelto en el kit).
  2. **La demo `--sin-red` tardó 4,7 s en el clon limpio; E1 midió 39,5 s a las 03:10** (cada `run`, 9-10 s allí y ~1 s aquí). No es el índice de `decisiones` (sigue sin estar). Causa no encontrada.
  3. Los reintentos ORA-00600 que promete el guion **no salen en ninguna traza**: los 122 eventos del ERP no llevan `file_id`.
  4. En la BD real hay **0 eventos `validate`**: el duplicado de `PO-2026-0492` no nombra a su pareja en la traza.
  5. Cada traza tiene 6 decisiones (ensayos del viernes, una con `erp v2-sim`, una ESCALAR por los `L2-*`) sin el porqué: `decide`/`run` no anotan el motivo del linaje.
  6. `make erp-status` sale 0 con el ERP caído; `erp pull` sin ERP es un traceback de 92 líneas.
- Pendiente / no llegué a: el ensayo en el portátil de Alfonso (es suyo, a las 15:00); explicar la diferencia 4,7 s / 39,5 s.
- Necesito de otros (quién · qué · para qué):
  - **F1** · que `make erp-status` falle cuando el ERP no responde.
  - **Miguel** · `erp pull` con un mensaje de una línea sin ERP; `trace --legible`; la línea del snapshot del ERP (consultas y reintentos) en `trace`; el grupo del duplicado en `trace`; el porqué del linaje también en `decide`/`run`; la tabla de `status` sin el histórico que asusta.
  - **Alejandro** · en Traza, la decisión vigente arriba y el historial plegado; el Panel enseña 2,38 EUR históricos.
  - **Alfonso** · reintentos ORA-00600 con `status`/`bench`, no con `trace`; la traza en la consola; confirmar que su portátil tiene bash; `bootstrap` en casa, con red.
  - **Javier** · pasar el kit a Alfonso antes de comer, y rehacerlo (`make kit-demo`) si se aplica lo de `scan_025`.
- Riesgos que veo:
  - Todas las cifras son del portátil de Javier: en el de Alfonso nadie ha medido nada todavía.
  - Si el portátil de Alfonso es Windows sin WSL, ni `bootstrap.sh` ni los comandos del breaker funcionan tal cual.
  - El kit es una foto: si la BD cambia (Mónica, lote 2), el de las 07:22 enseñará otros números que la entrega. `kit-instalar` imprime el sha256 de la entrega de ese momento para comprobarlo.
  - En la sala, `status` enseña `extract pendiente 7` y `2.3823 EUR` hasta que Miguel lo cambie: la chuleta lleva la frase.
- Propongo como siguiente tarea: que Alfonso cronometre la chuleta entera en su portátil a las 15:00 y apunte los tiempos en KIT-DEFENSA.md; y que Miguel dé a `trace` el grupo del duplicado y la línea del ERP antes del domingo, porque son justo las dos preguntas de traza que el tribunal hará con PO-2026-0492.
