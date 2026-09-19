#!/usr/bin/env bash
# La demo, de un tirón: puente (con bandeja), chat y consola, todo en local, sobre una copia de la BD.
#
#   bash scripts/demo.sh arrancar     # los tres; deja los PID en dist/demo/
#   bash scripts/demo.sh estado       # qué responde cada uno (local y público)
#   bash scripts/demo.sh parar        # para lo que arrancó este script
#   bash scripts/demo.sh despertar    # mantiene despierta la demo pública de Render (Ctrl+C para salir)
#
# Variables (con sus valores por defecto):
#   PUERTO_PUENTE=8000  PUERTO_CHAT=8101  PUERTO_CONSOLA=3002  DB_DEMO=dist/bandeja.db
#   CHAT_HASTA=<+12 h>  (la ventana del chat; sin ella, la del .env)
# El 3000 y el 8001 suelen estar ocupados por contenedores de otros proyectos: por eso 3002 y 8101.

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ" || exit 1

PUERTO_PUENTE="${PUERTO_PUENTE:-8000}"
PUERTO_CHAT="${PUERTO_CHAT:-8101}"
PUERTO_CONSOLA="${PUERTO_CONSOLA:-3002}"
DB_DEMO="${DB_DEMO:-dist/bandeja.db}"
CHAT_HASTA="${CHAT_HASTA:-$(date -d '+12 hours' +%Y-%m-%dT%H:%M)}"
ORIGENES="http://localhost:$PUERTO_CONSOLA,http://127.0.0.1:$PUERTO_CONSOLA,https://albertitos.vercel.app"
PUBLICO_PUENTE="${PUBLICO_PUENTE:-https://albertitos-puente.onrender.com}"
PUBLICO_CHAT="${PUBLICO_CHAT:-https://albertitos-chat.onrender.com}"
PIDS="$RAIZ/dist/demo"
mkdir -p "$PIDS"

# Cualquier dirección: Next escucha en *:3002 y el puente en 127.0.0.1:8000
pid_en_puerto() {
  ss -ltnp 2>/dev/null | awk -v p=":$1" '$4 ~ p"$" {print}' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2
}
espera() {  # espera <url> <segundos>
  for _ in $(seq $(( ${2:-20} * 2 ))); do curl -fs -m 1 -o /dev/null "$1" && return 0; sleep 0.5; done
  return 1
}

arrancar() {
  [ -f "$DB_DEMO" ] || { echo "no existe $DB_DEMO: crea la bandeja con 'uv run python -c \"from albertitos.console import bandeja; bandeja.preparar()\"'"; exit 1; }
  for p in "$PUERTO_PUENTE" "$PUERTO_CHAT" "$PUERTO_CONSOLA"; do
    if [ -n "$(pid_en_puerto "$p")" ]; then
      echo "el puerto $p ya está ocupado (PID $(pid_en_puerto "$p")). 'bash scripts/demo.sh parar' o cambia el puerto."
      exit 1
    fi
  done

  ALBERTITOS_CONSOLA_ORIGENES="$ORIGENES" \
    nohup uv run python -m albertitos.console.api --bandeja --db "$DB_DEMO" --puerto "$PUERTO_PUENTE" \
    >"$PIDS/puente.log" 2>&1 &
  echo $! >"$PIDS/puente.pid"

  ALBERTITOS_CHAT_PUERTO="$PUERTO_CHAT" ALBERTITOS_CHAT_HASTA="$CHAT_HASTA" ALBERTITOS_CHAT_ORIGENES="$ORIGENES" \
    nohup uv run python -m albertitos.chat --servidor --db "$DB_DEMO" >"$PIDS/chat.log" 2>&1 &
  echo $! >"$PIDS/chat.pid"

  if [ ! -d console-web/node_modules ]; then
    echo "instalando dependencias de la consola (una vez, con red)…"
    (cd console-web && npx --yes pnpm install --frozen-lockfile >"$PIDS/pnpm-install.log" 2>&1) || { echo "falló pnpm install, mira $PIDS/pnpm-install.log"; exit 1; }
  fi
  echo "compilando la consola contra los puertos locales…"
  (cd console-web && NEXT_PUBLIC_USE_MOCK=false \
      NEXT_PUBLIC_API_URL="http://127.0.0.1:$PUERTO_PUENTE" \
      NEXT_PUBLIC_CHAT_URL="http://127.0.0.1:$PUERTO_CHAT" \
      npx --yes pnpm build >"$PIDS/consola-build.log" 2>&1) || { echo "falló el build, mira $PIDS/consola-build.log"; exit 1; }
  (cd console-web && nohup npx --yes pnpm start -p "$PUERTO_CONSOLA" >"$PIDS/consola.log" 2>&1 & echo $! >"$PIDS/consola.pid")

  espera "http://127.0.0.1:$PUERTO_PUENTE/salud" 30 || echo "aviso: el puente no responde, mira $PIDS/puente.log"
  espera "http://127.0.0.1:$PUERTO_CHAT/chat/salud" 30 || echo "aviso: el chat no responde, mira $PIDS/chat.log"
  espera "http://localhost:$PUERTO_CONSOLA/" 60 || echo "aviso: la consola no responde, mira $PIDS/consola.log"
  echo
  echo "Consola:  http://localhost:$PUERTO_CONSOLA   (ábrela por localhost, no por 127.0.0.1)"
  echo "Puente :  http://127.0.0.1:$PUERTO_PUENTE   ·  Chat: http://127.0.0.1:$PUERTO_CHAT (ventana hasta $CHAT_HASTA)"
  estado
}

