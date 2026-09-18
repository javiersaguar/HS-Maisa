---
description: Ejecuta make check y arregla sólo lo que sea de mi módulo.
allowed-tools: Bash(make *) Bash(uv run *)
---
Ejecuta `make check`. Si hay errores de lint o tests:
- si el fichero está en mi módulo (mira mi rama `<nombre>/...` y el dueño en CLAUDE.md), arréglalo y repite;
- si está en otro módulo, no lo toques: lista fichero, línea y error, y sugiere a quién avisar.
Termina diciendo si está verde y cuántos tests corrieron/saltaron (los `erp` se saltan si el ERP no está arriba).
