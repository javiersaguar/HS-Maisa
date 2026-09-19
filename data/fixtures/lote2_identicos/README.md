# Lote 2 SIMULADO con PDFs idénticos (P0-1) — NO es el lote real

Para reproducir y probar el caso de `docs/agentes/P0-1-IDENTICOS.md`: la misma factura, byte a byte, con otro nombre.
Se usa como lote 2 junto a un lote 1 que contenga `2026-01-08_P001.pdf` (tests/test_identicos.py lo monta en tmp).

| fichero | sha256 (12) | qué es |
|---|---|---|
| `L2I-reenvio_2026-01-08_P001.pdf` | `12a5e1eff429` | copia exacta de `data/caja/facturas/2026-01-08_P001.pdf` (lote 1) con otro nombre |
| `L2I-2026-01-14_P002.pdf` | `3f295e8868b9` | factura nueva del lote 2 (= `lote2_sim/L2-2026-01-14_P002.pdf`) |
| `L2I-2026-01-14_P002_copia.pdf` | `3f295e8868b9` | la misma, byte a byte, con otro nombre dentro del lote 2 |
| `L2I-2026-01-15_P003.pdf` | `de08ad117833` | control: una factura normal, sin copias |
