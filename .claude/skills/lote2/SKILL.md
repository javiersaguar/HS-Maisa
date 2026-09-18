---
name: lote2
description: Runbook del sábado 18:00 — integrar lote-2-sorpresa (40 facturas), la actualización del ERP y la norma v4, y reprocesar sólo lo impactado. Ensayado el viernes con un lote simulado (docs/agentes/ENSAYO-LOTE2.md). Úsalo en cuanto llegue el zip.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(unzip *) Bash(sha256sum *) Bash(ls *) Bash(git *) Bash(python3 data/caja/alberto_erp.py *) Bash(curl *)
---
# Lote 2 (sábado 18:00) · ensayado: ~15 min hasta tener hechos y diff

Lo que evalúan aquí no es el acierto: es **cómo diseñamos el cambio, el reprocesado y los límites**. Documenta cada paso.
Tiempos medidos el viernes sobre un lote simulado de 10 (8 con texto, 2 escaneadas): ingest 0,3 s · extract 68 s (plantillas 0 s; cada escaneada ~35 s con doble lectura, 4 hilos) · `erp pull` ~4 s · `erp diff` 0,2 s · inventario 0,1 s · `reprocess --impacted` ~5 s.

## 0. Antes de tocar nada (Javier)
- **Si en la BD hay restos del lote simulado** (`uv run albertitos status` → `ficheros por lote: {1: 500, 2: 10}`), quítalos o `package` los incluirá en `outcomes_lote2.jsonl`:
  `sqlite3 dist/albertitos.db "delete from eventos where file_id like 'L2-%'; delete from decisiones where file_id like 'L2-%'; delete from hechos where sha256 in (select sha256 from ficheros where file_id like 'L2-%'); delete from ficheros where file_id like 'L2-%';"`
- Commit del estado actual en tu rama. `make package` para tener el lote 1 congelado en `dist/entrega/` (entrega de seguro si no se hizo a las 17:30 → `/entrega`).
- Pregunta al mentor si `outcomes.jsonl` (lote 1) debe reflejar la norma v3 y el ERP v1, o la v4 y el ERP actualizado. Anota la respuesta en `docs/hitos.md`.

## 1. Datos (2 min)
```
sha256sum lote-2-sorpresa-v3.2.zip                 # compáralo con el hash publicado en el canal
unzip -o lote-2-sorpresa-v3.2.zip -d data/lote2/
ls -R data/lote2 | head -30                        # esperado: facturas/ (40 pdf) · erp_export_lote2.csv · la norma v4 (txt/xlsx/md)
uv run albertitos caja verify --lote 2             # 40 PDFs, nombres NFC (sin manifiesto para el lote 2)
git add data/lote2 && git commit -m "data: lote 2 sorpresa v3.2 + norma v4"
```
Si los PDFs vienen en otra carpeta (p. ej. `data/lote2/lote-2-sorpresa/facturas`), muévelos a `data/lote2/facturas/` o usa `--dir` en ingest y `ALBERTITOS_DIR_LOTE2=<ruta>` en extract.

## 2. ERP actualizado (1 min) — en OTRO puerto, sin parar el v1
```
python3 data/caja/alberto_erp.py --rapido --puerto 8011 --lote2 data/lote2/erp_export_lote2.csv &   # o make erp-lote2-fast si prefieres el 8009
curl -sf http://127.0.0.1:8011/erp/estado | grep -oE '<asientos>[0-9]+|<actualizacion_cargada>[A-Z]+'   # SI
ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2
uv run albertitos erp diff v1 v2                    # nuevos / cambiados / pedidos_afectados: cópialo a docs/reprocesado-lote2.md
```
`pedidos_afectados` + `hechos` de la Caja = la lista exacta de facturas del lote 1 que deberían cambiar de resultado (ver ENSAYO-LOTE2.md §3 para el cruce).

## 3. Hechos del lote 2 (2-6 min según escaneadas)
```
uv run albertitos ingest --dir data/lote2/facturas --lote 2
uv run albertitos extract --workers 4               # sólo pendientes = los 40 nuevos; plantillas 0 tokens, escaneadas por visión
uv run albertitos status                            # ficheros por lote {1: 500, 2: 40}; 0 sin hechos
uv run python scripts/inventario_trampas.py --facturas data/lote2/facturas --erp-tag v2 --salida data/fixtures/anomalias_lote2.csv --sin-docs --solo-resumen
```
Si el inventario o `status` muestran frases de instrucción nuevas o PDFs pendientes, avisa a B2/A2 (extract/) antes de decidir. Las facturas que salen por plantilla NO pasan por el LLM: una frase inyectada con redacción nueva sólo la cazan las regex de `instrucciones.py` o una pasada de contraste LLM (`contrastar`, en extract/).

## 4. Norma v4 (Mónica)
- Lee la norma v4 y escribe en `docs/adr/` (vía `/adr norma-v4`) qué cambia respecto a v3 y qué decisiones toca.
- Implementa `src/albertitos/rules/norma_v4.py` **sin editar** `norma_v3.py`. Registra `"v4"` en `REGISTRO`. Tests de tabla para cada regla nueva o cambiada.

## 5. Reprocesar sólo lo impactado (Miguel, ~5 s)
```
uv run albertitos reprocess --impacted --norma v4 --erp v2     # imprime: impactados N de M · K cambian de resultado
uv run albertitos status
```
Guarda la salida en `docs/reprocesado-lote2.md`: cuántas decisiones se recalcularon vs. total, cuántas cambian y por qué (contrastar con la lista del paso 2), tiempo. Nota: hoy `linaje.impactados` recalcula todo lo que lleva otra versión de ERP/norma (los 540), que tarda segundos; lo que importa enseñar es que **cambian sólo las que referencian los asientos modificados**.

## 6. Entrega
`/entrega` genera ambos JSONL. Si a las 22:00 el lote 2 no está procesado, se cancela el bonus y todo el equipo va aquí (`docs/hitos.md`).
