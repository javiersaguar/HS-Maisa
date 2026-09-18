---
paths:
  - "docs/**"
---
# Documentación que puntúa

- `docs/plan/albertitos_plan.md` es la fuente del PDF de 35 puntos. Dos secciones obligatorias: **Arquitectura** (componentes, flujo de datos y estado, reparto agentes/modelos/personas, observabilidad y recuperación) y **ADRs / trade-offs** (2 a 5).
- Un ADR = `docs/adr/NNNN-titulo.md` con: Contexto · Alternativas consideradas (mínimo 2) · Decisión · Consecuencias aceptadas · **Evidencia** (cifra, test, log o commit). Sin evidencia no es un ADR, es una opinión.
- Se escribe cuando se toma la decisión, no el domingo. Plantilla: `docs/adr/0000-plantilla.md`. Comando: `/adr <titulo>`.
- Cifras de escala y coste sólo si están medidas (`make bench` → `docs/benchmark.md`) y con condiciones: hardware, tamaño de lote, % que toca LLM, modelo, fecha.
- Español, frases cortas, sin marketing. El tribunal pregunta por lo que está escrito: no escribas lo que no puedas defender.
