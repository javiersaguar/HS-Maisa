---
name: benchmark
description: Cómo medir ficheros/segundo, latencias por etapa y coste real en el portátil de la demo, y escribir docs/benchmark.md con condiciones. Úsalo cuando el pipeline complete la Caja (sábado) y otra vez tras el lote 2.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(sqlite3 *) Bash(cat *)
---
# Benchmark (25 puntos + primer desempate)

El tribunal separa "medido" de "estimado". Todo lo que escribas tiene que salir de la BD de eventos.

## 1. Condiciones (anótalas antes de medir)
Hardware (CPU, RAM, SO), tamaño del lote, ERP con/sin latencia, % de ficheros que tocan el LLM y por qué (sin texto, plantilla no reconocida), modelo, caché vacía o llena, concurrencia (`ALBERTITOS_WORKERS`).

## 2. Medir
```
make clean && make db
time uv run albertitos run                     # caché vacía = coste real
uv run albertitos bench                         # lee eventos: ficheros/s total y por etapa, p50/p95 latencia, tokens y EUR por etapa
time uv run albertitos run                      # segunda pasada: todo desde caché → coste 0, ficheros/s de "reprocesado"
```
Consultas útiles:
```
sqlite3 dist/albertitos.db "select etapa, count(*), avg(latencia_ms), sum(coste_eur) from eventos where estado='ok' group by etapa"
sqlite3 dist/albertitos.db "select count(*) from eventos where error_codigo='ORA-00600'"
```

## 3. Fórmula de coste
`coste = N · p_llm · (tokens_in · precio_in + tokens_out · precio_out) + N · p_vision · coste_vision + fijo`
con `p_llm` = fracción que toca el LLM (medida), precios del modelo a fecha de hoy (cítalos), `fijo` = 0 en portátil.
Da el coste por factura y por 10.000 facturas. Di qué palanca lo baja (plantillas → p_llm↓, modelo más barato, caché).

## 4. Límites y evolución
- Cuello de botella medido (¿ERP 10 rps? ¿LLM rate limit? ¿CPU en PDF→imagen?). Qué pasa con 10× y 100×: qué se paraleliza (workers), qué se cola.
- Nuevos tipos de archivo (emails, Excel, escaneados): qué cambia → un conector nuevo en `extract/` que produce el mismo `InvoiceFacts`; nada en `rules/` ni `core/`.

## 5. Escribir `docs/benchmark.md`
Tabla de condiciones, tabla de cifras (medidas), fórmula con números, límites, plan de evolución. Fecha y commit. Copia las cifras clave al plan (`docs/plan/albertitos_plan.md`).
