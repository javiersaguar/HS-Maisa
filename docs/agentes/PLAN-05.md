# PLAN-05 · ciclo 5 · sábado 19/09 ~09:15 → ~11:15 · rama `javier/ingesta` · tres agentes

**Por qué este ciclo.** Anoche, tres cosas estuvieron a punto de costarnos la elegibilidad, y las tres dependían de que
alguien se acordara en el momento justo:

1. Los 10 ficheros del lote 2 **simulado** seguían en la BD; al detectar duplicados, marcó como duplicados a sus
   **originales del lote 1** y movió 20 decisiones.
2. `marcar_duplicados` **sólo corre dentro de `run`**; como la BD se construyó con pasos sueltos, nunca se ejecutó y
   `PO-2026-0492` (facturado dos veces, 1.512,50 € cada una) estaba **en PAGAR las dos veces**.
3. El hash del zip y el recuento de ficheros sólo se comprueban si alguien lo hace a mano.

A las 18:00 de hoy llega el lote 2 de verdad. Este ciclo convierte esas tres cosas en **comprobaciones que fallan solas
y en voz alta**, y las deja ensayadas. Son dos horas; corre en paralelo con la consola de Alejandro, la muestra
etiquetada de Mónica y el PDF de Alfonso.

## Antes de lanzar (Javier, 3 min)
```bash
cd /home/javier/proyectos/HackSpain && git switch javier/ingesta && git pull --ff-only && make check
curl -sf http://127.0.0.1:8009/erp/estado | grep -o '<asientos>[0-9]*' || echo "arranca el ERP: make erp-fast"
uv run albertitos status | head -2      # debe decir: ficheros por lote {1: 500}
```

## Propiedad de ficheros (`plan.json`; `make agentes-check` lo verifica)
| Agente | Misión | Escribe SÓLO en |
|---|---|---|
| **E1** | Preflight: la BD no puede llegar contaminada al lote 2 | `scripts/preflight_lote2.py` · `tests/test_preflight.py` · `src/albertitos/sources/estado_bd.py` |
| **E2** | Auditoría de entrega: ningún PAGAR que no toque, ningún duplicado sin marcar | `scripts/auditoria_entrega.py` · `tests/test_auditoria.py` · `docs/agentes/AUDITORIA-ENTREGA.md` |
| **E3** | Materiales verificados y runbook cronometrado de punta a punta | `scripts/verificar_material.py` · `tests/test_material.py` · `.claude/skills/lote2/SKILL.md` · `docs/agentes/ENSAYO-LOTE2.md` |
| todos | canal y cierre | `docs/agentes/BITACORA.md` (append) · `docs/agentes/PARTE.md` (su sección) |

Interfaces: E3 llama a los scripts de E1 y E2 desde la skill, no los reescribe. E1 expone
`sources/estado_bd.py` con funciones puras que E2 puede importar (E2 no las modifica: si necesita una, la pide en la
bitácora). Nadie toca `core/`, `pipeline/`, `cli.py`, `rules/` (Miguel/Mónica): las peticiones van a la bitácora.

---

## Prompt E1 · Preflight del lote 2

