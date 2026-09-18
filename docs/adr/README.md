# ADRs

| Nº | Título | Estado | Dueño |
|---|---|---|---|
| 0001 | El LLM extrae; la norma, como código versionado, decide | aceptado | Miguel |
| 0002 | Las plantillas deterministas extraen el 93,6 % de la Caja; el LLM es el resto, y además el control | propuesto | Javier |
| 0003 | Las escaneadas se leen dos veces y el desacuerdo se resuelve con el maestro, no con el modelo | propuesto (falta que Mónica ratifique la reconciliación) | Javier |
| 0004 | Un gateway detrás de una interfaz, caché por contenido y respaldo sólo donde compra algo | propuesto | Javier |
| 0005 | El ERP de 2009 se descarga entero una vez, versionado, y el cambio se cuenta con un diff | propuesto | Javier |
| 0006 | Reprocesar sólo lo que el cambio toca, sin reescribir las decisiones que siguen valiendo | aceptado | Miguel |
| 0007 | Una CLI que escribe, una consola que sólo lee, y la traza dentro de la entrega | aceptado | Miguel |
| 0008 | SQLite (WAL, SQL a mano) como única fuente de verdad, con el log de eventos dentro | aceptado | Miguel |

Cada ADR termina con un **Resumen para el plan (5 líneas)** listo para pegar en
`docs/plan/albertitos_plan.md` § ADRs (lo hace Alfonso; los dueños no tocan el plan).
El PDF sólo admite de 2 a 5: la selección la hace Alfonso con Miguel.

Candidatos (crear con `/adr <titulo>` cuando se decidan de verdad, no el domingo): frontera NO_PAGAR/ESCALAR
(Mónica, con mentor) · qué hace la norma con `DOCUMENTO_SUPERPUESTO` y con las lecturas reconciliadas (Mónica) ·
mejora adicional para el bonus, si se construye.
