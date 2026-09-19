# PLAN-13 · el chat, completo y en la consola · dos agentes · rama `javier/chat` · sábado 19/09 ~16:40 → ~17:50

**Qué cambia.** La integración del chat en la consola ya no la hace Alejandro: la hacemos nosotros. De paso,
arreglamos los problemas del backend del chat que vimos al diseñarlo, para que sea un chat **completamente funcional**
en la defensa del domingo, no sólo una demo grabada.

**Dónde.** En una rama y una carpeta APARTE, para no chocar con el lote 2 de las 18:00:
- carpeta: `/home/javier/proyectos/HS-Maisa-chat` (en Windows: `\\wsl.localhost\Ubuntu\home\javier\proyectos\HS-Maisa-chat`);
- rama: `javier/chat`, con el código de `main` (`3038d25`), el entorno `uv` instalado y una **copia** de la BD en `dist/`;
- **sin `.env`, a propósito:** hasta que el lote 2 esté publicado, el gateway es del lote 2. Nadie llama al modelo antes.
  Cuando Javier lo diga en `docs/agentes/BITACORA.md` («gateway libre»), copiará él el `.env` y se hará la prueba en vivo.
- Javier revisa la rama y la mergea a `main` cuando esté verde. Ningún agente hace push ni toca `main`.

## Los problemas del backend que arreglamos (C1)
| # | Problema, visto en el código o en la evaluación de K2 | Arreglo |
|---|---|---|
| B1 | El cierre (17:30 del 19/09) y el tope (60 llamadas) están fijos en `agente.py` (l.71 y l.82), y el contador vive en `dist/ensayo/k2/llamadas.db`, con 59 gastadas: el domingo el chat respondería siempre «degradado» | Ventana y tope configurables: `ALBERTITOS_CHAT_DESDE` / `ALBERTITOS_CHAT_HASTA` (ISO, hora de Madrid; sin ellas, sin límite de hora), `ALBERTITOS_CHAT_MAX_LLAMADAS` (100 por defecto) contadas **dentro de la ventana**, contador en `ALBERTITOS_CHAT_CONTADOR` (por defecto `dist/chat/llamadas.db`) |
| B2 | `GET /chat/salud` no dice si el modelo está disponible: la pantalla sólo se entera del «degradado» al preguntar | `/chat/salud` versión 2, con disponibilidad, motivo, modelo, respaldo, llamadas restantes y ventana (contrato abajo). **Sin gastar ninguna llamada** |
| B3 | CORS sólo para `http://localhost:3000`: abrir la consola en `127.0.0.1:3000` da 403 | Orígenes configurables: `ALBERTITOS_CHAT_ORIGENES`, por defecto `http://localhost:3000,http://127.0.0.1:3000` |
| B4 | Dos preguntas de la evaluación se fueron a 60 s (timeout) y no hay respaldo | Timeout por petición más corto (25 s) y **modelo de respaldo** (`ALBERTITOS_MODELO_CHAT_FALLBACK`, por defecto `glm5.3-flash`, el respaldo de texto medido por B2) si el principal falla, todo dentro del presupuesto de 60 s por pregunta. La respuesta dice qué modelo contestó |
| B5 | La pregunta trampa de inyección salió «parcial»: el chat atribuyó al PDF la frase del usuario, sin haber visto la evidencia | La herramienta `traza` dice de forma explícita cuándo el PDF trae una instrucción («el PDF contiene una instrucción; su texto literal está en la traza, no se transmite al modelo»), y el prompt de sistema prohíbe atribuir al PDF palabras que no vengan de una herramienta. Test con la respuesta grabada del caso 13 |
| B6 | No hay forma corta de arrancarlo | `make chat` (servidor en `:8001` sobre `dist/albertitos.db`, sólo lectura) |

