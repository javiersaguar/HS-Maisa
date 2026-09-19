# Parte de fin de ciclo · ciclo 10

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (… · 08: H1-H2 · 09: I1-I2).

## J1 · Ensayo general del lote 2 con `main`, cronometrado

**Estado: BLOQUEADO, nada ejecutado.** El shell del agente no arranca (`powershell.exe ENOENT`; el
host tampoco puede aplicar el sandbox `workspace_readwrite`). Es el mismo bloqueo del ciclo 9 con I1.
**No hay ni un tiempo medido, y no he inventado ninguno.** BD real, `dist/entrega/`, `data/caja/` y el
bridge de `:8009`: intactos, porque no he ejecutado nada. Tampoco he podido correr `make check`.

**Hora:** las entradas van con la del reloj del entorno (UTC+2 = Madrid); `TZ=Europe/Madrid date` no
se pudo ejecutar.

### Lo que dejo hecho
| Ruta | Qué es |
|---|---|
| `dist/ensayo/j1/ensayo.sh` | La receta entera en una orden, cronometrada paso a paso (`ensayo.log`, `tiempos.tsv`). Worktree desechable, copia de la BD con `Connection.backup`, ERP v2 en `:8011`, material `lote2_sim` + `lote2_identicos`. Cubre verificar_material (directorio y ZIP con `--hash`), ingest, `run --erp v1`, status, pull v2, diff, `reprocess --impacted`, `reprocess --todo` (el coste del camino de la v4), inventario, auditoría, package, validate ×2, tres trazas y `publicar_entrega.py` contra un bare local. Desvío 2 (rojo forzado + `--aceptar-rojo` + su evento) y desvío 3 (contingencia en seco con el caos en la copia) incluidos |
| `dist/ensayo/j1/desvio-p05.sh` | Desvío 1 (P0-5): verificador en ROJO → `git merge origin/miguel/p0-5-nombre-repetido` → `make check` → ingest → `package` APTO, cronometrando la recuperación completa |
| `docs/agentes/CHULETA-LOTE2.md` | Reescrita. Una página, comandos verificados **contra el código fuente** de `main`, con un aviso en negrita arriba: los tiempos están **sin medir** |
| `.claude/skills/lote2/SKILL.md` | Tres correcciones (abajo) |
| `docs/agentes/ENSAYO-LOTE2.md` | Sección nueva que avisa de que las únicas cifras del documento son las de E3 (01:52), con código viejo |

### Hallazgos (revisión estática del código, no ejecución)
1. **`run --erp <versión>` existe** (`cli.py`, opción `erp`): sobraba la rama `if uv run albertitos run --help | grep -q -- '--erp'` y toda la alternativa `extract` + `reprocess --todo` que la skill daba como obligatoria.
2. **`package` ya audita** y se niega en rojo salvo `--aceptar-rojo "<motivo>"` (que exige motivo no vacío y nunca acepta un JSONL inválido). La skill seguía diciendo que la puerta no estaba puesta y que había que auditar a mano antes de `/entrega`.
3. **P0-5: la receta decía «no hay salida hasta que Miguel decida».** Es falso desde su entrada de las 11:40: la salida es `git merge origin/miguel/p0-5-nombre-repetido` (`334845e`) y seguir. Esa frase, leída a las 18:00, habría parado el lote entero.
4. **Trampa de los ensayos:** `cli.LOTE2` es la constante `Path("data/lote2")`. `run`, `package` y `validate --lote 2` **no** leen `ALBERTITOS_DIR_LOTE2` (sí lo leen el preflight y el inventario). Un ensayo que apunte esa variable a `lote2_sim` y llame a `run` no recorre el camino real; por eso los dos scripts copian el material a `data/lote2/facturas` dentro de un worktree.
5. El estado de `main` que da PLAN-10 (`990a75d`) ya se ha quedado corto: en GitHub `main` y `javier/ingesta` van por `62a28d6`.

