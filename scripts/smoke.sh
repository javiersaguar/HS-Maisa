#!/usr/bin/env bash
# Comprobación de ~30 s antes de salir a la sala. Sólo lectura: no escribe en la BD ni en la entrega.
# Uso, desde la raíz del repo: bash scripts/smoke.sh
set -u
cd "$(dirname "$0")/.."
export PYTHONUTF8=1
mkdir -p dist/smoke

fallos=0
linea() { printf '%s\n' "$*"; }

medir() {
  local nombre="$1" espera="$2"
  shift 2
  local t0 t1 rc segs
  t0=$(date +%s.%N)
  salida=$("$@" 2>&1)
  rc=$?
  t1=$(date +%s.%N)
  segs=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.2f", b - a }')
  if [ "$rc" -eq "$espera" ]; then
    linea "OK    ${nombre}  ${segs} s"
  else
    linea "FALLA ${nombre}  ${segs} s  (exit ${rc}, se esperaba ${espera})"
    printf '%s\n' "$salida" | tail -n 8
    fallos=1
  fi
}

medir status 0 uv run albertitos status
medir auditoria 0 uv run python scripts/auditoria_entrega.py
medir trace 0 uv run albertitos trace F26-2201_transportes.pdf
medir bonus 0 uv run python -m albertitos.bonus --salida dist/smoke

t0=$(date +%s.%N)
salida=$(uv run python - <<'PY'
import os

from albertitos.confianza import rutas
from albertitos.console import api
from albertitos.core import db

api.RUTAS.update(rutas())
conn = db.conectar(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"), solo_lectura=True)
try:
    st, body = api.despachar("GET", "/confianza/resumen", {}, conn)
finally:
    conn.close()
ok = st == 200 and isinstance(body, dict) and "bandas" in body
print(f"status={st} bandas={ok and sorted(body['bandas'])}")
raise SystemExit(0 if ok else 1)
PY
)
rc=$?
t1=$(date +%s.%N)
segs=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.2f", b - a }')
if [ "$rc" -eq 0 ]; then
  linea "OK    confianza/resumen  ${segs} s"
else
  linea "FALLA confianza/resumen  ${segs} s  (exit ${rc})"
  printf '%s\n' "$salida" | tail -n 8
  fallos=1
fi

t0=$(date +%s.%N)
salida=$(uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf" 2>&1)
rc=$?
t1=$(date +%s.%N)
segs=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.2f", b - a }')
if [ "$rc" -eq 0 ] && printf '%s' "$salida" | grep -q '"estado": "solo_lectura"'; then
  linea "OK    chat-solo-lectura  ${segs} s"
else
  linea "FALLA chat-solo-lectura  ${segs} s  (exit ${rc})"
  printf '%s\n' "$salida" | tail -n 8
  fallos=1
fi

if [ "$fallos" -ne 0 ]; then
  linea "VEREDICTO: FALLA"
  exit 1
fi
linea "VEREDICTO: OK"
exit 0
