#!/usr/bin/env bash
# J1 · ensayo general del lote 2 con el código de main. NO escribe en la BD real ni en dist/entrega.
# Uso, desde la raíz del repo:  bash scripts/ensayo/lote2-ensayo.sh
# Todo queda en dist/ensayo/j1/: ensayo.log (salidas literales) y tiempos.tsv (paso, segundos, exit).

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
J1="$RAIZ/dist/ensayo/j1"
WT="$J1/wt"
LOG="$J1/ensayo.log"
TIEMPOS="$J1/tiempos.tsv"
DB_REAL="$RAIZ/dist/albertitos.db"
PUERTO=8011
ERP_PID=""

mkdir -p "$J1"
: >"$LOG"
printf 'paso\tsegundos\texit\n' >"$TIEMPOS"

hora() { TZ=Europe/Madrid date +%H:%M:%S; }

paso() {  # paso <nombre> <comando...>
  local nombre="$1"; shift
  local t0 t1 rc
  { echo; echo "=== $nombre · $(hora) ==="; echo "\$ $*"; } >>"$LOG"
  t0=$(date +%s.%N)
  "$@" >>"$LOG" 2>&1; rc=$?
  t1=$(date +%s.%N)
  printf '%s\t%s\t%s\n' "$nombre" "$(awk "BEGIN{printf \"%.3f\", $t1-$t0}")" "$rc" | tee -a "$TIEMPOS"
  echo "--- exit=$rc" >>"$LOG"
  return 0   # un paso que falla no aborta el ensayo: se anota y se sigue
}

limpiar() {
  [ -n "$ERP_PID" ] && kill "$ERP_PID" 2>/dev/null
  git -C "$RAIZ" worktree remove --force "$WT" 2>/dev/null
}
trap limpiar EXIT

echo "J1 · inicio $(hora)" | tee -a "$LOG"

# ---------------------------------------------------------------- 0 · huellas y salud
paso huellas-antes bash -c "sha256sum '$DB_REAL' '$RAIZ/dist/entrega/outcomes.jsonl' | tee '$J1/huellas-antes.txt'"
paso erp-8009-vivo curl --fail --silent --show-error http://127.0.0.1:8009/erp/estado

# ---------------------------------------------------------------- 1 · worktree con el código de main
# El worktree es imprescindible: cli.LOTE2 es la constante Path("data/lote2"), NO lee
# ALBERTITOS_DIR_LOTE2. run/package/validate miran siempre data/lote2/facturas. Poblándolo dentro
# del worktree, el ensayo recorre exactamente el mismo camino que el lote real de las 18:00.
paso worktree-add git -C "$RAIZ" worktree add --detach "$WT" HEAD
cd "$WT" || exit 1