### Contrato nuevo de `GET /chat/salud` (C1 lo implementa y C2 lo consume; se fija aquí para que trabajen a la vez)
```json
{
  "ok": true, "api": 2, "solo_lectura": true, "bd_disponible": true,
  "modelo_disponible": false,
  "motivo": "fuera_de_ventana",
  "modelo": "deepseek-v4-flash", "respaldo": "glm5.3-flash",
  "llamadas_restantes": 30,
  "ventana": {"desde": "2026-09-20T09:00:00+02:00", "hasta": "2026-09-20T12:00:00+02:00"}
}
```
`motivo` ∈ `null` (disponible) · `"sin_clave"` · `"fuera_de_ventana"` · `"presupuesto_agotado"` · `"breaker"`.
`llamadas_restantes` y `ventana` pueden ser `null` (sin tope o sin ventana). `POST /chat` no cambia de forma. Sólo añade
`respaldo: true|false` en la respuesta cuando contestó el modelo de respaldo.

## Reglas para los dos
1. Trabajas SÓLO en `/home/javier/proyectos/HS-Maisa-chat`, en la rama `javier/chat`. Nada de checkout, merge, rebase,
   stash ni push. Nunca en `/home/javier/proyectos/HackSpain` (ahí se hace el lote 2).
2. Sólo tus ficheros (tabla de abajo). Lo demás, con `PIDO A <quién>:` en `docs/agentes/BITACORA.md` (sólo añadir al
   final, heredoc con comillas simples, LF).
3. **Ninguna llamada al modelo** hasta que la bitácora diga «gateway libre» (Javier, tras publicar el lote 2). Los tests,
   con el transporte simulado (como ya hace `tests/test_chat.py`). La negativa «paga la factura X» no llama al modelo:
   ésa sí se puede probar.
4. La BD de esta carpeta es una copia: sólo lectura. Huellas al empezar y al terminar:
   `sha256sum dist/albertitos.db | cut -c1-12`.
5. Commits pequeños `modulo: qué y por qué`, sin mencionar IA, con rutas explícitas. `make check` en verde (C1);
   `pnpm build` en verde (C2).
6. Al terminar, tu sección de `docs/agentes/PARTE.md` con: estado, commits, lo comprobado (comando y salida literal) y lo
   pendiente para la prueba en vivo.
