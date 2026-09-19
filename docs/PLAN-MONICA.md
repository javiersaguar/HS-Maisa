# Plan de Mónica · sábado 19/09 · la norma

**Por qué hoy depende de ti.** El sistema extrae bien 500 de 500. Que Alberto pague lo que debe **lo decide la norma**,
y la norma sólo la puedes validar tú. Tres cosas del resto del equipo están esperando una respuesta tuya:

1. **La entrega está en rojo por una sola factura** (`scan_025`), y se arregla con **una línea tuya**. Hasta entonces no
   se puede republicar la entrega de seguro, y el kit de la demo de Alfonso enseña un motivo falso.
2. **El ADR-0003 no se puede aceptar** hasta que ratifiques las lecturas reconciliadas (5 PAGAR con confianza 0,6).
3. **A las 18:00 llega una regla nueva** y la escribes tú, en `norma_v4.py`. Si llegas con la v3 sin tests y sin
   la frontera NO_PAGAR/ESCALAR decidida, la v4 se escribe a ciegas y con prisa.

Todo lo que necesitas está en **`docs/agentes/DECISIONES-NORMA.md`**: cada política con los ficheros a los que afecta
hoy y una recomendación. Decidir cuesta minutos; las pruebas las pueden escribir tus agentes.

**Regla del día:** tú decides, los agentes escriben. Ningún agente elige una política: si le falta una decisión, te
pregunta.

---

## 0 · Arranque (08:45, 5 min)
```bash
cd <tu clon de HS-Maisa> && git fetch && git switch monica/norma && git pull --ff-only
./bootstrap.sh && make check                     # 363 en verde
uv run albertitos status | head -3               # 500 ficheros · 443 PAGAR · 48 ESCALAR · 9 NO_PAGAR
```
Tu rama ya está al día con `main`. No hace falta merge, sólo el `pull`. Si no tienes `dist/albertitos.db`, pídele el
kit a Javier (`make kit-instalar KIT=<fichero>`; son 1,2 MB): sin la BD no ves las decisiones de verdad.

## 1 · Tres respuestas que desbloquean a los demás (08:50 → 09:15)
Contéstalas en el canal antes de ponerte con la muestra. Son las tres que más gente tiene esperando.

| # | Pregunta | Recomendación | Qué desbloquea |
|---|---|---|---|
| **A** | ¿`DOCUMENTO_SUPERPUESTO` entra en `ANOMALIAS_HUMANO` (una persona lo revisa)? | **Sí.** Medido por E2: sólo cambia `scan_025`, que sigue en ESCALAR pero con el motivo verdadero; 443/48/9 no se mueve. Sin tu cambio, `scan_025` pasaría a PAGAR con otra factura transparentándose por detrás | Auditoría en verde → republicar la entrega de seguro → kit nuevo para la demo |
| **B** | Las 5 escaneadas cuyas dos lecturas no coincidían y se eligió la que cuadra con el maestro (`scan_006`, `009`, `011`, `012`, `017`): ¿PAGAR o ESCALAR? | Hay argumentos para las dos. PAGAR, si te fías del cruce con maestro, pedido e importe (ADR-0003). ESCALAR, si «ante duda razonable» pesa más: son 5 facturas de 500 y ESCALAR nunca paga de más | ADR-0003 aceptado; la auditoría deja de avisar en ámbar |
| **C** | Si a la hora de entregar el lote 2 un PDF no tiene hechos (LLM caído, ilegible), ¿se decide como ESCALAR con el motivo «sin hechos validados: lo revisa una persona», registrado y reversible? | **Sí.** Sin eso, un solo PDF sin decisión = no hay `outcomes_lote2.jsonl` = NO APTO para todo. Nunca PAGAR ni NO_PAGAR | ADR-0009 (lo prepara el agente G1 de Javier) |

