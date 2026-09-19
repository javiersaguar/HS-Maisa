# Qué queda del backend para terminar · sábado 19/09, 09:50 (actualizado 10:15)

**Resumen.** El backend hace todo lo que la entrega exige y está ensayado. Con los datos de hoy, 500 de 500 facturas
tienen decisión (**438 PAGAR · 53 ESCALAR · 9 NO_PAGAR** desde las decisiones de Mónica) y la entrega publicada es la
`232bb76` (10:07, auditoría en verde). El lote 2 se
ha ensayado entero dos veces. `make check` pasa con 392 tests. Lo que queda **no es construir el sistema**, sino
cuatro agujeros que pueden dejarnos NO APTO y una lista de mejoras que valen puntos en la defensa.

**10:15:** `main` = `javier/ingesta` (merge de Mónica incluido); las ramas de Mónica y Alfonso, avanzadas al mismo
punto. Alfonso y Alejandro no han subido nada todavía hoy.

## 1 · Lo que puede dejarnos sin premio (P0)
Por orden de hora límite. Ninguno es mucho código; todos dependen de una decisión o de una persona concreta.

| # | Qué | Por qué es P0 | Quién | Antes de |
|---|---|---|---|---|
| **P0-1** | **PDF idéntico con otro nombre** (misma sha256, distinto `file_id`), dentro del lote 2 o repetido del lote 1 | `ficheros` tiene la sha256 como clave: la ingesta **sobrescribe el `file_id` y el lote del original**. El lote 1 pierde una línea → NO APTO. `verificar_material` lo detecta y **se para**, pero entonces ese PDF del lote 2 no tiene línea → NO APTO igual. Hoy no tiene salida. En el lote 1 no hay ningún caso (500 sha256 distintas), así que nunca se ha probado. Una «factura duplicada» exacta es una trampa muy plausible en el lote 2 | **Miguel** (`core/` + ingest) · política: **Mónica** | 17:00 |
| **P0-2** | **¿La entrega final del lote 1 va con la regla nueva y el ERP actualizado?** | Pregunta 3 de `docs/hitos.md` a los mentores, **sin respuesta desde el viernes**. Si la respuesta es sí y no rehacemos el lote 1, la entrega queda mal hecha aunque pase el validador. Técnicamente cuesta 7 s (`reprocess --todo`, ENSAYO-REPROCESADO); lo que falta es saberlo | **Mónica** (mentores) | 18:00 |
| ~~P0-3~~ ✅ 10:07 | **`scan_025` y la auditoría en rojo** — resuelto: ADR-0010 de Mónica, reextraído y reprocesado; auditoría VERDE | Es lo único rojo, y lo arregla una línea de Mónica (respuesta A: `DOCUMENTO_SUPERPUESTO` en `ANOMALIAS_HUMANO`). Mientras siga así: no se puede republicar sin `--aceptar-rojo`, el kit de la demo enseña un motivo falso y no se puede activar la auditoría dentro de `package` | **Mónica** → Miguel mergea → **Javier** aplica a la BD real (final de `AUDITORIA-ENTREGA.md`) | 12:00 |
| ~~P0-4~~ ✅ 10:05 | **La auditoría no para `package`** — resuelto: la puerta de G1 está activada (`c2a8e58`); falta sólo, como seguro, el `--aceptar-rojo` de Miguel | Miguel dejó el hueco y G1 el módulo (`dist/ensayo/g1/puerta-auditoria.patch`: 394 tests en verde en un clon). No se puede activar hasta que (a) la auditoría real salga verde (P0-3) **o** (b) `package` tenga `--aceptar-rojo "<motivo>"` (parche en la bitácora, G1 09:05). Sin él, una puerta roja a las 07:55 del domingo no tiene salida | **Miguel** (b) · **Javier** aplica el parche | 17:00 |

**Ya cerrado y ensayado:** la contingencia para un PDF del lote 2 sin hechos (ADR-0009, aceptado; `scripts/contingencia.py`,
13 tests y ensayo de punta a punta) y la entrega de seguro. Ya no hace falta pensar en ellas.

