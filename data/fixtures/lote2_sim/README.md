# Lote 2 SIMULADO (ensayo del sábado 18:00) — NO es el lote real

10 PDFs derivados de la Caja con metadatos cambiados (sha256 distinto) para ensayar el runbook `/lote2` sin tocar `data/lote2/`.
Se usan con `ingest --dir data/fixtures/lote2_sim/facturas --lote 2` y `ALBERTITOS_DIR_LOTE2=data/fixtures/lote2_sim/facturas`.
El ERP simulado correspondiente es `data/fixtures/erp_lote2_simulado.csv` (bridge: `python3 data/caja/alberto_erp.py --rapido --puerto 8011 --lote2 data/fixtures/erp_lote2_simulado.csv`).

| fichero | origen | páginas | texto | plantilla/rasgo |
|---|---|---|---|---|
| `L2-2026-01-08_P001.pdf` | `2026-01-08_P001.pdf` | 1 | sí | clasica |
| `L2-2026-01-14_P002.pdf` | `2026-01-14_P002.pdf` | 1 | sí | mayusculas |
| `L2-2026-01-15_P003.pdf` | `2026-01-15_P003.pdf` | 1 | sí | abono |
| `L2-2026-01-16_P004.pdf` | `2026-01-16_P004.pdf` | 1 | sí | moderna |
| `L2-2026-01-24_P009.pdf` | `2026-01-24_P009.pdf` | 1 | sí | simplificada |
| `L2-2026-01-26_P007.pdf` | `2026-01-26_P007.pdf` | 1 | sí | invoice |
| `L2-2026-01-25_P001.pdf` | `2026-01-25_P001.pdf` | 2 | sí | dos páginas |
| `L2-F26-2201_transportes.pdf` | `F26-2201_transportes.pdf` | 1 | sí | instrucción inyectada (bajo revisión) |
| `L2-scan_002.pdf` | `scan_002.pdf` | 1 | no | escaneada |
| `L2-scan_004.pdf` | `scan_004.pdf` | 1 | no | escaneada |

Los `file_id` empiezan por `L2-`: para quitarlos de una BD, `sqlite3 dist/albertitos.db "delete from eventos where file_id like 'L2-%'; delete from decisiones where file_id like 'L2-%'; delete from hechos where sha256 in (select sha256 from ficheros where file_id like 'L2-%'); delete from ficheros where file_id like 'L2-%';"`.
