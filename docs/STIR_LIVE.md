# STIR Curves Live Dashboard

Full **3M SOFR / SONIA / €STR** forward curves from **Barchart EOD**, auto-refreshing.

## What you get

| Curve | Barchart prefix | Contracts (typical) |
|---|---|---|
| 3M SOFR | `SQ*` | **39** (Jun-26 → Dec-35) |
| 3M SONIA | `J8*` | **24** (listed ICE quarterlies) |
| 3M €STR | `EB*` | **25** (Jun-26 → Jun-32) |

**88+ contracts total** — every quarterly 3M contract on each Barchart chain.

Panels:
- Full curve per currency (every listed contract)
- All-contract table with symbol, delivery, rate
- Calendar slopes (Dec-28−Jun-27, etc.) over time
- Per-currency history (every contract line)

## Live server

```bash
python3 analyze_stir_curves.py      # fetch all chains (~3–5 min)
python3 build_stir_curves_dashboard.py
python3 serve_stir_live.py            # http://localhost:8787
```

- `GET /` — dashboard (polls `/api/data` every 60s)
- `GET /api/data` — JSON snapshot
- `GET /api/status` — refresh schedule
- `POST /api/refresh` — trigger Barchart fetch

Auto-refresh default: **every 30 minutes** (`STIR_REFRESH_MINUTES=30`).

## Microsoft Dev Tunnel (persistent URL)

1. Install CLI: https://aka.ms/devtunnels/download (or use `./devtunnel` in repo root)
2. Login once (GitHub or Microsoft):
   ```bash
   ./devtunnel user login -g -d
   ```
3. Start stack:
   ```bash
   ./scripts/start_stir_devtunnel.sh
   ```
4. URL saved to `.stir_devtunnel_url` — **stable across restarts** (same tunnel ID).

Anonymous access is enabled (`--allow-anonymous`) so you can open the link on your phone without signing in.

## Quick start (this VM)

Live server + Cloudflare quick tunnel (temporary URL while Dev Tunnel auth is pending):

```bash
python3 serve_stir_live.py &
# expose with devtunnel or cloudflared
```

## Rebuild only

```bash
python3 analyze_stir_curves.py && python3 build_stir_curves_dashboard.py
```

Not investment advice. Barchart EOD settles; futures quoted `100 − rate`.
