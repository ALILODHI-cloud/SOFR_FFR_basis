# FFR − SOFR Basis: Monthly-Average Distribution, Persistence & July Trade

Analysis of the **FFR − SOFR** overnight basis (EFFR − SOFR, in bp) since SOFR inception
(Apr 2018), built to evaluate the trade **"July FFR−SOFR average > −1bp"** (Barclays
"long July SOFR/FF", entry −1.0bp, target +2bp).

## Contents
- `analyze.py` — pulls daily EFFR & SOFR (NY Fed reference rates / FRED-mirrored),
  computes calendar-month averages, the distribution, percentile of −1bp, autocorrelation
  (ACF/PACF), and predictive regressions (AR(1) and trailing-3-month). Writes `basis_data.json`.
- `build_app.py` — builds the self-contained dashboard from `basis_data.json`.
- `index.html` — responsive (mobile + desktop) dashboard: verdict, distribution histogram,
  full history, autocorrelation cards, July seasonality, and the full trade write-up.
- `basis_data.json` — computed snapshot used by the dashboard.
- `analyze_sonia.py` — UK 1M SONIA Dec-27/Dec-26 slope, basis, Brent correlation & vol; writes `sonia_dashboard_data.json` (uses Playwright for ICE futures settles via Barchart).
- `build_sonia_dashboard.py` — builds `sonia_dashboard.html` from that JSON.
- `sonia_dashboard.html` — interactive UK rates monitor (50-session window, Chart.js hover tooltips).
- `spx_dispersion.py` — pulls 10 years of Yahoo Finance daily prices for SPX and the current
  top 10 S&P 500 constituents, then plots 60-day annualized dispersion
  (`SPX vol − average top-10 constituent vol`). Writes `data/spx_dispersion_60d_10y.csv`
  and `charts/spx_dispersion_60d_10y.png`.

## Reproduce
```bash
python analyze.py        # refresh data + stats
python build_app.py      # rebuild index.html
pip3 install -r requirements-spx.txt
python3 spx_dispersion.py # refresh SPX dispersion chart + CSV
```

Override the top-ten constituent list with `--symbols NVDA,AAPL,MSFT,AMZN,GOOGL,GOOG,AVGO,META,TSLA,BRK-B`.

### SONIA dashboard — permanent link + auto-refresh

**One-time setup (you do this once):**
1. Merge this branch to `main` (or ask the agent to)
2. Open **https://github.com/ALILODHI-cloud/SOFR_FFR_basis/settings/pages**
3. Set **Source → GitHub Actions**

**Permanent URL:** https://alilodhi-cloud.github.io/SOFR_FFR_basis/

GitHub Actions refreshes from **Barchart** twice on weekdays (~10:00 and ~18:30 London) and redeploys automatically. You can also trigger manually: **Actions → SONIA dashboard — fetch, build, deploy → Run workflow**.

**Local refresh:**
```bash
pip install -r requirements-sonia.txt
playwright install chromium
python analyze_sonia.py
python build_sonia_dashboard.py
python serve_sonia_dashboard.py   # http://127.0.0.1:8765/sonia_dashboard.html
```

Do **not** use `*.trycloudflare.com` links — they expire when the cloud agent stops.

### 1M SONIA curve dashboard — permanent link + live refresh

**Permanent URL (static, auto-refreshed weekdays):**  
https://alilodhi-cloud.github.io/SOFR_FFR_basis/sonia_1m_dashboard.html

**One-time setup (you do this once):**
1. Merge the `cursor/sonia-1m-live-dashboard-3cf3` branch to `main`
2. Open **https://github.com/ALILODHI-cloud/SOFR_FFR_basis/settings/pages**
3. Set **Source → GitHub Actions**

GitHub Actions fetches all 24 1M SONIA contracts from Barchart twice on weekdays (~10:00 and ~18:30 London) and redeploys. Trigger manually: **Actions → 1M SONIA curve — fetch, build, deploy → Run workflow**.

**Live server (auto-refresh + MPC pricing + daily Δ table):**
```bash
python3 analyze_sonia_1m.py
python3 build_sonia_1m_dashboard.py
./scripts/start_sonia_1m_live.sh    # Dev Tunnel if logged in, else Cloudflare
```

Stable Dev Tunnel URL (same link across restarts, while this machine is on):
```bash
./devtunnel user login -g -d    # one-time
./scripts/start_sonia_1m_devtunnel.sh
# URL saved to .sonia_1m_devtunnel_url
```

### 3M SOFR curve dashboard — permanent link + live refresh

**Permanent URL (static, auto-refreshed weekdays):**  
https://alilodhi-cloud.github.io/SOFR_FFR_basis/sofr_3m_dashboard.html

Same UX as the 1M SONIA dashboard: frozen latest curve (green), historical time-travel (amber), pin legs, FOMC meeting pricing panel, and daily Δ table across all listed quarterly contracts.

GitHub Actions fetches all CME 3M SOFR (`SQ*`) contracts from Barchart twice on weekdays (~10:00 and ~18:30 London) and redeploys. Trigger manually: **Actions → 3M SOFR curve — fetch, build, deploy → Run workflow**.

**Live server (auto-refresh + FOMC pricing + daily Δ table):**
```bash
python3 analyze_sofr_3m.py
python3 build_sofr_3m_dashboard.py
./scripts/start_sofr_3m_live.sh    # Dev Tunnel if logged in, else Cloudflare
```

Stable Dev Tunnel URL (same link across restarts, while this machine is on):
```bash
./devtunnel user login -g -d    # one-time
./scripts/start_sofr_3m_devtunnel.sh
# URL saved to .sofr_3m_devtunnel_url
```

### Live trade tracker

**URL:** https://alilodhi-cloud.github.io/SOFR_FFR_basis/trade_tracker.html

Pages load JSON at runtime — **refresh is data-only** (no HTML rebuild):

```bash
pip install -r requirements-sonia.txt
playwright install chromium
python3 analyze_spread_trades.py   # Barchart EOD → trades_index.json + *_trade_data.json
```

Rebuild HTML shells only when adding a new trade or changing layout:

```bash
python3 build_trade_tracker.py
```

## Key findings
- 99 months (Apr-2018 → Jun-2026). Mean ≈ +0.2bp, median ≈ +0.5bp, std ≈ 4.2bp.
- **−1bp sits around the ~30th percentile** — ~70% of months printed above it.
- Strong persistence: AR(1) β ≈ 0.61; trailing-3m → next-month β ≈ 0.72.
- Models imply a July expectation of roughly **+0.3 to +1.2bp**, above the −1bp priced.
- Main risk: fat left tail (e.g. Sep-2019 and late-2025 funding spikes).

> Note: extracted text from Barclays Global Rates Weekly reports is intentionally excluded
> from version control (`pages_dump.txt` is gitignored) as it is restricted research.
