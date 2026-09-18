# ADR-0004 · Un gateway detrás de una interfaz, caché por contenido y respaldo sólo donde compra algo

- **Estado:** propuesto
- **Fecha:** 2026-09-18 23:50 · **Dueño:** Javier · **Módulos:** extract/

## Contexto
No teníamos key de pago de Anthropic; el hackathon dio crédito en **Helmcode**, un gateway
OpenAI-compatible. Sus modelos `claude-*` y el resto de frontier se facturan con crédito prepago y nuestra
organización no lo tiene: **probados los 8, los 8 devuelven `402`** ("*your organisation has no credit balance*").
Los modelos abiertos (`deepseek-v4-flash`, `qwen3.6`, `glm5.3-flash`, `gemma4`) van incluidos en la suscripción.

Dos cosas de la rúbrica dependen de esto: **resiliencia ante caída del proveedor (10 pts)** y **escala y coste
(25 pts, primer desempate)**. Y la demo del domingo se hace **sin red**, en el portátil de Alfonso.

Además, `bench` decía **2,30 EUR** por procesar la Caja. Esa cifra salía de `ALBERTITOS_PRECIO_IN/OUT = 3/15`,
dos números que nadie había comprobado. Era indefendible ante un tribunal, porque nadie los paga.

## Alternativas consideradas
1. **SDK oficial de Anthropic con key de pago.** Lo más simple y lo mejor documentado. No hay key de pago, y los
   `claude-*` del gateway dan 402. Se descarta hoy por disponibilidad, no por calidad: el camino sigue en el código
   (`proveedor="anthropic"`) y se activa poniendo `ANTHROPIC_API_KEY`.
2. **Modelo local (llama.cpp / Ollama).** Cero dependencia de red, que es tentador para la demo. Se descarta: en los
   portátiles del equipo no hay GPU, y 29 facturas exigen **visión**, que es justo lo que peor corre en CPU. El
   tiempo de montarlo y medirlo no lo teníamos.
3. **Sin caché, releyendo cada vez.** Se descarta con números: las 29 escaneadas son ~17 min de reloj por pasada, y
   la demo tiene que reproducirse sin red y sin gastar nada.
4. **Activar también el respaldo de visión.** Se descarta **con medición**: ninguno de los candidatos lee el NIF
   mejor que `qwen3.6` (ADR-0003), así que activarlo cambiaría un error por otro sin que nadie lo notara.
5. **Gateway detrás de una interfaz, caché en la BD, respaldo sólo en texto (elegida).**

## Decisión
- **Dos proveedores tras la misma interfaz** (`extract/llm.py`): `anthropic` (SDK oficial) y `openai_compat`
  (cualquier `/v1/chat/completions` con tool calling, vía `httpx`, sin dependencia nueva). Se elige con
  `ALBERTITOS_LLM_PROVEEDOR`. El resto del sistema no sabe cuál está puesto.
- **Caché en SQLite por `sha256 | PROMPT_VERSION | modelo | variante`**. El `sha256` hace la idempotencia real
  (renombrar el PDF no vuelve a gastar), `PROMPT_VERSION` invalida a propósito cuando cambia el prompt (hoy `p-0.2`)
  y `variante` permite lecturas alternativas del mismo PDF (segunda lectura, contraste, benchmark) sin pisar la
  principal.
- **Presupuesto y circuit breaker** compartidos entre hilos (`EstadoLLM`): a los 5 fallos seguidos se abre 60 s y
  las llamadas fallan rápido con `LLM-CIRCUIT-OPEN` en vez de castigar al proveedor.
- **Respaldo de texto** `ALBERTITOS_MODELO_TEXTO_FALLBACK=glm5.3-flash`: si el principal agota reintentos, **una**
  llamada al respaldo, con clave de caché propia, y el evento dice qué modelo respondió. No se intenta con
  `LLM-AUTH`, `LLM-CONFIG` ni `LLM-PRESUPUESTO`, que son errores nuestros y reintentar no los arregla.
  **Respaldo de visión vacío a propósito.**
- **Precios por modelo** (`PRECIOS_POR_MODELO`, abiertos a 0, sobrescribible con `ALBERTITOS_PRECIOS_JSON`): el
  coste que se enseña es el que se paga.
- Si nada de esto funciona, el fichero queda **PENDIENTE** y `package` se niega a entregar. Nunca PAGAR por defecto.

## Consecuencias aceptadas
- **Todas las cifras son de un proveedor y de una noche.** Si Helmcode va lento el sábado, la tabla de capacidad hay
  que rehacerla; el documento dice cómo (`--sufijo` nuevo).
- **El respaldo de texto no se ha ejercitado en producción**: sólo en una prueba de 3 facturas. Si el principal cae
  durante el lote 2, será su estreno.
