---
paths:
  - "tests/**"
---
# Tests: sólo lo que nos deja NO APTO o sin puntos

- Sin objetivos de cobertura. Un test vale si su fallo cambiaría un `result` o rompería la entrega.
- Prioridad: reglas (tabla, fronteras) > formatos españoles (importes, fechas numéricas y en letra, IBAN, NIF) > cliente ERP (descarga completa = `<meta>`, ORA-00600, renovación de token) > validador JSONL (conjunto exacto, NFC, únicos, enum) > idempotencia (dos `run` → mismo output).
- `@pytest.mark.erp` para lo que necesita el bridge; se salta solo si no responde (fixture `erp_vivo`). `@pytest.mark.llm` para lo que gasta dinero; excluido de `make check`.
- Nada de UI. Nada de mocks del ERP: es local y `make erp-fast` tarda 1 s en arrancar.
- Fixtures de facturas: `data/fixtures/muestra.txt` (21 file_id representativos). No copiar PDFs a tests/.
