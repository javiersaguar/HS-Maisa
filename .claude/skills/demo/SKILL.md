---
name: demo
description: Checklist previo y guion de la defensa de 10 minutos (2 demo / 2 arquitectura / 4 traza+escala+coste / 2 resiliencia). Úsalo el sábado noche para ensayar y el domingo antes de presentar.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(ls *) Bash(curl *)
---
# Defensa (10 min, guion fijo del tribunal)

Presenta Alfonso. Portátil de Alfonso, sin depender de red. Guion detallado en `docs/guion-defensa.md`.

## Pre-vuelo (30 min antes)
```
make erp                    # con latencia real: los ORA-00600 y los 0,12 s son parte de la historia
make erp-status
uv run albertitos status    # 500/500 (+40/40) con decisión vigente, 0 pendientes
make console                # abre en < 3 s; las tres vistas cargan
uv run albertitos trace <file_id_elegido>     # la decisión que vas a seguir en vivo, ya probada
```
- La caché LLM está llena: `sqlite3 dist/albertitos.db 'select count(*) from cache_llm'` ≈ nº de ficheros que tocaron el LLM. Sin red, todo debe reproducirse desde caché.
- El escenario de caos está ensayado: `uv run albertitos chaos --llm-down` → ficheros PENDIENTES, nada se paga → `chaos --off` → se reanuda sin duplicados.
- El cambio en vivo del domingo está ensayado: editar un dato (ERP CSV o maestro) → `reprocess --impacted` → diff antes/después en < 30 s.
- PDF del plan abierto en otra pestaña. `docs/benchmark.md` a mano con las cifras.

## Guion (min:seg)
- **0:00–2:00 Demo y contexto.** Quién es Alberto, qué recibe (500 PDF, Excel, ERP 2009). Consola: panel con 500/500, cola de escalados, un ESCALAR con su evidencia (mejor uno con instrucción inyectada: `F26-2201_transportes.pdf`). Si hay bonus, 20 s aquí.
- **2:00–4:00 Arquitectura y ADRs.** Diagrama del PDF. "El LLM extrae, la norma decide": ADR-0001 con la evidencia de los 12 PDFs con instrucciones. Formato CLI+consola (ADR). Reparto agentes/modelo/personas.
- **4:00–8:00 Traza, escala y coste.** `trace` de una decisión real: input → hechos → maestro → asiento ERP → reglas → resultado, con reintentos ORA-00600 reales, latencias, tokens. Panel: ficheros/s medidos, hardware, fórmula de coste, qué cambia si llegan emails/escaneos/Excel (conector nuevo, mismo `InvoiceFacts`). Cambio en vivo → `reprocess --impacted` → diff.
- **8:00–10:00 Resiliencia y preguntas.** `chaos --llm-down` en directo: circuit breaker abierto, PENDIENTES, ningún PAGAR; `chaos --off`: reanuda sin duplicados (sha256 + caché). Preguntas.

## Si algo falla
- Consola no abre → `trace` y `status` en terminal (ya ensayado).
- ERP no arranca → `make erp-fast` y explicar la diferencia de latencia.
- Pregunta que no sabes → "está en el ADR N como consecuencia aceptada" sólo si es verdad; si no, "no lo medimos, lo estimamos así".
