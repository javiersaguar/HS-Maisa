# Estado del proyecto y lo que falta · domingo 20/09, 10:35 (repaso previo a la defensa)

Lo de las 01:00 y lo de ayer está en el historial (`git log -p docs/ESTADO-BACKEND.md`).
**La entrega ya está publicada y cierra a las 11:00. Lo de abajo es lo que se enseña y con qué repliegue.**

## 0 · Repaso de las 10:35, medido

| Qué | Resultado |
|---|---|
| Raíz de `../HS-Maisa-Entrega` | ✅ exactamente `.git`, `outcomes.jsonl`, `outcomes_lote2.jsonl`, `albertitos_plan.pdf` |
| `validate` lote 1 / lote 2 | ✅ **APTO** 500 líneas (445/46/9) y **APTO** 40 líneas (23/1/16), en 0,9 s y 0,2 s |
| Elegibilidad | ✅ 540 `file_id` = los 540 PDF, en NFC, sin repetidos; `result` siempre PAGAR/NO_PAGAR/ESCALAR |
| `albertitos_plan.pdf` | ✅ 4 páginas, «1. Arquitectura» y «2. ADRs / trade-offs», ADR-0001/0006/0017/0021/0022; sin «(rellenar» ni «ADR-000N» |
| Subagente `auditor-outcomes` | ✅ **VERDE**, 0 discrepancias con la BD; las 31 facturas con texto inyectado, ninguna en PAGAR |
| `make check` · enlaces · cifras | ✅ 718 passed · sin enlaces rotos · sin cifras obsoletas |
| `scripts/smoke.sh` | ✅ **VEREDICTO: OK**, 6 comprobaciones, **1,4 s** |
| `scripts/demo.sh estado` | ✅ los seis endpoints en 200 (local < 10 ms, público 0,23-0,36 s) |
| `dato_en_vivo.py --pagada PO-2026-0003` | 🟠 funciona en **0,2 s**, pero cambia **2** facturas, no 1 (ver §2 R2) |
| `demo_caos.py --sin-red` | 🔴 **no demuestra nada desde el lote 2** (ver §2 R1) |
| Ventana del chat local | ✅ movida a las **20:00** de hoy (`CHAT_HASTA=2026-09-20T20:00 bash scripts/demo.sh arrancar`) |
| Ventana del chat público | 🔴 cierra hoy a las **14:00**; lo cambia Javier en Render (ver §2 R3) |

## 1 · Dónde estamos, en una frase por área
| Área | Estado | Evidencia |
|---|---|---|
| **Entrega, los dos lotes** | ✅ Publicada `d2ade3f` (20/09 00:17): `outcomes.jsonl` 500 (**445/46/9**) + `outcomes_lote2.jsonl` 40 (**23/16/1**) + `albertitos_plan.pdf`. Auditoría VERDE | `docs/entregas.log` |
| **Lote 2 integrado** | ✅ 40 facturas: maestro con los CSV nuevos (15 proveedores, 555 pedidos), ERP v2 (556 asientos) y norma v4 | `docs/agentes/lote2/EXTRACCION.md` |
| **Lote 1 al día** | ✅ ADR-0017 aplicado: 7 escaneadas legibles pasan de ESCALAR a PAGAR (438→445). Etiquetado a ciegas de Miguel: 26/26 frente a 23/26 | ADR-0017 |
| **Extracción del lote 2** | ✅ 40/40, 23 por plantilla y 17 por LLM. Fechas en 7 idiomas, 8 monedas leídas, 3 manuscritas marcadas | `data/fixtures/hechos_lote2.jsonl` |
| **Subir facturas por la consola** | ✅ Probado con 6 PDF reales de los 3 resultados y de los 2 lotes; decide con la norma de la BD y enseña cada importe en su divisa | `EXTRACCION.md` §2 |
| **Demo pública** | ✅ `https://albertitos.vercel.app` (Vercel) contra Render, de sólo lectura. Prueba de jurado en Chromium limpio: **12/12**, chat incluido. No se duerme: workflow cada 10 min | ADR-0023 · `deploy/README.md` |
| **Demo local** | ✅ `bash scripts/demo.sh arrancar` levanta puente, chat y consola (3002/8000/8101) sobre una copia | `KIT-DEFENSA.md` |
| **Resiliencia (10 pts)** | ✅ Demo sin red, breaker, contingencia, y el «cambia un dato» **arreglado** tras el ADR-0021 (`dato_en_vivo.py --lote`) | `KIT-DEFENSA.md` |
| **Trazabilidad (20 pts)** | ✅ `trace` legible y la consola; cada decisión guarda norma, maestro, ERP y fecha de corte | consola · `trace` |
| **Código en `main`** | ✅ 702 tests en verde. Ramas del lote 2 (fuentes y extracción) integradas | `make check` |
| **Divisas** | 🟠 Las 8 facturas en divisa **escalan**: sin tabla de cambio oficial no convertimos (ADR-0022). Ver §2 A | `EXTRACCION.md` §3 |
| **La norma v4 (Mónica)** | 🔴 **Sin revisar por ninguna persona.** La escribió Miguel anoche | ADR-0022 |
| **Plan PDF (35 pts, Alfonso)** | 🔴 El publicado es el de ayer por la mañana; no incluye el lote 2, las divisas ni los ADR 0017-0023 | `docs/plan/albertitos_plan.md` |
| **Guion de la defensa** | 🔴 Sin tocar desde el viernes. Alfonso está grabando la demo esta noche | `docs/guion-defensa.md` |

## 2 · Lo que falta, por orden de lo que nos cuesta si no se hace

### 🔴 R1 · `demo_caos.py` ya no demuestra la resiliencia (bloque 4 de la defensa, 10 pts)
Desde que entró el lote 2, **los tres pasos de la demo del caos acaban en `run → exit 2`**: `run` se niega porque
el lote 1 está decidido con la v3 y el ERP v1 y el lote 2 con la v4 y el ERP v2 (ADR-0021, y hace bien). Las tres
facturas nuevas salen con «decisión: NINGUNA» en los pasos 1 y 2, así que no se ve caer el LLM ni reanudar: se ve
una negativa por otro motivo. El guion dice «mira, se cae el LLM y el pipeline reanuda», y lo que se proyecta no
es eso. **No lo he tocado** (`scripts/demo_caos.py` no es mío). Arreglo previsible: que la demo use
`reprocess --impacted --lote 2 --norma v4 --erp v2` o que fije `--lote 1`, como ya se hizo con `dato_en_vivo.py`.
**Repliegue para hoy si no da tiempo:** enseñar el corte de LLM con `scripts/smoke.sh` y la contingencia de
ADR-0009, y no proyectar `demo_caos.py`.

### 🟠 R2 · «Cambia un dato» cambia dos facturas, no una
`uv run python scripts/dato_en_vivo.py --pagada PO-2026-0003` recalcula **2 de 500 en 0,2 s** y cambian las dos:
`factura_8764` (la del dato que toca el jurado) y `factura_4635`, que cambia por `AS-90001` del **ERP v2 del lote
2**, no por lo que acaba de tocar nadie. El guion cuenta «1 de 500». La causa: el guion construye el ERP «vivo»
desde el último snapshot (v2) y el lote 1 se decidió con el v1. **Tampoco lo he tocado** (`scripts/dato_en_vivo.py`
no es mío). **Repliegue inmediato, probado:** hacerlo sobre el lote 2, que sale limpio —
`uv run python scripts/dato_en_vivo.py --lote 2 --norma v4 --pagada PO-2026-0517` → **1 de 40 recalculadas, 1
cambia**, `2026-08-26_P010.pdf` PAGAR → NO_PAGAR por R5, con su traza.

### 🔴 R3 · La ventana del chat público cierra a las 14:00
`https://albertitos-chat.onrender.com/chat/salud` dice `ventana.hasta = 2026-09-20T14:00:00+02:00`. Si la defensa
se alarga, el chat de la demo pública dirá «fuera de horario» en mitad de la exposición. **Lo cambia Javier en
Render** (servicio `albertitos-chat` → Environment): variable **`ALBERTITOS_CHAT_HASTA`**, valor
**`2026-09-20T20:00`**. Se confirma con `curl -s https://albertitos-chat.onrender.com/chat/salud`. El chat local ya
está hasta las 20:00.


### 🔴 A · Preguntar a los mentores por las divisas y el IVA · Mónica (o quien pille a un mentor)
**Se juegan 5 facturas de 540, y la validación es binaria.** Las ocho en divisa escalan hoy por dos motivos: no
convertimos (no hay tabla de cambio) y nuestra R3 exige un 21 % que la norma del Excel no pide («el IVA debe estar
bien calculado»). Siete de ellas facturan al 0 % declarando exportación.
1. ¿Hay tabla de tipos de cambio oficial? Si no, ¿vale el tipo fijo con el que cuadran los pedidos? (El mismo tipo
   sale en facturas de fechas distintas y convertido cuadra al céntimo con el pedido y con el ERP.)
2. Una factura de exportación con **IVA 0 %** que, convertida, cuadra con el pedido y con el ERP, ¿es PAGAR o ESCALAR?
3. La regla 3, ¿es «IVA bien calculado» o «siempre 21 %»?

Medido: si la respuesta fuera «convertir y aceptar el 0 % de exportación», **cambiarían 5** (`e02`, `e10`, `e12`,
`e13`, `e15`, todas de ESCALAR a PAGAR). `e09`, `e11` y `e14` escalan igual, por IVA incoherente, IBAN cambiado y
cuentas que no cuadran. Hoy estamos en la opción conservadora, que es la regla 6 de la norma de Alberto.
Las respuestas, **literales y con hora**, en `docs/hitos.md`. Lo demás sigue abierto desde ayer: frontera
NO_PAGAR/ESCALAR, pedido ANULADO y copias exactas.

### 🔴 B · El PDF del plan (35 pts), antes de las 08:00 · Alfonso
- Contar el lote 2: las 40, la norma v4 y la regla de moneda, el ERP v2 y el maestro con los CSV.
- Elegir 2-5 ADRs de los 23. Propuesta: 0001 (el LLM extrae, la norma decide), 0006 (linaje), 0017 (desacuerdo entre
  lecturas), 0021 (cada lote en su contexto) y 0022 (divisas detrás de su regla).
- `uv run python scripts/cifras_check.py`, `make plan-pdf` y **republicar**, que el PDF entra en la entrega.

### 🟠 C · La defensa · Alfonso (+ todos)
- Guion 2/2/4/2 al día: consola, traza, bloque 4, dato en vivo, bonus y ahora el lote 2.
- Demo: la pública (`albertitos.vercel.app`) o la local (`scripts/demo.sh arrancar`). La local no necesita red; la
  pública, sí, pero se abre desde cualquier ordenador.
- Cronometrar en el portátil de Alfonso.

### 🟡 D · Operación · Javier
- **Republicar si cambia algo** (norma, PDF): `reprocess --impacted --lote 2 …`, `package`, auditoría y
  `make publicar ARGS=--publicar`. Se puede hasta las 11:00. Después, reexportar la demo pública
  (`scripts/exportar_demo_db.py`), commit y push.
- **Antes de salir:** `bash scripts/smoke.sh` y `bash scripts/demo.sh estado`.
- Rotar la clave del gateway después del hackathon: está como secreto en Render.

### 🟢 E · Sabido y sin arreglar (no bloquea la entrega)
- **El chat contestó «no he podido verificar las citas»** a una pregunta global («¿cuántas facturas hay en el lote
  2?»): citó algo que las herramientas no le devolvieron. Es el guardarraíl funcionando, pero queda raro en vivo.
- **La bandeja no marca duplicados:** llama a `decide`, no a `reprocess`. Una copia idéntica sí se detecta por su
  huella; una reemisión con otro pedido, no.
- **Al releer `e10_P006.pdf`**, el modelo marcó como sospechosa la línea de la divisa, que no ordena nada. No afecta
  a lo entregado (las 31 con instrucción son reales), pero en una demo en vivo podría escalar una limpia.
- **Jev (TypeSafe):** evaluado y descartado, sin ADR escrito (`docs/agentes/ANALISIS-JEV.md`).

## 3 · Calendario que queda
| Hora | Qué | Quién |
|---|---|---|
| **noche** | Grabar y editar la demo (la pública está despierta y probada) | Alfonso |
| **08:00** | Entrega final: ya está publicada; sólo se republica si cambia la norma o el PDF | Javier / Miguel |
| 09:00 | Mentores: divisas e IVA. Si cambia, reprocesar y republicar | Mónica |
| 10:30 | Cierre interno (oficial 11:00). Última ventana para publicar | todos |
| defensa | 2/2/4/2, con el bloque 4 ensayado (`KIT-DEFENSA.md`) | Alfonso |
