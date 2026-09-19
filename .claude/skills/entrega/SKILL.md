---
name: entrega
description: Runbook de entrega al repo público HS-Maisa-Entrega (outcomes.jsonl, outcomes_lote2.jsonl, albertitos_plan.pdf). Úsalo para la entrega de seguro del sábado 17:30 y la final del domingo 08:00.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(git *) Bash(gh *) Bash(ls *) Bash(sha256sum *)
---
# Entrega

## 1. Preparar

La BD debe tener las decisiones vigentes y el PDF del plan debe estar actualizado en `dist/entrega/albertitos_plan.pdf` (`make plan-pdf` cuando cambie el plan). El script genera los JSONL desde la BD; nunca se editan a mano.

## 2. Confirmar destino y horario

Por defecto se usa el repo público `javiersaguar/HS-Maisa-Entrega`, sobreescribible con `ENTREGA_REPO`, y el clon `../HS-Maisa-Entrega` (`--destino` para cambiarlo). Se verifica que sea PUBLIC y que origin, incluido el destino de push, coincida. `--sin-gh` omite sólo visibilidad, para pruebas con remotos locales; no usarlo en la entrega oficial.

Madrid: ámbar desde el domingo 20/09 a las 02:00; rojo desde las 10:30 salvo `--despues-del-cierre` explícito. El cierre oficial sigue siendo a las 11:00; la excepción no amplía el plazo.

## 3. Publicar con auditoría obligatoria

```bash
make publicar
# Leer el paquete, auditoría, nombres y hashes; sólo entonces:
make publicar ARGS=--publicar
```

Orden: backup SQLite coherente → package en carpeta temporal → validate de cada lote → auditoría → comprobar repo público y destino → comparar archivos → push. Cada ejecución vuelve a comprobar todo. Si hay PDFs del lote 2, falta de su JSONL o una validación incorrecta bloquean siempre.

El modo seco no modifica BD, dist/entrega, clon de destino, remoto ni registro: ensaya copia/commit en un clon temporal y hace `push --dry-run`. Si la auditoría da rojo, se detiene antes de consultar GitHub o tocar el destino. La publicación usa los mismos controles y sólo escribe los entregables en el repo separado; todos los comandos Git llevan `git -C`.

El destino debe estar limpio, al día con origin/main y contener sólo .git y los entregables. No se borran README ni otros archivos automáticamente. Si no hay diferencias, termina sin commit vacío. Si hay cambios, el commit incluye fecha, recuentos, norma y ERP de las decisiones de la copia; las versiones múltiples se enumeran (linaje granular). Tras confirmar el push, añade fecha, commit, recuentos, norma, ERP, persona y excepción si la hubo a `docs/entregas.log`.

Un push rechazado no se registra como publicado: conserva el commit local, revisa el error y el estado del remoto antes de reintentar. No se fuerza ni se hace pull oculto. Si el push llegó pero falló escribir el registro, el script muestra el commit y la línea exacta que hay que recuperar.

## Aceptar un rojo

Sólo una decisión explícita de la persona que entrega permite esta excepción. Ejemplo histórico: scan_025 permanece ESCALAR correctamente, pero su motivo cita «None» y Mónica aún no ha decidido DOCUMENTO_SUPERPUESTO. Esto no supone autorización permanente.

```bash
make publicar ARGS='--aceptar-rojo "scan_025: ESCALAR correcto; evidencia None pendiente de decisión de Mónica"'
# Tras revisar la salida y confirmar ese criterio:
make publicar ARGS='--publicar --aceptar-rojo "scan_025: ESCALAR correcto; evidencia None pendiente de decisión de Mónica"'
```

El motivo no puede estar vacío y queda íntegro en el mensaje del commit y en el registro (escapado como JSON si contiene saltos de línea). Se acepta el informe rojo completo: leer todos sus hallazgos. No permite saltarse package, validate, un fallo técnico de la auditoría, el horario ni archivos extra.

Ensayo F1, 19/09: `make publicar` **0,685 s**, package/validate APTO (500, 443/48/9), rojo sólo por la evidencia falsa de scan_025. BD, dist/entrega y archivos del clon real con hashes idénticos antes/después. Publicaciones ensayadas exclusivamente contra remotos bare locales.

## Si el script falla: comandos manuales de diagnóstico y recuperación

