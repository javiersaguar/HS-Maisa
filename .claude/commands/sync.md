---
description: Trae main a tu rama con merge (nunca rebase), resuelve conflictos y deja make check en verde.
allowed-tools: Bash(git *) Bash(make *) Bash(uv run *)
---
Sincroniza mi rama con `main`:

1. `git fetch origin` y `git merge origin/main` (merge, no rebase: aquí no se reescribe historia).
2. Si hay conflictos: resuélvelos tú si están en mi módulo (mira el `CLAUDE.md` de la carpeta). Si tocan `src/albertitos/core/`, NO los resuelvas a tu criterio: muéstrame el conflicto y párate, decide Miguel.
3. `uv sync` si cambió `uv.lock`. `make db` si cambió `schema.sql`.
4. `make check`. Si falla algo que no es mío, dímelo con el fichero y la línea, no lo arregles en el módulo de otro.
5. Resume en 3 líneas qué entró de main que me afecta.
