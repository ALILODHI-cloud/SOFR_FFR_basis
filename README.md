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

## Reproduce
```bash
python analyze.py        # refresh data + stats
python build_app.py      # rebuild index.html
```

## Key findings
- 99 months (Apr-2018 → Jun-2026). Mean ≈ +0.2bp, median ≈ +0.5bp, std ≈ 4.2bp.
- **−1bp sits around the ~30th percentile** — ~70% of months printed above it.
- Strong persistence: AR(1) β ≈ 0.61; trailing-3m → next-month β ≈ 0.72.
- Models imply a July expectation of roughly **+0.3 to +1.2bp**, above the −1bp priced.
- Main risk: fat left tail (e.g. Sep-2019 and late-2025 funding spikes).

> Note: extracted text from Barclays Global Rates Weekly reports is intentionally excluded
> from version control (`pages_dump.txt` is gitignored) as it is restricted research.

---

# SPY Realized Monthly Volatility (20-Year History)

Computes **SPY realized monthly volatility** from Investing.com daily prices over the
trailing 20 years and identifies the most volatile month.

## Contents
- `spy_vol.py` — pulls SPY daily closes from **Investing.com** (SPDR S&P 500 ETF,
  pair_id `525`, via the `investgo` client), computes per-calendar-month realized vol
  from daily log returns, and writes `spy_vol_data.json`.
- `build_spy_vol.py` — builds the responsive dashboard `spy_vol.html` from the JSON.
- `spy_vol_data.json` / `spy_vol.html` — computed snapshot + dashboard.

## Reproduce
```bash
pip install investgo
python spy_vol.py          # fetch + compute (writes spy_vol_data.json)
python build_spy_vol.py    # rebuild spy_vol.html
```

## Method
Daily close-to-close log returns `r_t = ln(P_t / P_{t-1})`, grouped by calendar month:
- `rv_ann  = sqrt(252/n · Σr²)` — annualized realized vol (primary ranking)
- `std_ann = std(r)·sqrt(252)` — annualized sample-std vol
- `rv_month = sqrt(Σr²)` — non-annualized monthly realized vol

## Key finding
- **March 2020 (COVID crash) had the highest SPY realized monthly volatility ≈ 89% annualized**,
  narrowly ahead of **October 2008 ≈ 87%** (GFC) and November 2008 ≈ 70%.
