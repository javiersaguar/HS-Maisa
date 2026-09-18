---
paths:
  - "docs/agentes/**"
---
# Trabajo con varios agentes en el mismo árbol

- `BITACORA.md` es append-only: añade al final, nunca edites ni reordenes entradas ajenas. Formato de la plantilla.
- `PARTE.md`: cada agente rellena SÓLO su sección; concreto (cifras, comandos con su salida literal, rutas).
- `plan.json` dice qué ficheros puede escribir cada agente en este ciclo. Si un fichero no está en tu lista, no lo edites: pide el cambio en la bitácora.
- Nadie cambia de rama, ni hace stash/merge/rebase/checkout, ni ejecuta `/handoff` o `/sync`: lo hace la persona al cerrar el ciclo.
- `git add` sólo con rutas explícitas de tu lista. Nunca `git add -A` ni `git add .`.
- Tests: los tuyos con `uv run pytest tests/test_X.py -q`. `make check` completo sólo al final; lo ajeno que falle se anota, no se arregla.