**Con A decidida, el cambio es tuyo y es de una línea** (el agente M1 escribe el test):
```python
# src/albertitos/rules/norma_v3.py, en ANOMALIAS_HUMANO
    Aviso.DOCUMENTO_SUPERPUESTO,  # otro documento encima o transparentándose (scan_025): lo ve una persona
```
Commit pequeño, `make check`, `/handoff`, y avisa a Miguel para que lo mergee **ya**, sin esperar al resto. Después
Javier aplica el arreglo a la BD real (comandos al final de `docs/agentes/AUDITORIA-ENTREGA.md`) y republica.

Si decides B = ESCALAR, es una regla nueva en R6, no un aviso: díselo a M1, que lo implementa con su test. Pero **no lo
mezcles en el mismo commit que A**: A tiene que llegar a `main` cuanto antes.

## 2 · La muestra etiquetada, con Alfonso (09:15 → 10:30)
Es lo único que valida la norma contra algo que no es la propia norma. `data/fixtures/esperado_muestra.csv` tiene las
21 filas **vacías**.
- **Cada uno por su cuenta y sin mirar lo que decide el sistema.** Si miras antes, lo que etiquetas es el sistema, no
  la factura. Abre cada PDF de `data/caja/facturas/`, con el Excel y la norma de Alberto, y rellena tu columna
  (`esperado_monica`: PAGAR / NO_PAGAR / ESCALAR) y el `motivo` en una frase.
- Después juntáis las dos columnas. Donde coincidáis va a `acordado`; donde no, la duda va a `pregunta_mentor`.
- **Sólo al final** se compara con lo que decide el sistema: `uv run python scripts/comparar_muestra.py` (lo hace M2
  mientras etiquetáis). Cada diferencia entre `acordado` y el sistema es **o un fallo de la norma o un fallo de
  vuestra etiqueta**, y hay que saber cuál antes de las 18:00.

## 3 · Mentores (10:00 → 10:30, en cuanto estén)
Llevas estas preguntas, por este orden (las tres primeras vienen del viernes):
1. ¿Cuándo es NO_PAGAR y cuándo ESCALAR? Hoy la norma da NO_PAGAR **sólo** si el ERP ya la marca PAGADA (9 facturas).
2. Dos facturas del mismo pedido (`PO-2026-0492`, 1.512,50 € cada una, una con sufijo «-A» 4 días después): ¿las dos
   ESCALAR (lo de ahora) o una PAGAR y otra NO_PAGAR?
3. Un escaneado con otro documento transparentándose, ¿se escala?
4. Las diferencias de la muestra que no hayáis resuelto entre Alfonso y tú.
5. **(P0, añadida a las 09:50) ¿La entrega final del lote 1 tiene que llevar la regla nueva y el ERP actualizado, o se
   queda con la v3 y el ERP v1?** Es la pregunta 3 de `docs/hitos.md` y lleva sin respuesta desde el viernes. Cambia lo
   que hacemos a las 18:00: rehacer el lote 1 cuesta 7 s, pero hay que saber si toca.
6. **(P0) ¿El lote 2 puede traer una factura idéntica byte a byte a otra, con otro nombre?** ¿Y qué esperan: las dos
   ESCALAR? Miguel lo está resolviendo en el pipeline (P0-1 de `docs/ESTADO-BACKEND.md`) y necesita la política.
7. **La regla nueva de las 18:00: ¿qué forma tiene?** Un umbral, una condición de proveedor, una fecha… Cualquier
   pista sirve para que la v4 esté medio escrita antes de que llegue.

Apunta las respuestas **literales** en `DECISIONES-NORMA.md`, en una sección «Respuestas del mentor (hora)».

## 4 · Las 9 políticas y los tests (10:30 → 12:30)
Recorre la tabla de `DECISIONES-NORMA.md`. Para cada una: mantener o cambiar, con una frase de por qué. El agente M1
convierte cada decisión en un test de `tests/test_rules.py`. **Ninguna política sin test**: la v4 de la tarde se copia
de la v3, y si la v3 no tiene tests, la v4 tampoco.
Faltan, además, los tests de los dos cambios que te adelantó Javier: la evidencia de R6 a 300 caracteres y
`NIF_INVALIDO` como anomalía. Revísalos y revierte cualquiera de los dos si no estás de acuerdo.

