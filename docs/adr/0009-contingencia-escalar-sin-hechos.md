# ADR-0009 · Si a la hora de entregar no hay hechos, ESCALAR explícito y reversible

- **Estado:** aceptado (19/09 09:00). Miguel, dueño de `pipeline/`, dijo sí con cuatro condiciones (C1-C4, en
  Decisión); Mónica, dueña de la norma, dijo sí después. Se aplica sólo al lote 2, a la hora de entregar y si hace falta.
- **Fecha:** 2026-09-19 09:10 · **Dueño:** Javier (agente G1) · **Módulos:** `scripts/contingencia.py`,
  `scripts/auditoria_entrega.py`, skill `/lote2`

## Contexto
La validación es binaria: un outcome por cada PDF, **540 de 540**, o no hay premio. `package` se niega a escribir un
JSONL si a un solo fichero le falta la decisión vigente. Es la regla 6 (nunca se paga sin hechos validados) y es
correcta.

Pero el lote 2 llega el sábado a las 18:00 y la entrega final es el domingo a las 08:00. Si a esa hora un PDF
sigue PENDIENTE, no hay `outcomes_lote2.jsonl` y la entrega entera es NO APTA. Motivos posibles: el proveedor
del LLM caído, una escaneada que no se deja leer o un 429 que no se va. Lo que sabemos del proveedor:
- la visión va a 0,065-0,106 facturas/s (ESCALA-10K §4);
- hubo colas de 94 s (RESILIENCIA §4);
- los modelos frontier devuelven 402 (ADR-0004);
- no hay respaldo de visión, a propósito (ADR-0004).

Hoy la única salida sería escribir líneas a mano. El hook lo bloquea, con razón: no dejaría traza ni se podría
deshacer.

## Alternativas consideradas
1. **No entregar el lote 2, o entregarlo incompleto.** Se descarta: es NO APTO seguro.
2. **PAGAR por defecto.** Se descarta: es exactamente lo que la regla 6 prohíbe, pagar sin hechos.
3. **NO_PAGAR por defecto.** Se descarta: NO_PAGAR afirma una violación comprobada (el pedido ya pagado), y aquí
   nadie ha comprobado nada. Además, no es lo que haría Alberto con una factura que no ha podido leer.
4. **Escribir las líneas a mano en el JSONL.** Se descarta: el hook lo bloquea, no queda en la BD, `trace` no lo
   cuenta y nada lo deshace.
5. **ESCALAR explícito, registrado y reversible (elegida).** Es lo que la norma haría con una factura que nadie ha
   podido leer: que la vea una persona.

## Decisión
`scripts/contingencia.py --lote 2` enseña, en seco, los ficheros sin decisión vigente y sus intentos de extracción.
Con `--aplicar --motivo "…"`, a cada uno le guarda:
- una `Decision` **ESCALAR**, con `hechos_hash="sin-hechos"`;
- un único Motivo `contingencia.C1` con `ok=False` y el detalle «sin hechos validados a la hora de entregar
  (<error>): lo revisa una persona»;
- la norma, el maestro, el ERP y el corte en vigor, los mismos que usa `decide`;
- un evento `decide` con `{"contingencia": true, "motivo": …}`.

Todo va en una transacción. Las cuatro condiciones de Miguel son parte de la decisión:
- **C1 · Manual y último recurso.** Ni `run` ni `package` la aplican nunca. Sólo `--aplicar --motivo`, después de
  reintentar de verdad. Se niega con el caos encendido en esa BD. Se niega con cualquier fichero que no haya tenido
  ningún intento real de extracción: los simulados llevan `caos:` en el evento, y `LLM-CIRCUIT-OPEN`,
  `LLM-PRESUPUESTO` y `LLM-CONFIG` no llegan al proveedor. En ese caso dice qué comando lanzar antes.
- **C2 · Sólo ESCALAR, sólo ficheros SIN decisión vigente y nunca en el lote 1.** Con `--lote 1` se niega siempre:
  si ahí falta algo, es otro problema.
- **C3 · Reversión por los dos caminos.** Cuando llegan los hechos, su hash real no es `sin-hechos`, así que
  `linaje.evaluar` la clasifica como «hechos cambiados». Tanto `reprocess --impacted` como `run` entero ponen
  entonces la decisión de la norma, y la contingencia queda en el historial con `vigente=0`.
- **C4 · Se ve en tres sitios.**
  - `"regla":"contingencia.C1"` en la línea que escribe `package`, porque es el único Motivo que falla.
  - El evento `decide` con `"contingencia": true`.
  - ÁMBAR en la auditoría de entrega. Además, la auditoría sale ROJA si una contingencia ya tiene hechos y nadie
    ha reprocesado.

