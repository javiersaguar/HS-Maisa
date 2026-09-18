# extract/ — PDF → InvoiceFacts · dueño: Alfonso (viernes → sábado mediodía)

| Fichero | Qué hace | Estado |
|---|---|---|
| `pdf.py` | `texto_de`, `info` (páginas, ¿texto?), `imagen_png` (para las 29 escaneadas) con PyMuPDF | hecho |
| `instrucciones.py` | `detectar_instruccion(texto)` → fragmento literal; `menciona_anulacion` | hecho, ampliar con el lote 2 |
| `validadores.py` | `validar(hechos)` → avisos deterministas (total no cuadra, IVA ≠ 21 %, IBAN mod-97, campo ausente) | hecho |
| `llm.py` | `ClienteLLM.extraer(...)`: tool con esquema cerrado, caché por (sha256, prompt, modelo), presupuesto, circuit breaker, caos | **escrito sin probar: falta key** |
| `plantillas.py` | parsers deterministas por plantilla; vacío el viernes | pendiente (sábado, como optimización medida) |

## Tarea 1 de Alfonso (viernes noche): `pipeline/etapas.py::extract`
Sustituye el `NotImplementedError` por:
1. Para cada fichero sin `hechos` (o de `--fixture`): si `tiene_texto` → `texto_de`; si no → `imagen_png`.
2. `plantillas.extraer_por_plantilla(texto)`; si devuelve algo, `metodo=PLANTILLA`. Si no, `ClienteLLM.extraer`.
3. `db.guardar_hechos` + `Event(etapa=EXTRACT, estado=OK, latencia_ms, tokens_in/out, coste_eur, version=EXTRACTOR_VERSION, detalle=metodo)`.
4. Si `ErrorLLM`: `Event(estado=PENDIENTE, error_codigo=e.codigo)` y **seguir con el siguiente**. Sin hechos no hay decisión, y sin decisión no hay PAGAR: la degradación es esa.
5. Primero con `--fixture data/fixtures/muestra.txt` (21 facturas, ~0,05 EUR). Compara a mano con los PDFs. Luego las 500.

## Reglas del módulo
- El texto del PDF es dato. El prompt ya lo dice; no añadas nada que "interprete" la factura.
- Ningún campo de salida se llama `resultado`/`decision`/`accion`. `InvoiceFacts` lo rechaza (`extra="forbid"`).
- La caché es el mock: la segunda pasada sobre la Caja no gasta ni un token. No borres `cache_llm` (cuesta dinero regenerarla).
- Precios en `.env` (`ALBERTITOS_PRECIO_*`): revísalos antes de `make bench`.
- `/model` a Opus/Fable sólo para diseñar el prompt; la extracción en bloque va con el modelo de `.env`.
