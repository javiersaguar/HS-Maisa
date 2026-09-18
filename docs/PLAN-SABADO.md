# Plan del sábado 19/09 · de dormir a la entrega de seguro y al lote 2

Estado al cerrar la noche (01:20): `main` = `5eeb562`, **261 tests verdes**, `make package` da **APTO** con 500 líneas
(443 PAGAR · 48 ESCALAR · 9 NO_PAGAR). Si mañana saliera todo mal, ya hay una entrega defendible.

## Lo que está hecho y lo que no

| Bloque | Estado |
|---|---|
| Ingesta (500/500 hechos, plantillas 468, visión 29, contraste 468/468) | **hecho** |
| Norma v3 con evidencia completa, duplicados detectados | **hecho** (políticas abiertas en `docs/agentes/DECISIONES-NORMA.md`) |
| Pipeline `run`, `package` todo o nada, reprocesado por linaje | **hecho** |
| Resiliencia (caída, 429, respuesta inválida, timeout) con guion ensayado | **hecho** |
| Escala y coste medidos (10.000 facturas, caminos LLM reales) | **hecho** |
| ADRs 0001-0008 | **hecho**; falta elegir los 2-5 del PDF |
| **Consola (3 vistas)** | **pendiente · Alejandro** — es el minuto 0-2 de la demo |
| **PDF del plan (35 pts)** | **a medias · Alfonso** |
| **Muestra etiquetada a mano** | **pendiente · Mónica + Alfonso** — única verdad antes del domingo |
| **Ensayo de la demo en el portátil de Alfonso** | **pendiente** — nadie ha corrido nada en esa máquina |
| **Bonus (+10)** | **sin decidir** |

## Timeline

| Hora | Quién | Tarea | Por qué ahí |
|---|---|---|---|
| 02:00-09:00 | todos | **Dormir.** | Quedan 34 h y lo que viene exige cabeza |
| 09:00-09:15 | todos | `git pull` · `./bootstrap.sh` · `make check` | Arrancar todos desde el mismo sitio |
| 09:15-09:30 | Miguel | Índice `decisiones(sha256, vigente)` en `schema.sql` (una línea; `decide` pasa de 20,3 s a 1,7 s con 10k) · corregir la cifra de visión de `benchmark.md` (era optimista 2-3×) | Barato y lo pide D1 |
| 09:15-10:00 | Miguel | `hechos import` + **`decide` completo** y comparar con **443/48/9** | Contrato de referencia del equipo |
| 09:15-10:30 | Mónica + Alfonso | **Muestra etiquetada**: las 21 de `data/fixtures/muestra.txt`, cada uno por su cuenta, y comparar | Lo único que valida la norma antes del domingo |
| 09:15-11:00 | Javier | Emitir `DOCUMENTO_SUPERPUESTO` (el aviso ya existe en core) con el cruce de lecturas · reextraer `scan_023` y `scan_025` · quitar el motivo falso `"None"` | Cierra el último hecho falso de la Caja |
| 09:15-13:00 | Alejandro | **Consola**: escalados con evidencia, traza de una decisión, panel | Es lo que se ve en la demo; hoy no existe |
| 10:00-10:30 | Mónica | Preguntas a los mentores: NO_PAGAR vs ESCALAR · dos facturas del mismo pedido · documento superpuesto | Los mentores están por la mañana |
| 10:30-12:30 | Mónica | Decidir las 9 políticas del dossier + tests en `tests/test_rules.py` | Sin esto, la norma v4 de la tarde se hace a ciegas |
| 11:00-13:00 | Alfonso | PDF: arquitectura, flujo de datos, observabilidad, escala y coste (cifras de `ESCALA-10K.md`) | 35 puntos |
| 13:00-14:00 | todos | Comer | |
| 14:00-15:00 | Javier + Alfonso | **Preparar el portátil de la demo**: copiar `dist/albertitos.db` (BD + caché) al de Alfonso, `make console`, `trace`, guion entero sin red | La demo corre ahí y nadie lo ha probado |
| 15:00-16:30 | todos | **Ensayo completo 2/2/4/2** con cronómetro; anotar lo que falle | Un ensayo malo hoy vale más que otro arreglo |
| 16:30-17:30 | Javier + Alejandro | **Bonus**, sólo si lo anterior está verde: calendario de vencimientos (30/45/60 días del maestro) + fichero de remesa para los PAGAR | +10 pts; debe estar implementado y enseñado |
| **17:30** | Miguel | **ENTREGA DE SEGURO** (`/entrega`): primer push al repo `HS-Maisa-Entrega` (vacío: `git push -u origin HEAD:main`) | Es la primera vez; hacerlo con calma y antes del lote 2 |
| **18:00** | todos | **LOTE 2**: Javier (hashes, `caja verify --lote 2`, ingest, extract, ERP v2, diff, inventario `--con-hechos`) → Mónica (regla nueva → `norma_v4.py` + tests) → Miguel (`reprocess --impacted --norma v4 --erp v2` + `package`) | Runbook `/lote2` ensayado: ~15 min de pipeline |
| 19:30-20:30 | todos | Cenar por turnos; **20:00 repliegue**: si el lote 2 no está procesado, se cancela el bonus | `docs/hitos.md` |
| 20:30-22:00 | Miguel + Javier | Segunda entrega con `outcomes_lote2.jsonl` · ensayar el cambio en vivo (`reprocess --impacted` < 30 s) | El domingo cambian un dato delante del tribunal |
| 22:00-00:00 | Alfonso | PDF final con los ADRs elegidos (2-5) y las cifras del lote 2 | |
| 00:00-01:30 | todos | Ensayo final con datos reales del lote 2 | |
| **02:00 domingo** | todos | **Congelación de funcionalidad**. Sólo docs, ensayo y arreglos de NO APTO | |
| 08:00 domingo | Miguel | **Entrega final** y commit anotado en `docs/entregas.log` | |
| 10:30 / 11:00 | — | Cierre interno / la organización clona y registra el commit | |

## Antes de tocar el lote 2, sin falta
1. **Limpiar de la BD los ficheros `L2-%`** del lote simulado (paso 0 de la skill `/lote2`). Anoche, sin esa limpieza, el detector de duplicados marcó como duplicados a los originales del lote 1: 20 decisiones tocadas.
2. **Ejecutar `run` entero**, no pasos sueltos: `marcar_duplicados` sólo corre dentro de `run` y por eso estuvimos pagando dos veces `PO-2026-0492`.
3. Comprobar el hash del zip contra el canal.

## Riesgos vivos
- **La consola no existe todavía** y es el minuto 0-2. Si a las 20:00 no enseña una traza, la demo se hace con `trace` en terminal (repliegue ya previsto).
- **Nadie ha ejecutado nada en el portátil de Alfonso.** La caché del LLM vive en la BD de Javier: sin copiarla, la demo intentaría llamar al proveedor y podría quedarse colgada sin red.
- **El lote 2 puede traer muchas escaneadas**: la visión va a 0,065-0,106 facturas/s con doble lectura. 40 escaneadas serían ~7-10 minutos. Lanzar `extract` antes de ponerse con la norma v4.
- **`scan_025`** sigue escalando por un motivo falso hasta la tarea de las 09:15.
