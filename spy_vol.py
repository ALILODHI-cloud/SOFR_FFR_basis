"""
SPY realized monthly volatility from Investing.com daily prices (past ~20 years).

Data source: Investing.com SPDR S&P 500 ETF (SPY), pair_id 525, fetched via the
`investgo` client (the same daily OHLC series shown on the SPY "Historical Data"
page on investing.com).

Realized volatility (per calendar month) is computed from daily close-to-close
log returns r_t = ln(P_t / P_{t-1}):

  * rv_ann  : annualized close-to-close realized vol
              = sqrt( (252 / n) * sum(r_t^2) )      (sum-of-squares estimator)
  * std_ann : annualized sample-std realized vol
              = std(r_t, ddof=1) * sqrt(252)
  * rv_month: non-annualized monthly realized vol = sqrt( sum(r_t^2) )

n = number of daily returns inside the calendar month. Months are kept only if
they have a minimum number of trading days (default 5) so partial/illiquid
months don't distort the ranking.

Writes spy_vol_data.json (consumed by build_app for the dashboard) and prints a
console summary identifying the month with the highest realized volatility.
"""
import json

import numpy as np
import pandas as pd
from investgo import get_historical_prices

SPY_PAIR_ID = "525"          # Investing.com pair_id for SPDR S&P 500 ETF (SPY)
START = "01012005"           # DDMMYYYY (gives a full 20y+ window of context)
TRADING_DAYS = 252
MIN_DAYS = 5                 # min daily returns required to rank a month


def fetch_spy(end_ddmmyyyy: str) -> pd.DataFrame:
    df = get_historical_prices(SPY_PAIR_ID, START, end_ddmmyyyy)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def main():
    end = pd.Timestamp.now("UTC").strftime("%d%m%Y")
    df = fetch_spy(end)

    # Restrict to the trailing 20 years (calendar) ending at the last print.
    last = df.index.max()
    window_start = last - pd.DateOffset(years=20)
    df = df[df.index >= window_start]

    close = df["price"].astype(float)
    ret = np.log(close / close.shift(1)).dropna()
    ret.name = "r"

    g = ret.groupby(ret.index.to_period("M"))
    n = g.size()
    sumsq = g.apply(lambda x: float(np.sum(x.values ** 2)))
    std = g.std(ddof=1)

    monthly = pd.DataFrame({"n": n, "sumsq": sumsq, "std": std})
    monthly = monthly[monthly["n"] >= MIN_DAYS]

    monthly["rv_ann"] = np.sqrt(TRADING_DAYS / monthly["n"] * monthly["sumsq"])
    monthly["std_ann"] = monthly["std"] * np.sqrt(TRADING_DAYS)
    monthly["rv_month"] = np.sqrt(monthly["sumsq"])
    monthly = monthly.sort_index()

    top = monthly.sort_values("rv_ann", ascending=False)
    winner = top.index[0]

    months = [
        {
            "ym": str(p),
            "n": int(r.n),
            "rv_ann": float(r.rv_ann),
            "std_ann": float(r.std_ann),
            "rv_month": float(r.rv_month),
        }
        for p, r in monthly.iterrows()
    ]

    out = {
        "generated_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Investing.com SPDR S&P 500 ETF (SPY), pair_id 525 (daily close)",
        "definition": (
            "Per-month realized vol from daily log returns. "
            "rv_ann = sqrt(252/n * sum(r^2)); std_ann = std(r)*sqrt(252); "
            "rv_month = sqrt(sum(r^2))."
        ),
        "window": {
            "first_month": str(monthly.index[0]),
            "last_month": str(monthly.index[-1]),
            "n_months": int(len(monthly)),
            "first_price_date": df.index.min().strftime("%Y-%m-%d"),
            "last_price_date": df.index.max().strftime("%Y-%m-%d"),
            "trading_days_used": int(len(ret)),
        },
        "highest": {
            "ym": str(winner),
            "rv_ann": float(top.iloc[0].rv_ann),
            "std_ann": float(top.iloc[0].std_ann),
            "rv_month": float(top.iloc[0].rv_month),
            "n": int(top.iloc[0].n),
        },
        "top10": [
            {
                "ym": str(p),
                "rv_ann": float(r.rv_ann),
                "std_ann": float(r.std_ann),
                "rv_month": float(r.rv_month),
                "n": int(r.n),
            }
            for p, r in top.head(10).iterrows()
        ],
        "months": months,
    }

    with open("spy_vol_data.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"SPY realized monthly volatility (Investing.com, pair 525)")
    print(
        f"Window: {out['window']['first_month']} -> {out['window']['last_month']} "
        f"({out['window']['n_months']} months, "
        f"{out['window']['trading_days_used']} daily returns)"
    )
    print(
        f"\nHighest realized-vol month: {winner}  "
        f"rv_ann={out['highest']['rv_ann']*100:.1f}%  "
        f"std_ann={out['highest']['std_ann']*100:.1f}%  "
        f"(n={out['highest']['n']} days)"
    )
    print("\nTop 10 months by annualized realized vol:")
    print(f"{'rank':>4}  {'month':<8}{'rv_ann':>9}{'std_ann':>9}{'days':>6}")
    for i, m in enumerate(out["top10"], 1):
        print(
            f"{i:>4}  {m['ym']:<8}{m['rv_ann']*100:>8.1f}%{m['std_ann']*100:>8.1f}%{m['n']:>6}"
        )


if __name__ == "__main__":
    main()
