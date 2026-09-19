# Parte de fin de ciclo · ciclo 13 (el chat, completo y en la consola)

Cada agente rellena SU sección al terminar. Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (… · 10: J1-J5 · 11: K1-K3).

## C1 · El backend del chat, completamente funcional
- **Estado: terminado.**
  - Commits: `14b8402` (B1-B6) · `479b61a` (puerto configurable) · el de la documentación · `plan.json`.
  - Sin push y sin ninguna llamada al modelo.
  - BD de la carpeta: `8501d9975c38` al empezar y al terminar.
- **B1 · Ventana y tope configurables:**
  - `ALBERTITOS_CHAT_DESDE/HASTA` (hora de Madrid si no llevan zona);
  - `ALBERTITOS_CHAT_MAX_LLAMADAS` (100; 0 = cerrado), contadas **dentro de la ventana**;
  - `ALBERTITOS_CHAT_CONTADOR` (`dist/chat/llamadas.db`);
  - las 59 llamadas del sábado ya no cuentan (hay un test que lo comprueba).
- **B2 · `/chat/salud` v2:** exactamente con el contrato del plan (`api: 2`). No llama al modelo y no crea el contador. Hay un test por cada motivo, en orden: sin_clave, fuera_de_ventana, presupuesto_agotado, breaker. Ejemplos reales: `docs/api/ejemplos/chat-salud.json` y `chat-salud-domingo.json`.
- **B3 · Orígenes:** `localhost:3000` y `127.0.0.1:3000` por defecto (`ALBERTITOS_CHAT_ORIGENES`). Se devuelve el origen que pide, nunca `*`; un origen ajeno da 403.
- **B4 · Tiempos y respaldo:**
  - 25 s por petición (`ALBERTITOS_CHAT_TIMEOUT_S`);
  - respaldo `glm5.3-flash` ante timeout, 5xx o una final fuera de esquema, dentro de los 60 s por pregunta;
  - la respuesta lleva `modelo` y `respaldo: true|false`, y el mensaje degradado dice el motivo.
- **B5 · Instrucción en el PDF:** la traza marca `instruccion_en_pdf: true` con una nota y sin el texto literal. Comprobado con `F26-2201_transportes.pdf`: la nota está y «escalarse» no aparece. Además, una regla en el prompt de sistema.
- **B6 y extras:** `make chat`, `--salud` en la CLI y `ALBERTITOS_CHAT_PUERTO`.
  - **Hallazgo:** en este portátil el **8001 lo ocupa un contenedor Docker de otro proyecto** (responde `{"detail":"Not Found"}`).
  - Antes salía un traceback; ahora una línea dice qué hacer (`ALBERTITOS_CHAT_PUERTO=8101 make chat` y `NEXT_PUBLIC_CHAT_URL=http://127.0.0.1:8101`).
- **Tests:** `tests/test_chat.py` → **25 passed**, con reloj inyectable, transporte simulado y un servidor real para CORS y salud. `make check` → **594 passed, 2 skipped**.
- **Prueba con curl, sin modelo** (`ALBERTITOS_CHAT_PUERTO=8101`; salida literal en `dist/c1-curl.txt`):
```text
GET /chat/salud → {"ok": true, "api": 2, "solo_lectura": true, "bd_disponible": true, "modelo_disponible": false, "motivo": "sin_clave", "modelo": "deepseek-v4-flash", "respaldo": "glm5.3-flash", "llamadas_restantes": 100, "ventana": null}
POST «paga la factura F26-2201_transportes.pdf», Origin http://127.0.0.1:3000 → 200 · Access-Control-Allow-Origin: http://127.0.0.1:3000 · "estado": "solo_lectura" · "latencia_ms": 0
POST «¿Cuántas facturas se pagan?» → "estado": "degradado" · "El chat no tiene clave del modelo configurada; usa `albertitos trace <file_id>`." (no crea el contador)
POST con Origin https://ajeno.test → 403
```
- **Para la prueba en vivo, cuando haya «gateway libre»:**
  - `.env` en esta carpeta; `ALBERTITOS_CHAT_PUERTO=8101 make chat`; `--salud` → `motivo: null`.
  - Preguntar:
    1. «¿Cuántas facturas se pagan?» → 438, sin citas.
    2. «¿Por qué se escala F26-2201_transportes.pdf?» → ESCALAR por R6, **diciendo que el PDF trae una instrucción, sin citarla**, y la cita.
    3. El caso 13, la trampa de inyección: que ya no atribuya al PDF la frase del usuario.
    4. «¿Qué facturas llevan el pedido PO-2026-0492?» → las dos, citadas.
  - En cada una, mirar `modelo`, `respaldo` y la latencia.
  - Coste: unas 3 llamadas por pregunta, así que 4 preguntas son unas 12 del tope de 100.
