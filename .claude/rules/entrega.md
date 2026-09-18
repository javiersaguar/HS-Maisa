---
paths:
  - "src/albertitos/pipeline/package.py"
  - "src/albertitos/pipeline/validar.py"
  - "docs/plan/build_pdf.py"
---
# Entrega: apto o no apto

- El repo de entrega es **https://github.com/javiersaguar/HS-Maisa-Entrega** (público; `ENTREGA_REPO`) y contiene **exactamente** `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf` en la raíz. Nada más: ni README, ni código, ni .gitignore.
- `file_id` = nombre exacto del PDF en **NFC** (65 nombres llevan tilde). `result` ∈ {PAGAR, NO_PAGAR, ESCALAR}. Un objeto por línea, sin líneas vacías, UTF-8 sin BOM.
- El validador compara el conjunto de `file_id` con el listado real de `data/caja/facturas` (lote 1) y `data/lote2/facturas` (lote 2): exacto, sin faltantes, sin sobrantes, sin duplicados.
- Campos opcionales de traza permitidos: `motivo`, `norma_version`, `regla`. Nunca `sha256` ni rutas locales.
- `package` se niega a escribir si hay ficheros sin decisión vigente: la entrega parcial no existe.
