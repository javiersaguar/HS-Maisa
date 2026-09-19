# ADR-0011 · Una lectura reconciliada con el maestro no se paga sola

- **Estado:** aceptado
- **Número:** escrito como ADR-0010 en la rama de Mónica (commit `d18ee3d`); renumerado al mergear (el 0009 ya era la contingencia).
- **Fecha:** 2026-09-19 09:40 · **Dueño:** Mónica · **Módulos:** rules/ (consecuencia para core/)

## Contexto
Las 29 facturas sin capa de texto se leen dos veces con visión. Cuando las dos lecturas discrepan, el
ADR-0003 decidió que no gane el modelo: gana la lectura respaldada por el maestro del Excel y por el
proveedor del pedido. El hecho queda con `confianza = 0,6` y las dos lecturas en la traza.

Seis ficheros quedaron así. Uno, `fax_2026_0411.pdf`, ya escala por `discrepancia_extractores`. Los otros
cinco — `scan_006`, `scan_009`, `scan_011`, `scan_012`, `scan_017` — pasaban las seis reglas y **se pagaban**.
La auditoría de entrega los sacaba en ámbar (`pagar_con_confianza_baja`) y era lo que faltaba para aceptar
el ADR-0003.

El problema no es la confianza baja en abstracto, es qué campo se reconcilió. En `scan_006`, `scan_012` y
`scan_017` se reconcilió el **NIF**, y ahí hay corroboración real: el pedido del Excel dice de forma
independiente qué proveedor debería ser. En `scan_009` y `scan_011` se reconcilió el **IBAN**, y ahí el
razonamiento se muerde la cola: se eligió ese IBAN porque coincide con el del maestro, que es exactamente
lo que comprueba la R1. Para esos dos ficheros **la R1 no puede fallar nunca**, y el IBAN es el campo que
decide a dónde va el dinero.

## Alternativas consideradas
1. **Ratificar: se pagan** — el ADR-0003 se acepta tal cual. Se descarta: en dos de los cinco, la regla que
   debería cazar el error está neutralizada por la forma en que se obtuvo el dato.
2. **Escalar sólo los dos del IBAN** — es lo que mejor encaja con la evidencia de cada fichero, pero es una
   regla más fina de explicar y de testear, y obliga a que la norma sepa qué campo se reconcilió, dato que
   hoy no llega en los hechos. Se descarta por coste y por superficie de error.
3. **(elegida) Las cinco a ESCALAR** — si el extractor admite que no está seguro, la duda la resuelve una
   persona. Es el principio escrito del módulo: ante duda razonable, escalar.

## Decisión
Un hecho con `confianza` por debajo de `CONFIANZA_MINIMA = 1.0` es una anomalía que debe ver una persona.
Se implementa en `regla_6_anomalias` de `src/albertitos/rules/norma_v3.py`: la R6 falla, con la confianza
en la evidencia y el motivo "la lectura del documento no es firme". Los hechos sin `confianza` (los 471 con
capa de texto) no se ven afectados.

## Consecuencias aceptadas
- Cinco ESCALAR más para Alberto. Si la referencia privada esperaba PAGAR en esos cinco, los perdemos; el
  riesgo simétrico —pagar a un IBAN reconstruido— nos pareció peor.
- **Aviso para Miguel, y es de contrato:** `confianza` está en la lista de campos excluidos de
  `InvoiceFacts.hash()` (`core/contracts.py`), junto a `metodo`, `extractor_version` y `texto_sospechoso`.
  Desde este ADR la decisión **sí** depende de `confianza`, así que un hecho reextraído que sólo cambie la
  confianza no cambia el `hechos_hash` y el linaje no marcará la decisión para recalcular. Hoy no muerde
  porque el cambio de norma obliga a reprocesar de todos modos, pero el invariante "si cambia lo que decide,
  cambia el hash" está roto mientras siga excluido.
- Como el ADR-0010, es un cambio in situ sobre la v3: la etiqueta de versión no cambia y hay que reprocesar
  explícitamente.

## Evidencia
- Medido en memoria sobre los 500 hechos de `data/fixtures/hechos_caja.jsonl`, con el maestro del Excel y
  un snapshot del ERP local, sin tocar la BD ni la entrega: sin la política **443 PAGAR · 48 ESCALAR ·
  9 NO_PAGAR** (reproduce el reparto de referencia del equipo), con la política **438 · 53 · 9**.
- Cambian exactamente cinco ficheros, todos PAGAR → ESCALAR: `scan_006`, `scan_009`, `scan_011`, `scan_012`,
  `scan_017`. Hechos con `confianza < 1`: seis; el sexto, `fax_2026_0411.pdf`, ya escalaba por otra regla.
- Tests: `tests/test_rules.py::test_lectura_reconciliada_no_se_paga` y `::test_frontera_confianza`
  (confianza 1.0 y None siguen pagando).
- Política nº 2 de `docs/agentes/DECISIONES-NORMA.md`; ámbar `pagar_con_confianza_baja` de
  `scripts/auditoria_entrega.py`.
