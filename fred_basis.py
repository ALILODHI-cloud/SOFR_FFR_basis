"""
FFR - SOFR overnight basis: monthly-average distribution, sourced from FRED.

Pulls daily series from FRED (no API key needed via fredgraph.csv):
  EFFR = Effective Federal Funds Rate (daily)    -> FRED series 'EFFR'
  SOFR = Secured Overnight Financing Rate (daily)-> FRED series 'SOFR'

If FRED is unreachable from the run environment, it transparently falls back to
the NY Fed reference-rate API, which is the official upstream that FRED
republishes these exact series from (the daily values are identical).

Difference is defined as (EFFR - SOFR), reported in basis points:
  basis_bp = (EFFR - SOFR) * 100

Outputs:
  - console summary of the monthly-average distribution since SOFR inception
  - where an average difference of -1bp sits in that distribution
  - monthly_basis_fred.csv   (monthly averages)
  - basis_distribution_fred.png (time series + histogram of the distribution)
"""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
NYFED = ("https://markets.newyorkfed.org/api/rates/{group}/{rate}/search.json"
         "?startDate=2018-04-01&endDate=2100-12-31")
NYFED_MAP = {"EFFR": ("unsecured", "effr"), "SOFR": ("secured", "sofr")}
HEADERS = {"User-Agent": "Mozilla/5.0"}
TARGET = -1.0  # the average difference (in bp) to locate within the distribution


def fetch_fred(series: str) -> pd.Series:
    """Download a daily FRED series as a date-indexed pandas Series."""
    url = FRED_CSV.format(series=series)
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    date_col, val_col = df.columns[0], df.columns[1]
    df[date_col] = pd.to_datetime(df[date_col])
    # FRED encodes missing observations as "."
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    s = df.set_index(date_col)[val_col].dropna()
    s.name = series
    return s


def fetch_nyfed(series: str) -> pd.Series:
    """Download a daily series from the NY Fed reference-rate API (FRED upstream)."""
    group, rate = NYFED_MAP[series]
    r = requests.get(NYFED.format(group=group, rate=rate), timeout=60, headers=HEADERS)
    r.raise_for_status()
    rows = r.json()["refRates"]
    s = pd.Series(
        {pd.to_datetime(d["effectiveDate"]): float(d["percentRate"]) for d in rows},
        name=series,
    ).sort_index()
    return s


def fetch(series: str) -> tuple[pd.Series, str]:
    """Prefer FRED; fall back to the NY Fed upstream if FRED is unreachable."""
    try:
        return fetch_fred(series), "FRED"
    except Exception as exc:  # noqa: BLE001 - network/parse fallbacks are expected
        print(f"  [warn] FRED fetch for {series} failed ({exc.__class__.__name__}); "
              f"falling back to NY Fed upstream.")
        return fetch_nyfed(series), "NY Fed (FRED upstream)"


def main() -> None:
    effr, src_e = fetch("EFFR")
    sofr, src_s = fetch("SOFR")
    source = src_e if src_e == src_s else f"{src_e} / {src_s}"
    print(f"Data source: {source}")
    print(f"Fetched EFFR: {len(effr)} obs ({effr.index.min().date()} -> {effr.index.max().date()})")
    print(f"Fetched SOFR: {len(sofr)} obs ({sofr.index.min().date()} -> {sofr.index.max().date()})")

    # Inner join on common business days -> only days where both rates exist.
    df = pd.concat([effr, sofr], axis=1).dropna()
    # Restrict to the SOFR sample (SOFR inception = first available SOFR date).
    df = df[df.index >= sofr.index.min()]
    df["diff_bp"] = (df["EFFR"] - df["SOFR"]) * 100.0

    # Monthly average of the daily difference (calendar-month mean).
    monthly = df["diff_bp"].resample("MS").mean().dropna()
    arr = monthly.values.astype(float)
    n = len(arr)

    # ---- Distribution stats ----
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1))
    mn, mx = float(np.min(arr)), float(np.max(arr))

    # Where -1bp sits in the distribution.
    pct_below = float((arr < TARGET).mean() * 100.0)
    pct_at_or_below = float((arr <= TARGET).mean() * 100.0)
    # Mid-rank percentile (handles ties at exactly -1).
    percentile_rank = float((np.sum(arr < TARGET) + 0.5 * np.sum(arr == TARGET)) / n * 100.0)

    # ---- Save monthly series to CSV ----
    out = monthly.to_frame("avg_diff_bp")
    out.index.name = "month"
    out.to_csv("monthly_basis_fred.csv", date_format="%Y-%m")

    # ---- Plot: time series + histogram ----
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.6, 1.0]}
    )

    # (1) Monthly average over time
    ax1.bar(monthly.index, arr, width=20,
            color=np.where(arr >= 0, "#2a7", "#d44"), alpha=0.85)
    ax1.axhline(0, color="#444", lw=0.8)
    ax1.axhline(TARGET, color="#06c", lw=1.4, ls="--", label=f"{TARGET:.0f} bp")
    ax1.axhline(mean, color="#000", lw=1.0, ls=":", label=f"mean {mean:.2f} bp")
    ax1.set_title("Monthly average of daily (EFFR − SOFR) — full sample")
    ax1.set_ylabel("basis points")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(axis="y", alpha=0.25)

    # (2) Distribution histogram
    lo = np.floor(min(mn, TARGET))
    hi = np.ceil(mx)
    bins = np.arange(lo, hi + 1.0, 1.0)
    ax2.hist(arr, bins=bins, color="#69a", edgecolor="white", alpha=0.9)
    ax2.axvline(TARGET, color="#06c", lw=1.8, ls="--",
                label=f"{TARGET:.0f} bp  (~{percentile_rank:.0f}th pct)")
    ax2.axvline(median, color="#000", lw=1.2, ls=":", label=f"median {median:.2f} bp")
    ax2.set_title(f"Distribution of monthly averages (n={n})")
    ax2.set_xlabel("basis points")
    ax2.set_ylabel("# of months")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle(
        f"FFR − SOFR basis  |  {monthly.index[0]:%b %Y} – {monthly.index[-1]:%b %Y}  "
        f"(source: {source} — EFFR & SOFR)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig("basis_distribution_fred.png", dpi=130)
    print("Saved basis_distribution_fred.png and monthly_basis_fred.csv")

    # ---- Console summary ----
    print("\n=== Monthly average of daily (EFFR − SOFR), in bp ===")
    print(f"Sample: {monthly.index[0]:%Y-%m} -> {monthly.index[-1]:%Y-%m}  ({n} months)")
    print(f"Mean   = {mean:+.2f} bp")
    print(f"Median = {median:+.2f} bp")
    print(f"Std    = {std:.2f} bp")
    print(f"Min    = {mn:+.2f} bp  ({monthly.idxmin():%Y-%m})")
    print(f"Max    = {mx:+.2f} bp  ({monthly.idxmax():%Y-%m})")
    for p in (5, 10, 25, 50, 75, 90, 95):
        print(f"  p{p:<2d} = {np.percentile(arr, p):+.2f} bp")
    print(f"\nWhere does an average difference of {TARGET:.0f} bp sit?")
    print(f"  percentile rank of {TARGET:.0f} bp : ~{percentile_rank:.1f}th percentile")
    print(f"  months strictly below {TARGET:.0f} bp : {pct_below:.1f}%")
    print(f"  months at or below {TARGET:.0f} bp   : {pct_at_or_below:.1f}%")
    print(f"  => ~{100 - pct_at_or_below:.1f}% of months printed above {TARGET:.0f} bp")


if __name__ == "__main__":
    main()
