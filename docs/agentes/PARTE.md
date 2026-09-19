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
_(pendiente)_