```
Eres el agente E1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otros dos agentes (E2, E3) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/preflight_lote2.py · tests/test_preflight.py · src/albertitos/sources/estado_bd.py. Cualquier otro fichero: NO lo toques; escribe `PIDO A E2:`/`PIDO A E3:`/`PIDO A Miguel:` en docs/agentes/BITACORA.md y sigue.
2. docs/agentes/BITACORA.md es append-only: entrada AL FINAL al empezar, por hito y al terminar. Lee las de E2 y E3 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no ejecutes /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas. Nunca `git add -A`.
4. **No modifiques la BD real** (`dist/albertitos.db`): tu script sólo LEE. Para los tests usa BD temporales (fixture `conn` de tests/conftest.py). Si necesitas borrar filas simuladas, el script debe PROPONER el comando, no ejecutarlo, salvo con `--limpiar` explícito.
5. Al terminar (o si llevas > 20 min bloqueado) rellena SÓLO tu sección "E1" de docs/agentes/PARTE.md.
6. Lee CLAUDE.md, .claude/skills/lote2/SKILL.md, docs/agentes/partes/PARTE-04.md (sección D2: el incidente de los duplicados) y docs/PLAN-SABADO.md antes de empezar.

MISIÓN: que sea IMPOSIBLE llegar al lote 2 con la BD contaminada, y que el estado de la BD se pueda leer de un vistazo.

Contexto del incidente (18/09, 01:30): B1 dejó 10 PDFs del lote 2 simulado (`L2-*`) ingeridos como `lote=2` para ensayar. Al ejecutar `marcar_duplicados`, como son copias de facturas reales, el detector marcó como duplicados también a sus **originales del lote 1**: 20 decisiones cambiaron a ESCALAR. Hubo que borrar las filas `L2-%`, reextraer 12 hechos y volver a decidir. Además `package` mete en `outcomes_lote2.jsonl` TODO fichero con `lote=2` de la BD: con los simulados dentro, la entrega habría salido con ficheros que no existen → NO APTO.

PASOS:
1. `src/albertitos/sources/estado_bd.py`: funciones puras, sin efectos, que reciben una conexión en solo lectura:
   - `ficheros_fantasma(conn, dir_lote1, dir_lote2)` → file_id que están en la BD pero NO en los directorios reales (los `L2-*` del simulado caen aquí).
   - `ficheros_sin_hechos(conn)`, `ficheros_sin_decision(conn)`.
   - `hechos_huerfanos(conn)` → hechos cuyo `sha256` ya no está en `ficheros`.
   - `resumen_estado(conn, ...)` → dataclass con todo lo anterior + recuentos por lote, por resultado y por método.
   Con docstrings que expliquen POR QUÉ existe cada una (el incidente).
2. `scripts/preflight_lote2.py`: comprobación de 10 segundos que se ejecuta ANTES de tocar el lote 2. Imprime una tabla y **sale con código 1** si algo está mal, con el comando exacto para arreglarlo. Comprueba:
   - ficheros fantasma en la BD (con el `DELETE` listo para copiar, y `--limpiar` para ejecutarlo);
   - hechos huérfanos;
   - que el interruptor de caos esté apagado (`sources.chaos.modo()` es None) — ojo: ahora es por BD;
   - ERP v1 vivo en :8009 y, si `--erp-lote2 <url>`, también el segundo bridge;
   - espacio libre en `dist/` (> 500 MB) y que la BD tenga copia reciente (avisa si no existe `dist/albertitos.db.bak`, y con `--respaldar` la crea: copiar el fichero, WAL incluido, es la red de seguridad más barata que tenemos);
   - que `data/lote2/facturas` esté vacío o no exista (si ya hay ficheros, dilo: puede ser un intento anterior);
   - coherencia de fixtures: `data/fixtures/hechos_caja.jsonl` tiene exactamente los 500 del lote 1.
3. `tests/test_preflight.py`: BD temporal con un fichero fantasma → el preflight falla y nombra el fichero; BD limpia → pasa; `--limpiar` borra sólo lo fantasma y deja intacto el resto (comprueba recuentos antes y después).
4. Ejecuta el preflight contra la BD real y pega la salida en tu sección del parte.

CRITERIOS DE ACEPTACIÓN: `uv run python scripts/preflight_lote2.py` sale 0 con la BD actual; introduciendo a mano un fichero fantasma en una BD de prueba sale 1 y explica qué hacer; tests verdes; el script no escribe nada sin `--limpiar`/`--respaldar`.

NO HAGAS: tocar core/, pipeline/, cli.py, rules/, la skill (es de E3); borrar filas de la BD real sin `--limpiar`; duplicar la lógica de `pipeline.validar` (impórtala).
```

---

## Prompt E2 · Auditoría de entrega