## Consecuencias aceptadas
- **Una línea de contingencia puede no coincidir con la referencia.** Si la referencia esperaba PAGAR o NO_PAGAR
  para esa factura, esa línea falla, y no sabemos qué acepta para un documento ilegible. Se acepta porque la otra
  opción es NO APTO seguro, y porque ESCALAR es la respuesta honesta de la norma.
- **Depende de que alguien la ejecute.** Es a propósito (C1): el sistema no se inventa decisiones por su cuenta.
- **Los eventos de fallo no dicen qué modelo falló ni si se probó el respaldo.** El script lo dice así. Está
  pedido a Javier, dueño de `extract/`, que el evento lo registre.
- **La decisión no la produce la norma.** Su `regla_id` (`contingencia.C1`) no es una regla de `rules/`: queda
  claro en la traza y en la entrega que es otra cosa.
- **Reintentar de verdad cuesta minutos** el domingo por la mañana. Son minutos que hay que dejar en el plan.

## Evidencia
- **Tests** (`tests/test_contingencia.py`, 12, sin red ni LLM, con PDF reales del lote 2 simulado):
  - C1: `test_c1_sin_motivo_se_niega`, `test_c1_con_el_caos_encendido_se_niega`,
    `test_c1_sin_ningun_intento_real_no_se_toca`;
  - C2: `test_c2_solo_escalar_y_solo_a_los_que_no_tienen_decision`, `test_c2_en_el_lote_1_se_niega_siempre`;
  - C3: `test_c3_se_revierte_con_reprocess_impacted` y `test_c3_se_revierte_con_run_entero`;
  - C4: `test_c4_package_pasa_de_negarse_a_apto_y_la_linea_lo_dice`, `test_c4_el_evento_decide_lo_dice`;
  - además, en seco no escribe e idempotente.
  - En la auditoría: `test_contingencia_es_ambar_y_con_hechos_sin_reprocesar_pasa_a_rojo`.
- **Ensayo de punta a punta** (19/09, 09:05, sobre una copia de la BD real en `dist/ensayo/g1/`, con el lote 2
  simulado; salida literal en `dist/ensayo/g1/ensayo.log` y en PARTE.md, sección G1). Paso a paso:
  1. Caos `llm_down` y `extract`: las 2 escaneadas quedan PENDIENTE. `package` se niega: `✗ falta
     'L2-scan_002.pdf'`, `✗ falta 'L2-scan_004.pdf'`.
  2. Contingencia en seco: «reales 0 · simulados 1». `--aplicar` con el caos encendido → `ROJO el caos está
     encendido`.
  3. Caos apagado y proveedor caído de verdad (URL a un puerto cerrado): `errores {'LLM-RED': 2}`, 7,5 s con los
     3 intentos. En seco: «reales 1 · simulados 1».
  4. `--aplicar` → `OK 2 decisiones ESCALAR de contingencia`. Repetirlo no escribe nada.
  5. Auditoría: ÁMBAR con los dos ficheros y su motivo. El único rojo es el `scan_025` heredado.
  6. `package` → APTO 500 + 10 líneas, con `"regla":"contingencia.C1"` en las dos.
  7. Vuelven las lecturas (desde la caché, sin red), `extract` y `reprocess --impacted`: las dos contingencias
     quedan con `vigente=0` y la vigente es la de la norma (R6).
  - Cada paso de la contingencia tarda 0,15-0,17 s.
  - La BD real (`bb8128d2c656`) y `dist/entrega/outcomes.jsonl` (`5ec17aaa5045`) tienen el mismo sha256 antes y
    después.

## Resumen para el plan (5 líneas)
La validación es de 540 de 540: si a la hora de entregar un PDF del lote 2 sigue sin hechos (LLM caído, escaneada ilegible), `package` se niega y la entrega entera sería NO APTA.
Para eso hay una salida prevista y manual: `scripts/contingencia.py` decide **ESCALAR** para esos ficheros, con motivo, evento y la regla `contingencia.C1` en la línea entregada; nunca PAGAR ni NO_PAGAR, nunca en el lote 1.
Sólo se aplica tras reintentar de verdad: se niega con el caos encendido y con ficheros que no han tenido ningún intento real de extracción.
Se deshace sola: la decisión lleva `hechos_hash="sin-hechos"`, así que en cuanto llegan los hechos el linaje la recalcula, por `reprocess --impacted` o por `run`, y queda en el historial con `vigente=0`.
Ensayado de punta a punta con el proveedor caído: `package` pasa de negarse a APTO (500 + 10) y, al volver el proveedor, la norma sustituye a las dos contingencias.
