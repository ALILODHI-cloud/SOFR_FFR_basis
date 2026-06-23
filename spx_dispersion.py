"""Plot a 60-day SPX dispersion measure over the last 10 years.

Definition:
  dispersion = SPX annualized volatility - average annualized volatility of
  the current top 10 largest S&P 500 constituents.

Daily prices come from Yahoo Finance's chart API. Constituent defaults are the
current mega-cap top ten by S&P 500 index weight; pass --symbols to override.
"""
import argparse
import datetime as dt
import os
import time
from urllib.parse import quote

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


INDEX_SYMBOL = "^GSPC"
DEFAULT_TOP_10 = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "GOOG",
    "AVGO",
    "META",
    "TSLA",
    "BRK-B",
]
ROLLING_DAYS = 60
TRADING_DAYS = 252
YEARS = 10
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}


def years_ago(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def fetch_yahoo_adj_close(symbol: str, start: dt.date, end: dt.date) -> pd.Series:
    period1 = int(dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    period2 = int(dt.datetime.combine(end, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
        "&includeAdjustedClose=true"
    )

    last_error = None
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=UA, timeout=60)
            resp.raise_for_status()
            payload = resp.json()
            result = payload["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote_data = result["indicators"]["quote"][0]
            close = quote_data["close"]
            adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose", close)
            rows = {}
            for ts, adj, raw_close in zip(timestamps, adjclose, close):
                value = adj if adj is not None else raw_close
                if value is None:
                    continue
                day = pd.Timestamp.fromtimestamp(ts, tz="UTC").tz_convert(None).normalize()
                rows[day] = float(value)
            if not rows:
                raise ValueError(f"no daily prices returned for {symbol}")
            return pd.Series(rows, name=symbol).sort_index()
        except Exception as exc:
            last_error = exc
            time.sleep(2 + attempt)

    raise RuntimeError(f"failed to fetch {symbol}: {last_error}")


def compute_dispersion(prices: pd.DataFrame, constituents: list[str]) -> pd.DataFrame:
    returns = np.log(prices).diff().dropna(how="any")
    annualized_vol = returns.rolling(ROLLING_DAYS).std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0
    annualized_vol = annualized_vol.dropna(how="any")
    annualized_vol["avg_top10_vol_ann_pct"] = annualized_vol[constituents].mean(axis=1)
    annualized_vol["dispersion_pct_pts"] = (
        annualized_vol[INDEX_SYMBOL] - annualized_vol["avg_top10_vol_ann_pct"]
    )
    annualized_vol = annualized_vol.rename(columns={INDEX_SYMBOL: "spx_vol_ann_pct"})
    return annualized_vol[["spx_vol_ann_pct", "avg_top10_vol_ann_pct", "dispersion_pct_pts"]]


def plot_dispersion(df: pd.DataFrame, constituents: list[str], out_path: str) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#0e1117",
            "axes.facecolor": "#0e1117",
            "savefig.facecolor": "#0e1117",
            "text.color": "#e6e6e6",
            "axes.labelcolor": "#e6e6e6",
            "xtick.color": "#b8b8b8",
            "ytick.color": "#b8b8b8",
            "axes.edgecolor": "#3a3f4b",
            "axes.grid": True,
            "grid.color": "#222631",
            "grid.linewidth": 0.8,
            "font.size": 11,
            "axes.titlesize": 14,
        }
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df["dispersion_pct_pts"], color="#3b82f6", lw=1.5, label="Dispersion")
    ax.fill_between(
        df.index,
        df["dispersion_pct_pts"],
        0,
        where=df["dispersion_pct_pts"] >= 0,
        color="#22c55e",
        alpha=0.14,
    )
    ax.fill_between(
        df.index,
        df["dispersion_pct_pts"],
        0,
        where=df["dispersion_pct_pts"] < 0,
        color="#ef4444",
        alpha=0.16,
    )
    ax.axhline(0, color="#8b949e", lw=1.1)
    ax.axhline(df["dispersion_pct_pts"].mean(), color="#f59e0b", lw=1.5, ls="--", label="Mean")
    ax.set_title("SPX dispersion: SPX vol minus avg top-10 constituent vol (60 trading days)")
    ax.set_ylabel("Annualized volatility spread (percentage points)")
    ax.set_xlabel("")
    ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6", loc="lower left")
    latest = df.iloc[-1]
    ax.text(
        0.99,
        0.03,
        (
            f"Latest {df.index[-1].date()}: {latest['dispersion_pct_pts']:.1f} pp\n"
            f"SPX vol {latest['spx_vol_ann_pct']:.1f}% | top-10 avg {latest['avg_top10_vol_ann_pct']:.1f}%\n"
            f"Top 10: {', '.join(constituents)}"
        ),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color="#e6e6e6",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#161b22", "edgecolor": "#3a3f4b"},
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=INDEX_SYMBOL, help="Index Yahoo symbol; default: ^GSPC")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_TOP_10),
        help="Comma-separated constituent Yahoo symbols; default: current top 10 S&P 500 constituents.",
    )
    parser.add_argument("--chart-out", default="/workspace/charts/spx_dispersion_60d_10y.png")
    parser.add_argument("--csv-out", default="/workspace/data/spx_dispersion_60d_10y.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global INDEX_SYMBOL
    INDEX_SYMBOL = args.index
    constituents = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
    if len(constituents) != 10:
        raise SystemExit(f"expected exactly 10 constituents, got {len(constituents)}")

    today = dt.datetime.now(dt.timezone.utc).date()
    start_for_plot = years_ago(today, YEARS)
    # Fetch extra history so the first plotted date has a full 60-day window.
    fetch_start = start_for_plot - dt.timedelta(days=140)
    fetch_end = today + dt.timedelta(days=1)

    symbols = [INDEX_SYMBOL] + constituents
    series = [fetch_yahoo_adj_close(symbol, fetch_start, fetch_end) for symbol in symbols]
    prices = pd.concat(series, axis=1).dropna(how="any")
    if len(prices) < ROLLING_DAYS + 2:
        raise SystemExit("not enough aligned daily observations to compute 60-day volatility")

    dispersion = compute_dispersion(prices, constituents)
    dispersion = dispersion[dispersion.index.date >= start_for_plot]
    if dispersion.empty:
        raise SystemExit("dispersion series is empty after trimming to the last 10 years")

    os.makedirs(os.path.dirname(args.chart_out), exist_ok=True)
    os.makedirs(os.path.dirname(args.csv_out), exist_ok=True)
    dispersion.round(6).to_csv(args.csv_out, index_label="date")
    plot_dispersion(dispersion, constituents, args.chart_out)

    latest = dispersion.iloc[-1]
    print(f"Fetched {len(prices)} aligned trading days for {', '.join(symbols)}")
    print(f"Dispersion observations: {len(dispersion)} ({dispersion.index[0].date()} -> {dispersion.index[-1].date()})")
    print(f"Definition: {INDEX_SYMBOL} 60d ann vol - average 60d ann vol of {', '.join(constituents)}")
    print(
        "Latest: "
        f"{latest['dispersion_pct_pts']:.2f} pp "
        f"(SPX {latest['spx_vol_ann_pct']:.2f}% - top10 avg {latest['avg_top10_vol_ann_pct']:.2f}%)"
    )
    print(f"Mean/min/max: {dispersion['dispersion_pct_pts'].mean():.2f} / "
          f"{dispersion['dispersion_pct_pts'].min():.2f} / {dispersion['dispersion_pct_pts'].max():.2f} pp")
    print(f"Wrote {args.csv_out}")
    print(f"Wrote {args.chart_out}")


if __name__ == "__main__":
    main()
