# ADRs

| Nº | Título | Estado | Dueño |
|---|---|---|---|
| 0001 | El LLM extrae; la norma, como código versionado, decide | aceptado | Miguel |
| 0002 | Las plantillas deterministas extraen el 93,6 % de la Caja; el LLM es el resto, y además el control | propuesto | Javier |
| 0003 | Las escaneadas se leen dos veces y el desacuerdo se resuelve con el maestro, no con el modelo | aceptado, acotado por el ADR-0011 (se reconcilia, pero no se paga sola) | Javier |
| 0004 | Un gateway detrás de una interfaz, caché por contenido y respaldo sólo donde compra algo | propuesto | Javier |
| 0005 | El ERP de 2009 se descarga entero una vez, versionado, y el cambio se cuenta con un diff | propuesto | Javier |
| 0006 | Reprocesar sólo lo que el cambio toca, sin reescribir las decisiones que siguen valiendo | aceptado | Miguel |
| 0007 | Una CLI que escribe, una consola que sólo lee, y la traza dentro de la entrega | aceptado | Miguel |
| 0008 | SQLite (WAL, SQL a mano) como única fuente de verdad, con el log de eventos dentro | aceptado | Miguel |
| 0009 | Si a la hora de entregar no hay hechos, ESCALAR explícito y reversible | aceptado (Miguel con cuatro condiciones y Mónica, 19/09 09:00) | Javier |
| 0010 | Un documento superpuesto lo mira una persona (`scan_025`) | aceptado | Mónica |
| 0011 | Una lectura reconciliada con el maestro no se paga sola (5 escaneadas pasan a ESCALAR) | aceptado | Mónica |
| 0012 | Calendario, tesorería y remesa de sólo lectura (bonus) | implementado (PLAN-10 y PLAN-11) | Javier (J5, K1) |
| 0013 | Un chat de consulta con herramientas cerradas, sin SQL generado y sin escritura (bonus) | implementado y evaluado (14/15 + 1 parcial) | Javier (K2) |
| 0014 | Confianza en la clasificación por factura: ordinal, por fuente y con razones, no una probabilidad (bonus) | propuesto (lo aceptan Javier y Mónica) | Javier (K3) |
| 0016 | La consola es Next sobre un puente HTTP de sólo lectura, no Streamlit | aceptado (implementado en #5 y #7) | Alejandro |

Cada ADR termina con un **Resumen para el plan (5 líneas)** listo para pegar en
`docs/plan/albertitos_plan.md` § ADRs (lo hace Alfonso; los dueños no tocan el plan).
El PDF sólo admite de 2 a 5: la selección la hace Alfonso con Miguel.

Candidatos (crear con `/adr <titulo>` cuando se decidan de verdad, no el domingo): frontera NO_PAGAR/ESCALAR
(Mónica, con mentor) · qué hace la norma con `DOCUMENTO_SUPERPUESTO` y con las lecturas reconciliadas (Mónica) ·
mejora adicional para el bonus, si se construye.
