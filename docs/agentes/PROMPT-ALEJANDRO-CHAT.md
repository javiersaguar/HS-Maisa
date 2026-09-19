# Prompt para el agente de Alejandro · el chat en la consola (19/09, ~15:30)

Después de `git fetch && git merge origin/main` (trae `albertitos.chat`, de K2). Se puede lanzar a la vez que el de la
confianza (`PROMPT-ALEJANDRO-CONFIANZA.md`): no comparten ficheros.

```
Eres el agente de Alejandro en el repo Albertitos (HackSpain 2026, reto Maisa). Alejandro es el dueño de console-web/ (Next 16, React 19, Tailwind 4). Trabajas en SU rama: antes de nada, `git fetch && git merge origin/main` (nunca rebase). En paralelo puede haber otro agente con la confianza: NO toques sus ficheros (lib/api/confianza.ts, lib/types-confianza.ts, components/confianza/*, ni las páginas de invoices, dashboard o pagos).

CONTEXTO: K2 ha hecho un chat para que Alberto pregunte en lenguaje natural por las decisiones («¿por qué se escala F26-2201_transportes.pdf?», «¿cuánto vence esta semana?»). Es un PROCESO APARTE del puente, en http://127.0.0.1:8001, y sólo consulta: herramientas cerradas de lectura, sin SQL generado y sin escritura. Si le piden «paga esta factura», responde que sólo lee. Cada respuesta cita las facturas en que se apoya. Evaluación: 14 de 15 correctas y 1 parcial, con una mediana de 5 s (docs/api/chat.md).
LIMITACIÓN QUE CONDICIONA LA PANTALLA: para no quitarle el gateway al lote 2 de las 18:00, el chat tiene un tope de 60 llamadas (van 59) y se cierra a las 17:30. A partir de ahí responde en estado `degradado`. Así que la pantalla tiene que ENSEÑAR BIEN ESE ESTADO y tener un modo «respuestas grabadas» con las 15 respuestas reales de la evaluación, marcado como tal, para poder enseñar el chat en la defensa aunque el modelo no esté disponible. (El equipo decidirá después del lote 2 si se reabre para el domingo.)

Lee antes: docs/api/chat.md (ENTERO: el contrato manda), docs/api/ejemplos/chat-*.json (las 15 preguntas reales con sus respuestas), docs/adr/0013-*, y de console-web: lib/config.ts, lib/api/client.ts (ApiError), lib/routes.ts (ficheroHref), components/layout/*.

REGLAS:
- Tus ficheros: console-web/lib/api/chat.ts (nuevo), console-web/lib/mock/chat* (nuevo), console-web/components/chat/* (nuevo), console-web/app/layout.tsx (sólo para montar el panel) y console-web/.env.example si existe. Nada del backend: el chat NO se registra en el puente de :8000 (necesita POST y va en su propio proceso).
- NUNCA pintes HTML que venga del modelo: `respuesta` se enseña como texto (o Markdown seguro sin HTML). Ni un botón que «ejecute» algo que diga el modelo.
- Commits `console: qué y por qué`, sin mencionar IA. `pnpm build` en verde.

TAREA 1 · lib/api/chat.ts, con la URL de NEXT_PUBLIC_CHAT_URL (por defecto http://127.0.0.1:8001):
  - chatSalud(): GET /chat/salud → {ok, solo_lectura, bd_disponible}. Si falla o tarda más de 2 s: no disponible.
  - preguntar(mensaje, historial): POST /chat, Content-Type application/json, {mensaje, historial} con historial ≤ 10 entradas {role: "user"|"assistant", content} (nada de system ni tool), mensaje de 1 a 4000 caracteres. Timeout de interfaz de 70 s (el servidor corta en 60). Respuesta: {respuesta, citas, herramientas_usadas, modelo, latencia_ms, estado}, con estado ok | solo_lectura | sin_datos | sin_evidencia | limite | degradado. Errores: 400, 403, 413, 415 y 429 («ya hay una consulta en curso»), con formato {"error": "..."}: enséñalos tal cual.
  - CORS: el servidor sólo admite el origen EXACTO http://localhost:3000. La consola se abre en http://localhost:3000, no en 127.0.0.1:3000 (si no, 403). Dilo en el README de console-web.
  - Modo grabado: lib/mock/chat.ts carga las 15 respuestas de docs/api/ejemplos/chat-*.json (cópialas a lib/mock/) para usar con USE_MOCK=true o cuando el servidor no responde o responde `degradado`.

TAREA 2 · El panel (components/chat/): un botón flotante «Pregunta a Albertitos» que abre un panel lateral.
  - Cabecera fija: «Consulta de sólo lectura · la norma decide».
  - Mensajes: tu pregunta y la respuesta. Debajo de cada respuesta, las `citas` como chips que enlazan a ficheroHref(file_id), y en pequeño el modelo, la latencia (s) y las herramientas usadas.
  - Estados: mientras espera, el botón de enviar bloqueado y «consultando… (hasta 60 s)»; `solo_lectura`: «El chat sólo consulta. Las decisiones las toma la norma» (sin llamar al modelo, 0 ms); `degradado`: un aviso visible, sin ocultarlo, con la sugerencia de la respuesta («usa albertitos trace <file_id>») y el enlace a la traza si hay cita; `sin_datos` / `sin_evidencia`: el texto tal cual; 429: «ya hay una consulta en curso».
  - Sugerencias (chips) con 4 preguntas de la evaluación: «¿Cuántas facturas se pagan?», «¿Por qué se escala F26-2201_transportes.pdf?», «¿Qué facturas llevan el pedido PO-2026-0492?», «¿Cuánto vence esta semana?».
  - Modo «respuestas grabadas»: si chatSalud() falla o una respuesta llega `degradado`, un interruptor visible «Ver respuestas grabadas (evaluación 19/09 15:00)». Con él activo, las sugerencias devuelven la respuesta real grabada de su JSON, con una etiqueta fija «respuesta grabada · no es una consulta en vivo». Nunca se mezcla una respuesta grabada con una en vivo sin esa etiqueta.
  - Sin el servidor y sin modo grabado, el botón flotante no aparece: la consola no cambia.

TAREA 3 · Cómo se arranca, en el README de console-web y en el panel (tooltip del botón): `uv run python -m albertitos.chat --servidor` (lee dist/albertitos.db en sólo lectura), y el repliegue por terminal `uv run python -m albertitos.chat "pregunta"`.

CRITERIOS DE ACEPTACIÓN:
- Con el servidor vivo (antes de las 17:30, y sin gastar llamadas: prueba primero «paga la factura X», que se responde en local sin modelo): el panel abre, la negativa de sólo lectura sale al instante y las citas enlazan a la traza.
- Con el servidor apagado o degradado: el aviso se ve y el modo grabado enseña las 15 respuestas reales con su etiqueta.
- Con USE_MOCK=true, sin red, el modo grabado funciona.
- No se renderiza HTML del modelo; `pnpm build` en verde.
- OJO CON EL TOPE: quedan como mucho 1-2 llamadas al modelo hasta las 17:30. Para probar la integración, usa las respuestas grabadas y la pregunta de pagar (no gasta). No hagas pruebas en bucle contra :8001.
```