paso material-a-lote2 bash -c "
  mkdir -p data/lote2/facturas
  cp '$RAIZ'/data/fixtures/lote2_sim/facturas/*.pdf data/lote2/facturas/
  cp '$RAIZ'/data/fixtures/lote2_identicos/facturas/*.pdf data/lote2/facturas/
  cp '$RAIZ'/data/fixtures/erp_lote2_simulado.csv data/lote2/erp_export_lote2.csv
  ls -1 data/lote2/facturas | wc -l"

# BD de ensayo: backup SQLite desde la real en SÓLO LECTURA (nunca cp con WAL).
paso bd-copia uv run python -c "
import sqlite3
o = sqlite3.connect('file:$DB_REAL?mode=ro', uri=True)
d = sqlite3.connect('$J1/ensayo.db')
o.backup(d); d.close(); o.close()
print('copia hecha')"

export ALBERTITOS_DB="$J1/ensayo.db"
export ALBERTITOS_CHAOS="$J1/chaos.json"
export ALBERTITOS_FECHA_CORTE=2026-09-18
export ALBERTITOS_DIR_LOTE2=data/lote2/facturas
export ALBERTITOS_WORKERS=4

# ---------------------------------------------------------------- 2 · ERP v2 propio en :8011
paso erp-8011-arranca bash -c "
  uv run python data/caja/alberto_erp.py --rapido --puerto $PUERTO \
    --lote2 data/lote2/erp_export_lote2.csv >>'$J1/erp8011.log' 2>&1 &
  echo \$! > '$J1/erp8011.pid'
  for i in \$(seq 30); do
    curl --fail --silent http://127.0.0.1:$PUERTO/erp/estado && break
    sleep 0.5
  done"
ERP_PID="$(cat "$J1/erp8011.pid" 2>/dev/null || true)"

# ---------------------------------------------------------------- 3 · la receta, paso a paso
paso preflight uv run python scripts/preflight_lote2.py --db "$ALBERTITOS_DB" \
  --dir-lote2 data/lote2/facturas --erp-esperado v1
paso verificar-dir uv run python scripts/verificar_material.py data/lote2 \
  --db "$ALBERTITOS_DB" --esperados 14
paso zip-crear bash -c "cd data/lote2 && zip -qr '$J1/lote2-sim.zip' facturas erp_export_lote2.csv && sha256sum '$J1/lote2-sim.zip' | cut -d' ' -f1 > '$J1/lote2-sim.sha256' && cat '$J1/lote2-sim.sha256'"
paso verificar-zip bash -c "uv run python scripts/verificar_material.py '$J1/lote2-sim.zip' \
  --hash \$(cat '$J1/lote2-sim.sha256') --db '$ALBERTITOS_DB' --esperados 14"
paso caja-verify uv run albertitos caja verify --lote 2 --dir data/lote2/facturas --esperados 14

paso ingest uv run albertitos ingest --dir data/lote2/facturas --lote 2
# --sin-extraer: las escaneadas se leen de caché o no se leen. J1 NO llama al LLM (eso es de J3).
paso run-erp-v1 uv run albertitos run --erp v1 --norma v3 --fecha-corte 2026-09-18 \
  --salida "$J1/entrega-preauditoria"
paso status uv run albertitos status

paso erp-pull-v2 bash -c "ALBERTITOS_ERP_URL=http://127.0.0.1:$PUERTO uv run albertitos erp pull --tag v2"
paso erp-diff uv run albertitos erp diff v1 v2
paso reprocess-impacted uv run albertitos reprocess --impacted --erp v2 --norma v3 --fecha-corte 2026-09-18
# Cuánto cuesta el camino de la regla nueva de Mónica (a las 18:00 será --norma v4):
paso reprocess-todo-v3 uv run albertitos reprocess --todo --erp v2 --norma v3 --fecha-corte 2026-09-18

paso inventario uv run python scripts/inventario_trampas.py --con-hechos \
  --facturas data/lote2/facturas --erp-tag v2 --salida "$J1/anomalias_lote2.csv" --sin-docs --solo-resumen
paso auditoria-previa uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos \
  --dir-lote1 data/caja/facturas --dir-lote2 data/lote2/facturas --entrega "$J1/entrega-preauditoria"
paso package uv run albertitos package --salida "$J1/entrega"
paso auditoria-final uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos \
  --dir-lote1 data/caja/facturas --dir-lote2 data/lote2/facturas --entrega "$J1/entrega"
paso validate-lote1 uv run albertitos validate "$J1/entrega/outcomes.jsonl" --lote 1
paso validate-lote2 uv run albertitos validate "$J1/entrega/outcomes_lote2.jsonl" --lote 2

# Tres trazas: una copia exacta, una tocada por el diff del ERP, una del lote 2 normal.
paso trace-copia uv run albertitos trace L2I-reenvio_2026-01-08_P001.pdf
paso trace-erp uv run albertitos trace F26-9865_ofimática.pdf
paso trace-lote2 uv run albertitos trace L2-2026-01-24_P009.pdf

# make publicar EN SECO contra un repo bare local: nunca el de entrega real.
paso plan-pdf make plan-pdf   # dist/entrega/ del worktree no lo tiene (es generado)
paso publicar-seco bash -c "
  git init --bare -q '$J1/entrega-bare.git' 2>/dev/null
  rm -rf '$J1/entrega-clon'
  git clone -q '$J1/entrega-bare.git' '$J1/entrega-clon'
  ENTREGA_REPO='$J1/entrega-bare.git' uv run python scripts/publicar_entrega.py \
    --db '$ALBERTITOS_DB' --destino '$J1/entrega-clon' --sin-gh"

# ---------------------------------------------------------------- 4 · desvío 2 · auditoría roja
paso desvio-rojo-forzar uv run python -c "
import sqlite3
c = sqlite3.connect('$J1/ensayo.db')
n = c.execute(\"UPDATE hechos SET hechos_json = replace(hechos_json, '\\\"texto_sospechoso\\\":null', '\\\"texto_sospechoso\\\":\\\"None\\\"') WHERE sha256 IN (SELECT sha256 FROM ficheros WHERE file_id='scan_025.pdf')\").rowcount
c.commit(); print('filas tocadas:', n)"
paso desvio-rojo-package-niega uv run albertitos package --salida "$J1/entrega-rojo"
paso desvio-rojo-aceptar uv run albertitos package --salida "$J1/entrega-rojo" \
  --aceptar-rojo "ensayo J1: rojo forzado a propósito, no es una entrega"
paso desvio-rojo-evento uv run python -c "
import sqlite3
c = sqlite3.connect('file:$J1/ensayo.db?mode=ro', uri=True)
for r in c.execute(\"SELECT ts, estado, detalle FROM eventos WHERE detalle LIKE '%ROJA%' ORDER BY id DESC LIMIT 5\"):
    print(r)"

# ---------------------------------------------------------------- 5 · desvío 3 · contingencia
paso desvio-conting-caos uv run albertitos chaos --llm-down
paso desvio-conting-seco uv run python scripts/contingencia.py --db "$ALBERTITOS_DB" --lote 2
paso desvio-conting-off uv run albertitos chaos --off

echo "J1 · fin $(hora)" | tee -a "$LOG"
cd "$RAIZ" || exit 1
paso huellas-despues bash -c "sha256sum '$DB_REAL' '$RAIZ/dist/entrega/outcomes.jsonl' | tee '$J1/huellas-despues.txt'"
paso huellas-iguales diff "$J1/huellas-antes.txt" "$J1/huellas-despues.txt"
paso erp-8009-sigue-vivo curl --fail --silent --show-error http://127.0.0.1:8009/erp/estado

echo
echo "TIEMPOS ($TIEMPOS):"
cat "$TIEMPOS"
