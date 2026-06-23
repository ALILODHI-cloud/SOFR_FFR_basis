#!/usr/bin/env bash
# Start live STIR dashboard + Microsoft Dev Tunnel (persistent URL).
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${STIR_LIVE_PORT:-8787}"
DEVTUNNEL="${DEVTUNNEL_BIN:-./devtunnel}"
TUNNEL_ID_FILE=".stir_devtunnel_id"
TUNNEL_URL_FILE=".stir_devtunnel_url"
LOG_DIR="${LOG_DIR:-/tmp/stir-live}"

mkdir -p "$LOG_DIR"

if [[ ! -x "$DEVTUNNEL" ]] && command -v devtunnel >/dev/null; then
  DEVTUNNEL=devtunnel
fi

if ! "$DEVTUNNEL" user show &>/dev/null; then
  echo "Dev Tunnel login required. Run once:"
  echo "  $DEVTUNNEL user login -g -d"
  echo "Then re-run this script."
  exit 1
fi

# Live data server
if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=stir-live-server" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s stir-live-server -c "$(pwd)" \
    -- bash -lc "python3 serve_stir_live.py 2>&1 | tee $LOG_DIR/server.log"
  echo "Started stir-live-server (port $PORT)"
else
  echo "stir-live-server already running"
fi

sleep 2

# Persistent tunnel (reuse ID if saved)
TUNNEL_ID=""
if [[ -f "$TUNNEL_ID_FILE" ]]; then
  TUNNEL_ID=$(cat "$TUNNEL_ID_FILE")
fi

if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=stir-devtunnel" 2>/dev/null; then
  if [[ -z "$TUNNEL_ID" ]]; then
    echo "Creating persistent Dev Tunnel…"
    TUNNEL_ID=$("$DEVTUNNEL" create --allow-anonymous -d "STIR curves live" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnel']['tunnelId'])")
    echo "$TUNNEL_ID" > "$TUNNEL_ID_FILE"
    "$DEVTUNNEL" port create "$TUNNEL_ID" -p "$PORT" --protocol http
  fi
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s stir-devtunnel -c "$(pwd)" \
    -- bash -lc "$DEVTUNNEL host $TUNNEL_ID -p $PORT --allow-anonymous --protocol http 2>&1 | tee $LOG_DIR/devtunnel.log"
  echo "Started stir-devtunnel ($TUNNEL_ID)"
else
  echo "stir-devtunnel already running"
  TUNNEL_ID=${TUNNEL_ID:-$(cat "$TUNNEL_ID_FILE" 2>/dev/null || true)}
fi

sleep 5
URL=$(rg -o "https://[a-z0-9-]+-[0-9]+\.[^/]+\.devtunnels\.ms" "$LOG_DIR/devtunnel.log" 2>/dev/null | tail -1 || true)
if [[ -z "$URL" ]]; then
  URL=$(rg -o "https://[a-z0-9-]+\.[a-z0-9]+\.devtunnels\.ms" "$LOG_DIR/devtunnel.log" 2>/dev/null | tail -1 || true)
fi
if [[ -n "$URL" ]]; then
  echo "$URL" > "$TUNNEL_URL_FILE"
  echo ""
  echo "=========================================="
  echo " LIVE DASHBOARD (Dev Tunnel)"
  echo " $URL"
  echo "=========================================="
else
  echo "Tunnel starting — check: tail -f $LOG_DIR/devtunnel.log"
  echo "Tunnel ID: $TUNNEL_ID"
fi
