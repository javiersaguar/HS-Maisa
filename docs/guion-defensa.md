# Guion de la defensa (10 min · tribunal único · presenta Alfonso)

Portátil de Alfonso. Sin red. ERP con latencia real arrancado. Consola abierta. `trace` de la factura elegida probado.

| min | Bloque del tribunal | Qué se enseña | Quién habla |
|---|---|---|---|
| 0:00–2:00 | Demo y contexto | Alberto y sus tres fuentes. Panel: 500/500 (+40/40) decididas, N escalados, 0 pendientes. Cola de escalados: abrir `F26-2201_transportes.pdf`: el PDF ordena escalar, nosotros escalamos porque la norma lo marca como anomalía, con el fragmento como evidencia. Bonus (si existe): 20 s | Alfonso |
| 2:00–4:00 | Arquitectura y ADRs | Diagrama del PDF. "El LLM extrae, la norma decide" (ADR-0001, 12 PDFs con instrucciones). Por qué CLI + consola de sólo lectura. Reparto modelo / código / persona | Alfonso |
| 4:00–8:00 | Traza, escala y coste | `trace` de una factura normal: hechos (método, tokens) → maestro (versión) → asiento ERP (con los reintentos ORA-00600 en los eventos) → 6 reglas con evidencia → PAGAR. Panel: ficheros/s medidos y hardware, fórmula de coste con números, % que tocó el LLM. Evolución: email/Excel/escaneado = conector nuevo, mismo `InvoiceFacts`. Cambio en vivo (el dato que cambie el tribunal) → `reprocess --impacted` → "N de 540 recalculadas, M cambian" | Alfonso (Miguel apoya en escala) |
| 8:00–10:00 | Resiliencia y preguntas | `chaos --llm-down` → `extract` sobre 3 ficheros nuevos: PENDIENTE, ningún PAGAR, circuit breaker en el panel. `chaos --off` → se reanuda, sin duplicados (sha256 + caché). Preguntas | Alfonso; Javier responde ERP, Mónica norma, Alejandro consola |

## Frases que hay que poder sostener con evidencia
- "Ninguna decisión depende de una frase del PDF." → `Aviso.TEXTO_INSTRUCCION` + R6 + test.
- "Reprocesamos sólo lo impactado." → `linaje.impactados` + salida de `reprocess` del sábado.
- "Si el proveedor cae, no pagamos nada por defecto." → PENDIENTE + `package` que se niega.
- "X ficheros/s en este portátil con Y % de LLM y Z EUR por 1.000 facturas." → `docs/benchmark.md`.

## Si algo falla
Consola → terminal (`status`, `trace`). ERP → `make erp-fast`. LLM → todo está en caché; la demo no necesita red.
