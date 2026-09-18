---
description: Cierra el trabajo de la sesión — make check, commit pequeño, push de la rama y PR con resumen para Miguel.
allowed-tools: Bash(git *) Bash(make *) Bash(gh *) Bash(uv run *)
---
Prepara la entrega de mi trabajo para el merge:

1. `make check` en verde. Si falla, arréglalo antes; no se pide merge en rojo.
2. `git status`: revisa que no haya ficheros ajenos a mi módulo, ni `.env`, ni nada de `dist/`. Si toqué `core/` sin ser Miguel, avísame y no sigas.
3. Commit(s) pequeños con mensaje `modulo: qué y por qué` (ej. `sources: cliente ERP renueva token a los 250 usos`).
4. Sube la rama con `git push -u origin <mi-rama>`. Si no hay PR, créala contra la rama principal con `gh pr create --fill`; si ya existe, dame sólo la URL.
5. Escribe un resumen de 5 líneas para Miguel: qué cambia, qué contrato consume, qué test lo cubre, qué queda pendiente, qué necesita de otro módulo. Ese resumen va al cuerpo de la PR y al canal.
6. Termina con: "Lanza el subagente revisor-diff si quieres una revisión antes del merge".
