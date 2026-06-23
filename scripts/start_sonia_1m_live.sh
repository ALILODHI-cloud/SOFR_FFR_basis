#!/usr/bin/env bash
# Start 1M SONIA live stack. Prefers Dev Tunnel (stable URL); falls back to Cloudflare.
set -euo pipefail
cd "$(dirname "$0")/.."
DEVTUNNEL="${DEVTUNNEL_BIN:-./devtunnel}"
[[ -x "$DEVTUNNEL" ]] || DEVTUNNEL=devtunnel

if "$DEVTUNNEL" user show &>/dev/null; then
  exec bash scripts/start_sonia_1m_devtunnel.sh
fi

echo "Dev Tunnel not logged in — using Cloudflare quick tunnel (expires when VM stops)."
echo "For a permanent URL: ./devtunnel user login -g -d && ./scripts/start_sonia_1m_devtunnel.sh"
echo "Or enable GitHub Pages — see README (1M SONIA section)."
exec bash scripts/start_sonia_1m_cloudflare.sh
