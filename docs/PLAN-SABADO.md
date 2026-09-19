# Plan del sábado 19/09 · de dormir a la entrega de seguro y al lote 2

**Estado a las 09:50** (actualiza el de la noche): `javier/ingesta` con **392 tests verdes** y 24 commits por delante de
`main`. **La entrega de seguro ya está publicada** (`fdc76e8`, 500 líneas, 443/48/9). **Lo que queda, con dueño y hora
límite, está en `docs/ESTADO-BACKEND.md`**. Resumen:

## Lo que está hecho y lo que no

| Bloque | Estado |
|---|---|
| Ingesta, norma v3, pipeline, linaje, resiliencia, escala y coste | **hecho y ensayado** |
| Entrega de seguro | **hecho** a las 07:10 (`make publicar`), antes de la hora prevista |
| Contingencia para PDFs del lote 2 sin hechos (ADR-0009) | **hecho y aceptado** |
| Kit de la demo para el portátil de Alfonso | **hecho** (enviado a las 09:05) |
| **PDF idéntico con otro nombre en el lote 2** (P0-1) | **pendiente · Miguel** — hoy no tiene salida: la ingesta lo sobrescribe o el verificador lo bloquea |
| **¿La entrega final del lote 1 lleva la regla nueva y el ERP v2?** (P0-2) | **pendiente · Mónica con los mentores** |
| **`scan_025` / auditoría en rojo** (P0-3) | **pendiente · Mónica** (respuesta A) |
| **Auditoría dentro de `package`** (P0-4) | **parche listo** (G1) · falta `--aceptar-rojo` de Miguel o la auditoría en verde |
| **Consola (3 vistas)** | **andamiaje del viernes** · Alejandro no ha subido cambios |
| **PDF del plan (35 pts)** | **a medias · Alfonso** · la línea 98 tiene una cifra falsa |
| **Muestra etiquetada a mano** | **0 de 21** · Mónica + Alfonso |
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

## Riesgos vivos (09:50)
- **Un PDF idéntico renombrado en el lote 2** nos deja NO APTO en cualquiera de los dos caminos (P0-1). Es lo más grave
  de lo que queda y lo tiene que resolver Miguel antes de las 17:00.
- **No sabemos si el lote 1 final va con la regla nueva** (P0-2). Rehacerlo cuesta 7 s; no saberlo cuesta la entrega.
- **La consola sigue siendo el andamiaje.** Funciona con datos, pero no enseña bien la traza. Repliegue a las 20:00.
- **Mónica y Alfonso no han subido nada hoy**: la muestra etiquetada y el PDF (35 pts) son los dos que más esperan.
- Sin cambios: el lote 2 puede traer muchas escaneadas (0,065-0,106 f/s): hay que lanzar `extract` antes que la norma v4.