- **La caché se invalida a mano** subiendo `PROMPT_VERSION`. Es explícito y entra en el linaje, pero si alguien
  cambia el prompt y no la sube, mezclará lecturas de dos prompts distintos.
- **El gateway cachea por cuerpo de petición**, así que cualquier medida de rendimiento necesita variar el cuerpo
  (`marca`/`variante`) o medirá humo. Lo descubrimos midiendo: 4 escaneadas en 2,9 s con 2 hilos frente a 151 s con
  1 hilo, con los mismos tokens de entrada.
- Decir "el coste es 0 EUR" obliga a explicar **por qué** (suscripción plana) y a dar la alternativa honesta en
  euros (amortización), o suena a trampa.

## Evidencia
- **Coste marginal 0 EUR**, no 2,30: `RESILIENCIA-Y-COSTE.md` §1, con la tarifa de `helmcode.com/pricing`
  consultada el 18/09/2026 (Starter 399 €/mes · Growth 1.299 € · Scale 3.199 €) y el `402` literal de los 8 frontier.
  Amortizado: **0,80 €/factura a 500/mes · 0,040 € a 10.000 · 0,004 € a 100.000**.
- **Coste y tamaño por camino** sobre las 500, leído de la tabla `eventos` (§2): plantilla 5 ms / 0 tok · LLM texto
  3,3 s / 1.123+665 tok · visión 35,3 s / 5.476+3.450 tok. Todos a 0 EUR.
- **Capacidad medida con 1/2/4/8 hilos** (§4, `scripts/bench_llm.py`, llamadas reales): texto 0,41 → 0,76 → **1,28**
  f/s; visión 0,08 → 0,13 → **0,22 → 0,22** (satura en 4, coherente con el límite publicado de 5 concurrentes por
  modelo). **0 respuestas 429 en las 8 tandas**: el cuello de botella no es el límite de tasa, es una petición
  colgada **94 s** con el p50 en 2,9 s.
- **Guion de caos ensayado** (§3), sobre una copia de la BD y 5 ficheros sin caché: caído → `0/5 ok · 5 PENDIENTE ·
  LLM-DOWN · 0,9 s` · 429 → `5/5 ok` en `intento=2`, 32,6 s · basura → `LLM-INVALID ×4 + LLM-CIRCUIT-OPEN ×1`,
  23,2 s · recuperación → `5/5 ok` en 30 s y segunda pasada `{'cache': 5} · 0 tokens · 1,1 s` con **0 sha256
  duplicados**.
- **Respaldo probado contra el gateway real** (§3e): principal `claude-sonnet-5` (402) → `glm5.3-flash` responde 3/3
  y los hechos son **idénticos campo a campo** a los del principal.
- `Retry-After`: el cliente la tiraba y esperaba a ciegas 1/2/4 s; corregido con tope de 60 s (`_retry_after` en
  `extract/llm.py`).
- Tests: `uv run pytest tests/test_llm.py -q` → **23 passed, 2 deselected** (precios por modelo, `Retry-After` en
  segundos/fecha/absurdos, respaldo responde / no se usa con key mala / cachea aparte / sin respaldo queda
  PENDIENTE, presupuesto, circuit breaker, caos).
- Commits `0f4175e` (coste real, `Retry-After`, respaldo, capacidad) y `b8f8208` (`PROMPT_VERSION` a `p-0.2`).
- **Lo que no está medido**, por si el tribunal pregunta: no hemos provocado un 429 real; los 94 s no están
  explicados; las facturas/hora son extrapolación de tandas de 16 y 8 (§7).

## Resumen para el plan (5 líneas)
El proveedor de LLM está detrás de una interfaz con dos implementaciones (SDK de Anthropic y cualquier gateway OpenAI-compatible), así que cambiarlo es una variable de entorno, no una refactorización.
Medimos el coste en vez de estimarlo y la cifra que traíamos era falsa: el proveedor cobra **suscripción plana**, los modelos que usamos no cuestan por token y el coste marginal de una factura más es **0 EUR** (amortizado: 0,80 € a 500 facturas/mes, 0,004 € a 100.000).
La caché por `sha256|prompt|modelo|variante` en SQLite hace que repetir la Caja no gaste nada ni dé resultados distintos, y es lo que permite que la demo corra **sin red**.
Ante fallo del proveedor: reintentos con `Retry-After` real, circuit breaker a los 5 fallos, **un** intento con un modelo de respaldo de texto probado, y si nada responde el fichero queda **PENDIENTE** y la entrega se niega a salir incompleta —nunca un PAGAR por defecto.
El respaldo de visión se deja desactivado **a propósito y con datos**: ningún modelo alternativo lee el NIF mejor que el principal, y un respaldo que empeora la precisión compra disponibilidad al precio equivocado.