## 5 · ADR de la frontera (12:30 → 13:00)
`/adr frontera-no-pagar-escalar`, con la respuesta del mentor como evidencia. Son parte de los 35 puntos del plan y
Alfonso decide qué ADRs entran en el PDF: dale el resumen de 5 líneas antes de las 15:00.

## 6 · Ensayo de la regla nueva (13:30 → 14:45)
A las 18:00 no quieres estrenar el procedimiento. **M2 prepara un ensayo con una regla inventada**, en una copia de la
BD y sin tocar `norma_v3.py` ni el `REGISTRO` real, y lo cronometra:
`norma_v4.py` copiada de la v3 + la regla inventada → sus tests → `reprocess --todo --norma v4` sobre la copia (medido
hoy: 7 s para las 500) → auditoría → `package`. El resultado es una lista de pasos con tiempos, que es la que seguirás
a las 18:00.

## 7 · Tarde
| Hora | Qué | Con quién |
|---|---|---|
| 15:00 | Ensayo de la defensa: si el tribunal pregunta «¿por qué esta factura?», la respuesta es tuya. Ten a mano `albertitos trace` de `PO-2026-0492` y de una con instrucción inyectada | Alfonso |
| 17:00 | **Todo lo tuyo mergeado en `main`**: la entrega de seguro sale a las 17:30 con la norma que haya | Miguel |
| 18:00 | Llega la regla. Lees el enunciado **dos veces** y escribes en el canal, en una frase, qué cambia | todos |
| 18:05 | `norma_v4.py` = v3 + la regla nueva, **sólo lo que cambie**. Tests del caso nuevo: ok / ko / frontera. Registrar `"v4"` en `REGISTRO` | M1 escribe los tests |
| ~18:40 | `make check` → `/handoff` → Miguel: `reprocess --impacted --norma v4 --erp v2` | Miguel |
| ~19:00 | Revisas **qué decisiones han cambiado** (`reprocess` las lista) y si cada cambio tiene sentido. Si alguna no lo tiene, es un fallo de la v4: se corrige antes de entregar | Javier (auditoría) |
| 19:30 | ADR de la v4: qué dice la regla, cómo se ha interpretado y cuántas decisiones ha movido | — |

---

## Prompt M1 · Tests de la norma y los cambios que tú decidas
```
Eres el agente M1 de Mónica en el repo Albertitos (HackSpain 2026, reto Maisa), rama `monica/norma`. Mónica es la dueña de la norma (src/albertitos/rules/). Tú NO decides políticas: implementas y pruebas las que ella decida. Si te falta una decisión, pregúntasela y espera.
Reglas: sólo editas src/albertitos/rules/norma_v3.py (y norma_v4.py cuando ella lo diga) y tests/test_rules.py. Ni core/, ni pipeline/, ni extract/, ni la BD real (dist/albertitos.db). Sin date.today() (un hook lo bloquea): la fecha es ctx.fecha_corte. Dinero con Decimal y tolerancia Decimal("0.01"). Commits pequeños con `rules: qué y por qué`, sin menciones a IA. `make check` en verde antes de cada commit.
Lee antes: CLAUDE.md, src/albertitos/rules/CLAUDE.md, .claude/rules/reglas-norma.md, src/albertitos/rules/norma_v3.py, tests/test_rules.py, docs/agentes/DECISIONES-NORMA.md y docs/trampas.md.

1. PRIMERO, y en un commit aparte, porque tiene que llegar a main antes que nada: si Mónica confirma que DOCUMENTO_SUPERPUESTO entra en ANOMALIAS_HUMANO, añádelo con un comentario de una línea y un test: unos hechos con ese aviso → ESCALAR, con regla v3.R6 y el detalle «anomalía que debe ver una persona: documento_superpuesto». Comprueba después, sin escribir en la BD real, que en una copia (sqlite3 backup a dist/ensayo/m1.db, ALBERTITOS_DB apuntando a ella) sólo cambia el motivo de scan_025 y el reparto sigue en 443/48/9.
2. Tests de lo que ya está en la v3 y no tiene test: la evidencia de R6 recortada a 300 caracteres (con un tramo de más de 300 y otro de 127, el de F26-2201) y NIF_INVALIDO → ESCALAR.
3. Una tabla de tests por regla (R1-R6) con los casos ok / ko / frontera: ±0,01 €, fecha igual al corte y un día después, asiento PAGADA frente a PENDIENTE, IBAN con espacios, IVA 16 % (FA-5590_ofimática), fecha None, pedido anulado según el PDF, dos avisos a la vez. Usa hechos construidos a mano, no la BD.
4. Cada política que Mónica decida en DECISIONES-NORMA: su test primero (que falle si la norma no lo cumple) y después el cambio, si lo hay.
Al terminar cada paso, dile a Mónica en una línea qué ha cambiado y si mueve algún resultado.
```

