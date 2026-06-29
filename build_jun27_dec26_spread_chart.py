#!/usr/bin/env python3
"""Line chart: Jun27−Dec26 calendar spread (bp) over time."""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from playwright.sync_api import sync_playwright

from analyze_sonia import UA, price_to_rate

ROOT = Path(__file__).resolve().parent
CHART_FILE = ROOT / "charts" / "jun27_dec26_spread.png"
DATA_FILE = ROOT / "data" / "jun27_dec26_spread.csv"
BARCHART_LIMIT = 500


def fetch_barchart(symbol: str) -> pd.Series:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA["User-Agent"]).new_page()

        def handle(route) -> None:
            url = route.request.url
            if "historical/get" in url and symbol in url:
                route.continue_(url=re.sub(r"limit=\d+", f"limit={BARCHART_LIMIT}", url))
            else:
                route.continue_()

        page.route("**/*", handle)
        with page.expect_response(
            lambda r, s=symbol: "historical/get" in r.url and s in r.url and r.status == 200,
            timeout=90_000,
        ) as resp_info:
            page.goto(
                f"https://www.barchart.com/futures/quotes/{symbol}/price-history/historical",
                wait_until="domcontentloaded",
                timeout=90_000,
            )
        data = resp_info.value.json()
        browser.close()

    recs = []
    for row in data.get("data", []):
        raw = row.get("raw") or {}
        d = raw.get("tradeTime") or row.get("tradeTime")
        px = raw.get("lastPrice") or row.get("lastPrice")
        if d and px is not None:
            recs.append((pd.to_datetime(d), float(px)))
    df = pd.DataFrame(recs, columns=["date", "price"]).drop_duplicates("date").set_index("date").sort_index()
    return price_to_rate(df["price"])


def load_spread() -> pd.DataFrame:
    dec26 = fetch_barchart("JUZ26")
    jun27 = fetch_barchart("JUM27")
    wide = pd.DataFrame({"dec26": dec26, "jun27": jun27}).dropna()
    wide["spread_bp"] = (wide["jun27"] - wide["dec26"]) * 100.0
    return wide[["spread_bp"]].reset_index().rename(columns={"index": "date"})


def make_chart(path: pd.DataFrame) -> None:
    path = path.copy()
    path["date"] = pd.to_datetime(path["date"])

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(path["date"], path["spread_bp"], color="#1f4e79", linewidth=2, label="Jun27 − Dec26")
    ax.axhline(0, color="#666", linewidth=0.9, linestyle="--", alpha=0.7)
    ax.fill_between(
        path["date"],
        0,
        path["spread_bp"],
        where=path["spread_bp"] >= 0,
        alpha=0.08,
        color="#1f4e79",
        interpolate=True,
    )
    ax.fill_between(
        path["date"],
        0,
        path["spread_bp"],
        where=path["spread_bp"] < 0,
        alpha=0.12,
        color="#c0392b",
        interpolate=True,
    )

    ax.set_title("ICE 1M SONIA: Jun27−Dec26 calendar spread")
    ax.set_ylabel("Spread (bp)")
    ax.set_xlabel("")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=35, ha="right")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", frameon=False)

    ymin, ymax = path["spread_bp"].min(), path["spread_bp"].max()
    pad = max(1.0, 0.08 * (ymax - ymin))
    ax.set_ylim(ymin - pad, ymax + pad)

    CHART_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHART_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    path = load_spread()
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    path.to_csv(DATA_FILE, index=False)
    make_chart(path)
    print(f"Wrote {CHART_FILE}")
    print(f"Wrote {DATA_FILE}")
    print(f"Range: {path['date'].min().date()} → {path['date'].max().date()} ({len(path)} sessions)")


if __name__ == "__main__":
    main()