```
Eres el agente E2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otros dos agentes (E1, E3) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/auditoria_entrega.py · tests/test_auditoria.py · docs/agentes/AUDITORIA-ENTREGA.md. Cualquier otro fichero: NO; `PIDO A E1:`/`PIDO A Miguel:`/`PIDO A Mónica:` en docs/agentes/BITACORA.md.
2. docs/agentes/BITACORA.md es append-only: entrada AL FINAL al empezar, por hito y al terminar. Lee las de E1 y E3 antes de cada hito.
3. No cambies de rama; nada de stash/checkout/merge/rebase; no /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas. Nunca `git add -A`.
4. Tu script sólo LEE la BD y los JSONL. No modifica nada.
5. Al terminar rellena SÓLO tu sección "E2" de docs/agentes/PARTE.md.
6. Lee CLAUDE.md, .claude/rules/entrega.md, docs/agentes/DECISIONES-NORMA.md, docs/trampas.md y docs/agentes/partes/PARTE-04.md (D2) antes de empezar.

MISIÓN: una auditoría que se ejecuta ANTES de cada entrega y que habría cazado sola los dos errores de anoche: dos facturas del mismo pedido en PAGAR, y una factura escalada por un motivo falso.

Contexto: `marcar_duplicados` sólo corre dentro de `run`; con pasos sueltos no se ejecuta y `PO-2026-0492` (dos facturas, 1.512,50 € cada una, un único asiento PENDIENTE) salió PAGAR dos veces. Y `scan_025.pdf` escalaba con el motivo literal `el documento dice: "None"` porque el modelo devolvió esa cadena. Referencia actual del lote 1: **443 PAGAR · 48 ESCALAR · 9 NO_PAGAR**.

PASOS:
1. `scripts/auditoria_entrega.py [--db ...] [--lote 1|2|ambos] [--json]`, sólo lectura, que comprueba y sale con código 1 si algo es ROJO:
   - **ROJO · duplicados sin marcar**: dos o más ficheros con hechos que comparten `pedido` o `(nif_emisor, num_factura)` y alguno en PAGAR. Mensaje: "ejecuta `albertitos run` entero o `marcar_duplicados`; con pasos sueltos no se ejecuta".
   - **ROJO · PAGAR incoherente**: para cada PAGAR, seis comprobaciones contra maestro y ERP (pedido en el Excel · IBAN del proveedor del pedido · NIF · importe ±0,01 · asiento existe · asiento no PAGADA) y fecha presente. Anoche daban 0/443.
   - **ROJO · evidencia falsa**: `texto_sospechoso` que sea "None"/"null"/vacío, o un motivo que cite una evidencia que no está en el texto del PDF.
   - **ROJO · conjunto**: los `file_id` con decisión vigente no coinciden exactamente con los PDFs del directorio del lote.
   - **ÁMBAR** (no bloquea, se informa): ESCALAR > 15 % o NO_PAGAR > 5 % · facturas con `confianza < 1` en PAGAR (hoy 5) · ficheros sin decisión.
   - Salida: tabla por comprobación con recuento y los primeros file_id; con `--json`, apto para engancharlo a otro script.
2. `tests/test_auditoria.py`: BD temporal construida a mano con (a) dos facturas del mismo pedido ambas PAGAR → ROJO que las nombra; (b) un PAGAR cuyo IBAN no es el del maestro → ROJO; (c) `texto_sospechoso = "None"` → ROJO; (d) una BD coherente → verde. Sin red, < 5 s.
3. Ejecútalo contra la BD real y pega la salida literal en `docs/agentes/AUDITORIA-ENTREGA.md`, con una sección "qué significa cada comprobación y qué hacer si sale roja" pensada para leerla a las 18:05 con prisa.
4. En la bitácora: **PIDO A Miguel** que `/entrega` (o `package`) llame a esta auditoría antes de escribir, o que la skill la ejecute; y dile la referencia 443/48/9 para comparar.

CRITERIOS DE ACEPTACIÓN: la auditoría pasa en verde contra la BD actual; en las tres BD de prueba con errores sale roja y nombra el fichero; el documento se lee en un minuto; tests verdes.

NO HAGAS: tocar core/, pipeline/, cli.py, rules/, ni los scripts de E1/E3; modificar la BD; "arreglar" decisiones (la auditoría informa, no decide).
```

---

## Prompt E3 · Materiales verificados y runbook cronometrado

