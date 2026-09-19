# ADR-0007 · Una CLI que escribe, una consola que sólo lee, y la traza dentro de la entrega

- **Estado:** aceptado
- **Fecha:** 2026-09-19 00:40 · **Dueño:** Miguel · **Módulos:** cli.py, console/, pipeline/package.py

## Contexto
Lo que se entrega son ficheros: `outcomes.jsonl` (500 líneas) y `outcomes_lote2.jsonl` (40). La validación
es binaria y exacta: el mismo conjunto de `file_id` en NFC, sin sobrantes ni duplicados. Aparte, 20 de los
100 puntos son trazabilidad y 10 son la ejecución de una defensa de 10 minutos. La defensa se hace en el
portátil de Alfonso, que puede estar sin red.

Somos cinco personas y 36 horas. Alejandro hace la consola con Cursor, que no ejecuta nuestros hooks. El
verificador admite tres campos opcionales de traza por línea: `motivo`, `norma_version` y `regla`
(`.claude/rules/entrega.md`).

## Alternativas consideradas
1. **API web (FastAPI) y una SPA.** Da una interfaz "de producto", pero hay que montar servidor, frontend y
   autenticación, y en la defensa depende de la red. Se descarta: lo que puntúa son ficheros y traza, no
   pantallas. Además serían dos equipos trabajando sobre el mismo estado.
2. **Sólo la CLI, sin consola.** Es lo más barato. Se descarta porque los 4 minutos de traza de la defensa
   se enseñarían con JSON en una terminal, y la cola de escalados que revisa Alberto no tendría dónde verse.
3. **Una consola que también opera** (lanzar extract/decide, corregir decisiones a mano). Se descarta: habría
   dos sitios que escriben en la BD, lógica de negocio repetida en la interfaz, y una corrección a mano no
   tendría regla ni evidencia, así que rompería la traza.
4. **Entregar sólo `file_id` y `result`.** Es el mínimo exigido y el menor riesgo frente al validador. Se
   descarta porque la traza dejaría de estar en lo que se entrega: hoy cada línea dice qué regla falló y
   con qué norma.
5. **La CLI escribe, la consola sólo lee, y la traza va en la entrega por defecto (elegida).**

## Decisión
- `albertitos` (typer) es el **único que escribe** en la BD. Cada verbo es una etapa o una operación.
- La consola Streamlit abre la BD en sólo lectura (`db.conectar(..., solo_lectura=True)`). Tiene una única
  acción, "Reprocesar impactados", que llama a la CLI como subproceso.
- La consola Next tiene una segunda acción, la **bandeja** (`POST /inbox`, `console/bandeja.py`): subir PDF
  sueltos. Tampoco escribe ella: guarda el PDF y llama a la CLI por subproceso (`ingest --lote 99`,
  `extract` y `decide --fixture`). Sólo se abre si el puente se arranca con `--bandeja`, que sirve
  `dist/bandeja.db` (una copia de la BD). La BD de la entrega nunca ve el lote 99, y `package` sólo emite
  los lotes 1 y 2.
- `run` y `package` añaden `motivo`, `norma_version` y `regla` (esta última sólo si alguna regla falla).
  `--sin-traza` quita esos campos con un solo flag.
- Toda entrega pasa por `validar.py`, que replica el verificador, y se escribe "todo o nada" (`.tmp`, se
  valida y sólo entonces se sustituye).

## Consecuencias aceptadas
- **Sin multiusuario ni permisos.** Alberto no puede corregir una decisión desde la consola: tiene que
  cambiar la norma o los datos y reprocesar. Es a propósito, pero es una limitación de producto.
- **La consola depende de que la BD exista y esté al día.** Si la CLI no ha corrido, la consola no enseña nada.
- **La traza en la entrega es un riesgo pequeño y aceptado.** Si el verificador real rechazara campos extra,
  la entrega saldría NO APTO. Lo mitigan dos cosas: la regla de entrega los permite de forma explícita, y
  `--sin-traza` los quita en un solo comando.
- **`package` escribe eventos `emit` en la BD** (qué se entregó y cuándo). Por eso ya no abre la BD en sólo lectura.
- **La bandeja decide sobre una copia.** Lo que se suba en la demo no llega a la entrega. Un PDF con el nombre
  de uno de la Caja y otro contenido se guarda como `./<nombre>` (P0-5) y el panel enseña su decisión, no la
  del original. El POST sólo acepta el origen de la consola (`localhost:3000`), para que otra web abierta en
  el navegador no pueda gastar LLM.

## Evidencia
- `dist/entrega/outcomes.jsonl`: 500 líneas, APTO, con `motivo` y `norma_version` en cada línea (18/09 23:05).
- Tests en `tests/test_pipeline.py`:
  - `test_run_sin_llm_entrega_valida_e_idempotente`: dos `run` dan el mismo JSONL byte a byte, y cada línea
    lleva `motivo` y `norma_version`;
  - `test_run_no_entrega_si_falta_una_decision_y_no_pisa_la_anterior`: con un fichero sin decisión, la
    entrega anterior queda intacta y no quedan `.tmp`.
- `tests/test_contracts.py::test_outcome_rechaza_campos_extra_y_rutas`: el contrato no admite más que
  esos tres campos opcionales.
- Tiempos medidos con la CLI en el portátil de Miguel:
  - `reprocess --impacted` con el ERP v2-sim: 0,51 s de principio a fin (ADR-0006);
  - demo de caos (`make demo-caos`, tres `run` completos): 21,9 s.
- Bandeja, en `tests/test_console.py`:
  - `test_inbox_cli_real_decide_un_pdf_de_la_caja_editado_sin_llm`: ingest, extract y decide con la CLI real
    sobre una factura de la Caja editada. Sale por plantilla, con 0 tokens;
  - `test_inbox_nombre_de_la_caja_con_otro_contenido_no_hereda_su_decision`;
  - `test_inbox_cerrado_sin_el_flag_aunque_la_bd_no_sea_la_de_la_entrega`.
