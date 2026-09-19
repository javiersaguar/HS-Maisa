# Prompt para el agente de Alejandro · el bonus en la consola (19/09, ~15:10)

Cópialo entero en tu agente (Cursor), desde tu rama de la consola, después de `git fetch && git merge origin/main`
(`main` = `9dcc5e8` o posterior, que ya trae `albertitos.bonus.rutas()`).

```
Eres el agente de Alejandro en el repo Albertitos (HackSpain 2026, reto Maisa). Alejandro es el dueño de la consola: src/albertitos/console/ (puente HTTP de sólo lectura, sólo GET) y console-web/ (Next 16, React 19, Tailwind 4, recharts). Trabajas en SU rama; antes de nada: `git fetch && git merge origin/main` (nunca rebase) y `make check` en verde.

CONTEXTO: el bonus (+10 pts, tercer desempate) son tres piezas del backend que la consola tiene que enseñar. Ninguna cambia una decisión ni la entrega: son lecturas. La primera YA está en main; las otras dos las están terminando K2 y K3 y sus contratos llegan a docs/api/ hacia las 16:30.
  1. Calendario de pagos y tesorería: HECHO. Contrato: docs/api/bonus.md. Ejemplos reales: docs/api/ejemplos/bonus-*.json.
  2. Métrica de confianza por factura (K3): EN CURSO. Contrato futuro: docs/api/confianza.md. Rutas GET /confianza/{resumen,ficheros,fichero}.
  3. Chat de sólo lectura con Alberto (K2): EN CURSO. Contrato futuro: docs/api/chat.md. Proceso aparte en :8001, POST /chat.

Lee antes: CLAUDE.md, src/albertitos/console/CLAUDE.md, docs/api/bonus.md (entero), docs/api/ejemplos/bonus-*.json, docs/BONUS.md y, de console-web: lib/config.ts, lib/api/client.ts, lib/api/ficheros.ts (el patrón: USE_MOCK → lib/mock/store, si no apiFetch + mappers), lib/types.ts, lib/format.ts, lib/routes.ts (ficheroHref) y components/layout/Sidebar.tsx.

REGLAS:
- Sólo tocas src/albertitos/console/*, tests/test_console.py, console-web/* y tu ADR. NADA de core/, pipeline/, extract/, rules/, bonus/, cli.py.
- El puente sigue siendo sólo GET y de sólo lectura. No añadas POST: el chat vive en su propio proceso (:8001).
- Importes: la API los da como STRING con 2 decimales ("2428159.06"). Para mostrar, formatea en EUR con 2 decimales (formatEur usa 4 por defecto: pásale 2). Para gráficos puedes convertir a number; para SUMAR, nunca con floats: usa los totales que ya da la API.
- Todo tiene que funcionar con USE_MOCK=true, sin red (la demo puede ser sin wifi): mocks a partir de los ejemplos reales de docs/api/ejemplos/.
- Commits pequeños `console: qué y por qué`, sin mencionar IA. `make check` y `pnpm build` en verde antes de pedir merge.

TAREA 1 · Registrar las rutas del bonus (y dejar preparada la de confianza). En src/albertitos/console/api.py, después de definir RUTAS:
    try:
        from albertitos import bonus
        RUTAS.update(bonus.rutas())
    except ImportError:
        logger.warning("sin rutas del bonus")
    try:
        from albertitos import confianza  # K3: llega hacia las 16:30
        RUTAS.update(confianza.rutas())
    except ImportError:
        pass
Test en tests/test_console.py: con la BD de prueba, GET /bonus/resumen da 200 y POST /bonus/resumen da 405. Arranca el puente contra la BD real y comprueba a mano: `curl -s localhost:8000/bonus/resumen` → calendario_total_eur "2428159.06".

TAREA 2 · lib/api/bonus.ts + tipos + mappers + mock, siguiendo el patrón de ficheros.ts. Funciones: fetchBonusResumen(estricto?), fetchCalendario({semana, proveedor, lote, vencido, limite, conConfianza}), fetchProveedores(), fetchRemesa(limite?), fetchAvisos(), fetchTesoreria(tope?). Tipos con los nombres de campo EXACTOS de docs/api/bonus.md (Pago, Tesoreria, Programa, ProveedorPago, AvisoBonus). Mock: copia los JSON de docs/api/ejemplos/bonus-*.json a lib/mock/ y sírvelos (el filtro del calendario en mock puede ser en memoria). Errores 400/409: su "error" es un mensaje para una persona; enséñalo tal cual.

TAREA 3 · La página /pagos (app/pagos/page.tsx), con una entrada «Pagos» en la barra lateral (icono CalendarDays de lucide-react), en este orden:
  a. Cabecera con /bonus/resumen: «438 facturas a pagar · 2.428.159,06 € · 2.383.400,88 € vencidos · 2 vencen esta semana». Y un AVISO SIEMPRE VISIBLE, no plegable, que no se puede quitar: «Borrador: los IBAN de esta Caja son sintéticos y un banco los rechazaría. No se ha ejecutado ningún pago.» (Es lo único obligatorio de la pantalla: sin él, la demo promete algo falso.)
  b. Calendario semanal con /bonus/tesoreria: barras por semana (importe), la parte vencida en otro color (rojo) y una línea con el acumulado (recharts ComposedChart). Un campo «Tope semanal (€)» que repite la petición con ?tope= y pinta el programa: «Con 150.000 € por semana, al día en 16 semanas; todo pagado en 17», y las barras del programa (supera_tope marcado).
  c. Tabla por proveedor con /bonus/proveedores (de mayor a menor importe, con las vencidas). Pulsar una fila filtra la lista de pagos por ese proveedor.
  d. Lista de pagos con /bonus/calendario: filtros de semana, lote y vencido; paginada en cliente; cada file_id enlaza a su detalle con ficheroHref(file_id). Columna «IBAN» con un distintivo «sin control» cuando iban_control_ok es false.
  e. Avisos (/bonus/avisos), plegados, con código y detalle.
  Estados vacíos y de error como en el resto de la consola (ApiError: red, 503 sin BD, 409 sin decisiones).

TAREA 4 · Huecos para K3 y K2, SIN inventar campos: los contratos llegan a docs/api/confianza.md y docs/api/chat.md hacia las 16:30.
  - Confianza: un componente <ConfianzaBadge> y un hueco para la columna «Confianza» en la lista de ficheros y en el detalle, que se ACTIVA solo si GET /confianza/resumen responde 200 (detección al arrancar; si da 404, no se ve nada). En /pagos, cuando exista, pide /bonus/calendario?con_confianza=true: cada pago trae `confianza` con lo que devuelva K3, o null. Cuando llegue el contrato, usa sus nombres de campo tal cual.
  - Chat: un panel lateral plegable «Pregunta a Albertitos» (botón flotante), contra NEXT_PUBLIC_CHAT_URL (por defecto http://127.0.0.1:8001). Sólo se muestra si GET {CHAT_URL}/chat/salud responde. Cada respuesta enseña sus citas (file_id) como enlaces a ficheroHref. Hasta que llegue docs/api/chat.md, deja el cliente con la forma prevista: POST /chat {mensaje, historial?} → {respuesta, citas, herramientas_usadas, modelo, latencia_ms}, y ajústalo al contrato real después.

TAREA 5 · Tu ADR de la consola: docs/adr/0016-consola-next-sobre-puente-de-lectura.md (el 0013 es del chat, el 0014 de la confianza y el 0015 de Jev). Contexto (el stack decía Streamlit), alternativas (Streamlit, Next sobre el puente, Next con BD directa), decisión, consecuencias (Node y pnpm en el portátil de la demo; `pnpm install` hecho ANTES de ir a la sala) y evidencia. Y `make console` apuntando a lo que se enseña: puente + Next (el Makefile es de Javier, que te autoriza a tocar sólo el objetivo `console`).

CRITERIOS DE ACEPTACIÓN:
- Con la BD real y el puente: /pagos enseña 438 · 2.428.159,06 € · 2.383.400,88 € vencidos, con el aviso de los IBAN; con tope 150000, «al día en 16 semanas»; el filtro por proveedor y por lote funciona; cada factura abre su traza.
- Con USE_MOCK=true, sin red, todo lo anterior se ve con los ejemplos.
- Confianza y chat no se ven si su servicio no responde, y no rompen nada.
- `make check` y `pnpm build` en verde; test del registro de rutas.
- Tiempo: /pagos listo para el ensayo de la defensa. Si a las 17:15 no está, se queda en tu rama y se mergea después del lote 2 (18:00).
```