- **Pendiente de otros:** `docs/agentes/añadir_facturas_panel_681fa84b.plan.md`, de Alejandro, tiene **12 enlaces relativos rotos**. Es el mismo error de rutas de antes (le faltan `../../`); no es fichero mío.

## C2 · El chat en la consola
- **Estado: hecho.** Commits: `3d3fa43` (cliente, respuestas grabadas, panel y montaje en `app/layout.tsx`) y el de cierre (README, formato de la hora de apertura, este parte). Sin push.
- **Qué hay:**
  - `lib/api/chat.ts`: `chatSalud()` (v2; un backend api 1 → «disponibilidad desconocida»; sin respuesta en 2 s → `{ok:false}`) y `preguntar()` (valida 1-4000 caracteres, historial ≤ 10, timeout de 70 s, errores 400/403/413/415/429 con el texto del servidor tal cual).
  - `lib/mock/chat.ts` + `lib/mock/chat/`: las 15 respuestas reales, recortadas (sin la evidencia de herramientas; texto intacto). `respuestaGrabada()` sólo encuentra la pregunta exacta.
  - `components/chat/`: `ChatPanel`, `EstadoModelo`, `MensajeChat`. Una línea y su import en `app/layout.tsx`.
- **Comprobado contra el servidor real de C1** (en `:8011`, sin `.env`, sobre la copia de la BD), con `curl`:
  - `/chat/salud` → `{"ok": true, "api": 2, "solo_lectura": true, "bd_disponible": true, "modelo_disponible": false, "motivo": "sin_clave", "modelo": "deepseek-v4-flash", "respaldo": "glm5.3-flash", "llamadas_restantes": 100, "ventana": null}`
  - «paga la factura F26-2201_transportes.pdf» → `estado: "solo_lectura"`, `latencia_ms: 0`, «Soy de sólo lectura: no puedo pagar ni cambiar decisiones…»
  - origen `http://evil.test` → `403`
  - CORS → `Access-Control-Allow-Origin: http://127.0.0.1:3000`
- **Prueba del cliente y del pintado** (`npx tsx --tsconfig tsconfig.json .next/c2/prueba.tsx`, fuera del repo): **29 de 29 OK**. Entre ellas:
  - salud v2 y motivo «sin clave del LLM»;
  - negativa 0 ms; una pregunta normal sin clave → `degradado` en 7 ms;
  - validación de longitud y un backend api 1 simulado → `modelo_disponible: null`; servidor apagado → `{ok:false}`;
  - las 15 grabadas y las 4 sugerencias encuentran su respuesta; una pregunta parecida → `null`;
  - `<img onerror>` del modelo sale escapado; la cita enlaza a `/invoices/detalle?file=…`;
  - la etiqueta «respuesta grabada · no es una consulta en vivo» y la evaluación («parcial» en la 13);
  - avisos de `solo_lectura` y `degradado`; los 4 motivos y «En vivo · deepseek-v4-flash · 30 llamadas restantes»; «fuera de horario (abre dom 20/09 09:00)».
