#!/usr/bin/env python3
"""Dec27−Dec26 SONIA calendar spread: line chart + three-phase regime analysis."""
from __future__ import annotations

import argparse
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
BARCHART_LIMIT = 500
START = "2026-03-02"

TENORS = {
    "1m": {
        "label": "ICE 1M SONIA (JU*)",
        "dec26_symbol": "JUZ26",
        "dec27_symbol": "JUZ27",
        "chart_labeled": ROOT / "charts" / "dec27_dec26_spread_phases_labeled.png",
        "chart_simple": ROOT / "charts" / "dec27_dec26_spread_mar26.png",
        "json_file": ROOT / "data" / "dec27_dec26_phase_regimes.json",
        "csv_file": ROOT / "data" / "dec27_dec26_spread.csv",
        "line_color": "#6e2c00",
    },
    "3m": {
        "label": "ICE 3M SONIA (J8*)",
        "dec26_symbol": "J8Z26",
        "dec27_symbol": "J8Z27",
        "chart_labeled": ROOT / "charts" / "dec27_dec26_spread_phases_labeled_3m.png",
        "chart_simple": ROOT / "charts" / "dec27_dec26_spread_mar26_3m.png",
        "json_file": ROOT / "data" / "dec27_dec26_phase_regimes_3m.json",
        "csv_file": ROOT / "data" / "dec27_dec26_spread_3m.csv",
        "line_color": "#1a5276",
    },
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


def build_frames(rates: pd.DataFrame) -> pd.DataFrame:
    chg = rates.diff() * 100.0
    d = chg.iloc[1:].copy()
    d["d26"] = d["dec26"]
    d["d27"] = d["dec27"]
    d["dS"] = d["d27"] - d["d26"]
    d["regime"] = [
        classify_curve_move(float(r.d26), float(r.d27), float(r.dS)) for _, r in d.iterrows()
    ]
    d["hawk"] = d["d26"] > 0.25
    d["dov"] = d["d26"] < -0.25
    return d.loc[START:]


def phase_bounds(d: pd.DataFrame) -> list[tuple[str, str, pd.Timestamp, pd.Timestamp]]:
    idx = d.index
    p1_end = pd.Timestamp("2026-04-17")
    p2_end = pd.Timestamp("2026-05-19")
    return [
        ("I", "Compression / inversion", pd.Timestamp(START), p1_end),
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


def analyze_phases(spread: pd.Series, daily: pd.DataFrame, rates: pd.DataFrame) -> list[dict]:
    out = []
    for pid, title, start, end in phase_bounds(daily):
        seg = daily.loc[start:end]
        n = len(seg)
        counts = Counter(seg["regime"])
        modal = counts.most_common(1)[0][0]
        r0, r1 = rates.loc[start], rates.loc[end]
        d26 = (r1["dec26"] - r0["dec26"]) * 100.0
        d27 = (r1["dec27"] - r0["dec27"]) * 100.0
        dS = d27 - d26
        overall = classify_curve_move(d26, d27, dS, eps=0.5)
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
                "dec26_chg_bp": round(float(d26), 1),
                "dec27_chg_bp": round(float(d27), 1),
                "overall_regime": overall,
                "overall_label": REGIME_LABELS.get(overall, overall),
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


def make_simple_chart(spread: pd.Series, cfg: dict) -> None:
    sub = spread.loc[START:]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sub.index, sub.values, color=cfg["line_color"], lw=2)
    ax.axhline(0, color="#666", ls="--", lw=0.9, alpha=0.7)
    ax.set_title(f"Dec27−Dec26 (bp) from {sub.index[0].strftime('%d %b %Y')} · {cfg['label']}")
    ax.set_ylabel("Spread (bp)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate(rotation=30, ha="right")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    cfg["chart_simple"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(cfg["chart_simple"], dpi=150, bbox_inches="tight")
    plt.close(fig)


def make_labeled_chart(spread: pd.Series, stats: list[dict], cfg: dict, rates: pd.DataFrame) -> None:
    start = pd.Timestamp(stats[0]["start"])
    end = pd.Timestamp(stats[-1]["end"])
    path = spread.loc[start:end]
    legs = rates.loc[start:end, ["dec26", "dec27"]]
    fills = {"I": "#fdecea", "II": "#e8f8f0", "III": "#eaf2fb"}
    ypos = {"I": 14, "II": 22, "III": 8}
    dec26_color = "#1f77b4"
    dec27_color = "#e67e22"

    fig, ax = plt.subplots(figsize=(14, 7.5))
    spread_line, = ax.plot(path.index, path.values, color=cfg["line_color"], lw=2.2, zorder=3, label="Dec27−Dec26 spread")
    ax.axhline(0, color="#666", ls="--", lw=0.9, alpha=0.75)

    ax2 = ax.twinx()
    ax2.plot(legs.index, legs["dec26"], color=dec26_color, lw=1.8, alpha=0.9, zorder=2, label="Dec-26 implied")
    ax2.plot(legs.index, legs["dec27"], color=dec27_color, lw=1.8, alpha=0.9, zorder=2, label="Dec-27 implied")
    ax2.set_ylabel("Implied rate (%)", color="#444")
    ax2.tick_params(axis="y", labelcolor="#444")

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
            f"OVERALL: {st['overall_label']}\n"
            f"  (Dec26 {st['dec26_chg_bp']:+.0f} bp, Dec27 {st['dec27_chg_bp']:+.0f} bp)\n"
            f"Daily modal: {st['modal_label']} — {st['modal_pct']}%\n"
            f"  Hawk days (n={st['hawk_days']}):\n{hawk_lines}\n"
            f"  Dov days (n={st['dov_days']}):\n{dov_lines}"
        )
        ax.annotate(
            txt,
            xy=(mid, ypos[st["id"]]),
            ha="center",
            va="top",
            fontsize=7.6,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#888", alpha=0.96),
            zorder=4,
        )

    ax.set_title(f"Dec27−Dec26: three phases · {cfg['label']}")
    ax.set_ylabel("Spread (bp)", color=cfg["line_color"])
    ax.tick_params(axis="y", labelcolor=cfg["line_color"])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=3))
    fig.autofmt_xdate(rotation=30, ha="right")
    ymin = min(-20, float(path.min()) - 3)
    ymax = max(24, float(path.max()) + 3)
    ax.set_ylim(ymin, ymax)
    leg_pad = max(0.05, (legs.max().max() - legs.min().min()) * 0.08)
    ax2.set_ylim(float(legs.min().min()) - leg_pad, float(legs.max().max()) + leg_pad)
    ax.grid(True, alpha=0.2, zorder=0)

    lines = [spread_line] + ax2.lines
    labels = [ln.get_label() for ln in lines]
    ax.legend(lines, labels, loc="upper left", fontsize=8, framealpha=0.92)

    fig.tight_layout()
    cfg["chart_labeled"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(cfg["chart_labeled"], dpi=160, bbox_inches="tight")
    plt.close(fig)


def run(tenor: str) -> None:
    cfg = TENORS[tenor]
    rates = pd.DataFrame(
        {
            "dec26": fetch_barchart(cfg["dec26_symbol"]),
            "dec27": fetch_barchart(cfg["dec27_symbol"]),
        }
    ).dropna()
    rates["S"] = (rates["dec27"] - rates["dec26"]) * 100.0
    spread = rates["S"]
    daily = build_frames(rates)
    stats = analyze_phases(spread, daily, rates)

    meta = {"tenor": tenor, "source": cfg["label"], "symbols": [cfg["dec26_symbol"], cfg["dec27_symbol"]]}
    payload = {"meta": meta, "phases": stats}
    cfg["csv_file"].parent.mkdir(parents=True, exist_ok=True)
    spread.loc[START:].reset_index().rename(columns={"index": "date", "S": "spread_bp"}).to_csv(
        cfg["csv_file"], index=False
    )
    cfg["json_file"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    make_simple_chart(spread, cfg)
    make_labeled_chart(spread, stats, cfg, rates)
    print(f"Wrote {cfg['chart_labeled']}")
    print(f"Wrote {cfg['chart_simple']}")
    print(f"Wrote {cfg['json_file']}")
    print(f"Wrote {cfg['csv_file']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tenor", choices=("1m", "3m"), default="1m")
    p.add_argument("--all", action="store_true", help="Build both 1M and 3M outputs")
    args = p.parse_args()
    if args.all:
        for t in ("1m", "3m"):
            run(t)
    else:
        run(args.tenor)


if __name__ == "__main__":
    main()
