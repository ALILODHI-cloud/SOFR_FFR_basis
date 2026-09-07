#!/usr/bin/env python3
"""Chart the Dec26 UK−EUR relative policy-pricing trade around its 30 Jul 2026 close."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "closed_trades" / "dec26_uk_eur_flattener_trade_data.json"
OUTS = [ROOT / "charts", ROOT / "docs" / "charts"]
NAME = "dec26_uk_eur_relative_policy_close.png"
TRIGGER_BP = 4.0

INK = "#1b2330"
MUT = "#6b7a90"
UK = "#2f6fd0"
EUR = "#e08a1e"
REL = "#8b5cf6"


def frame(payload: dict) -> pd.DataFrame:
    rows = payload["trade_path"] + payload.get("post_exit_path", [])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    df = frame(payload)
    ex = payload["exit"]
    entry_dt = pd.Timestamp(payload["entry"]["date"])
    exit_dt = pd.Timestamp(ex["date"])
    entry_rel = payload["entry"]["relative_vs_policy_bp"]
    exit_rel = ex["relative_vs_policy_bp"]

    held = df.loc[:exit_dt]
    after = df.loc[exit_dt:]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 8.6), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]}
    )

    ax1.axhspan(-12, TRIGGER_BP, color=REL, alpha=0.05)
    ax1.axhline(0, color=MUT, lw=1, ls=(0, (2, 3)))
    ax1.axhline(TRIGGER_BP, color=REL, lw=1.2, ls="--")
    ax1.annotate(
        f"close trigger +{TRIGGER_BP:.0f} bp",
        xy=(df.index[-1], TRIGGER_BP),
        xytext=(-6, 6),
        textcoords="offset points",
        ha="right",
        fontsize=9,
        color=REL,
    )
    ax1.plot(
        after.index,
        after["relative_vs_policy_bp"],
        color=MUT,
        lw=1.4,
        ls=":",
        label="After close (not held)",
    )
    ax1.plot(
        held.index,
        held["relative_vs_policy_bp"],
        color=REL,
        lw=2.6,
        marker="o",
        ms=6,
        label="Relative implied policy change, position held",
    )
    ax1.scatter([entry_dt], [entry_rel], s=110, color="#16a34a", zorder=6)
    ax1.annotate(
        f"Entry 28 Jul · {entry_rel:+.1f} bp",
        xy=(entry_dt, entry_rel),
        xytext=(12, -26),
        textcoords="offset points",
        fontsize=9.5,
        color="#16a34a",
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": "#16a34a", "lw": 0.9},
    )
    ax1.scatter([exit_dt], [exit_rel], s=140, marker="X", color="#dc2626", zorder=6)
    ax1.annotate(
        f"Close 30 Jul · {exit_rel:+.1f} bp\nBoE hold 6–3, +{ex['pnl_bp']:.1f} bp / +${ex['pnl_usd']:,.0f}",
        xy=(exit_dt, exit_rel),
        xytext=(16, 10),
        textcoords="offset points",
        fontsize=9.5,
        color="#dc2626",
        fontweight="bold",
    )
    ax1.set_ylabel("bp", color=INK)
    ax1.set_title(
        "Dec-26 relative policy pricing: (SONIA − Bank Rate) − (ESTR − ECB deposit)",
        loc="left",
        fontsize=13,
        fontweight="bold",
        color=INK,
    )
    ax1.legend(frameon=False, fontsize=9, loc="lower left")

    ax2.plot(df.index, df["sonia_vs_bank_bp"], color=UK, lw=2, label="SONIA Dec-26 vs Bank Rate 3.75%")
    ax2.plot(df.index, df["estr_vs_deposit_bp"], color=EUR, lw=2, label="ESTR Dec-26 vs ECB deposit 2.25%")
    for dt, style in ((entry_dt, "-"), (exit_dt, "--")):
        ax2.axvline(dt, color=MUT, lw=1, ls=style)
        ax1.axvline(dt, color=MUT, lw=1, ls=style)
    ax2.annotate(
        "BoE MPC\n30 Jul",
        xy=(exit_dt, df.loc[exit_dt, "sonia_vs_bank_bp"]),
        xytext=(12, 22),
        textcoords="offset points",
        fontsize=9,
        color=UK,
        arrowprops={"arrowstyle": "->", "color": UK, "lw": 1},
    )
    ax2.set_ylabel("bp of hikes priced by end-2026", color=INK)
    ax2.set_title("Each leg against its own policy rate", loc="left", fontsize=12, color=INK)
    ax2.legend(frameon=False, fontsize=9, loc="lower right", ncol=2)
    ax2.margins(y=0.22)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))

    for ax in (ax1, ax2):
        ax.grid(alpha=0.18, lw=0.7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUT)

    fig.text(
        0.008,
        0.008,
        "Short JUZ26 / long IJZ26, $25/bp. Barchart EOD. Policy rates unchanged over the window, "
        "so relative and absolute UK−EUR P&L coincide.",
        fontsize=8,
        color=MUT,
    )
    fig.tight_layout(rect=(0, 0.022, 1, 1))

    for out_dir in OUTS:
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / NAME, dpi=150, facecolor="white")
        print(f"Wrote {out_dir / NAME}")


if __name__ == "__main__":
    main()
