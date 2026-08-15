"""
SOFR - FFR overnight basis since SOFR inception (Apr 2018).

User definition: the daily difference between SOFR and FFR (SOFR - EFFR),
aggregated to the monthly average of those daily differences.

Outputs:
  - data/sofr_ffr_monthly_basis.csv   (every month, avg daily basis in bp)
  - data/sofr_ffr_daily_basis.csv     (daily SOFR, EFFR, basis in bp)
  - charts/sofr_ffr_distribution.png  (histogram of monthly averages)
  - prints distribution summary + peak months

Basis (bp) = (SOFR - EFFR) * 100.
Note: this is the negative of the repo's existing EFFR-SOFR ("SOFR/FF") series.
"""
import numpy as np
import pandas as pd
import requests

NYFED = ("https://markets.newyorkfed.org/api/rates/{group}/{rate}"
         "/search.json?startDate=2018-04-01&endDate=2026-12-31")
HEADERS = {"User-Agent": "Mozilla/5.0"}
INCEPTION = "2018-04-03"  # first SOFR publication


def fetch(name, group, rate):
    r = requests.get(NYFED.format(group=group, rate=rate), timeout=60, headers=HEADERS)
    r.raise_for_status()
    rows = r.json()["refRates"]
    return pd.Series(
        {pd.to_datetime(d["effectiveDate"]): float(d["percentRate"]) for d in rows},
        name=name,
    ).sort_index()


def main():
    sofr = fetch("SOFR", "secured", "sofr")
    effr = fetch("EFFR", "unsecured", "effr")

    df = pd.concat([sofr, effr], axis=1, sort=True).dropna()
    df = df[df.index >= INCEPTION]
    df["basis_bp"] = (df["SOFR"] - df["EFFR"]) * 100.0

    # Monthly average of daily differences
    m = df["basis_bp"].resample("MS").mean().dropna()
    monthly = m.to_frame("avg_basis_bp")
    monthly.index.name = "month"
    monthly_out = monthly.copy()
    monthly_out.index = monthly_out.index.strftime("%Y-%m")
    monthly_out["avg_basis_bp"] = monthly_out["avg_basis_bp"].round(3)
    monthly_out.to_csv("data/sofr_ffr_monthly_basis.csv")

    daily_out = df.copy()
    daily_out.index = daily_out.index.strftime("%Y-%m-%d")
    daily_out.index.name = "date"
    daily_out.round(4).to_csv("data/sofr_ffr_daily_basis.csv")

    arr = m.values.astype(float)
    n = len(arr)

    # ---- Distribution ----
    stats = {
        "n_months": n,
        "start": monthly_out.index[0],
        "end": monthly_out.index[-1],
        "mean": np.mean(arr),
        "median": np.median(arr),
        "std": np.std(arr, ddof=1),
        "min": np.min(arr),
        "max": np.max(arr),
        "p05": np.percentile(arr, 5),
        "p10": np.percentile(arr, 10),
        "p25": np.percentile(arr, 25),
        "p75": np.percentile(arr, 75),
        "p90": np.percentile(arr, 90),
        "p95": np.percentile(arr, 95),
        "skew": float(pd.Series(arr).skew()),
        "kurtosis": float(pd.Series(arr).kurtosis()),
    }

    print("=== SOFR - FFR monthly-average basis (bp) ===")
    print(f"Window: {stats['start']} -> {stats['end']}  ({n} months)")
    print(f"Mean   {stats['mean']:+.2f}   Median {stats['median']:+.2f}   Std {stats['std']:.2f}")
    print(f"Min    {stats['min']:+.2f}   Max    {stats['max']:+.2f}")
    print(f"P05 {stats['p05']:+.2f}  P10 {stats['p10']:+.2f}  P25 {stats['p25']:+.2f}  "
          f"P75 {stats['p75']:+.2f}  P90 {stats['p90']:+.2f}  P95 {stats['p95']:+.2f}")
    print(f"Skew {stats['skew']:+.2f}  Excess kurtosis {stats['kurtosis']:+.2f}")

    # ---- Peak months (highest SOFR - FFR) ----
    top = monthly["avg_basis_bp"].sort_values(ascending=False).head(10)
    print("\n=== Top 10 peak months (SOFR richest vs FFR) ===")
    for ym, v in top.items():
        print(f"  {ym.strftime('%Y-%m')}  {v:+.2f} bp")

    low = monthly["avg_basis_bp"].sort_values().head(5)
    print("\n=== 5 most negative months (SOFR softest vs FFR) ===")
    for ym, v in low.items():
        print(f"  {ym.strftime('%Y-%m')}  {v:+.2f} bp")

    # Which calendar month tends to peak?
    by_cal = monthly.copy()
    by_cal["cal_month"] = by_cal.index.month
    cal_mean = by_cal.groupby("cal_month")["avg_basis_bp"].mean()
    cal_name = {i: pd.Timestamp(2020, i, 1).strftime("%b") for i in range(1, 13)}
    print("\n=== Average basis by calendar month ===")
    for i, v in cal_mean.items():
        print(f"  {cal_name[i]}  {v:+.2f} bp")
    peak_cal = cal_mean.idxmax()
    print(f"Seasonal peak calendar month: {cal_name[peak_cal]} ({cal_mean.max():+.2f} bp)")

    # ---- Distribution chart ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.5))
    lo, hi = np.floor(arr.min()), np.ceil(arr.max())
    bins = np.arange(lo, hi + 1.0, 1.0)
    ax.hist(arr, bins=bins, color="#2b6cb0", edgecolor="white", alpha=0.9)
    ax.axvline(stats["mean"], color="#e53e3e", lw=2, ls="--",
               label=f"Mean {stats['mean']:+.2f} bp")
    ax.axvline(stats["median"], color="#38a169", lw=2, ls=":",
               label=f"Median {stats['median']:+.2f} bp")
    ax.set_title("Distribution of monthly-average SOFR - FFR basis "
                 f"({stats['start']} to {stats['end']}, n={n})")
    ax.set_xlabel("Monthly-average daily (SOFR - FFR), bp")
    ax.set_ylabel("Number of months")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("charts/sofr_ffr_distribution.png", dpi=130)
    print("\nWrote data/sofr_ffr_monthly_basis.csv, data/sofr_ffr_daily_basis.csv, "
          "charts/sofr_ffr_distribution.png")


if __name__ == "__main__":
    main()
