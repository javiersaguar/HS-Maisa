#!/usr/bin/env bash
# Bootstrap idempotente de Albertitos. Ejecútalo tantas veces como quieras; sólo cambia lo que falte.
# Necesita: git, python3, curl. Instala uv si no está. Todo lo demás lo trae uv (ruff, pytest, deps).
set -euo pipefail
cd "$(dirname "$0")"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✗\033[0m %s\n' "$*"; exit 1; }

echo "== Albertitos · bootstrap =="

# 1. Herramientas base
for t in git python3 curl; do command -v "$t" >/dev/null || die "falta $t"; done
ok "git, python3, curl"

if ! command -v uv >/dev/null; then
  echo "  instalando uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null || die "uv instalado pero no está en PATH: abre otra terminal o añade ~/.local/bin al PATH"
fi
ok "uv $(uv --version | cut -d' ' -f2)"

# 2. Python 3.12 gestionado por uv (mismo intérprete en todos los portátiles) + dependencias
uv python install 3.12 >/dev/null 2>&1 || true
uv sync --quiet
ok "entorno .venv sincronizado (python $(uv run python -c 'import sys;print(".".join(map(str,sys.version_info[:3])))'))"

# 3. .env personal
if [ ! -f .env ]; then
  cp .env.example .env
  warn ".env creado desde .env.example → pon tu ANTHROPIC_API_KEY (sin ella, extract/ sólo usa caché)"
else
  ok ".env existe"
fi
grep -q '^ANTHROPIC_API_KEY=sk-ant-\.\.\.' .env 2>/dev/null && warn "ANTHROPIC_API_KEY sigue siendo el placeholder"

# 4. Directorios de trabajo
mkdir -p dist data/lote2 data/fixtures
ok "dist/ data/lote2/ data/fixtures/"

# 5. La Caja
if [ -d data/caja/facturas ]; then
  uv run albertitos caja verify >/dev/null 2>&1 && ok "Caja verificada (500 PDFs, NFC, manifiesto)" || warn "Caja: revisa \`uv run albertitos caja verify\` (¿zip oficial distinto? ¿nombres NFD?)"
else
  warn "no está data/caja/facturas: git pull, o descomprime la Caja oficial ahí"
fi

# 6. BD
uv run albertitos db init >/dev/null && ok "esquema SQLite en ${ALBERTITOS_DB:-dist/albertitos.db}"

# 7. Hooks de Claude Code: cada uno tiene que ejecutarse aquí, hoy
probar_hook() {  # nombre json_stdin esperado(deny|allow|texto)
  local salida
  salida=$(printf '%s' "$2" | CLAUDE_PROJECT_DIR="$PWD" python3 ".claude/hooks/$1" 2>&1 || true)
  case "$3" in
    deny)  echo "$salida" | grep -q '"deny"'  && ok "hook $1 bloquea lo que debe" || die "hook $1 NO bloquea: $salida" ;;
    allow) echo "$salida" | grep -q '"deny"'  && die "hook $1 bloquea de más: $salida" || ok "hook $1 deja pasar lo normal" ;;
    *)     echo "$salida" | grep -q "$3"      && ok "hook $1 responde" || die "hook $1 falla: $salida" ;;
  esac
}
probar_hook guard_bash.py   '{"tool_input":{"command":"git push --force origin javier/x"},"cwd":"'"$PWD"'"}' deny
probar_hook guard_bash.py   '{"tool_input":{"command":"uv run pytest -q"},"cwd":"'"$PWD"'"}' allow
probar_hook guard_edit.py   '{"tool_input":{"file_path":"'"$PWD"'/dist/entrega/outcomes.jsonl","content":"x"},"cwd":"'"$PWD"'"}' deny
probar_hook guard_edit.py   '{"tool_input":{"file_path":"'"$PWD"'/src/albertitos/rules/norma_v3.py","new_string":"x = date.today()"},"cwd":"'"$PWD"'"}' deny
probar_hook guard_edit.py   '{"tool_input":{"file_path":"'"$PWD"'/src/albertitos/sources/erp.py","new_string":"x = 1"},"cwd":"'"$PWD"'"}' allow
probar_hook session_start.py '{"cwd":"'"$PWD"'","hook_event_name":"SessionStart"}' 'Albertitos'

# 8. Claude Code
command -v claude >/dev/null && ok "claude $(claude --version 2>/dev/null | head -1)" || warn "no encuentro \`claude\` en PATH (la app de escritorio vale igual)"

# 9. Rama de trabajo
rama=$(git symbolic-ref --short -q HEAD 2>/dev/null || echo "?")
if [ "$rama" = "main" ] && [ ! -f .claude/dueno.local ]; then
  warn "estás en main. Crea tu rama: git switch -c <nombre>/<tema>   (Miguel: printf 'merge\ncontratos\n' > .claude/dueno.local)"
else
  ok "rama: $rama"
fi

echo
echo "Listo. Siguiente: make erp-fast (otra terminal) · make check · claude"
