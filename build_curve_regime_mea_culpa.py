#!/usr/bin/env python3
"""Regime split + chart for Dec27−Dec26 steepener mea culpa note."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_sonia import BANK_RATE_PCT, classify_curve_move

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "sonia_1m_data.json"
SUMMARY_FILE = ROOT / "data" / "curve_regime_summary.json"
PATH_FILE = ROOT / "data" / "curve_regime_path.csv"
CHART_FILE = ROOT / "charts" / "curve_regime_mea_culpa.png"

DEC26, DEC27, JUN27 = "2026-12", "2027-12", "2027-06"
ENTRY = pd.Timestamp("2026-06-05")
CRISIS_START = pd.Timestamp("2026-03-24")
EPS = 0.25


def load_rates() -> pd.DataFrame:
    with DATA_FILE.open(encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw["timeseries"]["rows"]).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df.sort_index().astype(float)


def period_summary(d: pd.DataFrame, label: str, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sub = d[(d.index >= start) & (d.index <= end)]
    n = len(sub)
    regimes = sub["regime"].value_counts()
    hawk = sub[sub["d26"] > EPS]
    dov = sub[sub["d26"] < -EPS]
    return {
        "period": label,
        "n_days": n,
        "dec26_total_bp": round(float(sub["d26"].sum()), 1),
        "dec27_total_bp": round(float(sub["d27"].sum()), 1),
        "slope_total_bp": round(float(sub["dslope"].sum()), 1),
        "modal_regime": regimes.idxmax() if n else None,
        "regime_counts": {k: int(v) for k, v in regimes.items()},
        "bull_flattening_pct": round(100 * regimes.get("bull_flattening", 0) / n, 1) if n else 0,
        "bear_steepening_pct": round(100 * regimes.get("bear_steepening", 0) / n, 1) if n else 0,
        "hawk_days": int(len(hawk)),
        "hawk_bear_steep_pct": round(100 * (hawk["regime"] == "bear_steepening").sum() / len(hawk), 1)
        if len(hawk)
        else None,
        "hawk_bear_flat_pct": round(100 * (hawk["regime"] == "bear_flattening").sum() / len(hawk), 1)
        if len(hawk)
        else None,
        "dov_days": int(len(dov)),
        "dov_bull_flat_pct": round(100 * (dov["regime"] == "bull_flattening").sum() / len(dov), 1)
        if len(dov)
        else None,
        "dov_bull_steep_pct": round(100 * (dov["regime"] == "bull_steepening").sum() / len(dov), 1)
        if len(dov)
        else None,
        "steepener_pnl_bp": round(float(sub["dslope"].sum()), 1),
        "outright_dec26_pnl_bp": round(float(-sub["d26"].sum()), 1),
    }


def build_daily(rates: pd.DataFrame) -> pd.DataFrame:
    chg = rates.diff() * 100
    d = chg[[DEC26, DEC27]].iloc[1:].copy()
    d = d.rename(columns={DEC26: "d26", DEC27: "d27"})
    d["dslope"] = d["d27"] - d["d26"]
    d["regime"] = [
        classify_curve_move(float(r["d26"]), float(r["d27"]), float(r["dslope"]))
        for _, r in d.iterrows()
    ]
    return d


def build_path(rates: pd.DataFrame) -> pd.DataFrame:
    path = rates[[DEC26, DEC27]].copy()
    if JUN27 in rates.columns:
        path[JUN27] = rates[JUN27]
    path["slope_bp"] = (path[DEC27] - path[DEC26]) * 100
    path["dec26_vs_bank_bp"] = (path[DEC26] - BANK_RATE_PCT) * 100
    path["dec27_vs_bank_bp"] = (path[DEC27] - BANK_RATE_PCT) * 100
    return path.reset_index()


def regime_color(regime: str) -> str:
    return {
        "bear_steepening": "#c0392b",
        "bull_flattening": "#2980b9",
        "bear_flattening": "#e67e22",
        "bull_steepening": "#27ae60",
        "mixed_steepening": "#8e44ad",
        "mixed_flattening": "#7f8c8d",
        "unchanged": "#bdc3c7",
    }.get(regime, "#95a5a6")


def make_chart(path: pd.DataFrame, daily: pd.DataFrame) -> None:
    path["date"] = pd.to_datetime(path["date"])
    daily = daily.copy()
    daily.index = pd.to_datetime(daily.index)

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1.2, 1]})
    ax0, ax1, ax2 = axes

    ax0.plot(path["date"], path["dec26_vs_bank_bp"], color="#1f77b4", lw=2, label="Dec-26 vs Bank")
    ax0.plot(path["date"], path["dec27_vs_bank_bp"], color="#ff7f0e", lw=2, label="Dec-27 vs Bank")
    ax0.axhline(0, color="black", lw=0.8, alpha=0.4)
    ax0.axvline(ENTRY, color="#e74c3c", ls="--", lw=1.2, alpha=0.85, label="Steepener entry (5 Jun)")
    ax0.set_ylabel("bp above Bank Rate (3.75%)")
    ax0.set_title("UK SONIA curve regimes: crisis onset → post-entry dovish unwind")
    ax0.legend(loc="upper right", fontsize=9)
    ax0.grid(True, alpha=0.25)

    ax1.plot(path["date"], path["slope_bp"], color="#2c3e50", lw=2)
    ax1.axhline(0, color="black", lw=0.8, alpha=0.4)
    ax1.axvline(ENTRY, color="#e74c3c", ls="--", lw=1.2, alpha=0.85)
    ax1.fill_between(path["date"], 0, path["slope_bp"], where=path["slope_bp"] >= 0, alpha=0.15, color="#27ae60")
    ax1.fill_between(path["date"], 0, path["slope_bp"], where=path["slope_bp"] < 0, alpha=0.15, color="#c0392b")
    ax1.set_ylabel("Dec27−Dec26 (bp)")

    for dt, row in daily.iterrows():
        if dt < CRISIS_START:
            continue
        ax2.bar(
            dt,
            row["dslope"],
            width=0.8,
            color=regime_color(row["regime"]),
            alpha=0.85,
            edgecolor="none",
        )
    ax2.axhline(0, color="black", lw=0.8, alpha=0.4)
    ax2.axvline(ENTRY, color="#e74c3c", ls="--", lw=1.2, alpha=0.85)
    ax2.set_ylabel("Daily Δslope (bp)")
    ax2.set_xlabel("Date")

    from matplotlib.patches import Patch

    legend_items = [
        Patch(facecolor=regime_color("bear_steepening"), label="Bear steepening"),
        Patch(facecolor=regime_color("bull_flattening"), label="Bull flattening"),
        Patch(facecolor=regime_color("bear_flattening"), label="Bear flattening"),
        Patch(facecolor=regime_color("bull_steepening"), label="Bull steepening"),
    ]
    ax2.legend(handles=legend_items, loc="upper right", fontsize=8, ncol=2)

    fig.tight_layout()
    CHART_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    rates = load_rates()
    daily = build_daily(rates)
    path = build_path(rates)

    periods = [
        period_summary(daily, "crisis_onset (24 Mar – 4 Jun)", CRISIS_START, ENTRY - pd.Timedelta(days=1)),
        period_summary(daily, "post_entry (5 Jun – latest)", ENTRY, daily.index.max()),
        period_summary(daily, "full_sample", daily.index.min(), daily.index.max()),
    ]

    entry = rates.loc[str(ENTRY.date())]
    latest = rates.iloc[-1]
    meta = {
        "entry_date": str(ENTRY.date()),
        "latest_date": str(rates.index[-1].date()),
        "entry": {
            "dec26_rate_pct": round(float(entry[DEC26]), 3),
            "dec27_rate_pct": round(float(entry[DEC27]), 3),
            "slope_bp": round(float((entry[DEC27] - entry[DEC26]) * 100), 1),
            "dec26_vs_bank_bp": round(float((entry[DEC26] - BANK_RATE_PCT) * 100), 1),
        },
        "latest": {
            "dec26_rate_pct": round(float(latest[DEC26]), 3),
            "dec27_rate_pct": round(float(latest[DEC27]), 3),
            "slope_bp": round(float((latest[DEC27] - latest[DEC26]) * 100), 1),
            "dec26_vs_bank_bp": round(float((latest[DEC26] - BANK_RATE_PCT) * 100), 1),
        },
        "periods": periods,
    }

    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    path.to_csv(PATH_FILE, index=False)
    make_chart(path, daily)
    print(f"Wrote {SUMMARY_FILE}")
    print(f"Wrote {PATH_FILE}")
    print(f"Wrote {CHART_FILE}")


if __name__ == "__main__":
    main()
