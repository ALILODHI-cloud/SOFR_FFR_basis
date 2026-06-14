# FFR − SOFR Basis: Monthly-Average Distribution, Persistence & July Trade

Analysis of the **FFR − SOFR** overnight basis (EFFR − SOFR, in bp) since SOFR inception
(Apr 2018), built to evaluate the trade **"July FFR−SOFR average > −1bp"** (Barclays
"long July SOFR/FF", entry −1.0bp, target +2bp).

## Contents
- `fred_basis.py` — focused, FRED-sourced answer to "compute the monthly average of
  daily (EFFR − SOFR) since SOFR inception, show its distribution, and locate −1bp".
  Pulls daily EFFR & SOFR from FRED (`fredgraph.csv`, no API key), automatically
  falling back to the NY Fed upstream when FRED is unreachable. Writes
  `monthly_basis_fred.csv` and `basis_distribution_fred.png` (time series + histogram).
- `analyze.py` — pulls daily EFFR & SOFR (NY Fed reference rates / FRED-mirrored),
  computes calendar-month averages, the distribution, percentile of −1bp, autocorrelation
  (ACF/PACF), and predictive regressions (AR(1) and trailing-3-month). Writes `basis_data.json`.
- `build_app.py` — builds the self-contained dashboard from `basis_data.json`.
- `index.html` — responsive (mobile + desktop) dashboard: verdict, distribution histogram,
  full history, autocorrelation cards, July seasonality, and the full trade write-up.
- `basis_data.json` — computed snapshot used by the dashboard.

## Reproduce
```bash
python fred_basis.py     # FRED data -> monthly distribution + chart + where -1bp sits
python analyze.py        # refresh data + stats (full dashboard dataset)
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
