"""10s30s Treasury curve daily moves (bp) from Investing.com.

Fetches US 10Y and 30Y bond yields via Investing.com HistoricalDataAjax,
builds the 10s30s spread (30Y − 10Y), computes daily changes in basis points
since Jan 2016, and plots a histogram with percentile markers highlighting
the most recent completed daily move.
"""
from __future__ import annotations

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

# Investing.com instrument IDs
PAIR_10Y = 23705
PAIR_30Y = 23706
START = dt.date(2016, 1, 1)

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
    for attempt in range(5):
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


def main() -> None:
    today = dt.date.today()
    # Pull a small buffer past today; Investing.com sometimes labels the live
    # session with today's calendar date.
    end = today + dt.timedelta(days=1)

    print(f"Fetching Investing.com US10Y ({PAIR_10Y}) and US30Y ({PAIR_30Y}) …")
    y10 = fetch_investing_history(PAIR_10Y, "u.s.-10-year-bond-yield", START, end)
    time.sleep(0.8)
    y30 = fetch_investing_history(PAIR_30Y, "u.s.-30-year-bond-yield", START, end)

    df = pd.DataFrame({"y10": y10, "y30": y30}).dropna().sort_index()
    df = df.loc[df.index >= START]
    # Drop an incomplete live session if it prints after the prior close with
    # today's date while US cash close has not settled (keep yesterday's move).
    # Heuristic: if the last date is today (UTC) and there is a prior day, treat
    # the last row as live and exclude it from the move series unless it is the
    # only data we have for "yesterday".
    if len(df) >= 2 and df.index[-1] >= today:
        live_date = df.index[-1]
        df_hist = df.iloc[:-1]
        print(f"Excluding live/incomplete session {live_date} (last complete: {df_hist.index[-1]})")
        df = df_hist

    df["s10s30"] = (df["y30"] - df["y10"]) * 100.0  # level in bp
    df["d_10s30_bp"] = df["s10s30"].diff()  # daily move in bp
    moves = df["d_10s30_bp"].dropna()

    if moves.empty:
        raise SystemExit("No daily moves available")

    last_date = moves.index[-1]
    last_move = float(moves.iloc[-1])
    pct = float((moves <= last_move).mean() * 100.0)
    # percentile rank of absolute magnitude also useful
    abs_pct = float((moves.abs() <= abs(last_move)).mean() * 100.0)

    qs = {
        "p1": float(np.percentile(moves, 1)),
        "p5": float(np.percentile(moves, 5)),
        "p10": float(np.percentile(moves, 10)),
        "p25": float(np.percentile(moves, 25)),
        "p50": float(np.percentile(moves, 50)),
        "p75": float(np.percentile(moves, 75)),
        "p90": float(np.percentile(moves, 90)),
        "p95": float(np.percentile(moves, 95)),
        "p99": float(np.percentile(moves, 99)),
    }

    summary = {
        "source": "Investing.com (US 10Y pair 23705, US 30Y pair 23706)",
        "definition": "10s30s = 30Y yield − 10Y yield; daily move in basis points",
        "start": str(moves.index[0]),
        "end": str(last_date),
        "n_days": int(len(moves)),
        "last_date": str(last_date),
        "last_move_bp": round(last_move, 3),
        "last_level_bp": round(float(df.loc[last_date, "s10s30"]), 3),
        "last_y10": round(float(df.loc[last_date, "y10"]), 4),
        "last_y30": round(float(df.loc[last_date, "y30"]), 4),
        "percentile_rank": round(pct, 2),
        "abs_percentile_rank": round(abs_pct, 2),
        "mean_bp": round(float(moves.mean()), 3),
        "std_bp": round(float(moves.std()), 3),
        "min_bp": round(float(moves.min()), 3),
        "max_bp": round(float(moves.max()), 3),
        "quantiles_bp": {k: round(v, 3) for k, v in qs.items()},
        "prior_close_date": str(moves.index[-2]) if len(moves) > 1 else None,
        "asof_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }

    # CSV of full series
    out_csv = os.path.join(OUT_DATA, "us_10s30s_daily_moves_since_2016.csv")
    out = df.copy()
    out.index.name = "date"
    out.to_csv(out_csv, float_format="%.6f")

    out_json = os.path.join(OUT_DATA, "us_10s30s_move_histogram_summary.json")
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))

    # ---- Histogram (primary deliverable) ----
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

    # Classic 1bp histogram bins; clip display to ~p1–p99 so bars read clearly
    bin_w = 1.0
    lo = np.floor(np.percentile(moves, 1) / bin_w) * bin_w - bin_w
    hi = np.ceil(np.percentile(moves, 99) / bin_w) * bin_w + bin_w
    # keep yesterday visible even if in the far tail
    lo = min(lo, np.floor(last_move / bin_w) * bin_w - bin_w)
    hi = max(hi, np.ceil(last_move / bin_w) * bin_w + bin_w)
    bins = np.arange(lo, hi + bin_w, bin_w)

    counts, edges = np.histogram(moves, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    # highlight the bin containing yesterday's move
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

    # percentile guides + labels along the top of the plot
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

    # annotate yesterday
    direction = "steepened" if last_move > 0 else ("flattened" if last_move < 0 else "unchanged")
    y_ann = max(counts) * 0.72
    x_text = lo + 0.12 * (hi - lo) if last_move >= 0 else hi - 0.12 * (hi - lo)
    ha = "left" if last_move >= 0 else "right"
    ax.annotate(
        f"Yesterday ({last_date:%d %b %Y})\n"
        f"{last_move:+.1f} bp  ·  {pct:.1f}th percentile\n"
        f"10s30s {direction}",
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
    ax.set_xlabel("Daily change in 10s30s (bp)    ·    + = steepener / − = flattener")
    ax.set_ylabel("Number of trading days")
    ax.set_title(
        f"Histogram: US Treasury 10s30s daily moves (Investing.com)\n"
        f"{START:%b %Y} – {last_date:%b %Y}   ·   n={len(moves):,}   ·   "
        f"1 bp bins   ·   red = yesterday's bin"
    )
    ax.text(
        0.01,
        0.02,
        f"Level {last_date:%d %b %Y}: {df.loc[last_date, 's10s30']:+.1f} bp"
        f"  (30Y {df.loc[last_date, 'y30']:.3f}% − 10Y {df.loc[last_date, 'y10']:.3f}%)"
        f"   ·   p5={qs['p5']:+.1f}  p50={qs['p50']:+.1f}  p95={qs['p95']:+.1f} bp",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.5,
        color=AMBER,
    )

    fig.tight_layout()
    name = "us_10s30s_daily_move_histogram_since_2016.png"
    for folder in (OUT_ART, OUT_CHARTS):
        path = os.path.join(folder, name)
        fig.savefig(path, dpi=160)
        print("wrote", path)
    plt.close(fig)

    # remove prior CDF artifact if present (histogram is the deliverable)
    for folder in (OUT_ART, OUT_CHARTS):
        cdf_path = os.path.join(folder, "us_10s30s_daily_move_cdf_since_2016.png")
        if os.path.exists(cdf_path):
            os.remove(cdf_path)
            print("removed", cdf_path)


if __name__ == "__main__":
    main()
