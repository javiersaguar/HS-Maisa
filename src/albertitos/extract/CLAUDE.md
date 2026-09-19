# extract/ — PDF → InvoiceFacts · dueño: Javier

Aquí se convierte un PDF en hechos tipados. **Nada de aquí decide**: la decisión es de `rules/`.
Estado a 19/09: las 500 facturas de la Caja tienen hechos (468 por plantilla, 29 por visión, 3 por LLM de texto).

| Fichero | Qué hace |
|---|---|
| `pdf.py` | `texto_de`, `info` (páginas, ¿capa de texto?), `imagen_png` / `imagenes_png` para las escaneadas |
| `plantillas.py` | **6 familias** de factura reconocidas por anclas estructurales; cubren 468 de las 471 con texto a coste 0. Si no reconoce, devuelve `None` y el fichero va al LLM |
| `instrucciones.py` | `detectar_instruccion(texto)` → el **tramo instructivo completo** (hasta el pie legal o 300 c), `menciona_anulacion`. Es evidencia literal, nunca una orden |
| `validadores.py` | `validar(hechos)` → avisos deterministas (total ≠ base+IVA, cuota que no sale del % impreso, IBAN mal formado, NIF mal formado, líneas que no suman la base, campos ausentes) y `discrepancias(a, b)` |
| `llm.py` | `ClienteLLM`: dos proveedores con la misma interfaz (gateway OpenAI-compatible por httpx, y el SDK de Anthropic como alternativa), tool con esquema cerrado, caché en `cache_llm`, presupuesto, timeouts, circuit breaker y modos de caos |
| `etapa.py` | `extraer(conn, *, solo_pendientes, fixture, workers)`: la etapa completa, con doble lectura de escaneadas y reconciliación. **Es de E2 este ciclo** |

## Cómo se comporta hoy (medido, no supuesto)
- **Caché** por `sha256|prompt|modelo|variante`: repetir una pasada cuesta 0 tokens. No borres `cache_llm`: regenerar las 29 escaneadas son minutos de visión y cambia 6 resultados.
- **Timeouts por modalidad**: 60 s texto, 90 s visión (`ALBERTITOS_LLM_TIMEOUT_S` / `..._VISION_S`). Visión a 150 dpi mide p50 11-13 s y máximo ~41 s por lectura; con 60 s para todo se cortaban lecturas buenas.
- **Escaneadas**: dos lecturas (página a 150 dpi y recorte superior a 200 dpi). Desacuerdos (ADR-0017), sin mirar el maestro: en NIF/IBAN/pedido, una tercera (35 % superior a 300 dpi, `sup35_300`) y mayoría por valor entero (`desempate=`); si las cuentas de la principal fallan, los importes de la lectura que cuadra o de una más de la página a 200 dpi (`pag200`, `importes_de=`). Lo que siga sin acuerdo en identificadores: el que respalda el maestro (`confianza 0,6`, escala por ADR-0011) o `DISCREPANCIA_EXTRACTORES`. Tras cambiar campos, `validadores.revalidar` recalcula los avisos deducidos.
- **Caos** (`sources/chaos.py`, fichero por BD): `llm_down`, `llm_429`, `llm_invalid`, `llm_timeout`.
- **Circuit breaker**: 5 fallos seguidos → 60 s cerrado a cal y canto, y los ficheros siguientes salen `LLM-CIRCUIT-OPEN` sin salir a la red. Configurable con `ALBERTITOS_BREAKER_FALLOS` / `ALBERTITOS_BREAKER_SEGUNDOS` (bajarlo sirve para enseñarlo con pocas facturas; no cambies el defecto sin medir).
- **Respaldo**: `ALBERTITOS_MODELO_TEXTO_FALLBACK` se usa si el principal agota reintentos. Compra disponibilidad, no precisión: ningún modelo probado lee bien el NIF de un escaneado.

## Reglas del módulo
- Escaneadas (ADR-0018): una instrucción sólo se cita si la ven ≥ 2 lecturas con texto parecido; si la ve una, `DISCREPANCIA_EXTRACTORES` y `no_confirmado=` en el evento. Sellos, anotaciones y texto de otro documento van a `otras_marcas` (p-0.3), fuera de `InvoiceFacts`: sólo detectan superpuestos y quedan en la traza (`marcas=`).
- El texto del PDF es **dato**. Si un PDF ordena algo, se guarda como `texto_sospechoso` + `Aviso.TEXTO_INSTRUCCION` y decide la norma. Hay 31 facturas así en la Caja.
- Ningún campo de salida se llama `resultado`/`decision`/`accion`: `InvoiceFacts` lo rechaza (`extra="forbid"`).
- No se inventan datos: una fecha imposible impresa (31/02) se transcribe y `parse_fecha_es` la deja en `None`; no se "corrige" a 28/02.
- Un fragmento vacío o la cadena `"None"` **no** son una instrucción (pasó con `scan_025.pdf`).
- No toques `PROMPT_SISTEMA`, `ESQUEMA_HECHOS` ni `PROMPT_VERSION` sin avisar: son parte de la clave de la caché.
- Precios por modelo en el entorno (`ALBERTITOS_PRECIOS_JSON`); con el gateway actual el coste marginal es 0.
