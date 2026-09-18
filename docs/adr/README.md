# ADRs

| Nº | Título | Estado | Dueño |
|---|---|---|---|
| 0001 | El LLM extrae; la norma, como código versionado, decide | propuesto | Miguel |
| 0002 | Las plantillas deterministas extraen el 93,6 % de la Caja; el LLM es el resto, y además el control | propuesto | Javier |
| 0003 | Las escaneadas se leen dos veces y el desacuerdo se resuelve con el maestro, no con el modelo | propuesto | Javier |
| 0004 | Un gateway detrás de una interfaz, caché por contenido y respaldo sólo donde compra algo | propuesto | Javier |
| 0005 | El ERP de 2009 se descarga entero una vez, versionado, y el cambio se cuenta con un diff | propuesto | Javier |

Cada ADR termina con un **Resumen para el plan (5 líneas)** listo para pegar en
`docs/plan/albertitos_plan.md` § ADRs (lo hace Alfonso; los dueños no tocan el plan).

Candidatos (crear con `/adr <titulo>` cuando se decidan de verdad, no el domingo): formato CLI + consola de
sólo lectura · SQLite con log de eventos como única fuente de verdad · frontera NO_PAGAR/ESCALAR (Mónica,
con mentor) · versionado de norma v3/v4 y reprocesado por linaje (Miguel).