### Lo que necesito
- **De Javier (persona):** una terminal. Lanzar `bash dist/ensayo/j1/ensayo.sh` y `bash dist/ensayo/j1/desvio-p05.sh` y pasarme `dist/ensayo/j1/tiempos.tsv`; con eso relleno chuleta, skill y ENSAYO-LOTE2. **Hasta entonces la chuleta no está ensayada y no debe usarse como si lo estuviera.**
- **De Miguel:** confirmar si el merge de P0-5 a las 18:00 lo hace él; si sí, el desvío sobra.

### Commits
Ninguno: sin shell no puedo commitear ni pasar `make check`. Los ficheros quedan editados en el árbol.

## J2 · Que un Excel o un ERP cambiados de forma no nos paren

**Estado: terminado.** El loader ya no lee por posición, cada forma nueva tiene su test y el ensayo está medido sobre
una copia de la BD real. `make check`: **497 passed, 2 deselected, 1 xfailed** (los 23 tests nuevos son míos;
`tests/test_excel.py` pasa de 12 a 35). Detalle completo, con los comandos que dan cada cifra:
[docs/agentes/ENSAYO-FUENTES.md](ENSAYO-FUENTES.md).

### Lo que dejo hecho
- `sources/excel.py` **tolerante a la forma y estricto con el contenido**: hojas y columnas por nombre normalizado
  (sin tildes, mayúsculas ni separadores) con alias por campo; la cabecera se busca en las 6 primeras filas; las filas
  vacías se saltan y la que tiene datos sin identificador se avisa con su número; lo que no se entiende va a
  `avisos_calidad` con una frase legible. Sólo se niega a cargar si falta la columna clave (`id`, `pedido`) o el
  importe de los pedidos, y entonces el error dice qué mirar: un maestro medio vacío escalaría 500 facturas sin
  explicar por qué. `ErrorMaestro` hereda de `KeyError`, así que nada de lo que ya existía cambia de comportamiento.
- **La regla de las 18:00, si llega dentro del Excel, se ve**: `hojas_norma(xlsx)` y un aviso
  `REGLA NUEVA?: la hoja «X» parece una norma y nadie la lee`. Con el Excel de hoy: `['Norma_Pagos_v3']` y ningún aviso.
- `data/fixtures/maestro_cambiado/generar.py`: **12 variantes** del Excel real (8 de forma, 4 de contenido), generadas
  al vuelo con openpyxl; el original no se toca y los `.xlsx` no entran en git.
- `tests/test_excel.py`: un test por variante más el invariante que importa (las 8 de forma dan un maestro **idéntico
  dato a dato** y la misma versión) y los errores con nombre (columna clave ausente, hoja que no está).

### Cifras (`bash dist/ensayo/j2/ensayo_maestro.sh`, copia fresca de la BD real por variante)
- Excel real y las **8 formas**: maestro `80911e429c6c` · `0 de 500 recalculadas · 0 cambian` · maestro 0,46-0,72 s,
  reprocess 0,22-0,36 s.
- `iban_cambiado` (P001): `47 de 500 recalculadas · 43 cambian` PAGAR → ESCALAR, 453 sin impacto por diff · 0,33 s.
- `importe_cambiado` (PO-2026-0002): 1 recalculada, 1 cambia · `proveedor_nuevo`: 0 de 500, 500 sin impacto.
- ERP con otra forma, sin levantar bridges (`uv run python dist/ensayo/j2/ensayo_erp_forma.py`): el CSV del bridge
  admite otro orden, columnas de más y BOM, y para con mensaje si falta un nombre; nuestro XML se parsea por etiqueta,
  así que una etiqueta nueva no rompe y una que falta da `ERP-FORMATO` con el asiento dentro. **No hay que tocar nada.**
- Huellas al empezar y al terminar: `c66d00e45be3` / `1ec4be206089`.

