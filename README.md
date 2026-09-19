# Albertitos · HackSpain 2026 · reto Maisa "500 Sombras de Alberto"

Trabajador digital de cuentas a pagar: para cada factura PDF de la Caja decide **PAGAR / NO_PAGAR / ESCALAR**
cruzando el Excel de proveedores y el ERP de 2009. **El LLM extrae; la norma, como código versionado, decide.**

**Estado (20/09 02:00):** 540 facturas decididas y entregadas — **468 PAGAR · 62 ESCALAR · 10 NO_PAGAR** —,
los dos lotes, con auditoría en verde. Cada lote se decide en su contexto: el 1 con la norma v3 y el ERP v1,
el 2 con la v4 y el ERP v2.

**Verlo funcionando sin instalar nada:** [albertitos.vercel.app](https://albertitos.vercel.app) (sólo lectura;
el panel, la traza de cualquier factura y el chat AlbertitosAI).

```bash
git clone https://github.com/javiersaguar/HS-Maisa.git && cd HS-Maisa
./bootstrap.sh              # uv, deps, .env, verificación de la Caja y de los hooks
make erp-fast               # en otra terminal: el bridge ERP 2009 en :8009
make check                  # lint + tests
```

Lo que hace el sistema, de punta a punta:

```bash
uv run albertitos run --fecha-corte 2026-09-18      # ingest → extract → decidir → empaquetar
uv run albertitos trace F26-2201_transportes.pdf    # por qué esa factura escala, paso a paso
bash scripts/demo.sh arrancar                       # consola, puente y chat en local (localhost:3002)
```

Para trabajar en el repo:

```bash
git switch -c <nombre>/<tema>
claude                      # las reglas del equipo se cargan solas (CLAUDE.md, .claude/)
```

- **Qué falta y quién lo lleva:** [`docs/ESTADO-BACKEND.md`](docs/ESTADO-BACKEND.md) · cifras citables con su
  fuente: [`docs/CIFRAS.md`](docs/CIFRAS.md).
- Reglas del equipo y layout: [`CLAUDE.md`](CLAUDE.md) · cada módulo tiene el suyo en `src/albertitos/<modulo>/CLAUDE.md`.
- Decisiones con alternativas y evidencia: [`docs/adr/`](docs/adr/) · plazos: [`docs/hitos.md`](docs/hitos.md) ·
  defensa: [`docs/guion-defensa.md`](docs/guion-defensa.md) · trampas de los datos: [`docs/trampas.md`](docs/trampas.md).
- Entrega (repo aparte, 3 ficheros): `/entrega` en Claude Code; la demo pública, en [`deploy/README.md`](deploy/README.md).

Este repo es la solución. **No es el repo de entrega** ([`HS-Maisa-Entrega`](https://github.com/javiersaguar/HS-Maisa-Entrega), público), que sólo lleva `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf`.
