# ADRs

| Nº | Título | Estado | Dueño |
|---|---|---|---|
| 0001 | El LLM extrae; la norma, como código versionado, decide | aceptado | Miguel |
| 0006 | Reprocesar sólo lo que el cambio toca, sin reescribir las decisiones que siguen valiendo | aceptado | Miguel |
| 0007 | Una CLI que escribe, una consola que sólo lee, y la traza dentro de la entrega | aceptado | Miguel |
| 0008 | SQLite (WAL, SQL a mano) como única fuente de verdad, con el log de eventos dentro | aceptado | Miguel |

0002-0005 están reservados para los ADRs de ingesta de Javier (PLAN-03, agente C2).

Candidatos (crear con `/adr <titulo>` cuando se decidan de verdad): snapshot del ERP en local vs. consulta en vivo ·
LLM para todo el viernes y plantillas como optimización medida · frontera NO_PAGAR/ESCALAR · degradación
ante caída del LLM · versionado de norma v3/v4.
