# Chuleta lote 2 · 18:00 sábado (I1)

Orden corto. Detalle en skill `/lote2` y `docs/agentes/ENSAYO-LOTE2.md`.

## Antes (seguro)
1. `uv run python scripts/preflight_lote2.py --respaldar` → 0 fantasmas, ERP v1.
2. Huellas: `sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl`.
3. Bridge v1 vivo en `:8009`. No tocarlo.

## Material (ZIP del canal)
```bash
: "${ZIP:?}" "${HASH_PUBLICADO:?}"
uv run python scripts/verificar_material.py "$ZIP" --hash "$HASH_PUBLICADO" --esperados 40
# data/lote2 vacío; si no → PARAR
unzip -n "$ZIP" -d data/lote2/
uv run python scripts/verificar_material.py data/lote2 --esperados 40
```

| Señal del verificador | Qué hacer |
|---|---|
| AVISO «copia exacta… (P0-1)» | Seguir: identidades → ESCALAR |
| ROJO «PDF idéntico…» sin P0-1 | `/sync` con main (falta `guardar_identidad`) |
| ROJO «nombre coincide con lote 1» (P0-5) | **PARAR.** Distinto contenido, mismo `file_id`. Sin parche Miguel → NO APTO. Fixture: `data/fixtures/lote2_nombre_repetido/` |
| ROJO NFC / `.PDF` / subcarpetas | Corregir estructura; no renombrar oficiales |

## Flujo
```bash
uv run albertitos ingest --dir data/lote2/facturas --lote 2
uv run albertitos run --erp v1 --norma v3 --fecha-corte 2026-09-18 --salida dist/lote2-preauditoria
# si no hay --erp: extract + reprocess --todo --erp v1
ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2
uv run albertitos erp diff v1 v2
uv run albertitos reprocess --impacted --erp v2 --norma v3 --fecha-corte 2026-09-18
# Hueco Mónica v4: NO inventar norma. Cuando exista:
#   reprocess --todo --norma v4 --erp v2 --fecha-corte 2026-09-18
uv run python scripts/auditoria_entrega.py … --lote ambos --entrega dist/lote2-preauditoria
uv run albertitos package --salida dist/entrega   # o --aceptar-rojo "motivo" si P0-4
uv run python scripts/auditoria_entrega.py … --entrega dist/entrega
```

## Contingencia (último recurso, lote 2)
- Seco: `uv run python scripts/contingencia.py --lote 2`
- Aplicar: `… --aplicar --motivo "…" --fecha-corte 2026-09-18` (nunca lote 1)

## Ensayo aislado (no BD real)
Worktree + merge `miguel/pipeline`; BD por `Connection.backup`; ERP propio `:8010`/`8011`; material = `lote2_sim` + `lote2_identicos` + P0-5. Ver ENSAYO-LOTE2 § I1.
