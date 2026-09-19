# ADR-0016 · La consola es Next sobre un puente HTTP de sólo lectura, no Streamlit

- **Estado:** aceptado (implementado en las PR #5 y #7)
- **Fecha:** 2026-09-19 · **Dueño:** Alejandro · **Módulos:** console/, console-web/

## Contexto
El stack del repo decía Streamlit (`console/app.py`, reglas de `.claude/rules/consola.md`). La consola tiene que enseñar
en 10 minutos de defensa la traza de una decisión (20 pts), subir facturas y ver por qué decide la norma, y desde el
sábado las tres piezas del bonus: calendario de pagos (K1), confianza por factura (K3) y chat (K2). Con Streamlit,
cada interacción vuelve a ejecutar el script entero, no hay rutas enlazables por `file_id` y lo interactivo (pinchar un
día del calendario y ver sus facturas, elegir una factura de la bandeja y ver su análisis al lado) se pelea con el
modelo de recarga. Además la demo corre sin red en el portátil de Alfonso: nada de CDN.

## Alternativas consideradas
1. **Streamlit sobre la SQLite**: no añade piezas y ya existía. Se descarta porque no hay URL por factura (la traza no
   se puede enlazar desde el chat ni desde el calendario), cada filtro recarga la página entera y hay poco control del
   layout para el aviso de borrador del calendario, que tiene que estar siempre a la vista.
2. **Next con acceso directo a la BD** (rutas API de Node con un driver SQLite): una sola pieza. Se descarta porque
   duplica en TypeScript las lecturas que ya están en Python (`lecturas.py`, `bonus.rutas()`, `confianza.rutas()`) y
   abre una segunda vía a la BD de la entrega que ningún test de Python vigila.
3. **Next sobre un puente HTTP de sólo lectura (elegida)**: `console/api.py` (stdlib, sin dependencias nuevas) sirve
   GET en `:8000`. Los módulos del bonus traen sus propios handlers con la misma firma y se registran con
   `RUTAS.update(...)` en un import perezoso. Next (`console-web/`) sólo pinta.

## Decisión
La consola que se enseña es Next hablando con el puente. El puente abre la BD en `ro`, sólo acepta GET y no importa
`rules/` ni `extract/`. El único POST es `/inbox` de la bandeja, y sólo con `--bandeja`, sobre `dist/bandeja.db`. Lo
que aún no ha respondido no se enseña:
- la confianza, sólo si `/confianza/resumen` responde;
- el chat, en su propio proceso (`:8001`), sólo si `/chat/salud` responde, o con respuestas grabadas y etiquetadas
  como tales si se pide.

`make console` arranca puente + Next. `app.py` queda como andamiaje y no se mantiene.

## Consecuencias aceptadas
- Node y pnpm en el portátil de la demo, y `pnpm install` hecho **antes** de ir a la sala (sin wifi no hay install).
- Dos procesos que arrancar (tres con el chat). Si Next falla, el repliegue es `albertitos trace <file_id>` en terminal.
- Los importes llegan como string con 2 decimales y la consola no suma: si hace falta un total, lo da la API.
- El mock (`NEXT_PUBLIC_USE_MOCK=true`) permite trabajar sin puente: bonus y confianza con cifras del lote 1 y el chat
  sólo con respuestas grabadas. La bandeja no funciona en mock, porque subir facturas necesita el puente real.
- `/pagos` pide el calendario entero (`/bonus/calendario?limite=1000`, 192 KB) y agrupa por día en el cliente: bien en
  local, no en una red lenta.

## Evidencia
- `tests/test_console.py::test_rutas_del_bonus_y_confianza_registradas_y_solo_get`: `/bonus/resumen` 200,
  `/bonus/tesoreria?tope=-1` 400, `POST /bonus/resumen` 405, `/confianza/resumen` 200.
- Contra `dist/albertitos.db` (lote 1, corte 2026-09-18), 19/09 por la tarde: `/pagos` enseña septiembre con 438
  facturas a pagar · 2.428.159,06 €, y el día de corte 431 facturas · 2.383.400,88 € (las vencidas). Cada `file_id`
  abre `/invoices/detalle` con su decisión y su traza.
- Tiempos del puente (misma BD, portátil de desarrollo): `/bonus/resumen` 0,07 s · `/bonus/calendario?limite=1000`
  0,08 s · `/confianza/resumen` 0,09 s · `/confianza/ficheros?limite=1000` 0,10 s · `/ficheros` (25) 0,03 s.
- `tsc --noEmit` y `next build` en verde.

## Resumen para el plan (5 líneas)
La consola es Next sobre un puente HTTP de sólo lectura (stdlib, BD en `ro`, sólo GET salvo la bandeja).
Descartamos Streamlit (sin URL por factura, recarga completa) y Next con BD directa (duplica lecturas y abre otra vía).
Bonus, confianza y chat se enchufan por contrato: rutas GET registradas o un proceso aparte, y no se enseñan si no responden.
Coste: Node y pnpm en el portátil de la demo, `pnpm install` antes de la sala; repliegue `albertitos trace`.
Evidencia: test de rutas, `/pagos` con 438 facturas · 2.428.159,06 €, 0,03-0,10 s por lectura.
