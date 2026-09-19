#!/usr/bin/env bash
# J3 · ensayo de «Alberto cambia un dato de la Caja el domingo, en la demo» (web del reto: «qué cambia, cómo seguís
# su impacto y cuáles son los límites del sistema»). NO escribe en la BD real, ni en dist/entrega, ni en data/caja.
#
# Uso, desde la raíz del repo:
#   bash scripts/ensayo/dato-cambiado.sh                          # IBAN de P006 (Electricidad Montcada)
#   bash scripts/ensayo/dato-cambiado.sh iban P010 ES0000000000000000000000
#   bash scripts/ensayo/dato-cambiado.sh importe PO-2026-0071 999.99
#   bash scripts/ensayo/dato-cambiado.sh nif P004 B00000000
#
# Qué hace, cronometrado:
#   1. copia la BD real (sqlite backup) y el Excel de la Caja a dist/ensayo/dato-cambiado/;
#   2. cambia UN dato en la copia del Excel, como lo haría Alberto a mano;
#   3. `albertitos maestro` con ese Excel: otra versión del maestro, porque la versión es el hash del contenido;
#   4. `reprocess --impacted --lote 1`: el linaje sólo redecide las facturas que usan ese dato;
#   5. la lista de las que cambian y `trace` de la primera.
# Todo queda en dist/ensayo/dato-cambiado/: ensayo.log (salidas literales) y tiempos.tsv (paso, segundos, exit).

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$RAIZ/dist/ensayo/dato-cambiado"
LOG="$DIR/ensayo.log"
TIEMPOS="$DIR/tiempos.tsv"
DB_REAL="${DB_REAL:-$RAIZ/dist/albertitos.db}"
XLSX_REAL="$RAIZ/data/caja/FINAL_v7_DEFINITIVO_ahorasi.xlsx"
CORTE="${ALBERTITOS_FECHA_CORTE:-2026-09-18}"

CAMPO="${1:-iban}"
CLAVE="${2:-P006}"
VALOR="${3:-ES9121000418450200051332}"

mkdir -p "$DIR"
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
  return $rc
}

cd "$RAIZ" || exit 1
huella_antes=$(sha256sum "$DB_REAL" | cut -c1-12)

export ALBERTITOS_DB="$DIR/albertitos.db"
export ALBERTITOS_FECHA_CORTE="$CORTE"
export COLUMNS=200  # rich no parte los motivos en el log
rm -f "$ALBERTITOS_DB" "$ALBERTITOS_DB-wal" "$ALBERTITOS_DB-shm"

paso "copia de la BD" uv run python - "$DB_REAL" "$ALBERTITOS_DB" <<'PY' || exit 1
import sqlite3, sys
origen = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
destino = sqlite3.connect(sys.argv[2])
origen.backup(destino)
destino.close()
PY

paso "cambiar el dato en una copia del Excel" uv run python - "$XLSX_REAL" "$DIR/caja_cambiada.xlsx" "$CAMPO" "$CLAVE" "$VALOR" <<'PY' || exit 1
import sys, unicodedata
import openpyxl

origen, destino, campo, clave, valor = sys.argv[1:]
wb = openpyxl.load_workbook(origen)
hoja, col_clave, col_campo = {
    "iban": ("Proveedores", "ID", "IBAN"),
    "nif": ("Proveedores", "ID", "NIF"),
    "importe": ("Pedidos_2026", "Pedido", "Importe_Total"),
}[campo]
ws = wb[hoja]
cab = [c.value for c in ws[1]]
i_clave, i_campo = cab.index(col_clave), cab.index(col_campo)
cambiadas = 0
for fila in ws.iter_rows(min_row=2):
    if str(fila[i_clave].value or "").strip().upper() == clave.upper():
        antes = fila[i_campo].value
        fila[i_campo].value = float(valor) if campo == "importe" else valor
        cambiadas += 1
        print(f"{hoja} · {clave} · {col_campo}: {antes!r} → {fila[i_campo].value!r}")
if not cambiadas:
    raise SystemExit(f"no encuentro {clave} en {hoja}")
wb.save(destino)
PY

paso "maestro con el Excel cambiado" uv run albertitos maestro --ruta "$DIR/caja_cambiada.xlsx" || exit 1
paso "reprocess --impacted (lote 1)" uv run albertitos reprocess --impacted --lote 1 --fecha-corte "$CORTE"
rc_reproceso=$?

# Las que cambian, completas (el reproceso sólo imprime 30): decisión vigente de la copia frente a la de la BD real.
uv run python - "$DB_REAL" "$ALBERTITOS_DB" >"$DIR/cambian.txt" <<'PY'
import json, sqlite3, sys

def vigentes(ruta):
    c = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    return {f: (r, m) for f, r, m in c.execute(
        "SELECT file_id, resultado, motivos_json FROM decisiones WHERE vigente=1")}

antes, despues = vigentes(sys.argv[1]), vigentes(sys.argv[2])
for f in sorted(despues):
    if f in antes and antes[f][0] != despues[f][0]:
        fallo = next((m for m in json.loads(despues[f][1]) if not m["ok"]), None)
        print(f"{f}: {antes[f][0]} → {despues[f][0]}  ({fallo['regla_id']}: {fallo['detalle']})" if fallo
              else f"{f}: {antes[f][0]} → {despues[f][0]}")
PY
primera=$(head -1 "$DIR/cambian.txt" | cut -d: -f1)
if [ -n "$primera" ]; then
  paso "trace de $primera" uv run albertitos trace "$primera"
fi

huella_despues=$(sha256sum "$DB_REAL" | cut -c1-12)
{
  echo
  echo "=== resumen · $(hora) ==="
  echo "dato: $CAMPO $CLAVE = $VALOR"
  echo "recalculadas y cambios: $(grep -E 'recalculadas' "$LOG" | tail -1 | sed 's/^ *//')"
  echo "cambian ($(wc -l <"$DIR/cambian.txt")):"
  sed 's/^/  /' "$DIR/cambian.txt"
  echo "BD real antes/después: $huella_antes / $huella_despues"
} | tee -a "$LOG"
[ "$huella_antes" = "$huella_despues" ] || { echo "LA BD REAL HA CAMBIADO" | tee -a "$LOG"; exit 1; }
exit $rc_reproceso
