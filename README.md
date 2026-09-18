# Albertitos · HackSpain 2026 · reto Maisa "500 Sombras de Alberto"

Trabajador digital de cuentas a pagar: para cada factura PDF de la Caja decide **PAGAR / NO_PAGAR / ESCALAR**
cruzando el Excel de proveedores y el ERP de 2009. **El LLM extrae; la norma, como código versionado, decide.**

```bash
git clone https://github.com/javiersaguar/HS-Maisa.git && cd HS-Maisa
./bootstrap.sh              # uv, deps, .env, verificación de la Caja y de los hooks
make erp-fast               # en otra terminal: el bridge ERP 2009 en :8009
make check                  # lint + tests
git switch -c <nombre>/<tema>
claude                      # las reglas del equipo se cargan solas (CLAUDE.md, .claude/)
```

- Reglas del equipo y layout: [`CLAUDE.md`](CLAUDE.md) · cada módulo tiene el suyo en `src/albertitos/<modulo>/CLAUDE.md`.
- Plazos y repliegues: [`docs/hitos.md`](docs/hitos.md) · defensa: [`docs/guion-defensa.md`](docs/guion-defensa.md) · trampas de los datos: [`docs/trampas.md`](docs/trampas.md).
- Entrega (repo aparte, 3 ficheros): `/entrega` en Claude Code.

Este repo es la solución. **No es el repo de entrega** (`la-caja-outcomes`), que sólo lleva `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf`.
