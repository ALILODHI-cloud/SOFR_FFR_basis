#!/usr/bin/env python3
"""Dec27−Dec26 ICE 3M SONIA: four-phase regime chart + stats for blog post."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from playwright.sync_api import sync_playwright

from analyze_sonia import UA, BANK_RATE_PCT, classify_curve_move, price_to_rate

ROOT = Path(__file__).resolve().parent
BARCHART_LIMIT = 500
WAR_OPEN = "2026-03-02"

# Data-pinned boundaries (EOD sessions on Barchart J8Z26/J8Z27)
PHASES = [
    ("I", "Bear flattening / inversion", "2026-03-02", "2026-03-20"),
    ("II", "Bull steepening", "2026-03-23", "2026-04-17"),
    ("III", "Bear steepening", "2026-04-20", "2026-05-15"),
    ("IV", "Bull flattening", "2026-05-16", None),
]

PHASE_FILL = {
    "I": "#fde8e6",
    "II": "#e5f7ed",
    "III": "#fff3cd",
    "IV": "#e8f0fe",
}

REGIME_LABELS = {
    "bear_steepening": "Bear steepening",
    "bull_steepening": "Bull steepening",
    "bear_flattening": "Bear flattening",
    "bull_flattening": "Bull flattening",
    "mixed_steepening": "Mixed steepening",
    "mixed_flattening": "Mixed flattening",
    "unchanged": "Unchanged",
}

OUTPUT = {
    "chart": ROOT / "charts" / "dec27_dec26_four_phases_3m.png",
    "json": ROOT / "data" / "dec27_dec26_four_phases_3m.json",
    "csv": ROOT / "data" / "dec27_dec26_spread_3m.csv",
    "docs_chart": ROOT / "docs" / "charts" / "dec27_dec26_four_phases_3m.png",
}


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


def resolve_phase_bounds(index: pd.DatetimeIndex) -> list[tuple[str, str, pd.Timestamp, pd.Timestamp]]:
    out = []
    for pid, title, start_s, end_s in PHASES:
        start = pd.Timestamp(start_s)
        if start not in index:
            start = index[index >= start][0]
        if end_s is None:
            end = index[-1]
        else:
            end = pd.Timestamp(end_s)
            if end not in index:
                end = index[index <= end][-1]
        out.append((pid, title, start, end))
    return out


def hawk_dov_threshold(d26: pd.Series, start: str, multiplier: float = 1.5) -> dict:
    base = d26.loc[start:].dropna()
    mu = float(base.mean())
    sigma = float(base.std(ddof=1))
    hawk_thr = mu + multiplier * sigma
    dov_thr = mu - multiplier * sigma
    return {
        "multiplier": multiplier,
        "mean_d26_bp": round(mu, 2),
        "stdev_d26_bp": round(sigma, 2),
        "hawk_threshold_bp": round(hawk_thr, 2),
        "dov_threshold_bp": round(dov_thr, 2),
        "rule": (
            f"Hawk if ΔDec26 > μ + {multiplier}σ = +{hawk_thr:.2f} bp; "
            f"Dov if ΔDec26 < μ − {multiplier}σ = {dov_thr:.2f} bp "
            f"(μ, σ of ΔDec26 over sample from {start})"
        ),
    }


def regime_dist(seg: pd.DataFrame, mask: pd.Series | None = None) -> dict[str, float]:
    sub = seg[mask] if mask is not None else seg
    if sub.empty:
        return {}
    counts = Counter(sub["regime"])
    n = len(sub)
    return {REGIME_LABELS.get(k, k): round(100 * v / n, 1) for k, v in counts.most_common()}


def analyze(rates: pd.DataFrame, bounds: list, hawk_rule: dict, d26: pd.Series) -> list[dict]:
    hawk_thr = hawk_rule["hawk_threshold_bp"]
    dov_thr = hawk_rule["dov_threshold_bp"]
    chg = rates.diff() * 100.0
    daily = chg.iloc[1:].copy()
    daily["d26"] = daily["dec26"]
    daily["d27"] = daily["dec27"]
    daily["dS"] = daily["d27"] - daily["d26"]
    daily["regime"] = [
        classify_curve_move(float(r.d26), float(r.d27), float(r.dS)) for _, r in daily.iterrows()
    ]
    daily["hawk"] = daily["d26"] > hawk_thr
    daily["dov"] = daily["d26"] < dov_thr
    daily["neutral"] = ~daily["hawk"] & ~daily["dov"]

    stats = []
    for pid, title, start, end in bounds:
        seg = daily.loc[start:end]
        n = len(seg)
        counts = Counter(seg["regime"])
        modal = counts.most_common(1)[0][0]
        r0, r1 = rates.loc[start], rates.loc[end]
        d26_tot = (r1["dec26"] - r0["dec26"]) * 100.0
        d27_tot = (r1["dec27"] - r0["dec27"]) * 100.0
        dS_tot = d27_tot - d26_tot
        overall = classify_curve_move(d26_tot, d27_tot, dS_tot, eps=0.5)
        hawk = seg["hawk"]
        dov = seg["dov"]
        neutral = seg["neutral"]
        stats.append(
            {
                "id": pid,
                "title": title,
                "start": str(start.date()),
                "end": str(end.date()),
                "n_days": n,
                "spread_start_bp": round(float(r0["S"]), 1),
                "spread_end_bp": round(float(r1["S"]), 1),
                "spread_change_bp": round(float(r1["S"] - r0["S"]), 1),
                "dec26_chg_bp": round(float(d26_tot), 1),
                "dec27_chg_bp": round(float(d27_tot), 1),
                "overall_label": REGIME_LABELS.get(overall, overall),
                "steepener_pnl_bp": round(float(seg["dS"].sum()), 1),
                "modal_label": REGIME_LABELS.get(modal, modal),
                "modal_pct": round(100 * counts[modal] / n, 1) if n else 0,
                "hawk_days": int(hawk.sum()),
                "neutral_days": int(neutral.sum()),
                "dov_days": int(dov.sum()),
                "hawk_breakdown_pct": regime_dist(seg, hawk),
                "dov_breakdown_pct": regime_dist(seg, dov),
                "neutral_breakdown_pct": regime_dist(seg, neutral),
                "all_days_pct": regime_dist(seg),
            }
        )
    return stats


def make_chart(rates: pd.DataFrame, bounds: list, stats: list[dict]) -> None:
    start = bounds[0][2]
    end = bounds[-1][3]
    sub = rates.loc[start:end]
    spread = sub["S"]

    fig, (ax_s, ax_r) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [1.1, 1], "hspace": 0.08}
    )

    for pid, _, ps, pe in bounds:
        ax_s.axvspan(ps, pe, color=PHASE_FILL[pid], alpha=0.65, zorder=0)
        ax_r.axvspan(ps, pe, color=PHASE_FILL[pid], alpha=0.45, zorder=0)

    ax_s.plot(spread.index, spread.values, color="#1a365d", lw=2.2, zorder=3)
    ax_s.axhline(0, color="#888", ls="--", lw=0.8)
    ax_s.set_ylabel("Dec27 − Dec26 (bp)", fontsize=10)
    ax_s.set_title("ICE 3M SONIA (J8Z26 / J8Z27): four curve regimes since the Iran shock", fontsize=11, pad=8)
    ax_s.grid(True, alpha=0.25, zorder=0)

    ax_r.plot(sub.index, sub["dec26"], color="#2e86c1", lw=2, label="Dec-26 implied", zorder=3)
    ax_r.plot(sub.index, sub["dec27"], color="#d35400", lw=2, label="Dec-27 implied", zorder=3)
    ax_r.axhline(BANK_RATE_PCT, color="#27ae60", ls=":", lw=1, alpha=0.8, label=f"Bank Rate ({BANK_RATE_PCT}%)")
    ax_r.set_ylabel("Implied rate (%)", fontsize=10)
    ax_r.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax_r.grid(True, alpha=0.25, zorder=0)

    # compact phase tags on spread panel
    y_tag = spread.max() - 2
    for st, (_, _, ps, pe) in zip(stats, bounds):
        mid = ps + (pe - ps) / 2
        ax_s.text(
            mid,
            y_tag,
            f"{st['id']}. {st['overall_label']}\n{st['start']} – {st['end']}",
            ha="center",
            va="top",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#ccc", alpha=0.92),
            zorder=4,
        )

    ax_r.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax_r.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()

    for path in (OUTPUT["chart"], OUTPUT["docs_chart"]):
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    dec26 = fetch_barchart("J8Z26")
    dec27 = fetch_barchart("J8Z27")
    rates = pd.DataFrame({"dec26": dec26, "dec27": dec27}).dropna()
    rates["S"] = (rates["dec27"] - rates["dec26"]) * 100.0
    d26 = rates["dec26"].diff() * 100.0

    bounds = resolve_phase_bounds(rates.index)
    hawk_rule = hawk_dov_threshold(d26, WAR_OPEN)
    stats = analyze(rates, bounds, hawk_rule, d26)

    payload = {
        "meta": {
            "source": "ICE 3M SONIA (J8Z26 / J8Z27)",
            "symbols": ["J8Z26", "J8Z27"],
            "sample_start": WAR_OPEN,
            "sample_end": str(rates.index[-1].date()),
            "boundary_notes": {
                "I_end": "Spread trough −30 bp (20 Mar), last session before 24 Mar re-open",
                "II_end": "Local implied-rate low in both legs (17 Apr)",
                "III_end": "Joint local implied-rate high (15 May; Dec-26 peak 12 May)",
                "IV_start": "Session after peak; dovish unwind",
            },
            "hawk_dov": hawk_rule,
            "daily_regime_note": "Curve regime from classify_curve_move(ΔDec26, ΔDec27, Δspread); ε=0.25 bp on spread",
        },
        "phases": stats,
    }

    OUTPUT["json"].parent.mkdir(parents=True, exist_ok=True)
    OUTPUT["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rates.loc[WAR_OPEN:, ["dec26", "dec27", "S"]].reset_index().rename(
        columns={"index": "date", "S": "spread_bp"}
    ).to_csv(OUTPUT["csv"], index=False)

    make_chart(rates, bounds, stats)
    print(f"Wrote {OUTPUT['chart']}")
    print(f"Wrote {OUTPUT['docs_chart']}")
    print(f"Wrote {OUTPUT['json']}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