### Lo que necesito
- **PIDO A Mónica (decisión de norma, no de loader):** con PO-2026-0001 puesto a `ANULADO` en el Excel, el linaje
  recalcula su factura (`F26-9865_ofimática.pdf`) y **se queda en PAGAR**. La v3 sólo mira el estado del asiento del
  ERP (`norma_v3.py:183-198`); `Pedido.estado` del Excel no lo lee ninguna regla. Hoy es inocuo (las 516 filas dicen
  `ABIERTO`), pero si el sábado llegan pedidos anulados los pagaríamos. Es la otra cara de tu Q2.
- **PIDO A Miguel (`cli.py` es tuyo, 4 líneas):** cuando el Excel no se puede cargar, el mensaje es el correcto pero
  sale detrás de 60 líneas de traceback de rich. Mismo caso que arreglaste en `erp pull` (`cli.py:320`). Parche y salida
  literal en `dist/ensayo/j2/pido-a-miguel-cli-maestro.patch`, reproducible con `bash dist/ensayo/j2/ver_error_cli.sh`.
  No bloquea el lote 2: el mensaje está, sólo hay que leer la última línea.
- **Para Javier a las 18:00:** si el Excel trae una hoja nueva, sale en `albertitos maestro` como `REGLA NUEVA?` con su
  nombre; y `make erp-lote2` espera el CSV en `data/lote2/erp_export_lote2.csv` (hoy sólo hay un `.gitkeep`), si llega
  con otro nombre: `make -C data/caja erp-lote2 LOTE2_ERP=<ruta>`.

### Lo que NO está cubierto
Hojas de datos partidas en varias pestañas (se leería sólo la primera y el recuento lo delataría), `.xls` antiguo o CSV
en vez de `.xlsx` (openpyxl no los abre), y un XML del ERP con etiquetas renombradas (se detecta, pero deja el snapshot
sin bajar: eso es política de reintentos).

### Commits
`sources: el Excel tolera otra forma (cabeceras y hojas por nombre) y avisa de la hoja que parece la regla nueva`

## J3 · Las escaneadas del lote 2 no dependen de un solo modelo

**Estado: HECHO.** Hay respaldo de visión recomendado con cifras propias, y el riesgo está acotado
contra el código, no supuesto. Informe: `docs/agentes/RESPALDO-VISION.md`.

### Lo que dejo hecho
- `scripts/bench_vision_respaldo.py`: `--listar` (qué modelos ofrece el gateway) y el banco de
  candidatos de visión, con tope duro de llamadas, caché en una BD de ensayo y la BD real en sólo
  lectura. Compara contra dos referencias: los hechos vigentes y el maestro (verdad independiente).
- `docs/agentes/RESPALDO-VISION.md`: tabla, recomendación, riesgo y la línea de `.env`.
- **24 llamadas** de un tope de 30 (3 modelos × 8 escaneadas), 6 min 46 s, 0 errores, 0 desde caché.

### Cifras (`uv run python scripts/bench_vision_respaldo.py --modelos qwen3.6,deepseek-v4-flash,glm5.3-flash --facturas 8 --max-llamadas 30 --sufijo j3a`)
| Modelo | p50 | máx | tokens in/out | pedido | fecha | NIF (5 limpias) | IBAN (5 limpias) |
|---|---|---|---|---|---|---|---|
| `qwen3.6` (control) | 12,0 s | 25,8 s | 23.864 / 16.258 | 8/8 | 8/8 | 5/5 | 5/5 |
| `deepseek-v4-flash` | 4,3 s | 8,9 s | 15.168 / 4.156 | 8/8 | 8/8 | 4/5 | 3/5 |
| `glm5.3-flash` | 15,3 s | 81,2 s | 28.576 / 4.827 | 7/8 | 7/8 | 3/5 | 3/5 |

NIF e IBAN, sólo sobre `scan_001`…`scan_005`: en las otras tres el IBAN impreso no es el del maestro
(trampa de R1) y los tres modelos leyeron lo mismo, así que ahí no se mide al modelo.

