#!/usr/bin/env python3
"""Jun27−Dec26 spread line chart with three phase regime labels."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from playwright.sync_api import sync_playwright

from analyze_sonia import UA, classify_curve_move, price_to_rate

ROOT = Path(__file__).resolve().parent
CHART_FILE = ROOT / "charts" / "jun27_dec26_spread_phases_labeled.png"
CHART_SIMPLE = ROOT / "charts" / "jun27_dec26_spread_mar26.png"
JSON_FILE = ROOT / "data" / "jun27_dec26_phase_regimes.json"
BARCHART_LIMIT = 500

REGIME_LABELS = {
    "bear_steepening": "Bear steepening",
    "bull_steepening": "Bull steepening",
    "bear_flattening": "Bear flattening",
    "bull_flattening": "Bull flattening",
    "mixed_steepening": "Mixed steepening",
    "mixed_flattening": "Mixed flattening",
    "unchanged": "Unchanged",
}

PHASE_ENDS = (
    ("I", "Compression / inversion", "2026-03-02", "2026-04-17"),
    ("II", "Steepening", None, "2026-05-19"),  # II start = next session after I
    ("III", "Flattening", None, None),  # III start after II; end = last
)


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


def build_daily_frame() -> tuple[pd.Series, pd.DataFrame]:
    rates = pd.DataFrame({"dec26": fetch_barchart("JUZ26"), "jun27": fetch_barchart("JUM27")}).dropna()
    rates["S"] = (rates["jun27"] - rates["dec26"]) * 100.0
    chg = rates.diff() * 100.0
    d = chg.iloc[1:].copy()
    d["d26"] = d["dec26"]
    d["d27"] = d["jun27"]
    d["dS"] = d["d27"] - d["d26"]
    d["regime"] = [
        classify_curve_move(float(r.d26), float(r.d27), float(r.dS)) for _, r in d.iterrows()
    ]
    d["hawk"] = d["d26"] > 0.25
    d["dov"] = d["d26"] < -0.25
    return rates["S"], d.loc["2026-03-02":]


def phase_bounds(d: pd.DataFrame) -> list[tuple[str, str, pd.Timestamp, pd.Timestamp]]:
    idx = d.index
    p1_end = pd.Timestamp("2026-04-17")
    p2_end = pd.Timestamp("2026-05-19")
    return [
        ("I", "Compression / inversion", pd.Timestamp("2026-03-02"), p1_end),
        ("II", "Steepening", idx[idx > p1_end][0], p2_end),
        ("III", "Flattening", idx[idx > p2_end][0], idx[-1]),
    ]


def regime_dist(seg: pd.DataFrame, mask: pd.Series | None = None) -> dict[str, float]:
    sub = seg[mask] if mask is not None else seg
    if sub.empty:
        return {}
    counts = Counter(sub["regime"])
    n = len(sub)
    return {REGIME_LABELS.get(k, k): round(100 * v / n, 1) for k, v in counts.most_common()}


def analyze_phases(spread: pd.Series, daily: pd.DataFrame) -> list[dict]:
    out = []
    for pid, title, start, end in phase_bounds(daily):
        seg = daily.loc[start:end]
        n = len(seg)
        counts = Counter(seg["regime"])
        modal = counts.most_common(1)[0][0]
        flat_pct = round(
            100
            * sum(counts.get(x, 0) for x in ("bear_flattening", "bull_flattening", "mixed_flattening"))
            / n,
            1,
        )
        steep_pct = round(
            100
            * sum(counts.get(x, 0) for x in ("bear_steepening", "bull_steepening", "mixed_steepening"))
            / n,
            1,
        )
        hawk = seg["hawk"]
        dov = seg["dov"]
        out.append(
            {
                "id": pid,
                "title": title,
                "start": str(start.date()),
                "end": str(end.date()),
                "n_days": n,
                "spread_start_bp": round(float(spread.loc[start]), 1),
                "spread_end_bp": round(float(spread.loc[end]), 1),
                "spread_change_bp": round(float(spread.loc[end] - spread.loc[start]), 1),
                "steepener_pnl_bp": round(float(seg["dS"].sum()), 1),
                "modal_regime": modal,
                "modal_label": REGIME_LABELS.get(modal, modal),
                "modal_pct": round(100 * counts[modal] / n, 1),
                "all_days_pct": regime_dist(seg),
                "flattening_days_pct": flat_pct,
                "steepening_days_pct": steep_pct,
                "hawk_days": int(hawk.sum()),
                "hawk_breakdown_pct": regime_dist(seg, hawk),
                "dov_days": int(dov.sum()),
                "dov_breakdown_pct": regime_dist(seg, dov),
            }
        )
    return out


def make_simple_chart(spread: pd.Series) -> None:
    sub = spread.loc["2026-03-02":]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sub.index, sub.values, color="#1f4e79", lw=2)
    ax.axhline(0, color="#666", ls="--", lw=0.9, alpha=0.7)
    ax.set_title(f"Jun27−Dec26 (bp) from {sub.index[0].strftime('%d %b %Y')}")
    ax.set_ylabel("Spread (bp)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate(rotation=30, ha="right")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    CHART_SIMPLE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_SIMPLE, dpi=150, bbox_inches="tight")
    plt.close(fig)


def make_labeled_chart(spread: pd.Series, stats: list[dict]) -> None:
    start = pd.Timestamp(stats[0]["start"])
    end = pd.Timestamp(stats[-1]["end"])
    path = spread.loc[start:end]
    fills = {"I": "#fdecea", "II": "#e8f8f0", "III": "#eaf2fb"}
    ypos = {"I": 17, "II": 24, "III": 11}

    fig, ax = plt.subplots(figsize=(14, 7.5))
    ax.plot(path.index, path.values, color="#1f4e79", lw=2.2, zorder=3)
    ax.axhline(0, color="#666", ls="--", lw=0.9, alpha=0.75)

    for st in stats:
        s = pd.Timestamp(st["start"])
        e = pd.Timestamp(st["end"])
        ax.axvspan(s, e, color=fills[st["id"]], alpha=0.55, zorder=0)
        mid = s + (e - s) / 2
        hawk_lines = "\n".join(f"    {k}: {v}%" for k, v in st["hawk_breakdown_pct"].items()) or "    (none)"
        dov_lines = "\n".join(f"    {k}: {v}%" for k, v in st["dov_breakdown_pct"].items()) or "    (none)"
        txt = (
            f"{st['id']}. {st['title']}\n"
            f"{st['start']} → {st['end']}   ΔS {st['spread_change_bp']:+.0f} bp\n"
            f"Modal (all days): {st['modal_label']} — {st['modal_pct']}%\n"
            f"  Flattening days: {st['flattening_days_pct']}%   Steepening days: {st['steepening_days_pct']}%\n"
            f"  Hawk days (n={st['hawk_days']}):\n{hawk_lines}\n"
            f"  Dov days (n={st['dov_days']}):\n{dov_lines}"
        )
        ax.annotate(
            txt,
            xy=(mid, ypos[st["id"]]),
            ha="center",
            va="top",
            fontsize=7.8,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#888", alpha=0.96),
            zorder=4,
        )

    ax.set_title("Jun27−Dec26: three phases with daily regime breakdown (hawk / dov)")
    ax.set_ylabel("Spread (bp)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=3))
    fig.autofmt_xdate(rotation=30, ha="right")
    ax.set_ylim(-15, 29)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    CHART_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_FILE, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    spread, daily = build_daily_frame()
    stats = analyze_phases(spread, daily)
    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    JSON_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    make_simple_chart(spread)
    make_labeled_chart(spread, stats)
    print(f"Wrote {CHART_FILE}")
    print(f"Wrote {CHART_SIMPLE}")
    print(f"Wrote {JSON_FILE}")


if __name__ == "__main__":
    main()
