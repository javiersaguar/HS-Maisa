---
name: lote2
description: Runbook del sábado 18:00 — integrar lote-2-sorpresa (40 facturas), la actualización del ERP y la norma v4, y reprocesar sólo lo impactado. Úsalo en cuanto llegue el zip.
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv run *) Bash(unzip *) Bash(sha256sum *) Bash(ls *) Bash(git *)
---
# Lote 2 (sábado 18:00)

Lo que evalúan aquí no es el acierto: es **cómo diseñamos el cambio, el reprocesado y los límites**. Documenta cada paso.

## 0. Antes de tocar nada
- Commit del estado actual en tu rama. `make package` para tener el lote 1 congelado en `dist/entrega/` (entrega de seguro si no se hizo a las 17:30 → `/entrega`).
- Pregunta al mentor si `outcomes.jsonl` (lote 1) debe reflejar la norma v3 o la v4 y el ERP v1 o v2. Anota la respuesta en `docs/hitos.md`.

## 1. Datos
```
sha256sum lote-2-sorpresa-v3.2.zip        # compáralo con el hash publicado en el canal
unzip -o lote-2-sorpresa-v3.2.zip -d data/lote2/
ls data/lote2                              # esperado: facturas/ (40 pdf) · erp_export_lote2.csv · norma v4 (txt/xlsx/md)
uv run albertitos caja verify --lote 2     # 40 PDFs, NFC
git add data/lote2 && git commit -m "data: lote 2 sorpresa v3.2"
```

## 2. ERP actualizado
Reinicia el ERP con la actualización y descarga el snapshot v2:
```
make erp-lote2-fast          # en otra terminal (o erp-lote2 con latencia para la demo)
uv run albertitos erp pull --tag v2
uv run albertitos erp diff v1 v2          # asientos nuevos / cambiados: qué pedidos pasan a PAGADA, importes que cambian
```

## 3. Norma v4
- Lee la norma v4 y escribe en `docs/adr/` (vía `/adr norma-v4`) qué cambia respecto a v3 y qué decisiones toca.
- Implementa `src/albertitos/rules/norma_v4.py` **sin editar** `norma_v3.py`. Registra `"v4"` en `REGISTRO`. Tests de tabla para cada regla nueva o cambiada.

## 4. Reprocesar sólo lo impactado
```
uv run albertitos ingest --dir data/lote2/facturas --lote 2
uv run albertitos extract --solo-pendientes
uv run albertitos reprocess --impacted --norma v4 --erp v2     # imprime: cuántas decisiones cambian y por qué
uv run albertitos status
```
Guarda la salida del `reprocess` en `docs/reprocesado-lote2.md`: número de decisiones recalculadas vs. total, cuántas cambian de resultado, tiempo. Es la evidencia para "Escalabilidad y coste" y "Resiliencia".

## 5. Entrega
`/entrega` genera ambos JSONL. Si a las 22:00 el lote 2 no está procesado, se cancela el bonus y todo el equipo va aquí (`docs/hitos.md`).