### P0-1 en detalle (para Miguel)
Requisitos, sin imponer el diseño:
1. Ingerir un PDF cuya sha256 ya existe con otro `file_id` **no toca la fila original** (ni `file_id` ni `lote`).
2. Cada `file_id` recibido tiene **su línea** en el JSONL de su lote, y `validate` lo acepta.
3. La copia **nunca sale PAGAR si el original sale PAGAR**: sería pagar dos veces la misma factura, lo único que la
   norma prohíbe por escrito. Lo coherente con la política de duplicados vigente es que las dos queden en ESCALAR,
   con un motivo que nombre a la pareja. Lo confirma Mónica.
4. `verificar_material` deja de bloquear ese caso y pasa a avisar (es de Javier; se cambia cuando exista 1-3).
5. Tests: la copia en el mismo lote, la copia entre lotes, y que `reprocess` y `package` no pierdan ninguna de las dos.

Una forma barata (tabla aditiva `CREATE TABLE IF NOT EXISTS`, sin migración): `identidades(file_id PK, sha256, lote)`.
Ingest escribe ahí las identidades extra y `package` emite una línea por identidad, con la decisión del sha256
reforzada a ESCALAR si tiene más de una. Es decisión de Miguel.

## 2 · Lo que da puntos en la defensa (P1)

### Trazabilidad (20 pts) · Miguel
Todo está pedido en la bitácora con el parche escrito; nada cambia resultados.
| Qué | Estado | Dónde |
|---|---|---|
| `erp pull` sin ERP: una línea en vez de 92 de traceback | la parte de `sources/` está hecha (G2); falta capturar `ErrorERP` en `cli.py` (5 líneas) | bitácora, G2 «ERP medido» |
| La línea del ERP en `trace`: «ERP v1 · 516 asientos · 31 consultas · 3 reintentos (ORA-00600×3)» | `sources.snapshot.resumen_erp` hecho (G2); falta una línea en `trace` | ídem |
| `trace` nombra la pareja del duplicado (`PO-2026-0492`) | pendiente | F2, punto 4 |
| `trace --legible`: hechos → maestro → ERP → reglas → resultado, en vez de JSON escapado | pendiente | F2, punto 2 |
| El porqué del linaje también en las decisiones de `decide`/`run` | pendiente | F2, punto 5 |
| `status` sin el histórico que asusta (`extract pendiente 7` antiguos, 2,38 € de ayer) | pendiente; el hook de inicio ya lo cuenta bien | F2, punto 6 |

### Consola · Alejandro
Funciona con datos (F2: 500, 443/48/9, sin excepciones), pero **sigue siendo el andamiaje del viernes**. Hay dos
peticiones: la decisión vigente arriba y el historial plegado (hoy la vigente es la última de seis), y el panel sin
los 2,38 € históricos. Repliegue de `docs/hitos.md`: a las 20:00, si no enseña una traza, la demo va por terminal.

### La norma · Mónica (plan del día en `docs/PLAN-MONICA.md`)
~~Respuesta B~~ ✅ (ADR-0011: las 5 reconciliadas pasan a ESCALAR; ADR-0003 aceptado), muestra etiquetada (**0 de 21**), frontera NO_PAGAR/ESCALAR
con el mentor, tests de las 9 políticas (hoy hay 7 tests de reglas) y `norma_v4.py` a las 18:00.

### Contrato de la norma · Miguel y Mónica (de su subida de las 10:00)
- **`confianza` fuera de `InvoiceFacts.hash()`** (lo pide Mónica): desde el ADR-0011 la decisión depende de ella. El
  riesgo real es menor de lo que parece: el linaje ya recalcula cuando los hechos se reescriben después de decidir,
  aunque el hash sea igual («hechos reescritos tras decidir», `test_evidencia_nueva_con_el_mismo_hash_tambien_se_redecide`).
  Meterla en el hash es lo limpio, pero cambia **todos** los `hechos_hash` y obliga a un `--todo` (7 s). Decide Miguel;
  si se hace, antes de las 17:00, no durante el lote 2.
- **Cambios in situ en la v3.** Los ADR-0010 y 0011 cambian el comportamiento sin cambiar la etiqueta `v3`: el linaje no
  los ve (ADR-0006) y hubo que hacer `reprocess --todo`. En la traza, dos decisiones «v3» distintas del mismo fichero
  sólo se distinguen por el motivo del recálculo. Propuesta: **el próximo cambio de comportamiento sube la etiqueta**
  (`v3.1`), y la regla nueva de las 18:00 va, como estaba previsto, en `v4`.