```
Eres el agente E3 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Trabajas EN PARALELO con otros dos agentes (E1, E2) en este mismo directorio y en la misma rama `javier/ingesta`, en ficheros distintos. Reglas de convivencia, sin excepción:
1. Sólo editas: scripts/verificar_material.py · tests/test_material.py · .claude/skills/lote2/SKILL.md · docs/agentes/ENSAYO-LOTE2.md. Cualquier otro fichero: NO; `PIDO A E1:`/`PIDO A E2:`/`PIDO A Miguel:` en docs/agentes/BITACORA.md.
2. docs/agentes/BITACORA.md es append-only: entrada AL FINAL al empezar, por hito y al terminar. Lee las de E1 y E2 antes de cada hito (sus scripts entran en tu runbook).
3. No cambies de rama; nada de stash/checkout/merge/rebase; no /handoff ni /sync. Commitea sólo tus ficheros con rutas explícitas. Nunca `git add -A`.
4. **No escribas en `data/lote2/`** (reservado para el material real) ni en `data/caja/`. Para ensayar usa `data/fixtures/lote2_sim/` (10 PDFs ya preparados) y una BD aparte: `ALBERTITOS_DB=dist/ensayo/ensayo.db`.
5. Al terminar rellena SÓLO tu sección "E3" de docs/agentes/PARTE.md.
6. Lee CLAUDE.md, la skill `/lote2` entera, docs/agentes/ENSAYO-LOTE2.md (tu propio antecedente, del ciclo 2) y docs/PLAN-SABADO.md antes de empezar.

MISIÓN: que a las 18:00 nadie tenga que pensar. Un comando verifica el material recibido, y el runbook está probado de punta a punta con los tiempos reales, incluyendo `run` entero (no pasos sueltos) y los preflights de E1 y E2.

PASOS:
1. `scripts/verificar_material.py <zip|directorio> [--hash <sha256 esperado>]`: comprueba y sale 1 con mensaje claro si falla:
   - sha256 del zip y comparación con el publicado en el canal (si se pasa `--hash`); si no se pasa, lo imprime para cotejarlo a ojo;
   - contenido esperado tras descomprimir: nº de PDFs, que todos abran (pymupdf), nombres en **NFC**, y si hay nombres repetidos ignorando mayúsculas/tildes;
   - el CSV del ERP, si viene: columnas exactas que espera `alberto_erp.py` (`asiento_id,fecha_registro,proveedor_id,nif,pedido,importe_esperado,estado`), filas legibles, y cuántos asientos son nuevos y cuántos modifican a los de v1;
   - si aparece un fichero con la regla nueva (txt/md/xlsx), lo lista y lo vuelca por pantalla: la web ya no promete un "norma v4" como fichero, puede venir de cualquier forma.
2. `tests/test_material.py`: con un zip construido al vuelo en tmp (2 PDFs + CSV bueno) pasa; con un PDF corrupto, un nombre en NFD o el CSV sin una columna, falla y lo dice. Sin red, < 5 s.
3. **Ensayo completo cronometrado** con el lote simulado y BD aparte, en este orden, que es el que irá a la skill:
   `preflight_lote2.py` (E1) → `verificar_material.py` → `ingest --dir … --lote 2` → **`albertitos run`** (entero: incluye `marcar_duplicados`) o, si `run` no admite el directorio simulado, `extract` + `marcar_duplicados` + `decide` documentando POR QUÉ → `erp pull --tag v2-sim` + `erp diff` → `inventario_trampas.py --con-hechos` → `auditoria_entrega.py` (E2) → `package`. Anota el reloj de cada paso.
4. Reescribe `.claude/skills/lote2/SKILL.md` con ese orden exacto, los comandos literales, los tiempos medidos y **las tres cosas que no se pueden olvidar** (limpiar simulados, `run` entero, hash del zip) como paso 0 con su comando. Actualiza `docs/agentes/ENSAYO-LOTE2.md` con los tiempos nuevos.

CRITERIOS DE ACEPTACIÓN: el ensayo completo corre sin intervención manual salvo los comandos de la skill; tiempos anotados; la skill la puede seguir alguien que no haya tocado el repo; tests verdes; nada escrito en data/lote2/ ni data/caja/.

NO HAGAS: tocar core/, pipeline/, cli.py, rules/, extract/, sources/ ni los scripts de E1/E2 (llámalos); ejecutar el caos global; dejar filas del ensayo en la BD real (usa `ALBERTITOS_DB=dist/ensayo/ensayo.db`).
```

---

## Cierre del ciclo (Javier)
```bash
make agentes-check && make check && git push
```
Y antes de las 18:00, con el material ya en la mano: `preflight_lote2.py` → `verificar_material.py` → skill `/lote2`.
