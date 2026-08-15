"""
SPY realized volatility, monthly, last ~20 years.

For each calendar month we compute the realized volatility of SPY from daily
log returns and annualize it:
    rv_annual_pct = std(daily_log_ret, ddof=1) * sqrt(252) * 100

Data: Yahoo Finance daily adjusted closes (range=20y).
Outputs:
  data/spy_realized_vol_monthly.csv  (month, trading_days, rv_annual_pct, rv_monthly_pct)
  charts/spy_realized_vol_monthly.png (time series)
"""
import json, urllib.request, time, os, datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
TRADING_DAYS = 252


def fetch(symbol, rng="20y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={rng}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.load(r)
            res = j["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]["close"]
            adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q)
            out = {}
            for t, a, c in zip(ts, adj, q):
                val = a if a is not None else c
                if val is None:
                    continue
                out[dt.datetime.utcfromtimestamp(t).date()] = val
            return out
        except Exception as e:
            print("retry", symbol, attempt, e); time.sleep(3)
    raise SystemExit("fetch failed " + symbol)


def main():
    spy = fetch("SPY")
    s = pd.Series(spy).sort_index()
    s.index = pd.to_datetime(s.index)

    logret = np.log(s / s.shift(1)).dropna()

    g = logret.groupby(logret.index.to_period("M"))
    rv = g.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0       # annualized %
    rv_m = g.std(ddof=1) * np.sqrt(21) * 100.0               # monthly-horizon %
    ndays = g.size()

    out = pd.DataFrame({
        "trading_days": ndays,
        "rv_annual_pct": rv.round(2),
        "rv_monthly_pct": rv_m.round(2),
    })
    # require a reasonably complete month
    out = out[out["trading_days"] >= 5]
    out.index = out.index.astype(str)
    out.index.name = "month"
    out.to_csv("data/spy_realized_vol_monthly.csv")

    arr = out["rv_annual_pct"].values.astype(float)
    print("=== SPY monthly realized volatility (annualized %), last ~20y ===")
    print(f"Window: {out.index[0]} -> {out.index[-1]}  ({len(out)} months)")
    print(f"Mean {arr.mean():.1f}  Median {np.median(arr):.1f}  Std {arr.std(ddof=1):.1f}")
    print(f"Min {arr.min():.1f}  Max {arr.max():.1f}")
    print(f"P10 {np.percentile(arr,10):.1f}  P25 {np.percentile(arr,25):.1f}  "
          f"P75 {np.percentile(arr,75):.1f}  P90 {np.percentile(arr,90):.1f}")

    top = out["rv_annual_pct"].sort_values(ascending=False).head(10)
    print("\n=== Top 10 highest-vol months ===")
    for ym, v in top.items():
        print(f"  {ym}  {v:.1f}%")
    low = out["rv_annual_pct"].sort_values().head(5)
    print("\n=== 5 calmest months ===")
    for ym, v in low.items():
        print(f"  {ym}  {v:.1f}%")

    # ---- chart ----
    plt.rcParams.update({"figure.facecolor": "#0e1117", "axes.facecolor": "#0e1117",
        "savefig.facecolor": "#0e1117", "text.color": "#e6e6e6", "axes.labelcolor": "#e6e6e6",
        "xtick.color": "#b8b8b8", "ytick.color": "#b8b8b8", "axes.edgecolor": "#3a3f4b",
        "axes.grid": True, "grid.color": "#222631"})
    x = pd.to_datetime(out.index + "-01")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(x, arr, color="#3b82f6", lw=1.4)
    ax.fill_between(x, arr, color="#3b82f6", alpha=0.15)
    ax.axhline(arr.mean(), color="#ef4444", lw=1.5, ls="--", label=f"Mean {arr.mean():.1f}%")
    ax.set_title(f"SPY monthly realized volatility (annualized), {out.index[0]}–{out.index[-1]}")
    ax.set_xlabel("Month"); ax.set_ylabel("Annualized realized vol (%)")
    ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6")
    fig.tight_layout(); fig.savefig("charts/spy_realized_vol_monthly.png", dpi=130)
    print("\nWrote data/spy_realized_vol_monthly.csv, charts/spy_realized_vol_monthly.png")


if __name__ == "__main__":
    main()
