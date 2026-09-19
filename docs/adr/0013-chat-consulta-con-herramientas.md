# ADR-0013 · Chat de consulta con herramientas cerradas

Estado: implementado y evaluado, PLAN-11 K2; ampliado en el PLAN-13 (C1). Fecha: 19/09/2026.

## Contexto

Alberto necesita preguntar por facturas, motivos y vencimientos sin conocer comandos ni reglas. El bonus no puede alterar decisiones ni competir con el gateway del lote 2. La consola de Alejandro usa un puente GET de sólo lectura y debe conservarlo. Hay instrucciones inyectadas dentro de los PDFs.

## Alternativas consideradas

1. SQL generado por el modelo: flexible, pero añade consultas arbitrarias y hace difícil controlar alcance, coste y datos enviados. Descartado.
2. Buscar texto y devolver respuestas prefijadas: útil sin gateway, pero limita preguntas que combinan proveedor, pedido y motivo. Se conserva la traza local como repliegue.
3. Tool calling con herramientas cerradas y sin escrituras (elegida): reutiliza lecturas y bonus, mantiene una frontera comprobable y cita los documentos consultados.

## Decisión

`albertitos.chat` tiene herramientas pydantic cerradas, consultas fijas y conexiones SQLite `mode=ro`. No importa el pipeline, las reglas ni extract. El modelo de Helmcode (OpenAI-compatible mediante httpx) elige entre buscar, traza, resumen y pagos; confianza aparece sólo cuando K3 publica su interfaz. No tiene shell, SQL libre, archivos, red adicional ni acciones bancarias.

Cinco consultas por pregunta; máximo seis llamadas al modelo; timeout con el presupuesto restante de 60 s, sin reintentos automáticos, breaker 3 fallos/60 s. Contador persistente independiente y transaccional: 60 intentos HTTP K2, incluidos los fallidos. La fecha límite del ciclo queda impuesta en código; no basta con una nota en el runbook.

Proceso HTTP local en `127.0.0.1:8001`, `POST /chat` y `GET /chat/salud`. CORS para localhost:3000; petición y concurrencia acotadas. CLI independiente para la defensa. No se escribe en la BD de negocio ni se modifica el puente de Alejandro.

Los fragmentos sospechosos del PDF se omiten; los datos restantes están delimitados como no instrucciones. Se rechazan peticiones directas de modificación y afirmaciones explícitas de ejecución de pagos. La respuesta final debe tener el esquema acordado y sus citas deben pertenecer a las herramientas usadas en esa pregunta. Se admite prosa del gateway antes del objeto JSON, pero sólo se utiliza el objeto validado.

## Consecuencias aceptadas

Las barreras de escritura son deterministas; la explicación lingüística no lo es. Verificar que una cita existe no prueba por sí solo toda afirmación del modelo. La evaluación de 15 preguntas es evidencia acotada, no garantía universal. La decisión y la traza persistidas conservan autoridad.

Omitir instrucciones literales evita exponerlas innecesariamente, pero limita la explicación exacta de una anomalía: se remite a la traza. Se rechazan respuestas con citas inventadas y preguntas sin datos. Sin gateway, no se inventa una respuesta: se ofrece el comando de traza.

No hay nuevas dependencias, memoria persistente de conversación, envío de pagos ni integración de Jev. El único estado escrito por chat es su contador local de presupuesto. No es servicio multiusuario de producción ni buscador para más de los documentos del reto.

## Cambios del PLAN-13 (C1, 19/09 tarde)
Para que el chat funcione el domingo, y no sólo como demo grabada:
- **B1 · Ventana y tope configurables.** El cierre (17:30 del 19/09) y el tope (60) estaban fijos en el código; ahora
  van por `ALBERTITOS_CHAT_DESDE/HASTA`, `ALBERTITOS_CHAT_MAX_LLAMADAS` (contadas dentro de la ventana) y
  `ALBERTITOS_CHAT_CONTADOR`. Se descartó borrar el contador viejo para «reabrir»: el tope se salta cambiando la
  configuración a la vista, no destruyendo el registro.
- **B2 · `/chat/salud` v2:** disponibilidad del modelo y motivo, sin llamarlo. La consola lo enseña antes de preguntar.
- **B3 · Orígenes configurables** (`localhost:3000` y `127.0.0.1:3000`), devolviendo el origen que pide, nunca `*`.
- **B4 · Respaldo de modelo** (`glm5.3-flash`, el de texto medido) ante timeout, 5xx o una final fuera de esquema, con
  25 s por petición para que quepa en los 60 s por pregunta. La respuesta dice qué modelo contestó. Alternativa
  descartada: reintentar el mismo modelo, porque los dos timeouts de la evaluación eran del proveedor, no transitorios.
- **B5 · Instrucción en el PDF:** la traza lo marca de forma explícita (`instruccion_en_pdf` + nota) y el prompt prohíbe
  atribuir al PDF frases que no vengan de una herramienta. Sigue sin pasar el texto literal al modelo.
- **B6 · `make chat`**, `--salud` en la CLI, y un puerto configurable con un mensaje claro si está ocupado.
Evidencia: 25 tests en `tests/test_chat.py` (reloj inyectable para la ventana, transporte simulado para el respaldo,
servidor real para CORS y salud), sin ninguna llamada al modelo. Prueba con curl en `docs/agentes/PARTE.md` (C1).

## Evidencia

`tests/test_chat.py`: filtros cerrados e inyección SQL como dato, PDF con orden de pagar, negativas sin modelo, límite de cinco herramientas, degradación, citas inventadas, historial no privilegiado, breaker HTTP simulado, contador persistente y corte horario, API local/CORS y respuesta real del gateway con prosa antes del JSON.

La prueba de integración crea una copia con SQLite backup, ejecuta chat y herramientas, comprueba que el volcado lógico no cambió y ejecuta `package` con auditoría: `outcomes.jsonl` idéntico byte a byte al publicado, SHA256 prefijo `1ec4be206089`.

Evaluación: 59 intentos HTTP de 60 permitidos, entre 14:58 y 15:04 Madrid. Serie inicial 12/15 completas; tras tres repeticiones, 14/15 completas y 1 parcial. La parcial conserva ESCALAR pero atribuye al PDF una frase del usuario no corroborada; no se presenta como acierto. Dos timeouts reales de 60 s activaron el repliegue. make check: 555 passed, 1 skipped, 2 deselected; 17 tests propios.

Evaluación y ejemplos reales: [contrato chat](../api/chat.md). Se contabilizan también llamadas de depuración y primeras pasadas fallidas.

## Resumen para el plan (5 líneas)
El chat explica hechos y decisiones mediante herramientas de consulta cerradas, sin SQL generado ni escrituras.
Cada cita debe proceder de las facturas recuperadas; se omiten instrucciones literales de PDFs y la norma conserva la autoridad.
Un proceso local separado sirve POST /chat y una CLI permite demostrarlo sin la pantalla de Alejandro.
Cinco consultas por pregunta, degradación explícita, breaker y tope persistente de 60 llamadas antes de las 17:30 protegen el lote 2.
Un test ejecuta el chat sobre copia y verifica que package conserva exactamente el outcomes publicado; la evaluación lingüística es limitada y se informa por separado.
