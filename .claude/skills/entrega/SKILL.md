---
name: entrega
description: Runbook de entrega al repo público HS-Maisa-Entrega (outcomes.jsonl, outcomes_lote2.jsonl, albertitos_plan.pdf). Úsalo para la entrega de seguro del sábado 17:30 y la final del domingo 08:00.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(git *) Bash(gh *) Bash(ls *) Bash(sha256sum *)
---
# Entrega

Objetivo: que a las 10:30 del domingo el verificador privado encuentre exactamente tres ficheros correctos.

## 1. Generar
```
make package            # dist/entrega/outcomes.jsonl (+ outcomes_lote2.jsonl si hay lote 2)
make plan-pdf           # dist/entrega/albertitos_plan.pdf
```
Si `package` falla, NO edites el JSONL: dice qué file_id faltan o sobran. Arregla en la BD (reprocesa) y repite.

## 2. Validar dos veces
```
uv run albertitos validate dist/entrega/outcomes.jsonl --lote 1
uv run albertitos validate dist/entrega/outcomes_lote2.jsonl --lote 2   # si existe
```
Después lanza el subagente `auditor-outcomes` y lee su informe. Si marca algo rojo, para.

## 3. Publicar en el repo separado (https://github.com/javiersaguar/HS-Maisa-Entrega, público)
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
Si `ls -A` muestra cualquier otra cosa (README, .gitignore, LICENSE, código), bórrala antes de commitear. No crees
README desde la web de GitHub: la raíz tiene que tener **exactamente** los tres ficheros.
```
git -C "$DEST" add -A && git -C "$DEST" commit -m "entrega $(date +%FT%H:%M)"
git -C "$DEST" push -u origin HEAD:main   # la primera vez crea la rama main en el repo vacío; después, igual
git -C "$DEST" rev-parse HEAD             # este commit es el que registrará la organización a las 11:00
```
Ensayado el 19/09 a las 02:30 con el lote 1 completo: `package` 2,1 s, `plan-pdf` 1,8 s, clonado y `push --dry-run`
correctos. El JSONL sale **byte a byte idéntico** si la BD no ha cambiado (sha256 `5ec17aaa…`), así que repetir
`make package` no es peligroso.

## 4. Registrar
Anota en `docs/entregas.log` (en este repo): fecha, commit del repo de entrega, nº de líneas de cada JSONL, versión de norma/ERP usada. Avisa en el canal con el commit.

## Antes del domingo 08:00 comprueba además
- `outcomes_lote2.jsonl` existe aunque el lote 2 no haya ido bien: 40 líneas, una por fichero. Un ESCALAR honesto vale; una línea ausente = NO APTO.
- El PDF abre y tiene las dos secciones (Arquitectura, ADRs).
- El repo es público: `gh repo view javiersaguar/HS-Maisa-Entrega --json visibility`.
- La organización clona y registra el commit a las **11:00** (cierre interno 10:30): nada de pushes después.
