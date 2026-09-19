UV ?= uv
CAJA := data/caja
ERP_URL ?= http://127.0.0.1:8009
LOTE ?= 1

.DEFAULT_GOAL := help
# En Windows, Python lee y escribe en cp1252 si no se le dice otra cosa: los nombres con tildes,
# los «€» y las salidas de git en UTF-8 revientan. Todo lo que lance make, en UTF-8.
export PYTHONUTF8 := 1
.PHONY: kit-demo kit-instalar publicar agentes-check help setup check fmt test erp erp-fast erp-lote2 erp-lote2-fast erp-status caja-verify db run status trace chat console package validate plan-pdf bench demo-caos worktree clean

help: ## Lista estos comandos
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  make %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Entorno idempotente (uv, deps, .env, verificación de la Caja y de los hooks)
	./bootstrap.sh

check: ## Lint + tests. Obligatorio verde antes de /handoff
	$(UV) run ruff format --check src tests scripts
	$(UV) run ruff check src tests scripts
	$(UV) run pytest -q

fmt: ## Formatea todo el código
	$(UV) run ruff format src tests scripts .claude/hooks docs
	$(UV) run ruff check --fix src tests scripts

test: ## Sólo tests
	$(UV) run pytest -q

erp: ## ERP 2009 con latencia real (déjalo abierto en una terminal)
	$(MAKE) -C $(CAJA) erp

erp-fast: ## ERP sin latencia (tests y desarrollo)
	$(MAKE) -C $(CAJA) erp-fast

erp-lote2: ## ERP con la actualización del sábado (data/lote2/erp_export_lote2.csv)
	$(MAKE) -C $(CAJA) erp-lote2 LOTE2_ERP=../lote2/erp_export_lote2.csv

erp-lote2-fast: ## Igual, sin latencia
	$(MAKE) -C $(CAJA) erp-lote2-fast LOTE2_ERP=../lote2/erp_export_lote2.csv

erp-status: ## ¿Está vivo el ERP?
	@curl --fail --silent --show-error $(ERP_URL)/erp/estado && echo

caja-verify: ## Comprueba que data/caja coincide con el manifiesto (500 PDFs, NFC, hashes)
	$(UV) run albertitos caja verify

db: ## Crea/actualiza el esquema SQLite
	$(UV) run albertitos db init

run: ## Pipeline completo sobre la Caja
	$(UV) run albertitos run

status: ## Estado por etapa
	$(UV) run albertitos status

trace: ## Traza de una decisión: make trace FILE=factura_123.pdf
	$(UV) run albertitos trace "$(FILE)"

chat: ## Chat de sólo lectura en :8001 sobre dist/albertitos.db (ventana y tope: ALBERTITOS_CHAT_*)
	$(UV) run python -m albertitos.chat --servidor

console: ## Puente HTTP (:8000) + consola Next (:3000); Ctrl-C para los dos. Antes: cd console-web && pnpm install
	@trap 'kill 0' INT TERM EXIT; \
	$(UV) run python -m albertitos.console.api & \
	cd console-web && pnpm dev

package: ## Genera y valida dist/entrega/*.jsonl (nunca a mano)
	$(UV) run albertitos package

publicar: ## Ensaya paquete, validación y auditoría; ARGS=--publicar sube la entrega
	$(UV) run python scripts/publicar_entrega.py $(ARGS)

kit-demo: ## Empaqueta la BD de la demo para otro portátil (dist/kit/)
	$(UV) run python scripts/kit_demo.py empaquetar

kit-instalar: ## Instala un kit: make kit-instalar KIT=<kit.tar.gz> [ARGS=--forzar]
	@test -n "$(KIT)" || (echo 'uso: make kit-instalar KIT=<kit.tar.gz>'; exit 1)
	$(UV) run python scripts/kit_demo.py instalar "$(KIT)" $(ARGS)

validate: ## Valida un JSONL: make validate FILE=dist/entrega/outcomes.jsonl LOTE=1
	$(UV) run albertitos validate "$(FILE)" --lote $(LOTE)

plan-pdf: ## docs/plan/albertitos_plan.md -> dist/entrega/albertitos_plan.pdf
	$(UV) run python docs/plan/build_pdf.py

bench: ## Mide ficheros/s y coste con el hardware actual
	$(UV) run albertitos bench

demo-caos: ## Demo de resiliencia (~60 s) sobre una copia de la BD: LLM caído → PENDIENTE → vuelve → reanuda
	$(UV) run python scripts/demo_caos.py

worktree: ## Segundo agente en paralelo en tu máquina: make worktree NAME=javier-erp
	@test -n "$(NAME)" || (echo 'uso: make worktree NAME=<nombre>-<tema>'; exit 1)
	git worktree add ../HS-Maisa-$(NAME) -b $(NAME) 2>/dev/null || git worktree add ../HS-Maisa-$(NAME) $(NAME)
	@echo 'cd ../HS-Maisa-$(NAME) && ./bootstrap.sh'

agentes-check: ## Cada fichero cambiado en la rama pertenece a un único agente (docs/agentes/plan.json)
	$(UV) run python scripts/agentes_check.py

clean: ## Borra BD y outcomes generados (la caché LLM también: cuesta dinero regenerarla)
	rm -rf dist/albertitos.db dist/albertitos.db-wal dist/albertitos.db-shm dist/entrega