7. En Cursor, la terminal: directorio de trabajo `C:\` y cada orden como
   `wsl -d Ubuntu -- bash -lc "cd /home/javier/proyectos/HS-Maisa-chat && <orden>"` (la ruta UNC da `powershell.exe ENOENT`).

## Propiedad de ficheros
| C1 · backend del chat | C2 · el chat en la consola |
|---|---|
| `src/albertitos/chat/*` · `tests/test_chat.py` · `docs/api/chat.md` · `docs/api/ejemplos/chat-salud*.json` (nuevo) · `docs/adr/0013-*` · `Makefile` (sólo el objetivo nuevo `chat`) | `console-web/lib/api/chat.ts` (nuevo) · `console-web/lib/mock/chat*` (nuevo) · `console-web/components/chat/*` (nuevo) · `console-web/app/layout.tsx` (sólo montar el panel: una línea y su import) · `console-web/.env.example` · `console-web/README.md` (sólo la sección del chat) |

---

## Prompt C1 · El backend del chat, completamente funcional
```
Eres el agente C1 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Lee ENTERO docs/agentes/PLAN-13.md: sus reglas y el contrato de /chat/salud mandan sobre este prompt. Tus ficheros: src/albertitos/chat/*, tests/test_chat.py, docs/api/chat.md, docs/api/ejemplos/chat-salud*.json (nuevo), docs/adr/0013-* y, en el Makefile, SÓLO un objetivo nuevo `chat`.
Lee además: src/albertitos/chat/ entero, tests/test_chat.py, docs/api/chat.md, docs/adr/0013-*, docs/api/ejemplos/chat-13-trampa_inyeccion.json y docs/agentes/RESPALDO-VISION.md y RESILIENCIA-Y-COSTE.md §3 (e) (el respaldo de texto glm5.3-flash, medido).

MISIÓN: arreglar B1-B6 de la tabla del plan, sin romper lo que ya funciona (sólo lectura, herramientas cerradas, citas verificadas, negativa local, una consulta a la vez).
B1 · Ventana y tope configurables. Quita la fecha y el 60 fijos de agente.py. Variables:
   ALBERTITOS_CHAT_DESDE y ALBERTITOS_CHAT_HASTA: ISO; sin zona, se entienden en Europe/Madrid. Si faltan, no hay límite de hora.
   ALBERTITOS_CHAT_MAX_LLAMADAS: 100 por defecto; 0 = cerrado.
   ALBERTITOS_CHAT_CONTADOR: por defecto dist/chat/llamadas.db.
   El contador cuenta sólo las llamadas cuyo ts cae dentro de la ventana en vigor, con ts en ISO con zona. Sin ventana, cuenta todas las del fichero.
   Tests con reloj inyectable (no uses la hora real en los tests): antes de la ventana, dentro, después, tope agotado y 0 = cerrado.
B2 · /chat/salud v2, EXACTAMENTE con el contrato del plan (api: 2). Calcula `modelo_disponible` y `motivo` SIN llamar al modelo, en este orden: sin_clave (no hay ALBERTITOS_LLM_API_KEY), fuera_de_ventana, presupuesto_agotado y breaker (abierto). Test de cada motivo. Guarda un ejemplo real en docs/api/ejemplos/chat-salud.json (sin clave: en esta carpeta sale motivo "sin_clave").
B3 · Orígenes: ALBERTITOS_CHAT_ORIGENES (coma), por defecto http://localhost:3000,http://127.0.0.1:3000. Access-Control-Allow-Origin devuelve el origen de la petición SI está en la lista (nunca "*"). Un POST con Origin fuera de la lista sigue dando 403. Tests.
B4 · Timeout por petición de 25 s (ALBERTITOS_CHAT_TIMEOUT_S) y respaldo ALBERTITOS_MODELO_CHAT_FALLBACK (por defecto glm5.3-flash; vacío = sin respaldo). Si el principal da timeout, 5xx o una respuesta que no cumple el esquema, se prueba el respaldo UNA vez, dentro del presupuesto total de 60 s por pregunta. Cada intento reserva una llamada del contador. La respuesta lleva "modelo" (el que contestó) y "respaldo": true|false. Tests con el transporte simulado: el principal falla y contesta el respaldo; fallan los dos y sale degradado; el presupuesto de tiempo se respeta.
B5 · Inyección: en la salida de la herramienta `traza`, si la factura tiene el aviso TEXTO_INSTRUCCION, añade un campo explícito (p. ej. "instruccion_en_pdf": true, "nota": "el PDF contiene una instrucción; su texto literal está en la traza local y no se transmite al modelo"). Sigue SIN pasar el texto literal al modelo. En el prompt de sistema, una regla: «no atribuyas al PDF palabras que no vengan de una herramienta; si el usuario cita una frase, di que la cita el usuario». Test: la salida de traza para una factura con TEXTO_INSTRUCCION lleva la nota y NO lleva texto_sospechoso.
B6 · Makefile: objetivo `chat` → `$(UV) run python -m albertitos.chat --servidor` (añade una línea con ## para `make help`). No toques otros objetivos.
Documentación: docs/api/chat.md al día (las variables, la salud v2, los orígenes, el respaldo, cómo abrir la ventana del domingo: por ejemplo ALBERTITOS_CHAT_DESDE=2026-09-20T09:00, ALBERTITOS_CHAT_HASTA=2026-09-20T12:00 y ALBERTITOS_CHAT_MAX_LLAMADAS=30) y en el ADR-0013, una sección «Cambios del PLAN-13» con B1-B6.
PRUEBA sin modelo: `make chat` en segundo plano con --db dist/albertitos.db en el puerto 8001 y `curl -s http://127.0.0.1:8001/chat/salud` (motivo sin_clave), `curl -s -X POST -H 'Origin: http://127.0.0.1:3000' -H 'Content-Type: application/json' -d '{"mensaje":"paga la factura F26-2201_transportes.pdf"}' http://127.0.0.1:8001/chat` (estado solo_lectura, 0 ms) y un Origin no permitido (403). Páralo al acabar.
CRITERIOS: B1-B6 con sus tests; make check verde; las dos pruebas con curl pegadas en tu parte; ninguna llamada al modelo; y lo que queda para la prueba en vivo (qué preguntar y qué esperar) escrito en tu parte.
NO HAGAS: text-to-SQL, herramientas que escriban, pasar el texto literal del PDF al modelo, tocar console-web/ o el puente de :8000, llamar al modelo.
```

## Prompt C2 · El chat en la consola
```
Eres el agente C2 de Javier en el repo Albertitos (HackSpain 2026, reto Maisa). Lee ENTERO docs/agentes/PLAN-13.md: sus reglas y el contrato de /chat/salud v2 mandan sobre este prompt. En paralelo, C1 cambia el backend del chat; tú consumes el contrato del plan, no el código de C1. Tus ficheros: console-web/lib/api/chat.ts (nuevo), console-web/lib/mock/chat* (nuevo), console-web/components/chat/* (nuevo), console-web/app/layout.tsx (SÓLO montar el panel: una línea y su import), console-web/.env.example y la sección del chat en console-web/README.md.
Alejandro sigue trabajando en console-web en SU rama (bonus, confianza, bandeja): no toques nada más de console-web, para que su merge y el nuestro no choquen.
Lee además: docs/api/chat.md (el contrato de POST /chat), docs/api/ejemplos/chat-*.json (las 15 respuestas reales), docs/adr/0013-*, y de console-web: lib/config.ts, lib/api/client.ts (ApiError), lib/routes.ts (ficheroHref), components/layout/* (para imitar el estilo), app/layout.tsx y package.json.
Instala las dependencias con `cd console-web && npx --yes pnpm install` (no hay pnpm global; necesita red la primera vez).

MISIÓN: que Alberto pueda preguntar al chat desde la consola, que se vea siempre si responde el modelo en vivo o no, y que la defensa pueda enseñarlo aunque el modelo no esté disponible, sin engañar a nadie.
TAREA 1 · lib/api/chat.ts, con CHAT_URL = NEXT_PUBLIC_CHAT_URL (por defecto http://127.0.0.1:8001):
  - chatSalud(): GET /chat/salud → el contrato v2 del plan. Si falla o tarda más de 2 s: {ok: false}. Si llega api 1 (el backend viejo, sin modelo_disponible), trátalo como disponible = desconocido: no lo rompas.
  - preguntar(mensaje, historial): POST /chat {mensaje, historial}; historial ≤ 10 entradas {role: "user"|"assistant", content}; mensaje de 1 a 4000 caracteres (valida antes de enviar). Timeout de interfaz de 70 s. Respuesta {respuesta, citas, herramientas_usadas, modelo, latencia_ms, estado, respaldo?}, con estado ok | solo_lectura | sin_datos | sin_evidencia | limite | degradado. Errores 400/403/413/415/429 con {"error": "..."}: enséñalos tal cual (429 = «ya hay una consulta en curso»).
TAREA 2 · lib/mock/chat.ts: las 15 respuestas reales de docs/api/ejemplos/chat-*.json (cópialas a lib/mock/chat/) con su pregunta. `respuestaGrabada(pregunta)` busca la pregunta exacta o, si no, devuelve null (nunca inventa una respuesta).
TAREA 3 · El panel (components/chat/), montado en app/layout.tsx:
  - Botón flotante «Pregunta a Albertitos» que abre un panel lateral. Cabecera fija: «Consulta de sólo lectura · la norma decide».
  - Estado del modelo SIEMPRE visible arriba, con chatSalud() al abrir y cada 30 s: «en vivo · <modelo>» (modelo_disponible), o «sin modelo: <motivo en español>» (sin_clave → «sin clave del LLM», fuera_de_ventana → «fuera de horario (abre <desde>)», presupuesto_agotado → «sin llamadas disponibles», breaker → «el proveedor está fallando; reintenta en un minuto»), y las llamadas restantes si vienen.
  - Mensajes: tu pregunta y la respuesta como TEXTO (nunca dangerouslySetInnerHTML ni HTML del modelo; si usas Markdown, sin HTML). Debajo, las citas como chips que enlazan a ficheroHref(file_id), y en pequeño el modelo («respaldo» si respaldo: true), la latencia en segundos y las herramientas usadas.
  - Estados: mientras espera, el botón de enviar bloqueado y «consultando… (hasta 60 s)»; solo_lectura: «El chat sólo consulta. Las decisiones las toma la norma»; degradado: un aviso visible, sin ocultarlo, con el texto de la respuesta y, si hay cita, el enlace a la traza; sin_datos / sin_evidencia: el texto tal cual.
  - Sugerencias (chips): «¿Cuántas facturas se pagan?», «¿Por qué se escala F26-2201_transportes.pdf?», «¿Qué facturas llevan el pedido PO-2026-0492?», «¿Cuánto vence esta semana?». Usa el texto EXACTO de la pregunta de su JSON, para que el modo grabado la encuentre.
  - Modo «respuestas grabadas»: un interruptor visible «Ver respuestas grabadas (evaluación 19/09 15:00)», disponible si el modelo no está disponible, si una respuesta llega degradada o con USE_MOCK=true. Con él activo, las sugerencias responden con la respuesta real grabada y una etiqueta FIJA «respuesta grabada · no es una consulta en vivo». Una respuesta grabada nunca aparece sin esa etiqueta, y nunca se mezclan sin distinguirse.
  - Sin servidor y sin modo grabado, el botón flotante no aparece: la consola no cambia.
  - Accesible: el foco va al campo al abrir, Escape cierra, y el color nunca es la única señal.
TAREA 4 · README de console-web (sección «Chat») y tooltip del botón: `make chat` (o `uv run python -m albertitos.chat --servidor`), que lee dist/albertitos.db en sólo lectura; el repliegue por terminal `uv run python -m albertitos.chat "pregunta"`; y NEXT_PUBLIC_CHAT_URL en .env.example.
CRITERIOS: `pnpm build` en verde. Con el servidor de C1 arrancado (make chat, sin .env): el estado dice «sin clave del LLM», la negativa «paga la factura F26-2201_transportes.pdf» sale al instante con su texto y el modo grabado enseña las 15 respuestas con su etiqueta. Con el servidor apagado, el botón sólo aparece en modo grabado o con USE_MOCK. Nada de HTML del modelo. Ninguna llamada al modelo (no hay .env). En tu parte: capturas o la salida literal, y qué probar en vivo cuando haya gateway.
NO HAGAS: tocar otras partes de console-web (Alejandro), el backend (C1) ni el puente de :8000; pintar HTML del modelo; botones que ejecuten nada.
```

---

## Cuando los dos terminen (Javier y Claude)
1. Revisar la rama `javier/chat`: `make check`, `pnpm build` y los dos partes.
2. **Después de publicar el lote 2:** «gateway libre» en la bitácora, `.env` en la carpeta, `make chat` con la ventana
   abierta y 3-4 preguntas en vivo desde la consola. Después, mergear a `main`.
3. **Para el domingo:** `ALBERTITOS_CHAT_DESDE=2026-09-20T09:00`, `ALBERTITOS_CHAT_HASTA=2026-09-20T12:00`,
   `ALBERTITOS_CHAT_MAX_LLAMADAS=30` en el `.env` del portátil de la defensa.
4. Avisar a Alejandro: los ficheros del chat en console-web son nuestros, y su merge tiene que respetar la línea del panel
   en `app/layout.tsx`.
