"""
Monthly return series of SDIA.L
  = iShares $ Short Duration Corp Bond UCITS ETF USD (Acc), LSE, USD.

The Acc (accumulating) share class reinvests coupons, so its price is a
total-return series -- monthly % change of month-end price is the total return.

Data: Yahoo Finance daily (range=max), resampled to month-end.
Outputs:
  data/SDIA_monthly_returns.csv  (month, month_end_price, ret_pct, cum_growth)
  charts/sdia_monthly_returns.png (bar of monthly returns + cumulative line)
"""
import urllib.request, json, time, datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
SYMBOL = "SDIA.L"


def get(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode()
        except Exception as e:
            print("retry", a, e); time.sleep(2 ** a)
    raise SystemExit("fetch failed")


def main():
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{SYMBOL}?interval=1d&range=max"
    j = json.loads(get(url))
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]["close"]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q)
    s = pd.Series(
        {pd.Timestamp(dt.date.fromtimestamp(t)): (a if a is not None else c)
         for t, a, c in zip(ts, adj, q) if (a is not None or c is not None)}
    ).sort_index()

    # month-end price -> monthly total return
    me = s.resample("ME").last().dropna()
    ret = me.pct_change() * 100.0
    out = pd.DataFrame({"month_end_price": me.round(4), "ret_pct": ret.round(3)})
    out = out.dropna(subset=["ret_pct"])
    out["cum_growth"] = (1 + out["ret_pct"] / 100.0).cumprod().round(4)
    out.index = out.index.strftime("%Y-%m"); out.index.name = "month"
    out.to_csv("data/SDIA_monthly_returns.csv")

    r = out["ret_pct"].values.astype(float)
    n = len(r)
    ann_ret = (out["cum_growth"].iloc[-1] ** (12.0 / n) - 1) * 100
    ann_vol = r.std(ddof=1) * np.sqrt(12)
    print(f"=== {SYMBOL}  iShares $ Short Duration Corp Bond UCITS ETF (Acc), monthly total return ===")
    print(f"Window {out.index[0]} -> {out.index[-1]}  ({n} months)")
    print(f"Mean {r.mean():+.3f}%/mo  Std {r.std(ddof=1):.3f}%/mo  "
          f"Ann.return {ann_ret:+.2f}%  Ann.vol {ann_vol:.2f}%")
    print(f"Total growth x{out['cum_growth'].iloc[-1]:.3f}  "
          f"Best {r.max():+.2f}% Worst {r.min():+.2f}%  Positive months {(r>0).mean()*100:.0f}%")
    print("\nBest 5 months:")
    for ym, v in out["ret_pct"].sort_values(ascending=False).head(5).items():
        print(f"  {ym}  {v:+.2f}%")
    print("Worst 5 months:")
    for ym, v in out["ret_pct"].sort_values().head(5).items():
        print(f"  {ym}  {v:+.2f}%")

    # ---- chart ----
    plt.rcParams.update({"figure.facecolor": "#0e1117", "axes.facecolor": "#0e1117",
        "savefig.facecolor": "#0e1117", "text.color": "#e6e6e6", "axes.labelcolor": "#e6e6e6",
        "xtick.color": "#b8b8b8", "ytick.color": "#b8b8b8", "axes.edgecolor": "#3a3f4b",
        "axes.grid": True, "grid.color": "#222631"})
    x = pd.to_datetime(out.index + "-01")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in r]
    ax1.bar(x, r, width=20, color=colors)
    ax1.axhline(0, color="#8b949e", lw=0.8)
    ax1.set_ylabel("Monthly total return (%)")
    ax1.set_title(f"{SYMBOL} — iShares $ Short Duration Corp Bond UCITS ETF (Acc): "
                  f"monthly total return ({out.index[0]}–{out.index[-1]})")
    ax2.plot(x, out["cum_growth"].values, color="#3b82f6", lw=1.8)
    ax2.fill_between(x, out["cum_growth"].values, 1, color="#3b82f6", alpha=0.15)
    ax2.set_ylabel("Growth of $1")
    ax2.set_xlabel("Month")
    fig.tight_layout(); fig.savefig("charts/sdia_monthly_returns.png", dpi=130)
    print("\nWrote data/SDIA_monthly_returns.csv, charts/sdia_monthly_returns.png")


if __name__ == "__main__":
    main()
