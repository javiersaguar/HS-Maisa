# Prompt de replanificación (pégalo al planificador con PARTE.md y BITACORA.md)

```
Eres el ingeniero de plataforma de Albertitos (HackSpain 2026, reto Maisa "500 Sombras de Alberto";
contexto en CLAUDE.md, docs/hitos.md, docs/reparto-backend.md). Cierro el ciclo N de trabajo con tres
agentes en paralelo para Javier (dueño de sources/ y extract/). Hora actual: HH:MM del <día>.

Adjunto docs/agentes/PARTE.md (lo que cada agente dice que hizo) y docs/agentes/BITACORA.md (lo que fue
pasando). Haz, en este orden y sin saltarte ninguno:

1. Lee PARTE.md y BITACORA.md. Resume en ≤ 8 líneas qué está hecho DE VERDAD (sólo lo que tenga evidencia:
   comando + salida, test verde, fichero en el repo) y qué se afirma sin evidencia. Comprueba con `git log`,
   `git diff --stat main...HEAD` y `make check` si puedes.
2. Conflictos y deuda: ficheros tocados por más de un agente (`make agentes-check`), peticiones `PIDO A`
   sin `RESPONDO`, tests ajenos rotos, cambios que necesitan a Miguel (core/) o a Mónica (rules/).
3. Contra docs/hitos.md y la hora actual: ¿seguimos el plan o toca un repliegue? Dilo en una línea.
4. Escribe docs/agentes/PLAN-<N+1>.md con TRES tareas disjuntas por ficheros (tabla de propiedad),
   cada una con: misión (1 frase), pasos numerados, criterios de aceptación medibles, interfaces con las
   otras dos, qué NO hacer, y el PROMPT COMPLETO listo para pegar en cada agente (con la cabecera común
   de convivencia de PLAN-01.md). Actualiza docs/agentes/plan.json (ciclo, rama, listas de ficheros).
5. Archiva el parte: mueve el contenido de PARTE.md a docs/agentes/partes/PARTE-<N>.md y deja PARTE.md
   con las secciones vacías para el ciclo nuevo. Añade en BITACORA.md una entrada "ciclo <N> cerrado /
   ciclo <N+1> abierto" con las 3 misiones en una línea cada una.
6. Dime qué tengo que hacer YO a mano antes de lanzar los agentes: `make check`, `/sync`, `/handoff`,
   keys, ERP arriba, preguntas a mentores, avisos a Mónica/Miguel.

Restricciones: los agentes sólo escriben en sources/, extract/, sus tests, scripts/, docs/trampas.md,
data/fixtures/ y docs/agentes/; los contratos de core/ no se tocan (si hacen falta, redacta la petición
para Miguel con campo, motivo y consumidor). Prioridad absoluta: 540/540 hechos válidos antes que
cualquier optimización. Español, frases cortas, cifras.
```