parar() {
  for n in consola chat puente; do
    f="$PIDS/$n.pid"
    [ -f "$f" ] || continue
    pid="$(cat "$f")"
    if kill "$pid" 2>/dev/null; then echo "parado $n (PID $pid)"; fi
    rm -f "$f"
  done
  # Lo que quedara escuchando de un arranque anterior
  for p in "$PUERTO_CONSOLA" "$PUERTO_CHAT" "$PUERTO_PUENTE"; do
    pid="$(pid_en_puerto "$p")"
    [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "parado lo que había en el puerto $p (PID $pid)"
  done
  return 0
}

linea() {  # linea <nombre> <url>
  local code tiempo
  read -r code tiempo < <(curl -s -m 90 -o /dev/null -w "%{http_code} %{time_total}\n" "$2")
  printf '%-26s %-58s %s en %ss\n' "$1" "$2" "$code" "$tiempo"
}

estado() {
  echo
  linea "consola (local)"  "http://localhost:$PUERTO_CONSOLA/"
  linea "puente (local)"   "http://127.0.0.1:$PUERTO_PUENTE/salud"
  linea "chat (local)"     "http://127.0.0.1:$PUERTO_CHAT/chat/salud"
  linea "consola (pública)" "https://albertitos.vercel.app/"
  linea "puente (público)" "$PUBLICO_PUENTE/salud"
  linea "chat (público)"   "$PUBLICO_CHAT/chat/salud"
  echo
  curl -fs -m 5 "http://127.0.0.1:$PUERTO_PUENTE/panel" 2>/dev/null |
    python3 -c 'import json,sys; d=json.load(sys.stdin); print("BD local :", d["ficheros"], "ficheros", d["por_estado"])' 2>/dev/null
  curl -fs -m 90 "$PUBLICO_PUENTE/panel" 2>/dev/null |
    python3 -c 'import json,sys; d=json.load(sys.stdin); print("BD pública:", d["ficheros"], "ficheros", d["por_estado"])' 2>/dev/null
}

despertar() {  # el plan gratuito de Render duerme a los 15 min sin tráfico: esto lo mantiene despierto
  local cada="${1:-600}"
  echo "despertando la demo pública cada $cada s (Ctrl+C para salir). Sólo /salud: no gasta ninguna llamada al modelo."
  while true; do
    printf '%s  ' "$(TZ=Europe/Madrid date +%H:%M:%S)"
    printf 'puente %s · chat %s\n' \
      "$(curl -s -m 90 -o /dev/null -w '%{http_code} (%{time_total}s)' "$PUBLICO_PUENTE/salud")" \
      "$(curl -s -m 90 -o /dev/null -w '%{http_code} (%{time_total}s)' "$PUBLICO_CHAT/chat/salud")"
    sleep "$cada"
  done
}

case "${1:-estado}" in
  arrancar|up|start) arrancar ;;
  parar|down|stop)   parar ;;
  estado|status)     estado ;;
  despertar|keepalive) shift; despertar "${1:-600}" ;;
  *) echo "uso: bash scripts/demo.sh [arrancar|parar|estado|despertar [segundos]]"; exit 2 ;;
esac
