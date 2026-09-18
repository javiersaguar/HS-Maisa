# Parte de fin de ciclo · ciclo 4

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (01: A1-A3 · 02: B1-B2 · 03: C1-C2).

## D1 · Escala medida a 10.000 facturas
- Estado: terminado | parcial | bloqueado
- Hecho (con cifras):
- Verificado con (comando → resultado literal):
- Ficheros tocados:
- Commits (hash · mensaje):
- Descubierto:
- Pendiente / no llegué a:
- Necesito de otros (quién · qué · para qué):
- Riesgos que veo:
- Propongo como siguiente tarea:

## D2 · Evidencia completa para la demo y trampas al día
- Estado: **terminado** (los 4 pasos; 00:14 → 01:10). Queda **un test ajeno en rojo** con parche de una línea propuesto (ver "Necesito de otros").
- Hecho (con cifras):
  - **Tramo instructivo completo** (`extract/instrucciones.py`): empieza en la frase de la instrucción saltando los importes que la preceden y termina en el pie legal, en la siguiente línea de importes o a los 300 caracteres. Antes se devolvía sólo la frase de la coincidencia y **en 11 de las 27 facturas de plantilla se perdía la orden**. Ahora las 29 con instrucción en capa de texto la incluyen.
  - **Tests**: tabla `ORDENES` con la orden exacta que debe contener cada una de las 29 (una por fichero), sin empezar por importe y ≤ 300 caracteres; 0 falsos positivos en 60 facturas limpias; `MAX_TRAMO` sustituye al tope de 240 en el test de A2.
  - **Falso positivo destapado**: las instrucciones inyectadas son **31, no 32**. `scan_025.pdf` no tiene ninguna; el modelo devolvió la cadena `"None"` y el código la tomó por instrucción (hoy se escala con el motivo `el documento dice: "None"`). Arreglado en `llm.py` (`_fragmento_valido`) con 8 casos de prueba. **No he reextraído `scan_025`**: quitarle el aviso podría pasarla de ESCALAR a PAGAR y la factura lleva otra transparentándose por detrás; es decisión de norma.
  - **Reextracción**: 29 facturas en 0,2 s, 0 tokens, 0 € · **15 fragmentos actualizados · 0 avisos cambian → ninguna huella de hechos cambia** (ninguna decisión queda invalidada, pero la traza guardada cita el fragmento viejo hasta que se ejecute `decide`).
  - **Fixtures reexportados**: `hechos_caja.jsonl` con **500** hechos (la exportación anterior incluía por error los 10 del lote 2 simulado de B1) y `hechos_muestra.jsonl` con 21.
  - **Caos por BD** (`sources/chaos.py`): el fichero vive junto a su base de datos (`<db>.chaos.json`) y se resuelve en cada llamada; `ALBERTITOS_CHAOS` sigue mandando. Test de aislamiento: el caos de una BD de ensayo no afecta a otra. Aviso del guion actualizado en `CONTRASTE-TOTAL.md` §7.
  - **`docs/trampas.md`**: recuento corregido (31), las 11 órdenes que se perdían, y tabla de trampas de escaneadas verificadas a 220 dpi (`scan_016` cambio de cuenta, `scan_023` documento contaminado, `scan_021` NIF tapado, `scan_025` transparencia invertida sin instrucción).
- Verificado con (comando → resultado literal):
  - `uv run pytest tests/test_extract.py tests/test_llm.py -q` → `117 passed, 2 deselected`
  - `uv run albertitos extract --no-solo-pendientes --fixture <29 de texto> --workers 4` → `29/29 ok · plantilla 27 · cache 2 · tokens 0/0 · 0.0000 EUR · 0.2 s`
  - `grep -c 'Debe escalarse cualquier factura suya' data/fixtures/hechos_caja.jsonl` → `1` (antes: 0)
  - `make check` → **1 fallo ajeno**: `tests/test_lote2_sim.py::test_extract_con_el_llm_caido…` (de C2)
- Ficheros tocados: `src/albertitos/extract/{instrucciones,llm}.py`, `src/albertitos/sources/chaos.py`, `tests/test_{extract,llm}.py`, `data/fixtures/hechos_{caja,muestra}.jsonl`, `docs/trampas.md`, `docs/agentes/CONTRASTE-TOTAL.md`, `docs/agentes/{BITACORA,PARTE}.md`
- Commits (hash · mensaje): (este ciclo) `extract: tramo instructivo completo, fragmento vacío no es instrucción y caos por BD (D2)`
- Descubierto:
  - El campo `texto_sospechoso` del LLM viene con la palabra `"None"` en **838 lecturas cacheadas**; sólo afectaba a un hecho guardado, pero con el lote 2 volvería a pasar.
  - `scan_025.pdf` y `scan_023.pdf` comparten trampa: **otro documento transparentándose** (en `scan_025`, invertido, con sello "URGENTE"). No hay aviso honesto para eso en `core`.
  - La exportación de fixtures arrastraba los 10 ficheros del lote 2 simulado: cualquiera que importara `hechos_caja.jsonl` se traía hechos de ficheros que no tiene.
- Pendiente / no llegué a: `--con-hechos` en `scripts/inventario_trampas.py` (era opcional): sumaría los avisos de visión al inventario sin releer los PDFs. Queda para el ciclo 5.
- Necesito de otros (quién · qué · para qué):
  - **Javier / dueño de `tests/test_lote2_sim.py`** (de C2; no está en mi lista y no lo toco): el test exige cita literal sobre el texto crudo y el tramo ya cruza un salto de línea. Parche: `assert trampa.texto_sospechoso in " ".join(pdf.texto_de(LOTE2_SIM / CON_INSTRUCCION).split())`. Sin eso `make check` queda rojo.
  - **Miguel**: `Aviso.DOCUMENTO_SUPERPUESTO` en core; y tras reimportar los fixtures, **`decide` completo** (no `reprocess --impacted`), porque la evidencia no entra en la huella de los hechos.
  - **Mónica**: R6 a 300 caracteres (hoy 120 y el tramo de F26-2201 mide 127); `NIF_INVALIDO` en `ANOMALIAS_HUMANO`; política para documento superpuesto.
- Riesgos que veo: (1) si nadie ejecuta `decide` completo, la demo del minuto 0-2 seguirá citando el fragmento viejo aunque los hechos ya estén bien; (2) `scan_025` sigue escalando por un motivo falso hasta que exista el aviso nuevo: es seguro (escala), pero es una traza que el tribunal puede preguntar; (3) el tramo más largo (269 c) se acerca al tope de 300: si el lote 2 trae párrafos más largos, se cortarán (se marca con "…").
- Propongo como siguiente tarea: (ciclo 5) `--con-hechos` en el inventario y pasarlo al lote 2 en cuanto llegue; revisar con Mónica los 31 fragmentos uno a uno en la muestra etiquetada; y un repaso de las 29 escaneadas buscando más documentos superpuestos.

## Javier (a mano, al cerrar el ciclo)
- `make check`:
- `make agentes-check`:
- `git push` (y merge a main por Miguel):
- Preguntas a mentores pendientes:
