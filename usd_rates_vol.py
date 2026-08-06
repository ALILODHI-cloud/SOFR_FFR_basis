"""
USD 1y1y rate volatility over time -- best free proxies.

NOTE ON DATA: Actual 1y1y ATM USD swaption *implied* volatility (e.g. Bloomberg
USSV0101, ICAP/Tullett quotes) is a proprietary series with no free public source,
and no Bloomberg/FRED key is available in this environment. This script builds the
two best free proxies for the same volatility regime:

  1) MOVE index  -- the market-standard gauge of US RATES IMPLIED vol (1-month
     options on the 2/5/10/30y Treasuries). Source: Yahoo Finance (^MOVE).
  2) 1y1y forward REALIZED normal vol -- built from the US Treasury par-yield
     curve (1Yr & 2Yr CMT). The 1y1y forward f solves (1+r2)^2=(1+r1)(1+f);
     monthly realized normal vol = std(daily Δf in bp, ddof=1) * sqrt(252),
     i.e. bp/year, the same unit swaption desks quote normal vol in.

Outputs:
  data/move_index_monthly.csv
  data/usd_1y1y_fwd_realized_vol_monthly.csv
  charts/usd_1y1y_vol_over_time.png
"""
import urllib.request, json, time, io, datetime as dt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
TRADING_DAYS = 252


def get(url, timeout=45):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode()
        except Exception as e:
            print("  retry", a, e); time.sleep(2 ** a)
    return None


def fetch_move():
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%5EMOVE?interval=1d&range=max"
    j = json.loads(get(url))
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    close = res["indicators"]["quote"][0]["close"]
    s = pd.Series(
        {pd.Timestamp(dt.date.fromtimestamp(t)): c for t, c in zip(ts, close) if c is not None}
    ).sort_index()
    return s


def fetch_treasury():
    frames = []
    this_year = dt.date.today().year
    for yr in range(2002, this_year + 1):
        url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
               f"daily-treasury-rates.csv/{yr}/all?type=daily_treasury_yield_curve"
               f"&field_tdr_date_value={yr}&page&_format=csv")
        d = get(url)
        if not d:
            print("  treasury", yr, "FAILED"); continue
        df = pd.read_csv(io.StringIO(d))
        frames.append(df)
        print(f"  treasury {yr}: {len(df)} rows")
    all_df = pd.concat(frames, ignore_index=True)
    all_df["Date"] = pd.to_datetime(all_df["Date"])
    all_df = all_df.set_index("Date").sort_index()
    return all_df[["1 Yr", "2 Yr"]].dropna()


def main():
    print("Fetching MOVE index...")
    move = fetch_move()
    move_m = move.resample("MS").mean().dropna()
    mo = move_m.to_frame("move_index")
    mo.index = mo.index.strftime("%Y-%m"); mo.index.name = "month"
    mo.round(2).to_csv("data/move_index_monthly.csv")
    print(f"  MOVE monthly: {mo.index[0]} -> {mo.index[-1]} ({len(mo)} months)")

    print("Fetching US Treasury CMT (1Yr, 2Yr)...")
    cmt = fetch_treasury()
    r1 = cmt["1 Yr"] / 100.0
    r2 = cmt["2 Yr"] / 100.0
    fwd = ((1 + r2) ** 2 / (1 + r1) - 1.0) * 100.0   # 1y1y forward, in %
    dfwd_bp = fwd.diff() * 100.0                       # daily change in bp

    g = dfwd_bp.groupby(dfwd_bp.index.to_period("M"))
    rv = g.std(ddof=1) * np.sqrt(TRADING_DAYS)         # normal vol, bp/year
    nd = g.size()
    rvdf = pd.DataFrame({"trading_days": nd, "fwd_level_pct_eom": fwd.groupby(fwd.index.to_period("M")).last().round(3),
                         "realized_normal_vol_bp": rv.round(1)})
    rvdf = rvdf[rvdf["trading_days"] >= 5]
    rvdf.index = rvdf.index.astype(str); rvdf.index.name = "month"
    rvdf.to_csv("data/usd_1y1y_fwd_realized_vol_monthly.csv")

    rva = rvdf["realized_normal_vol_bp"].values.astype(float)
    mva = mo["move_index"].values.astype(float)
    print("\n=== 1y1y forward REALIZED normal vol (bp/yr), monthly ===")
    print(f"Window {rvdf.index[0]} -> {rvdf.index[-1]} ({len(rvdf)} months)")
    print(f"Mean {rva.mean():.0f}  Median {np.median(rva):.0f}  Min {rva.min():.0f}  Max {rva.max():.0f}")
    print("Top 8 highest-vol months:")
    for ym, v in rvdf["realized_normal_vol_bp"].sort_values(ascending=False).head(8).items():
        print(f"  {ym}  {v:.0f} bp")

    print("\n=== MOVE index (implied), monthly ===")
    print(f"Mean {mva.mean():.0f}  Median {np.median(mva):.0f}  Min {mva.min():.0f}  Max {mva.max():.0f}")
    for ym, v in mo["move_index"].sort_values(ascending=False).head(5).items():
        print(f"  peak {ym}  {v:.0f}")

    # ---- chart: twin axis ----
    plt.rcParams.update({"figure.facecolor": "#0e1117", "axes.facecolor": "#0e1117",
        "savefig.facecolor": "#0e1117", "text.color": "#e6e6e6", "axes.labelcolor": "#e6e6e6",
        "xtick.color": "#b8b8b8", "ytick.color": "#b8b8b8", "axes.edgecolor": "#3a3f4b",
        "axes.grid": True, "grid.color": "#222631"})
    xr = pd.to_datetime(rvdf.index + "-01")
    xm = pd.to_datetime(mo.index + "-01")
    fig, ax = plt.subplots(figsize=(12, 6))
    l1, = ax.plot(xm, mva, color="#f59e0b", lw=1.6, label="MOVE index (rates implied vol)")
    ax.set_ylabel("MOVE index", color="#f59e0b")
    ax.tick_params(axis="y", labelcolor="#f59e0b")
    ax2 = ax.twinx()
    l2, = ax2.plot(xr, rva, color="#3b82f6", lw=1.4, label="1y1y fwd realized normal vol (bp/yr)")
    ax2.set_ylabel("1y1y fwd realized normal vol (bp/yr)", color="#3b82f6")
    ax2.tick_params(axis="y", labelcolor="#3b82f6")
    ax2.grid(False)
    ax.set_title("USD 1y1y rate volatility over time (free proxies)\n"
                 "MOVE implied vs 1y1y forward realized normal vol")
    ax.set_xlabel("Month")
    ax.legend(handles=[l1, l2], facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6", loc="upper left")
    fig.tight_layout(); fig.savefig("charts/usd_1y1y_vol_over_time.png", dpi=130)
    print("\nWrote data/move_index_monthly.csv, data/usd_1y1y_fwd_realized_vol_monthly.csv, "
          "charts/usd_1y1y_vol_over_time.png")


if __name__ == "__main__":
    main()
