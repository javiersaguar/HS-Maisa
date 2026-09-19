# PLAN-12 · revisión con cuatro agentes (Cursor, Grok 4.6 fast) · sábado 19/09 ~15:45 → 17:15

**Para qué.** No hay trabajo nuevo hasta que llegue el lote 2 a las 18:00. Cuatro agentes **comprueban que todo lo
que decimos que funciona funciona de verdad**, pulen lo pequeño que encuentren y añaden **una** cosa sencilla cada uno.
Al terminar, cada uno deja un **resumen con formato fijo** (`docs/revision/RESUMEN-Rn.md`). Javier se los pasa a Claude,
que los revisa y lleva a `main` lo que valga.

**Dónde.** En una carpeta y una rama APARTE, para no tocar nada de lo que se entrega:
- carpeta: `/home/javier/proyectos/HS-Maisa-revision` (en Windows: `\\wsl.localhost\Ubuntu\home\javier\proyectos\HS-Maisa-revision`)
- rama: `revision/grok` (ya creada, con el código de `main`, el entorno `uv` instalado y una **copia** de la BD y de la
  entrega en `dist/`)
- **sin `.env`** a propósito: nadie puede llamar al LLM, porque el gateway es para el lote 2 de las 18:00.

## La terminal en Cursor (léelo antes de nada)
El terminal de Cursor sobre la ruta `\\wsl.localhost\…` falla con `powershell.exe ENOENT`; dos agentes de hoy se
quedaron sin shell por eso. Lo que funciona (lo encontró J2): poner como directorio de trabajo una ruta de Windows
normal (por ejemplo `C:\`) y ejecutar cada orden así:
```
wsl -d Ubuntu -- bash -lc "cd /home/javier/proyectos/HS-Maisa-revision && <tu orden>"
```
Edita ficheros desde esa terminal (heredoc) o con el editor, pero **deja siempre los finales de línea en LF**: si el
editor los pasa a CRLF, arréglalo antes de commitear (`sed -i 's/\r$//' <fichero>`).

## Reglas para los cuatro (no se negocian)
1. Trabajas SÓLO en `/home/javier/proyectos/HS-Maisa-revision`, en la rama `revision/grok`. **Nunca** en
   `/home/javier/proyectos/HackSpain`, nunca en `main` ni en `javier/ingesta`. Nada de `checkout`, `switch`, `merge`,
   `rebase`, `stash` ni `push`.
2. Sólo editas los ficheros de TU lista (abajo). Si ves algo que arreglar fuera de ella, NO lo arregles: escríbelo en
   tu resumen como propuesta, con el parche en texto.
3. **Nada de LLM ni de red**, salvo el ERP local de `http://127.0.0.1:8009`, que sólo se lee. No hay `.env` y no lo
   crees. No arranques ningún servidor en los puertos `8000`, `8001` ni `8011`: usa `8100` (R3) y `8200` (R4).
4. **La BD y la entrega de esta carpeta son copias, pero se tratan como reales**: no las borres ni las modifiques. Si
   necesitas escribir (ensayos), haz otra copia con `sqlite3.Connection.backup` dentro de `dist/ensayo/<tú>/` y apunta
   `ALBERTITOS_DB` a ella. Al empezar y al terminar apunta las huellas:
   `sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl | cut -c1-12`. Tienen que coincidir.
5. **Cambios pequeños.** Como mucho ~150 líneas por agente entre todo lo que añadas o cambies. Nada de refactorizar,
   renombrar ni «mejorar» código que funciona. Nada en `src/albertitos/{core,pipeline,extract,rules,sources}/`, `cli.py`,
   `docs/plan/`, `docs/guion-defensa.md` ni `data/`.
6. Antes de cada commit: `uv run ruff format <tus ficheros> && uv run ruff check <tus ficheros>` y
   `uv run pytest -q <tus tests>`. Al final, `make check` entero. Commit con rutas explícitas (nunca `git add -A`),
   mensaje `modulo: qué y por qué`, sin mencionar IA.
7. Si algo falla y no es de tus ficheros: **no lo arregles**. Escribe en tu resumen el comando exacto, la salida
   literal (las líneas que importan) y qué crees que pasa.
8. Coordinación: `docs/revision/BITACORA-R.md`, sólo añadiendo al final, una línea al empezar y otra al terminar.
9. **Hora límite: 17:15.** A esa hora, aunque no hayas terminado, escribe tu resumen con lo que tengas.

## Formato OBLIGATORIO del resumen (`docs/revision/RESUMEN-Rn.md`)
```
# RESUMEN Rn · <título> · <hora de inicio>–<hora de fin>
## Huellas
- al empezar: BD <12> · outcomes <12>   ·   al terminar: BD <12> · outcomes <12>
## Comprobaciones (una fila por comprobación)
| # | Qué comprobé | Comando exacto | Resultado (OK / FALLA / RARO) | Salida literal que lo demuestra |
## Hallazgos (lo que está mal o confunde), de más grave a menos
| # | Gravedad (alta/media/baja) | Dónde (fichero:línea o comando) | Qué pasa | Propuesta (parche en texto si es fuera de mis ficheros) |
## Lo que he cambiado yo
| Commit | Ficheros | Qué y por qué | Cómo se prueba |
## Lo que he añadido (la cosa sencilla)
- qué es · cómo se usa · su test · por qué ayuda
## make check al final
- literal: "NNN passed, …"
## Lo que no he podido hacer y por qué
```
Nada de «parece», «debería» o «probablemente funciona»: sólo lo que hayas ejecutado, con su salida.

## Propiedad de ficheros (rama `revision/grok`)
| R1 · lote 2 y entrega | R2 · documentación | R3 · API del bonus, confianza y chat | R4 · portabilidad y demo |
|---|---|---|---|
| `docs/agentes/CHULETA-LOTE2.md` · `scripts/ensayo/*.sh` · `docs/revision/RESUMEN-R1.md` · `docs/revision/r1/*` | `scripts/enlaces_check.py` (nuevo) · `tests/test_enlaces.py` (nuevo) · `docs/ESTADO-BACKEND.md` · `docs/CIFRAS.md` · `docs/BONUS.md` · `docs/api/*.md` · `docs/revision/RESUMEN-R2.md` · `docs/revision/r2/*` | `scripts/contrato_api_check.py` (nuevo) · `tests/test_contrato_api.py` (nuevo) · `docs/revision/RESUMEN-R3.md` · `docs/revision/r3/*` | `scripts/smoke.sh` (nuevo) · `docs/agentes/KIT-DEFENSA.md` · `docs/revision/RESUMEN-R4.md` · `docs/revision/r4/*` |

`docs/revision/BITACORA-R.md` es compartida (sólo añadir al final).

---

## Prompt R1 · El lote 2 y la entrega, ensayados otra vez tal como están escritos
```
Eres el agente R1. Lee ENTERO docs/agentes/PLAN-12.md (reglas, terminal y formato del resumen) antes de hacer nada: manda sobre este prompt. Tus ficheros: docs/agentes/CHULETA-LOTE2.md, scripts/ensayo/*.sh, docs/revision/RESUMEN-R1.md y docs/revision/r1/*.
Lee además: docs/agentes/CHULETA-LOTE2.md, .claude/skills/lote2/SKILL.md, docs/agentes/ENSAYO-LOTE2.md (la sección del 19/09 13:12) y .claude/skills/entrega/SKILL.md.

MISIÓN: a las 18:00 Javier seguirá la chuleta del lote 2 al pie de la letra. Comprueba que cada orden de la chuleta existe, con esas opciones, y hace lo que dice.
1. Huellas al empezar (regla 4).
2. `bash scripts/ensayo/lote2-ensayo.sh` y `bash scripts/ensayo/lote2-desvio-p05.sh`. Copia `dist/ensayo/j1/tiempos.tsv` y `p05-tiempos.tsv` a docs/revision/r1/. Compara los tiempos con los de la chuleta y apunta las diferencias de más del 50 %.
3. Para CADA orden de CHULETA-LOTE2.md: comprueba con `uv run albertitos <subcomando> --help` o `uv run python <script> --help` que el subcomando y cada opción que usa existen. Tabla: orden · ¿existe? · ¿opciones correctas? · nota. NO ejecutes las que escriben en la BD de esta carpeta (ingest, run, reprocess, package, contingencia --aplicar): para ésas basta con --help (el ensayo del paso 2 ya las ejecuta sobre copias).
4. `uv run python scripts/preflight_lote2.py` y `uv run python scripts/auditoria_entrega.py`: pega el veredicto.
5. `make publicar` en seco NO (necesita GitHub): comprueba sólo `uv run python scripts/publicar_entrega.py --help` y que la chuleta y la skill /entrega usan sus opciones reales.
PULIR (dentro de tus ficheros): si una orden de la chuleta tiene una opción que no existe o un nombre mal escrito, corrígela; si los tiempos han cambiado mucho, actualízalos con los del paso 2.
AÑADIR (una cosa sencilla): al final de scripts/ensayo/lote2-ensayo.sh, un resumen de una pantalla: total de segundos, pasos con exit ≠ 0 (y cuáles son esperados, como desvio-rojo-package-niega) y «huellas iguales: sí/no». Pruébalo ejecutándolo.
Resumen en docs/revision/RESUMEN-R1.md con el formato del plan. Hora límite 17:15.
```

## Prompt R2 · La documentación dice la verdad y sus enlaces funcionan
```
Eres el agente R2. Lee ENTERO docs/agentes/PLAN-12.md (reglas, terminal y formato del resumen) antes de hacer nada: manda sobre este prompt. Tus ficheros: scripts/enlaces_check.py (nuevo), tests/test_enlaces.py (nuevo), docs/ESTADO-BACKEND.md, docs/CIFRAS.md, docs/BONUS.md, docs/api/*.md, docs/revision/RESUMEN-R2.md y docs/revision/r2/*.

MISIÓN: el tribunal y el equipo leen estos documentos. Que cada comando que citan exista, que cada cifra cuadre con la BD y que cada enlace lleve a algún sitio.
1. Huellas al empezar (regla 4).
2. `uv run python scripts/cifras_check.py`: pega la salida.
3. Cifras de la BD (sólo lectura): `uv run albertitos status | head -5` y `uv run python -m albertitos.bonus --salida dist/ensayo/r2/bonus | head -12`. Busca en docs/ESTADO-BACKEND.md, docs/CIFRAS.md, docs/BONUS.md, docs/api/*.md, docs/agentes/KIT-DEFENSA.md y CLAUDE.md las cifras 438/53/9, 2.428.159,06, 2.383.400,88, 16 semanas y 1ec4be206089, y apunta cualquier sitio donde salga otra cifra para lo mismo SIN estar marcada como histórica.
4. Comandos citados: en esos mismos documentos, cada `uv run albertitos <x>` y `uv run python -m albertitos.<y>` que aparezca: comprueba con --help que existe. Tabla con los que no.
5. ADRs: `ls docs/adr/` frente a docs/adr/README.md: ¿están todos en el índice y con el mismo estado que dice su fichero?
AÑADIR (la cosa sencilla): scripts/enlaces_check.py: recorre los .md de docs/ y la raíz (CLAUDE.md, README si existe), saca los enlaces relativos `[texto](ruta)` y `[texto](ruta#ancla)`, y dice cuáles apuntan a un fichero que no existe (fichero:línea → destino). Ignora http(s)://, mailto: y los que están dentro de bloques ``` de código. Sale 1 si hay rotos. Sólo lee. tests/test_enlaces.py con un árbol temporal: uno bueno, uno roto, uno http y uno dentro de un bloque de código. Ejecútalo sobre el repo y pon la salida en tu resumen.
PULIR: arregla los enlaces rotos y las cifras sin marcar SOLO en tus ficheros. Los demás, como propuesta en el resumen.
Resumen en docs/revision/RESUMEN-R2.md con el formato del plan. Hora límite 17:15.
```

## Prompt R3 · Las rutas del bonus, la confianza y el chat, probadas por fuera
```
Eres el agente R3. Lee ENTERO docs/agentes/PLAN-12.md (reglas, terminal y formato del resumen) antes de hacer nada: manda sobre este prompt. Tus ficheros: scripts/contrato_api_check.py (nuevo), tests/test_contrato_api.py (nuevo), docs/revision/RESUMEN-R3.md y docs/revision/r3/*. NO tocas src/: lo que falle va como propuesta, con el parche en texto.
Lee además: docs/api/bonus.md, docs/api/confianza.md, docs/api/chat.md, src/albertitos/console/api.py (función despachar y RUTAS), src/albertitos/bonus/consola.py y src/albertitos/confianza/ (sólo leer).

MISIÓN: Alejandro está montando las pantallas contra estas rutas. Que lo que dice el contrato es lo que devuelven, también en los casos raros.
1. Huellas al empezar (regla 4).
2. En un script de Python (sin servidor), abre la BD en sólo lectura (`db.conectar('dist/albertitos.db', solo_lectura=True)`), añade a `console.api.RUTAS` las de `bonus.rutas()` y `confianza.rutas()` (en memoria, sin editar api.py) y llama a `api.despachar("GET", ruta, query, conn)` para CADA ruta de docs/api/bonus.md y docs/api/confianza.md: con parámetros normales; con parámetros malos (limite=-1, limite=abc, vencido=quizá, tope=0, banda=rara, file_id que no existe, file_id con tildes como «F26-3355_mensajería.pdf»); y con POST (tiene que dar 405). Tabla: ruta · query · status · ¿coincide con el contrato?
3. Tiempos: cada ruta 5 veces; la mediana, en la tabla.
4. Chat SIN LLM: `uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf"` tiene que negarse en local (estado solo_lectura, 0 ms, sin modelo). Pega la salida. NO hagas ninguna otra pregunta al chat (no hay .env ni gateway, y el tope de llamadas es de verdad).
5. Servidor HTTP de verdad: `uv run python -m albertitos.console.api --puerto 8100` en segundo plano (si no acepta --puerto, mira main() y usa lo que tenga; si no hay forma, sáltatelo y dilo), y `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8100/salud`. Páralo al acabar. (Hoy las rutas del bonus y la confianza sólo están en el puente si Alejandro ya las registró: si dan 404, apúntalo, no es un fallo tuyo.)
AÑADIR (la cosa sencilla): scripts/contrato_api_check.py: para cada ejemplo de docs/api/ejemplos/bonus-*.json y confianza-*.json que tenga "peticion"/"status"/"respuesta" (o su forma equivalente: míralos), repite la petición con despachar sobre la BD de esta carpeta y compara las CLAVES (no los valores) de la respuesta con las del ejemplo, a todos los niveles. Imprime las claves que faltan o sobran, por fichero; sale 1 si hay diferencias. Así, si alguien cambia un nombre de campo, Alejandro lo sabe antes de que se le rompa la pantalla. tests/test_contrato_api.py con un ejemplo inventado en tmp_path. Ejecútalo y pon la salida.
Resumen en docs/revision/RESUMEN-R3.md con el formato del plan. Hora límite 17:15.
```

## Prompt R4 · Que la demo funcione en un portátil que no es el de Javier
```
Eres el agente R4. Lee ENTERO docs/agentes/PLAN-12.md (reglas, terminal y formato del resumen) antes de hacer nada: manda sobre este prompt. Tus ficheros: scripts/smoke.sh (nuevo), docs/agentes/KIT-DEFENSA.md, docs/revision/RESUMEN-R4.md y docs/revision/r4/*.
Lee además: docs/agentes/KIT-DEFENSA.md, scripts/kit_demo.py (--help), scripts/demo_caos.py, scripts/dato_en_vivo.py y docs/demo/ENSAYO-CLON-LIMPIO.md.

MISIÓN: la defensa se hace en el portátil de Alfonso. Repite lo que hará él, con cronómetro, en un clon limpio.
1. Huellas al empezar (regla 4).
2. Clon limpio: `git worktree add dist/ensayo/r4/limpio HEAD --detach` y, dentro: `./bootstrap.sh`. Kit: `uv run python scripts/kit_demo.py empaquetar` en la carpeta de revisión (lee su BD en sólo lectura) y, en el clon, `uv run python scripts/kit_demo.py instalar <el .tar.gz>`. Mide cada paso con `time`.
3. En el clon, uno a uno, con `time` y la salida importante: `uv run albertitos status`; `uv run albertitos trace F26-2201_transportes.pdf`; `uv run python scripts/demo_caos.py --sin-red`; `uv run python scripts/dato_en_vivo.py --listar` y `--pagada <el primer pedido que liste>`; `uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000`; y `uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf"` (se niega en local, sin LLM: no hagas otra pregunta).
4. Compara cada tiempo y cada salida con lo que dice KIT-DEFENSA.md. Tabla: paso · lo que dice la chuleta · lo que ha salido · ¿coincide?
5. `git worktree remove dist/ensayo/r4/limpio --force` al acabar.
PULIR: pon al día KIT-DEFENSA.md con lo medido (sólo lo que haya cambiado de verdad) y añade una línea con el comando del bonus y otra con la negativa del chat, que aún no están en la chuleta.
AÑADIR (la cosa sencilla): scripts/smoke.sh: la comprobación de 30 segundos antes de salir a la sala, en SÓLO LECTURA. Lanza, con su tiempo, `albertitos status`, `scripts/auditoria_entrega.py`, `albertitos trace F26-2201_transportes.pdf`, `python -m albertitos.bonus` (salida a dist/smoke/), la ruta `/confianza/resumen` por despachar (en Python, en memoria, como en tests/test_bonus.py) y la negativa local del chat. Al final, una línea por paso (OK/FALLA y segundos) y exit 1 si alguno falla. Ejecútalo en la carpeta de revisión y en el clon limpio y pega las dos salidas.
Resumen en docs/revision/RESUMEN-R4.md con el formato del plan. Hora límite 17:15.
```

---

## Qué hace Javier
1. Abre cuatro agentes en Cursor sobre la carpeta `HS-Maisa-revision` y pega a cada uno su prompt.
2. A las 17:15, recoge los cuatro `docs/revision/RESUMEN-Rn.md` y se los pasa a Claude. Los commits están en la rama
   `revision/grok`.
3. Claude revisa cada commit, lleva a `main` lo que valga (por cherry-pick o reescrito) y descarta lo demás, diciendo
   por qué. Nada de la rama de revisión entra en `main` sin esa revisión.