### Plan PDF (35 pts) · Alfonso
- `docs/plan/albertitos_plan.md:98` dice «reprocesar 500 decisiones, 0,04 s»: es falso (0,04 s fueron 2 de 500; las 500,
  0,11 s). `uv run python scripts/cifras_check.py` tiene que decir OK.
- Elegir los 2-5 ADRs. El ADR-0009 (contingencia) es buen candidato: responde a «¿y si el LLM no vuelve?».
- Todas las cifras, de `docs/CIFRAS.md`.

## 3 · Deseable (P2)
| Qué | Quién | Nota |
|---|---|---|
| `run --erp <versión>` explícito | Miguel | Hoy `run` usa el último snapshot, que tras `erp pull --tag v2` es el v2. El preflight vigila cuál se usaría |
| `regla_5_erp` reconstruye `por_pedido()` en cada factura | Mónica/Miguel | 28 ms/factura con 50k asientos; a 540 facturas no se nota |
| `ALBERTITOS_BREAKER_FALLOS`/`_SEGUNDOS` en `.env.example` | Miguel | Los agentes no pueden leer ese fichero; comprobarlo a mano |
| Bonus (+10): calendario de vencimientos y fichero de remesa | Javier + Alejandro | Sólo si P0 y P1 están verdes a las 16:30; se cancela a las 22:00 si el lote 2 no está hecho |

## 4 · Lo de Javier hoy
1. ~~Arreglo de `scan_025`, auditoría verde, publicar, kit nuevo, puerta de G1~~ ✅ 10:07 (entrega `232bb76`, kit
   `albertitos-kit-20260919-1007.tar.gz`). **Falta pasarle el kit nuevo a Alfonso.**
2. **Con P0-1 hecho por Miguel:** cambiar `verificar_material` para que avise en vez de bloquear, y ensayarlo con una
   copia exacta renombrada dentro del lote 2 simulado.
3. **15:00:** ensayo de la defensa en el portátil de Alfonso (kit, chuleta `docs/agentes/KIT-DEFENSA.md`).
4. **18:00, lote 2 (skill `/lote2`):** hashes → `verificar_material` → ingest → extract (primero las escaneadas, que
   son lo lento: 0,065-0,106 f/s) → `erp pull --tag v2` → diff → inventario. Después: la v4 de Mónica →
   `reprocess` → auditoría → `make publicar`. Contingencia sólo si a la hora de entregar queda algún PENDIENTE.

## 5 · Hecho (para no volver a mirarlo)
| Bloque | Evidencia |
|---|---|
| Ingesta: 500/500, 468 por plantilla, 29 por visión con doble lectura, contraste 468/468 | CONTRASTE-TOTAL, CIFRAS.md |
| Norma v3 con evidencia completa, duplicados detectados, `DOCUMENTO_SUPERPUESTO` emitido | DECISIONES-NORMA, E2 |
| Pipeline todo o nada, reprocesado por linaje (40 de 500 en 0,78 s; las 500 en 7 s) | ENSAYO-REPROCESADO |
| Resiliencia: caída, 429, respuesta inválida, timeout, breaker, respaldo; demo sin red (~4 s) | RESILIENCIA-Y-COSTE §3 |
| El fallo del LLM dice qué modelo falló y si se probó el respaldo | `extract/llm.py`, 19/09 09:40 |
| Escala y coste medidos (10.000 facturas) | ESCALA-10K, CIFRAS.md |
| Entrega: `make publicar` con la auditoría como puerta; entrega de seguro publicada | `docs/entregas.log` |
| Preflight del lote 2, verificador de material, auditoría de entrega, contingencia | E1, E3, E2, G1 |
| Kit de la demo instalable en otro portátil, probado en un clon limpio | KIT-DEFENSA, F2 |
| ERP: error de una línea, reintentos por snapshot; catálogo de cifras con fuente | CIFRAS.md, G2 |
| ADRs 0001-0009 (0009 aceptado) | `docs/adr/README.md` |