### Hallazgos
- **Nadie lee mejor que `qwen3.6`.** Se confirma §5 de RESILIENCIA con una tanda propia y control.
- **`glm5.3-flash` queda descartado para visión:** 81,2 s contra un timeout de 90 s, y se dejó un
  `pedido` (`PO-2026-0463` por `PO-2026-0480`) y una `fecha`. Además ya es el respaldo de TEXTO:
  ponerlo también en visión concentra el riesgo en un modelo.
- **`deepseek-v4-flash` es el respaldo:** 3× más rápido que el principal, 0 fallos, y sus errores son
  dígitos sueltos, los mismos que comete el principal.
- **Una lectura del respaldo no puede acabar en PAGAR:** doble lectura → reconciliación con el maestro
  → `confianza` 0,6 → R6 escala (ADR-0011); y si el NIF mal leído no está en el maestro, R1 en rojo.
  El peor caso es un ESCALAR de más. Comprobado en `etapa._segunda_lectura`, `_reconciliar_con_maestro`,
  `norma_v3.regla_1_proveedor` y `regla_6`.
- **No hace falta tocar código.** `TIMEOUT_VISION_S` (90 s) le sobra al candidato; el respaldo ya se
  salta el breaker (arreglo de E1) y cachea con clave propia. `llm.py` y `test_llm.py`, sin tocar.

### Lo que necesito
- **PIDO A Javier:** una línea en `.env` antes de las 17:30 (los agentes no pueden escribirlo):
  `ALBERTITOS_MODELO_VISION_FALLBACK=deepseek-v4-flash`. Sin ella, el respaldo sigue vacío.
- **PIDO A quien lleve `docs/CIFRAS.md`** (no es mi fichero este ciclo): dos filas, con población,
  máquina y comando, desde RESPALDO-VISION.md — la de `deepseek-v4-flash` 4,3 s p50 / 8,9 s máx y la
  de `qwen3.6` 12,0 s p50 sobre estas 8 escaneadas. La §7 de RESILIENCIA dice que el respaldo de
  visión «se deja vacío a propósito»: si Javier pone la línea, esa frase queda vieja.

### Commits
`extract: mido los candidatos a respaldo de visión y recomiendo uno, porque hoy no hay ninguno`

## J4 · La defensa con el código de hoy, y el dato en vivo del domingo

**Estado: PARCIAL. El dato en vivo está escrito; el kit y los cronómetros, no.** El shell del agente
no arranca (mismo bloqueo que I1 en el ciclo 9 y que J1 hoy), así que **no he ejecutado nada**: ni un
tiempo medido, ni `make check`, ni commit. BD real, `dist/entrega/`, `data/caja/` y el bridge `:8009`
intactos, porque no los he tocado. Las horas van con el reloj del entorno (UTC+2 = Madrid);
`TZ=Europe/Madrid date` no se pudo ejecutar.

### Lo que dejo hecho
| Ruta | Qué es |
|---|---|
| `scripts/dato_en_vivo.py` | El escenario del domingo en un comando, sobre una copia (`dist/vivo.db`, `Connection.backup`): `--pagada PEDIDO`, `--importe PEDIDO=1234,56`, `--iban P003=ES…`, `--estado-pedido PEDIDO=ANULADO`, `--fecha-corte`, `--listar` (pedidos que hoy se pagan y siguen PENDIENTE), `--json` para medir. El cambio entra como snapshot nuevo (ERP `vivo`, o maestro con su versión recalculada), nunca encima del que se usó para entregar; luego `reprocess --impacted` cronometrado y la traza legible del primero que cambia |
| `tests/test_dato_en_vivo.py` | 14 tests sin red ni BD real. Los tres que importan van por el camino de verdad: un asiento a PAGADA deja esa factura en NO_PAGAR y **la otra ni se recalcula**; cambiar un IBAN sólo impacta a las facturas de ese proveedor (la otra cae en `sin_impacto`); cambiar el estado de un pedido impacta sólo a la suya. Los demás cubren que el snapshot original no se muta, que no se finge una descarga, el diff, los errores legibles y el parseo de `CLAVE=VALOR` |
| `docs/agentes/KIT-DEFENSA.md` | Al día con `main` (`8935c3e` ya mergeado), sección nueva «Si el tribunal cambia un dato», y por qué conviene pedir kit nuevo en vez del de las 10:07 |

