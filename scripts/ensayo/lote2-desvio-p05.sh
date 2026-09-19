#!/usr/bin/env bash
# J1 · desvío 1 · P0-5: un PDF del lote 2 con el mismo nombre que uno del lote 1 y otro contenido.
# Mide lo que Javier tendrá que hacer a las 18:00 si verificar_material dice «nombre coincide con
# lote 1»: mergear la rama de Miguel y seguir. Cronometra desde el aviso hasta package APTO.
# Uso, desde la raíz:  bash scripts/ensayo/lote2-desvio-p05.sh

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
J1="$RAIZ/dist/ensayo/j1"
WT="$J1/wt-p05"
LOG="$J1/p05.log"
TIEMPOS="$J1/p05-tiempos.tsv"
DB_REAL="$RAIZ/dist/albertitos.db"

mkdir -p "$J1"
: >"$LOG"
printf 'paso\tsegundos\texit\n' >"$TIEMPOS"

hora() { TZ=Europe/Madrid date +%H:%M:%S; }
paso() {
  local nombre="$1"; shift
  local t0 t1 rc
  { echo; echo "=== $nombre · $(hora) ==="; echo "\$ $*"; } >>"$LOG"
  t0=$(date +%s.%N); "$@" >>"$LOG" 2>&1; rc=$?; t1=$(date +%s.%N)
  printf '%s\t%s\t%s\n' "$nombre" "$(awk "BEGIN{printf \"%.3f\", $t1-$t0}")" "$rc" | tee -a "$TIEMPOS"
  echo "--- exit=$rc" >>"$LOG"
  return 0
}
trap 'git -C "$RAIZ" worktree remove --force "$WT" 2>/dev/null' EXIT

# --- 1 · ANTES del merge: el verificador tiene que PARAR (esto es lo que se ve a las 18:00)
paso worktree-sin-p05 git -C "$RAIZ" worktree add --detach "$WT" HEAD
cd "$WT" || exit 1
paso material bash -c "
  mkdir -p data/lote2/facturas
  cp '$RAIZ'/data/fixtures/lote2_sim/facturas/*.pdf data/lote2/facturas/
  cp '$RAIZ'/data/fixtures/lote2_nombre_repetido/facturas/*.pdf data/lote2/facturas/
  ls -1 data/lote2/facturas | wc -l"
paso bd-copia uv run python -c "
import sqlite3
o = sqlite3.connect('file:$DB_REAL?mode=ro', uri=True); d = sqlite3.connect('$J1/p05.db')
o.backup(d); d.close(); o.close(); print('copia hecha')"

export ALBERTITOS_DB="$J1/p05.db"
export ALBERTITOS_CHAOS="$J1/p05-chaos.json"
export ALBERTITOS_FECHA_CORTE=2026-09-18
export ALBERTITOS_DIR_LOTE2=data/lote2/facturas

# Se espera exit 1 y «nombre coincide con lote 1». Aquí arranca el cronómetro de la recuperación.
paso verificar-antes-del-merge uv run python scripts/verificar_material.py data/lote2 \
  --db "$ALBERTITOS_DB" --esperados 11
INICIO_RECUPERACION=$(date +%s.%N)

# --- 2 · la instrucción de Miguel (bitácora 11:40): mergear su rama y seguir
paso merge-p05 git merge --no-edit origin/miguel/p0-5-nombre-repetido
paso make-check-p05 make check
paso verificar-tras-el-merge uv run python scripts/verificar_material.py data/lote2 \
  --db "$ALBERTITOS_DB" --esperados 11

paso ingest uv run albertitos ingest --dir data/lote2/facturas --lote 2
paso run-erp-v1 uv run albertitos run --erp v1 --norma v3 --fecha-corte 2026-09-18 \
  --salida "$J1/p05-preauditoria"
paso auditoria uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos \
  --dir-lote1 data/caja/facturas --dir-lote2 data/lote2/facturas --entrega "$J1/p05-preauditoria"
paso package uv run albertitos package --salida "$J1/p05-entrega"
paso validate-lote1 uv run albertitos validate "$J1/p05-entrega/outcomes.jsonl" --lote 1
paso validate-lote2 uv run albertitos validate "$J1/p05-entrega/outcomes_lote2.jsonl" --lote 2

FIN=$(date +%s.%N)
printf 'RECUPERACION-TOTAL\t%s\t0\n' "$(awk "BEGIN{printf \"%.3f\", $FIN-$INICIO_RECUPERACION}")" \
  | tee -a "$TIEMPOS"

# --- 3 · lo que hay que comprobar a mano en el log: las dos líneas existen y son distintas
paso lineas-del-nombre-repetido bash -c "
  grep -n '2026-01-16_P004.pdf' '$J1/p05-entrega/outcomes.jsonl' '$J1/p05-entrega/outcomes_lote2.jsonl'
  echo '--- interno en la BD (debe llevar el prefijo de db.PREFIJO_INTERNO):'
  uv run python -c \"
import sqlite3
c = sqlite3.connect('file:$ALBERTITOS_DB?mode=ro', uri=True)
for r in c.execute(\\\"SELECT file_id, lote FROM ficheros WHERE file_id LIKE '%2026-01-16_P004%'\\\"):
    print(r)\""

cd "$RAIZ" || exit 1
echo; echo "TIEMPOS ($TIEMPOS):"; cat "$TIEMPOS"
