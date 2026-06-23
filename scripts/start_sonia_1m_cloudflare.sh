#!/usr/bin/env bash
# Quick Cloudflare tunnel for 1M SONIA live dashboard (URL changes each VM session).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${SONIA_1M_PORT:-8790}"
URL_FILE=".sonia_1m_cloudflare_url"
LOG_DIR="${LOG_DIR:-/tmp/sonia-1m-live}"
mkdir -p "$LOG_DIR"

if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=sonia-1m-server" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s sonia-1m-server -c "$(pwd)" \
    -- bash -lc "python3 serve_sonia_1m_live.py 2>&1 | tee $LOG_DIR/server.log"
fi

sleep 2

if ! tmux -f /exec-daemon/tmux.portal.conf has-session -t "=sonia-1m-cf" 2>/dev/null; then
  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s sonia-1m-cf -c "$(pwd)" \
    -- bash -lc "npx --yes cloudflared tunnel --url http://127.0.0.1:$PORT 2>&1 | tee $LOG_DIR/cf.log"
fi

for _ in $(seq 1 30); do
  URL=$(rg -o 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/cf.log" 2>/dev/null | tail -1 || true)
  [[ -n "$URL" ]] && break
  sleep 1
done

if [[ -n "$URL" ]]; then
  echo "$URL" > "$URL_FILE"
  echo "Live dashboard (session): $URL"
  echo "Saved to $URL_FILE"
else
  echo "Tunnel starting — check: tail -f $LOG_DIR/cf.log"
  exit 1
fi
