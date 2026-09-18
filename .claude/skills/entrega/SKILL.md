---
name: entrega
description: Runbook de entrega al repo público la-caja-outcomes (outcomes.jsonl, outcomes_lote2.jsonl, albertitos_plan.pdf). Úsalo para la entrega de seguro del sábado 17:30 y la final del domingo 08:00.
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

## 3. Publicar en el repo separado
```
ENTREGA=$(grep ^ENTREGA_REPO .env | cut -d= -f2)
gh repo view "$ENTREGA" >/dev/null 2>&1 || gh repo create "$ENTREGA" --public --description "HackSpain 2026 · entrega Albertitos"
test -d ../la-caja-outcomes || gh repo clone "$ENTREGA" ../la-caja-outcomes
cd ../la-caja-outcomes && (git pull --ff-only || true)
cp "$OLDPWD/dist/entrega/outcomes.jsonl" "$OLDPWD/dist/entrega/albertitos_plan.pdf" .
cp "$OLDPWD/dist/entrega/outcomes_lote2.jsonl" . 2>/dev/null || true
ls -A          # DEBE listar sólo: .git outcomes.jsonl outcomes_lote2.jsonl albertitos_plan.pdf
```
Si `ls -A` muestra cualquier otra cosa (README, .gitignore, código), bórrala antes de commitear.
```
git add -A && git commit -m "entrega $(date +%FT%H:%M)" && git push
git rev-parse HEAD
```

## 4. Registrar
Anota en `docs/entregas.log` (en este repo): fecha, commit del repo de entrega, nº de líneas de cada JSONL, versión de norma/ERP usada. Avisa en el canal con el commit.

## Antes del domingo 08:00 comprueba además
- `outcomes_lote2.jsonl` existe aunque el lote 2 no haya ido bien: 40 líneas, una por fichero. Un ESCALAR honesto vale; una línea ausente = NO APTO.
- El PDF abre y tiene las dos secciones (Arquitectura, ADRs).
- El repo es público: `gh repo view "$ENTREGA" --json visibility`.
