#!/usr/bin/env bash
# Persistent Dev Tunnel for 3M SOFR live dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${SOFR_3M_PORT:-8791}"
DEVTUNNEL="${DEVTUNNEL_BIN:-./devtunnel}"
ID_FILE=".sofr_3m_devtunnel_id"
URL_FILE=".sofr_3m_devtunnel_url"
LOG_DIR="${LOG_DIR:-/tmp/sofr-3m-live}"
mkdir -p "$LOG_DIR"

[[ -x "$DEVTUNNEL" ]] || DEVTUNNEL=devtunnel

if ! "$DEVTUNNEL" user show &>/dev/null; then
  echo "Login required: $DEVTUNNEL user login -g -d"
  exit 1
fi

if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=sofr-3m-server" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s sofr-3m-server -c "$(pwd)" \
    -- bash -lc "python3 serve_sofr_3m_live.py 2>&1 | tee $LOG_DIR/server.log"
fi

sleep 2
TUNNEL_ID=""
[[ -f "$ID_FILE" ]] && TUNNEL_ID=$(cat "$ID_FILE")

if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=sofr-3m-tunnel" 2>/dev/null; then
  if [[ -z "$TUNNEL_ID" ]]; then
    TUNNEL_ID=$("$DEVTUNNEL" create --allow-anonymous -d "3M SOFR curve live" --json \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnel']['tunnelId'])")
    echo "$TUNNEL_ID" > "$ID_FILE"
    "$DEVTUNNEL" port create "$TUNNEL_ID" -p "$PORT" --protocol http
  fi
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s sofr-3m-tunnel -c "$(pwd)" \
    -- bash -lc "$DEVTUNNEL host $TUNNEL_ID -p $PORT --allow-anonymous --protocol http 2>&1 | tee $LOG_DIR/tunnel.log"
fi

sleep 6
URL=$(rg -o 'https://[a-z0-9-]+-[0-9]+\.[^/]+\.devtunnels\.ms' "$LOG_DIR/tunnel.log" 2>/dev/null | tail -1 || true)
[[ -n "$URL" ]] && echo "$URL" > "$URL_FILE" && echo "Dashboard: $URL"