### Decisiones de diseño (para que no se discutan el domingo)
1. **Nunca se toca una decisión a mano**: se cambia el dato y vuelve a decidir la norma. El script no
   sabe escribir en `decisiones`; sólo guarda snapshots y llama a `reprocess`.
2. **El snapshot derivado lleva `consultas=0` y `reintentos=0`**. No es una descarga del ERP, y
   `trace` no debe decir que lo fue: `resumen_erp` lo dará como «sin eventos atribuibles».
3. **Copia siempre, y desde cero en cada ejecución**: por eso es idempotente y repetible delante del
   tribunal, y por eso da igual la etiqueta fija `vivo`.
4. `version_maestro()` **duplica** el cálculo de `sources/excel.py` (el maestro de este script no sale
   de un Excel). Lo ata `test_la_version_del_maestro_es_la_que_calcula_excel`, que salta si J2 cambia
   ese cálculo. Es deliberado.

### Lo que necesito (todo requiere terminal)
- **De Javier (persona):** (1) `make kit-demo` y pasarle el kit a Alfonso —es la mitad de mi encargo y
  no lo he podido hacer—; (2) cronometrar a las 15:00 en el portátil de Alfonso `--listar`, el
  `--pagada` entero y el bloque 4; (3) un `--listar` sobre la BD real para poner el pedido concreto en
  la chuleta en lugar de `PO-2026-XXXX`.
- **De J3:** `scripts/bench_vision_respaldo.py` no compila (lleva los números de línea del visor
  dentro: `    30|import os`). Rompe `ruff format --check`, o sea el `make check` de todos.

### Lo que NO está verificado
- Que mis 14 tests pasen. El formato sí: el `check.log` de J5 señalaba mi `skipif` y ya está
  corregido; en su `check-final.log`, posterior, mis ficheros ya no aparecen.
- Ningún tiempo del dato en vivo. La chuleta lo dice en negrita en sus dos casillas.

### Commits
Ninguno: sin shell no puedo commitear ni pasar `make check`. Los tres ficheros quedan editados en el árbol.

## J5 · Bonus (+10): remesa y calendario de pagos
_(pendiente)_


### Cierre J5 · implementado, comprobación global pendiente de formato ajeno
- Commit: 8e8301d (código, 16 tests, ADR-0012 y docs/BONUS.md). Sin push.
- Comando medido: `uv run python -m albertitos.bonus --db dist/ensayo/j5/bonus.db --salida dist/ensayo/j5/bonus/`: 0,184 s. Calendario 438 / 2.428.159,06 EUR, 431 vencidos, 2 en semana 2026-W38; remesa 0 / 0,00 EUR. Las 438 diferencias están identificadas en avisos.csv como IBAN_INVALIDO: los 11 IBAN de proveedores fallan mod-97.
- `uv run pytest -q tests/test_bonus.py`: 16 passed. `uv run pytest -q`: 459 passed, 2 deselected, 1 xfailed en 39,33 s. Ruff propio y `make agentes-check` OK.
- `make check` final se detiene en formato de sources/excel.py (J2 en edición; antes ficheros de J4). No toco esos ficheros; repetir al cerrar cambios concurrentes. Logs en dist/ensayo/j5/.
- BD / outcomes al inicio y fin: c66d00e45be3 / 1ec4be206089. Copia hecha con SQLite backup, sin LLM ni red; ningún cambio en decisiones o entrega.
- PIDO A Alejandro: conectar calendario.csv, avisos.csv y resumen.json si lo quiere en consola. Calendario HTML ya enseñable; CSV es borrador, no orden bancaria. La remesa con IBAN válido está probada sólo con datos sintéticos de tests.
