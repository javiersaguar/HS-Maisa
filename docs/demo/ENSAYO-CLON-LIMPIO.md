# Ensayo de la defensa en un clon limpio (F2 · sábado 19/09/2026, 07:22-07:30)

**Qué se probó.** El portátil de Alfonso no tiene `dist/albertitos.db`. Se simuló con un clon limpio del repo:
`git worktree add dist/ensayo/limpio HEAD --detach` (commit `184cb50`), sin `.env` propio (lo crea `bootstrap.sh`
desde `.env.example`, sin key) y sin `dist/`. Dentro, `./bootstrap.sh`, el kit y la demo entera. Script:
`dist/ensayo/f2/` guarda la salida literal de cada paso (gitignorado). El worktree se quitó al terminar.

**Condiciones.** La misma máquina que el repo de Javier (WSL2, Ryzen 9 8940HX). **No es el portátil de Alfonso**: allí
los tiempos serán otros. `uv` ya tenía todo en su caché, por eso `bootstrap` tarda 1,6 s; en un portátil nuevo
descargará las dependencias y necesita red. Sin llamadas al LLM en ningún paso.

## Tiempos

| Paso | Comando | Resultado | Tiempo |
|---|---|---|---:|
| 1 | `./bootstrap.sh` | todo ✓ (crea `.env` sin key y una BD vacía con `db init`) | 1,6 s |
| 2 | `uv run python scripts/kit_demo.py instalar dist/kit/albertitos-kit-20260919-0722.tar.gz` | BD íntegra; «la BD anterior (estaba vacía: la crea ./bootstrap.sh) queda en …antes-del-kit»; 500 · 443/48/9 · caché 881 | 0,3 s |
| 3 | `uv run albertitos status` | 500 ficheros · 443/48/9 · 0 sin decisión | 0,2 s |
| 4 | `uv run albertitos trace scan_025.pdf` | la traza completa | 0,2 s |
| 5 | `uv run python scripts/demo_caos.py --sin-red` | paso 1 `run → exit 1 · entrega escrita: no`; paso 2 `exit 0 · outcomes.jsonl 5ec17aaa5045`; paso 3 `igual: True` | **4,7 s** (repetida: 4,1 y 3,8 s) |
| 6 | comando del breaker de RESILIENCIA §3 (b bis), tal cual | `{'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3} · 0.5 s` | 2,1 s el bloque (incluye `db init` e `ingest` de las 500) |
| 7 | `uv run streamlit run src/albertitos/console/app.py --server.headless true --server.port 8599` | `/_stcore/health` → `ok` | 1,0 s hasta responder |
| 8 | la consola ejecutada con AppTest (como la abriría un navegador) | 0 excepciones · métricas `Ficheros 500 · PAGAR 443 · ESCALAR 48 · NO_PAGAR 9 · pendientes 0` · pestañas Escalados, Traza, Panel | 1,3 s |

**La demo tardó 4,7 s, no 39,5 s.** E1 midió 39,5 s a las 03:10 en el repo de Javier, con cada `run` de 9-10 s; aquí
cada `run` tarda 0,8-1,3 s, en tres pasadas seguidas. No he encontrado la causa (el índice de `decisiones` sigue sin
estar en `schema.sql`, así que no es eso). La cifra que vale para la sala es la que salga a las 15:00 en el portátil de
Alfonso. En cualquier caso, cabe de sobra en el bloque de 2 minutos.

## Sala sin ERP (bridge apagado)

El bridge de `:8009` no se paró (lo usaban otros agentes): se apuntó `ALBERTITOS_ERP_URL` a `http://127.0.0.1:8999`.

| Comando | ¿Funciona? | Qué se ve |
|---|---|---|
| `albertitos status`, `trace`, `reprocess --impacted --erp v1` | **sí** | igual que con ERP: trabajan sobre el snapshot guardado en la BD |
| `demo_caos.py --sin-red` | **sí** (3,9 s) | igual: `run` usa el snapshot `v1` de la BD y no llama al ERP |
| `auditoria_entrega.py` | sí (sale 1) | rojo sólo por `scan_025`, como con ERP |
| `preflight_lote2.py` | sale 1 | `[ROJO ] ERP v1  no responde en http://127.0.0.1:8999 → make erp-fast (en otra terminal)` |
| `albertitos erp pull --tag prueba` | **no**, tras 6,1 s | un traceback de 92 líneas; la última: `ErrorERP: ERP-AGOTADO: /erp/login tras 8 intentos (último: ERP-RED)` |
| `make erp-status` | **dice que sí** (exit 0) | `curl: (7) Failed to connect …` pero el objetivo acaba en `; echo` y sale 0 |

**Conclusión:** la demo de la defensa no necesita el ERP. Sólo lo necesitan `erp pull` (el lote 2) y el preflight.

## Hallazgos (lo que falla en un clon limpio o en una sala sin ERP)

1. **`bootstrap.sh` crea una BD vacía** (`db init`). Sin tratarla aparte, el kit habría exigido `--forzar` en todos
   los portátiles. Arreglado en `kit_demo.py` (mío): una BD sin ficheros se sustituye sin `--forzar`, con copia.
2. **`make erp-status` sale 0 con el ERP caído.** · PIDO A F1 (el `Makefile` es suyo).
3. **`erp pull` sin ERP escupe un traceback de 92 líneas.** · PIDO A Miguel (`cli.py`): capturar `ErrorERP` y dar una
   línea con el arreglo (`make erp-fast`).
4. **`albertitos status` enseña `extract pendiente 7` y `EUR 2.3823`.** Son eventos del viernes: pruebas de caos cuyos
   ficheros después se extrajeron bien, y 39 eventos cobrados con la tarifa inventada de 3/15 €/Mtok antes de ponerla
   a 0. En la sala asustan si no se explican: la chuleta lleva la frase. (F1 arregla el mensaje del hook de inicio;
   la tabla de `status` es de Miguel.)
5. **Los comandos de la demo son de bash** (`ls … | xargs`, `export`, `./bootstrap.sh`). En un Windows sin WSL no
   corren. Hay que saber hoy qué tiene el portátil de Alfonso.
6. **`bootstrap.sh` necesita red** la primera vez (descarga Python y dependencias con `uv`). Se hace en casa.

Todo lo demás funcionó igual que en el repo de Javier: no apareció ninguna ruta absoluta ni ningún fichero que sólo
exista allí, salvo la BD, que es lo que lleva el kit.