## Prompt M2 · Comparar la muestra y ensayar la v4 sin tocar la v3
```
Eres el agente M2 de Mónica en el repo Albertitos (HackSpain 2026, reto Maisa), rama `monica/norma`. Trabajas en paralelo con M1, que es el dueño de norma_v3.py y de tests/test_rules.py: no los toques.
Reglas: sólo editas scripts/comparar_muestra.py (nuevo), tests/test_comparar_muestra.py (nuevo), docs/agentes/ENSAYO-V4.md (nuevo) y, sólo dentro de dist/ensayo/m2/, lo que necesites para el ensayo. NUNCA escribas en la BD real (dist/albertitos.db) ni en dist/entrega/: trabaja sobre una copia hecha con sqlite3.Connection.backup en dist/ensayo/m2/. No rellenes esperado_muestra.csv: lo etiquetan Mónica y Alfonso a mano, y tú no puedes influirles. Commits con `modulo: qué y por qué`, sin menciones a IA. `make check` en verde.
Lee antes: CLAUDE.md, src/albertitos/rules/CLAUDE.md, src/albertitos/rules/__init__.py, docs/agentes/ENSAYO-REPROCESADO.md, docs/agentes/AUDITORIA-ENTREGA.md, .claude/skills/lote2/SKILL.md y data/fixtures/esperado_muestra.csv.

1. scripts/comparar_muestra.py: lee data/fixtures/esperado_muestra.csv y las decisiones vigentes de la BD (en sólo lectura). Imprime, para las 21: la etiqueta de Mónica, la de Alfonso, la acordada, lo que decide el sistema y el motivo principal. Arriba, un resumen: coincidencias Mónica-Alfonso y acordado-sistema, y la lista de diferencias. Si una columna está vacía, lo dice y no cuenta la fila. Con tests sobre un CSV y una BD de prueba. Tiene que estar listo antes de las 10:30.
2. Ensayo de la regla de las 18:00 con una regla INVENTADA (por ejemplo: «una factura de más de 5.000 € de un proveedor con menos de 3 pedidos en el Excel se escala»), sin tocar la v3 ni el REGISTRO del repo. Crea el módulo de la v4 fuera de src/ o regístralo sólo en memoria dentro de un script de ensayo en dist/ensayo/m2/. Cronometra cada paso: copiar la v3 → escribir la regla → sus tests → reprocess --todo --norma v4 sobre la copia → la lista de decisiones que cambian → auditoría (scripts/auditoria_entrega.py con ALBERTITOS_DB en la copia) → package en una carpeta de ensayo.
3. docs/agentes/ENSAYO-V4.md: la receta de las 18:00 paso a paso, con el comando literal, lo que tarda y lo que hay que mirar en cada paso. Incluye cómo detectar que la v4 ha movido decisiones que no debía (las que no tocan la regla nueva no deberían cambiar) y qué hacer entonces.
Al terminar, dile a Mónica los tiempos y lo que la sorprendería a las 18:00.
```

---

**Si vas justa de tiempo, por orden de lo que no puede faltar:** (1) respuesta A y su commit · (2) la regla nueva a
las 18:00 con sus tests · (3) la muestra etiquetada · (4) la frontera con el mentor · (5) las 9 políticas · (6) el ADR.
