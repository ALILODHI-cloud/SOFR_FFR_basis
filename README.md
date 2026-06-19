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

## Reproduce
```bash
python analyze.py        # refresh data + stats
python build_app.py      # rebuild index.html
```

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

## Key findings
- 99 months (Apr-2018 → Jun-2026). Mean ≈ +0.2bp, median ≈ +0.5bp, std ≈ 4.2bp.
- **−1bp sits around the ~30th percentile** — ~70% of months printed above it.
- Strong persistence: AR(1) β ≈ 0.61; trailing-3m → next-month β ≈ 0.72.
- Models imply a July expectation of roughly **+0.3 to +1.2bp**, above the −1bp priced.
- Main risk: fat left tail (e.g. Sep-2019 and late-2025 funding spikes).

> Note: extracted text from Barclays Global Rates Weekly reports is intentionally excluded
> from version control (`pages_dump.txt` is gitignored) as it is restricted research.
