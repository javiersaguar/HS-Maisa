# Lote 2 SIMULADO · P0-5 (mismo nombre, otro contenido) — NO es el lote real

Reproduce el riesgo de Miguel (bitácora 10:55): un PDF del lote 2 con el **mismo `file_id`** que uno del lote 1 y **bytes distintos**. Hoy `verificar_material` sale ROJO («nombre coincide con lote 1») e ingest choca con UNIQUE → el lote 2 sin línea → NO APTO. Lo decide Miguel; aquí no hay parche.

| fichero | qué es |
|---|---|
| `2026-01-16_P004.pdf` | nombre de `data/caja/facturas/2026-01-16_P004.pdf` (no está en `muestra.txt`); contenido = copia de `lote2_sim/L2-2026-01-16_P004.pdf` (≠ Caja). sha256 `4d15672a49cc` (el de la Caja: `dc54bdbf1be4`) |

Tests: `tests/test_nombre_repetido.py`.
