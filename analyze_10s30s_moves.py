"""US Treasury curve daily-move histograms from Investing.com.

Fetches front/back bond yields via Investing.com HistoricalDataAjax, builds
spreads (e.g. 10s30s = 30Y−10Y, 5s30s = 30Y−5Y), computes daily changes in
basis points since Jan 2016, and plots a 1 bp histogram with percentile
markers highlighting yesterday's move.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT_ART = os.environ.get("CHART_OUT", "/opt/cursor/artifacts")
OUT_CHARTS = "/workspace/charts"
OUT_DATA = "/workspace/data"
os.makedirs(OUT_ART, exist_ok=True)
os.makedirs(OUT_CHARTS, exist_ok=True)
os.makedirs(OUT_DATA, exist_ok=True)

START = dt.date(2016, 1, 1)

# Investing.com instrument IDs / page slugs
TENORS = {
    "5Y": (23703, "u.s.-5-year-bond-yield"),
    "10Y": (23705, "u.s.-10-year-bond-yield"),
    "30Y": (23706, "u.s.-30-year-bond-yield"),
}

SPREADS = {
    "10s30s": ("10Y", "30Y"),
    "5s30s": ("5Y", "30Y"),
}

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/plain, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.investing.com",
}


def fetch_investing_history(curr_id: int, slug: str, st: dt.date, end: dt.date) -> pd.Series:
    """Return daily close yield series from Investing.com HistoricalDataAjax."""
    headers = dict(UA)
    headers["Referer"] = f"https://www.investing.com/rates-bonds/{slug}-historical-data"
    payload = urllib.parse.urlencode(
        {
            "curr_id": str(curr_id),
            "smlID": "300002",
            "header": f"{slug} Historical Data",
            "st_date": st.strftime("%m/%d/%Y"),
            "end_date": end.strftime("%m/%d/%Y"),
            "interval_sec": "Daily",
            "sort_col": "date",
            "sort_ord": "ASC",
            "action": "historical_data",
        }
    ).encode()

    last_err = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                "https://www.investing.com/instruments/HistoricalDataAjax",
                data=payload,
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read().decode("utf-8", "replace")
            break
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    else:
        raise SystemExit(f"Investing.com fetch failed for {curr_id}: {last_err}")

    rows = []
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        chunk = m.group(1)
        md = re.search(r'data-real-value="(\d+)"', chunk)
        if not md:
            continue
        nums = re.findall(r">([0-9]+\.[0-9]+)<", chunk)
        if not nums:
            continue
        d = dt.datetime.fromtimestamp(int(md.group(1)), dt.timezone.utc).date()
        rows.append((d, float(nums[0])))

    if not rows:
        raise SystemExit(f"No rows parsed for curr_id={curr_id}")

    s = pd.Series({d: v for d, v in rows}, dtype=float).sort_index()
    s.name = slug
    return s


def run_spread(name: str, front: str, back: str, cache: dict[str, pd.Series], end: dt.date) -> dict:
    today = dt.date.today()
    front_id, front_slug = TENORS[front]
    back_id, back_slug = TENORS[back]

    if front not in cache:
        print(f"Fetching Investing.com {front} ({front_id}) …")
        cache[front] = fetch_investing_history(front_id, front_slug, START, end)
        time.sleep(0.8)
    if back not in cache:
        print(f"Fetching Investing.com {back} ({back_id}) …")
        cache[back] = fetch_investing_history(back_id, back_slug, START, end)
        time.sleep(0.8)

    y_front = cache[front]
    y_back = cache[back]
    front_col = "y" + front[:-1] if front.endswith("Y") else front.lower()
    back_col = "y" + back[:-1] if back.endswith("Y") else back.lower()

    df = pd.DataFrame({front_col: y_front, back_col: y_back}).dropna().sort_index()
    df = df.loc[df.index >= START]
    if len(df) >= 2 and df.index[-1] >= today:
        live_date = df.index[-1]
        df_hist = df.iloc[:-1]
        print(f"[{name}] Excluding live/incomplete session {live_date} (last complete: {df_hist.index[-1]})")
        df = df_hist

    spread_col = f"s{name}"
    move_col = f"d_{name}_bp"
    df[spread_col] = (df[back_col] - df[front_col]) * 100.0
    df[move_col] = df[spread_col].diff()
    moves = df[move_col].dropna()
    if moves.empty:
        raise SystemExit(f"No daily moves available for {name}")

    last_date = moves.index[-1]
    prior_date = moves.index[-2]
    last_move = float(moves.iloc[-1])
    pct = float((moves <= last_move).mean() * 100.0)
    abs_pct = float((moves.abs() <= abs(last_move)).mean() * 100.0)

    qs = {
        f"p{p}": float(np.percentile(moves, p))
        for p in (1, 5, 10, 25, 50, 75, 90, 95, 99)
    }

    summary = {
        "spread": name,
        "source": (
            f"Investing.com (US {front} pair {front_id}, US {back} pair {back_id})"
        ),
        "definition": f"{name} = {back} yield − {front} yield; daily move in basis points",
        "start": str(moves.index[0]),
        "end": str(last_date),
        "n_days": int(len(moves)),
        "last_date": str(last_date),
        "prior_close_date": str(prior_date),
        "last_move_bp": round(last_move, 3),
        "last_level_bp": round(float(df.loc[last_date, spread_col]), 3),
        f"last_{front_col}": round(float(df.loc[last_date, front_col]), 4),
        f"last_{back_col}": round(float(df.loc[last_date, back_col]), 4),
        f"prior_{front_col}": round(float(df.loc[prior_date, front_col]), 4),
        f"prior_{back_col}": round(float(df.loc[prior_date, back_col]), 4),
        "prior_level_bp": round(float(df.loc[prior_date, spread_col]), 3),
        "percentile_rank": round(pct, 2),
        "abs_percentile_rank": round(abs_pct, 2),
        "mean_bp": round(float(moves.mean()), 3),
        "std_bp": round(float(moves.std()), 3),
        "min_bp": round(float(moves.min()), 3),
        "max_bp": round(float(moves.max()), 3),
        "quantiles_bp": {k: round(v, 3) for k, v in qs.items()},
        "asof_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }

    out_csv = os.path.join(OUT_DATA, f"us_{name}_daily_moves_since_2016.csv")
    out = df.copy()
    out.index.name = "date"
    out.to_csv(out_csv, float_format="%.6f")

    out_json = os.path.join(OUT_DATA, f"us_{name}_move_histogram_summary.json")
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))

    # ---- Histogram ----
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
            "font.size": 12,
            "axes.titlesize": 14,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": "#222631",
            "grid.linewidth": 0.8,
        }
    )
    BLUE, RED, GREEN, AMBER, MUTED = (
        "#3b82f6",
        "#ef4444",
        "#22c55e",
        "#f59e0b",
        "#8b949e",
    )

    fig, ax = plt.subplots(figsize=(12, 6.5))
    bin_w = 1.0
    lo = np.floor(np.percentile(moves, 1) / bin_w) * bin_w - bin_w
    hi = np.ceil(np.percentile(moves, 99) / bin_w) * bin_w + bin_w
    lo = min(lo, np.floor(last_move / bin_w) * bin_w - bin_w)
    hi = max(hi, np.ceil(last_move / bin_w) * bin_w + bin_w)
    bins = np.arange(lo, hi + bin_w, bin_w)

    counts, edges = np.histogram(moves, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    last_bin = int(np.digitize([last_move], edges, right=False)[0] - 1)
    last_bin = max(0, min(last_bin, len(counts) - 1))
    colors = [RED if i == last_bin else BLUE for i in range(len(counts))]

    ax.bar(
        centers,
        counts,
        width=bin_w * 0.92,
        color=colors,
        edgecolor="#0e1117",
        linewidth=0.6,
        align="center",
        zorder=2,
    )

    ylim_top_guide = max(counts) * 1.18
    for key, lab in [
        ("p5", "5th"),
        ("p25", "25th"),
        ("p50", "50th"),
        ("p75", "75th"),
        ("p95", "95th"),
    ]:
        x = qs[key]
        if x < lo or x > hi:
            continue
        is_med = key == "p50"
        ax.axvline(
            x,
            color=GREEN if is_med else MUTED,
            lw=1.8 if is_med else 1.15,
            ls="-" if is_med else "--",
            alpha=0.9,
            zorder=3,
        )
        ax.text(
            x,
            ylim_top_guide * 0.98,
            f"{lab}\n{x:+.1f}",
            ha="center",
            va="top",
            fontsize=8.5,
            color=GREEN if is_med else MUTED,
            linespacing=1.05,
        )

    ax.axvline(0, color="#6b7280", lw=1.0, zorder=1)

    direction = "steepened" if last_move > 0 else ("flattened" if last_move < 0 else "unchanged")
    y_ann = max(counts) * 0.72
    x_text = lo + 0.12 * (hi - lo) if last_move >= 0 else hi - 0.12 * (hi - lo)
    ha = "left" if last_move >= 0 else "right"
    ax.annotate(
        f"Yesterday ({last_date:%d %b %Y})\n"
        f"{last_move:+.1f} bp  ·  {pct:.1f}th percentile\n"
        f"{name} {direction}",
        xy=(centers[last_bin], counts[last_bin]),
        xytext=(x_text, y_ann),
        color="#e6e6e6",
        fontsize=12,
        ha=ha,
        va="center",
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#161b22", edgecolor=RED, lw=1.6),
        arrowprops=dict(arrowstyle="->", color=RED, lw=2.0),
        zorder=5,
    )

    ax.set_xlim(lo, hi)
    ax.set_ylim(0, max(counts) * 1.22)
    ax.set_xlabel(f"Daily change in {name} (bp)    ·    + = steepener / − = flattener")
    ax.set_ylabel("Number of trading days")
    ax.set_title(
        f"Histogram: US Treasury {name} daily moves (Investing.com)\n"
        f"{START:%b %Y} – {last_date:%b %Y}   ·   n={len(moves):,}   ·   "
        f"1 bp bins   ·   red = yesterday's bin"
    )
    ax.text(
        0.01,
        0.02,
        f"Level {last_date:%d %b %Y}: {df.loc[last_date, spread_col]:+.1f} bp"
        f"  ({back} {df.loc[last_date, back_col]:.3f}% − {front} {df.loc[last_date, front_col]:.3f}%)"
        f"   ·   p5={qs['p5']:+.1f}  p50={qs['p50']:+.1f}  p95={qs['p95']:+.1f} bp",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.5,
        color=AMBER,
    )

    fig.tight_layout()
    fname = f"us_{name}_daily_move_histogram_since_2016.png"
    for folder in (OUT_ART, OUT_CHARTS):
        path = os.path.join(folder, fname)
        fig.savefig(path, dpi=160)
        print("wrote", path)
    plt.close(fig)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="US Treasury spread daily-move histograms")
    ap.add_argument(
        "spreads",
        nargs="*",
        default=["5s30s"],
        choices=list(SPREADS.keys()),
        help="Spreads to build (default: 5s30s)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="Build all supported spreads (5s30s, 10s30s)",
    )
    args = ap.parse_args()
    names = list(SPREADS.keys()) if args.all else (args.spreads or ["5s30s"])

    today = dt.date.today()
    end = today + dt.timedelta(days=1)
    cache: dict[str, pd.Series] = {}
    for name in names:
        front, back = SPREADS[name]
        run_spread(name, front, back, cache, end)


if __name__ == "__main__":
    main()