Se conservan los comandos anteriores debajo. No son una vía para omitir la auditoría: después de generar/validar, ejecutar `uv run python scripts/auditoria_entrega.py` y detenerse con rojo. Para aceptar uno, volver al script con motivo. El flujo manual sí escribe dist/entrega y eventos emit en la BD; no usarlo para un ensayo que deba dejar los originales intactos.

### Generar
```
make package            # dist/entrega/outcomes.jsonl (+ outcomes_lote2.jsonl si hay lote 2)
make plan-pdf           # dist/entrega/albertitos_plan.pdf
```
Si `package` falla, NO edites el JSONL: dice qué file_id faltan o sobran. Arregla en la BD (reprocesa) y repite.

### Validar dos veces
```
uv run albertitos validate dist/entrega/outcomes.jsonl --lote 1
uv run albertitos validate dist/entrega/outcomes_lote2.jsonl --lote 2   # si existe
```
Después lanza el subagente `auditor-outcomes` y lee su informe. Si marca algo rojo, para; la excepción sólo se tramita con el script y --aceptar-rojo, para que quede registrada.

### Publicar en el repo separado (https://github.com/javiersaguar/HS-Maisa-Entrega, público)
El valor por defecto es ese; `ENTREGA_REPO` en el entorno lo sobrescribe (no se lee `.env`: los agentes no tienen permiso).
Se trabaja con `git -C` y **sin `cd`**: así el hook sabe que estos comandos van al repo de entrega y no
al de la solución (si usas `cd`, la regla "a main sólo Miguel" te bloqueará el push en tu portátil).
```
SOL="$PWD"; ENTREGA="${ENTREGA_REPO:-javiersaguar/HS-Maisa-Entrega}"; DEST=$(cd .. && pwd)/HS-Maisa-Entrega
gh repo view "$ENTREGA" --json visibility -q .visibility          # tiene que decir PUBLIC
test -d "$DEST/.git" || gh repo clone "$ENTREGA" "$DEST"          # la primera vez el repo está vacío: clona igual (aviso)
git -C "$DEST" pull --ff-only origin main 2>/dev/null || true
cp "$SOL/dist/entrega/outcomes.jsonl" "$SOL/dist/entrega/albertitos_plan.pdf" "$DEST/"
cp "$SOL/dist/entrega/outcomes_lote2.jsonl" "$DEST/" 2>/dev/null || true
ls -A "$DEST"  # DEBE listar sólo: .git outcomes.jsonl outcomes_lote2.jsonl albertitos_plan.pdf
```
Si `ls -A` muestra cualquier otra cosa (README, .gitignore, LICENSE, código), para y pide a su dueño que la retire conservando lo necesario. No crees
README desde la web de GitHub: la raíz tiene que tener **exactamente** los tres ficheros.
```
git -C "$DEST" add -- outcomes.jsonl albertitos_plan.pdf
# Añadir outcomes_lote2.jsonl explícitamente sólo si existe.
git -C "$DEST" diff --cached --stat && git -C "$DEST" commit -m "entrega $(date +%FT%H:%M)"
git -C "$DEST" push -u origin HEAD:main   # la primera vez crea la rama main en el repo vacío; después, igual
git -C "$DEST" rev-parse HEAD             # este commit es el que registrará la organización a las 11:00
```
Ensayado el 19/09 a las 02:30 con el lote 1 completo: `package` 2,1 s, `plan-pdf` 1,8 s, clonado y `push --dry-run`
correctos. El JSONL sale **byte a byte idéntico** si la BD no ha cambiado (sha256 `5ec17aaa…`), así que repetir
`make package` no es peligroso.

### Registrar
Anota en `docs/entregas.log` (en este repo): fecha, commit del repo de entrega, nº de líneas de cada JSONL, versión de norma/ERP usada. Avisa en el canal con el commit.

### Antes del domingo 08:00 comprueba además
- `outcomes_lote2.jsonl` existe aunque el lote 2 no haya ido bien: 40 líneas, una por fichero. Un ESCALAR honesto vale; una línea ausente = NO APTO.
- El PDF abre y tiene las dos secciones (Arquitectura, ADRs).
- El repo es público: `gh repo view javiersaguar/HS-Maisa-Entrega --json visibility`.
- La organización clona y registra el commit a las **11:00** (cierre interno 10:30): nada de pushes después.