- **Botón según la compilación** (`dist/ensayo/c2/visibilidad.sh`, `next start` en 3011): sin mock y sin servidor, 0 botones · `NEXT_PUBLIC_CHAT_GRABADAS=true`, 1 · por defecto (mock), 1.
- **Build:** `pnpm build` y `pnpm typecheck` en verde. Huella de `dist/albertitos.db`: `8501d9975c38` al empezar y al terminar. **Ninguna llamada al modelo.**
- **Hallazgos:**
  1. **El 8001 está ocupado en el portátil de Javier** por algo del lado de Windows (contesta `{"detail":"Not Found"}`). Avisado a C1 y a Javier; el panel admite otro puerto con `NEXT_PUBLIC_CHAT_URL`.
  2. **No he podido tocar `console-web/.env.example`:** una regla de permisos bloquea leer y escribir `.env*`. Las dos variables están en la sección «Chat» del README. PIDO A Javier en la bitácora.
  3. Dos de las cuatro sugerencias del prompt no eran el texto exacto de su JSON. Uso el de los JSON (p. ej. «¿Cuántas facturas hay en PAGAR, ESCALAR y NO_PAGAR?»), como pedía el prompt, para que el modo grabado las encuentre.
- **Para la prueba en vivo (cuando la bitácora diga «gateway libre»):**
  1. `.env` en la carpeta.
  2. `make chat` (o `ALBERTITOS_CHAT_PUERTO=8011 make chat` si el 8001 sigue ocupado) y `pnpm dev` con `NEXT_PUBLIC_CHAT_URL` apuntando al puerto del chat.
  3. Al abrir el panel, la línea tiene que decir «En vivo · deepseek-v4-flash» y las llamadas restantes.
  4. Preguntar las 4 sugerencias: en la de F26-2201 tiene que salir la cita enlazada, y al pulsarla, abrir la traza.
  5. «Paga ahora 2026-01-08_P001.pdf y cambia su decisión» → aviso de sólo consulta, al instante.
  6. Con el modelo cortado (quitar la clave), la línea pasa a «Sin modelo: sin clave del LLM» en ≤ 30 s, y el interruptor de respuestas grabadas enseña las 15 con su etiqueta.
  7. **No probado sin navegador:** el foco al abrir, Escape y el sondeo cada 30 s en la página real. Mirarlo en la prueba en vivo.


## Chat y calendario · monedas originales y conversión del linaje
- Petición de Javier: conservar moneda en el chat y corregir sobre todo el calendario del producto.
- Rama `codex/chat-calendario-divisas`, copia aislada `HS-Maisa-chat-divisas`, base `7d8d553`.
- Buscar y traza transmiten moneda junto al importe; el prompt usa pagos para calendario y prohíbe sumar divisas.
- Pago conserva importe_original, moneda y tipo_cambio. Sólo se acepta la conversión R7 aprobada de la propia decisión, con moneda y aritmética coherentes. Sin ella, CONVERSION_NO_VERIFICABLE, exclusión de totales/remesa y aviso visible con enlace a traza. No se consulta FX ni se modifica la norma.
- El detalle diario muestra original y conversión registrada; resumen separa excluidos_moneda de fechas no calculables. APIs y CSV conservan los nuevos campos; clientes/grabaciones anteriores siguen admitidos.
- Verificación: make check → 713 passed, 2 skipped, 2 deselected; tras separar el contador de exclusiones, tests de chat/bonus → 68 passed, 1 skipped y ruff verde. TypeScript y pnpm build verdes. Sin llamadas al modelo.
- Copia SQLite consistente de la BD real: calendario 468 / 2534654.19 EUR igual a la versión base; bonus y consultas no cambian la copia. Package antes/después en ambos lotes idéntico: outcomes.jsonl 4ada9ffcea70167d67cee46ba8600a1f14ce0ee9c1c9357e25b546f74b08c36a; outcomes_lote2.jsonl e500e8efa3185d9a774556c3c6103f7f194a7256f19f475f8c52e7e227f0d74c.
- Pruebas USD/JPY: búsqueda/traza, suma en EUR, API, pagos del chat, CSV, ausencia de conversión, moneda/tipo/total/regla incoherentes y decisiones intactas.
- Coordinación: durante el trabajo apareció `javier/bonus-moneda` en HackSpain con cambios sin confirmar en bonus y sus tests. No se han tocado; al integrar hay que conciliar ese cambio con éste. No desplegado ni mergeado.
