# ADR-0016 · La consola es Next sobre un puente HTTP de sólo lectura, no Streamlit

- **Estado:** aceptado
- **Fecha:** 2026-09-19 · **Dueño:** Alejandro · **Módulos:** console/, console-web/

## Contexto
El stack del repo decía Streamlit (`console/app.py`, reglas de `.claude/rules/consola.md`). La consola tiene que enseñar
en 10 minutos de defensa la traza de una decisión (20 pts), el panel de operación y, desde el sábado, las tres piezas
del bonus: calendario de pagos (K1), confianza por factura (K3) y chat (K2). Con Streamlit, cada interacción vuelve a
ejecutar el script entero, no hay rutas enlazables por `file_id` y los gráficos interactivos (clic en una semana para
filtrar pagos, tope de tesorería) se pelean con el modelo de recarga. Además la demo corre sin red en el portátil de
Alfonso: nada de CDN.

## Alternativas consideradas
1. **Streamlit sobre la SQLite** — cero piezas nuevas y ya existía. Se descarta: sin URL por factura (la traza no se
   puede enlazar desde el chat ni desde el calendario), recarga completa en cada filtro y poco control del layout para
   el aviso de borrador, que tiene que estar siempre a la vista.
2. **Next con acceso directo a la BD** (rutas API de Node con un driver SQLite) — una sola pieza. Se descarta: duplica
   en TypeScript las lecturas que ya están en Python (`lecturas.py`, `bonus.rutas()`, `confianza.rutas()`) y abre una
   segunda vía a la BD de la entrega que ningún test de Python vigila.
3. **Next sobre un puente HTTP de sólo lectura (elegida)** — `console/api.py` (stdlib, sin dependencias nuevas) sirve
   GET en `:8000`; los módulos del bonus traen sus propios handlers con la misma firma y se registran con
   `RUTAS.update(...)` en un import perezoso. Next (`console-web/`) sólo pinta.

## Decisión
La consola que se enseña es Next hablando con el puente. El puente abre la BD en `ro`, sólo acepta GET (el único POST
es `/inbox` de la bandeja, y sólo con `--bandeja` sobre `dist/bandeja.db`) y no importa `rules/` ni `extract/`. El chat
vive en su propio proceso (`:8001`); la consola lo enseña sólo si `/chat/salud` responde. La confianza se enseña sólo si
`/confianza/resumen` responde. `make console` arranca puente + Next. `app.py` queda como andamiaje y no se mantiene.

## Consecuencias aceptadas
- Node y pnpm en el portátil de la demo, y `pnpm install` hecho **antes** de ir a la sala (sin wifi no hay install).
- Dos procesos que arrancar (tres con el chat). Si Next falla, el repliegue es `albertitos trace <file_id>` en terminal.
- Los importes llegan como string con 2 decimales y la consola no suma: si hace falta un total, lo da la API.
- El mock (`NEXT_PUBLIC_USE_MOCK=true`) permite trabajar sin puente, pero no finge K2 ni K3, y para el programa de
  tesorería sólo trae los topes de 100.000 a 300.000 € (no repite en el navegador el cálculo del backend).
- `/bonus/calendario?con_confianza=true` con los 438 pagos pesa 824 KB: aceptable en local, no en una red lenta.

## Evidencia
- `tests/test_console.py::test_rutas_del_bonus_y_confianza_registradas_y_solo_get`: `/bonus/resumen` 200,
  `/bonus/tesoreria?tope=-1` 400, `POST /bonus/resumen` 405, `/confianza/resumen` 200.
- Contra `dist/albertitos.db` (lote 1, corte 2026-09-18), 19/09 por la tarde: `/pagos` enseña 438 facturas ·
  2.428.159,06 € · 2.383.400,88 € vencidos; con tope 150.000 € «al día en 16 semanas; todo pagado en 17»; filtro P002
  → 45 pagos; cada `file_id` abre `/invoices/detalle` (detalle y traza 200).
- Tiempos del puente (misma BD, portátil de desarrollo): `/bonus/resumen` 0,28 s · `/bonus/tesoreria?tope=150000`
  0,28 s · `/bonus/calendario?limite=1000` 0,27 s · con confianza 0,42 s · `/confianza/ficheros?limite=1000` 0,29 s.
- `next build` y `tsc --noEmit` en verde; `ruff` y `pytest` en verde salvo un fallo intermitente ajeno
  (`test_chat.py::test_api_contrato_cors_y_sin_modelo`, WinError 10053, 1 de 3 repeticiones).

## Resumen para el plan (5 líneas)
La consola es Next sobre un puente HTTP de sólo lectura (stdlib, BD en `ro`, sólo GET).
Descartamos Streamlit (sin URL por factura, recarga completa) y Next con BD directa (duplica lecturas y abre otra vía).
Bonus, confianza y chat se enchufan por contrato: rutas GET registradas o un proceso aparte, y se ocultan si no responden.
Coste: Node y pnpm en el portátil de la demo, `pnpm install` antes de la sala; repliegue `albertitos trace`.
Evidencia: test de rutas, `/pagos` con 438 · 2.428.159,06 € y el programa a 16 semanas, 0,27-0,42 s por lectura.
