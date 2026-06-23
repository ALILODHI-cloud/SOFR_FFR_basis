#!/usr/bin/env python3
"""Hawkish/dovish day regimes + contract correlation matrix for 1M SONIA curve."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_sonia import classify_curve_move

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "sonia_1m_data.json"
DASH_FILE = ROOT / "sonia_dashboard_data.json"
OUT_FILE = ROOT / "sonia_regime_analysis.json"

DEC26, JUL27, DEC27 = "2026-12", "2027-07", "2027-12"
EPS = 0.25  # bp — unchanged band for slope


def load_rates() -> pd.DataFrame:
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["timeseries"]["rows"]).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df.sort_index().astype(float)


def load_brent() -> pd.Series:
    if not DASH_FILE.exists():
        return pd.Series(dtype=float)
    with DASH_FILE.open(encoding="utf-8") as f:
        dash = json.load(f)
    rows = dash.get("daily_corr") or dash.get("daily") or []
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series(
        {r["date"]: r.get("brent_ret_pct") for r in rows if r.get("brent_ret_pct") is not None},
        name="brent_ret_pct",
    )
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def contract_labels(data: dict) -> dict[str, str]:
    return {c["key"]: c["label"] for c in data.get("contracts", [])}


def slope_regime(d_back: float, d_front: float, dslope: float) -> str:
    return classify_curve_move(d_back, d_front, dslope)


def slope_bucket(dslope: float) -> str:
    if dslope > EPS:
        return "steepening"
    if dslope < -EPS:
        return "flattening"
    return "unchanged"


def regime_summary(
    mask: pd.Series,
    d: pd.DataFrame,
    label: str,
    spread: str,
    ds_col: str,
    reg_col: str,
) -> dict:
    sub = d[mask].copy()
    n = len(sub)
    if n == 0:
        return {"label": label, "spread": spread, "n_days": 0}

    buckets = Counter(sub["bucket"])
    regimes = Counter(sub[reg_col])
    return {
        "label": label,
        "spread": spread,
        "n_days": n,
        "steepening_pct": round(100 * buckets.get("steepening", 0) / n, 1),
        "flattening_pct": round(100 * buckets.get("flattening", 0) / n, 1),
        "unchanged_pct": round(100 * buckets.get("unchanged", 0) / n, 1),
        "mean_dslope_bp": round(float(sub[ds_col].mean()), 2),
        "median_dslope_bp": round(float(sub[ds_col].median()), 2),
        "total_dslope_bp": round(float(sub[ds_col].sum()), 1),
        "regimes": {k: regimes[k] for k in sorted(regimes)},
        "bear_steepening_pct": round(100 * regimes.get("bear_steepening", 0) / n, 1),
        "bear_flattening_pct": round(100 * regimes.get("bear_flattening", 0) / n, 1),
        "bull_steepening_pct": round(100 * regimes.get("bull_steepening", 0) / n, 1),
        "bull_flattening_pct": round(100 * regimes.get("bull_flattening", 0) / n, 1),
    }


def build_day_frame(rates: pd.DataFrame, brent: pd.Series) -> pd.DataFrame:
    chg = rates.diff() * 100  # bp
    d = chg.join(brent, how="left")
    d = d.iloc[1:].copy()

    d["curve_avg_bp"] = chg.mean(axis=1).iloc[1:]
    d["curve_med_bp"] = chg.median(axis=1).iloc[1:]

    for spread, back, front in [
        ("jul27_dec26", DEC26, JUL27),
        ("dec27_dec26", DEC26, DEC27),
    ]:
        if back in d.columns and front in d.columns:
            ds = f"dslope_{spread}"
            reg = f"regime_{spread}"
            d[ds] = d[front] - d[back]
            d[f"bucket_{spread}"] = d[ds].apply(slope_bucket)
            d[reg] = [
                slope_regime(float(r[back]), float(r[front]), float(r[ds]))
                for _, r in d[[back, front, ds]].iterrows()
            ]

    return d


def threshold_scan(
    d: pd.DataFrame,
    col: str,
    thresholds: list[float],
    spread_key: str,
) -> list[dict]:
    ds_col = f"dslope_{spread_key}"
    reg_col = f"regime_{spread_key}"
    bucket_col = f"bucket_{spread_key}"
    d = d.copy()
    d["bucket"] = d[bucket_col]

    out = []
    for thr in thresholds:
        out.append(
            regime_summary(d[col] >= thr, d, f"{col} >= {thr} bp (hawkish)", spread_key, ds_col, reg_col)
        )
        out.append(
            regime_summary(d[col] <= -thr, d, f"{col} <= -{thr} bp (dovish)", spread_key, ds_col, reg_col)
        )
    return out


def oil_threshold_scan(d: pd.DataFrame, thresholds: list[float], spread_key: str) -> list[dict]:
    ds_col = f"dslope_{spread_key}"
    reg_col = f"regime_{spread_key}"
    bucket_col = f"bucket_{spread_key}"
    sub = d[d["brent_ret_pct"].notna()].copy()
    sub["bucket"] = sub[bucket_col]
    out = []
    for thr in thresholds:
        out.append(
            regime_summary(
                sub["brent_ret_pct"] >= thr,
                sub,
                f"Oil >= +{thr}% (hawkish)",
                spread_key,
                ds_col,
                reg_col,
            )
        )
        out.append(
            regime_summary(
                sub["brent_ret_pct"] <= -thr,
                sub,
                f"Oil <= -{thr}% (dovish)",
                spread_key,
                ds_col,
                reg_col,
            )
        )
    return out


def correlation_matrix(rates: pd.DataFrame, labels: dict[str, str]) -> dict:
    chg = rates.diff() * 100
    chg = chg.dropna(how="all")
    corr = chg.corr()

    keys = list(corr.columns)
    display = [labels.get(k, k) for k in keys]
    matrix = []
    for i, rk in enumerate(keys):
        row = []
        for j, ck in enumerate(keys):
            v = corr.iloc[i, j]
            row.append(None if pd.isna(v) else round(float(v), 3))
        matrix.append(row)

    # highlight pairs
    pairs = []
    if DEC26 in keys and JUL27 in keys:
        pairs.append(
            {
                "pair": "Jul27 vs Dec26",
                "corr": round(float(corr.loc[JUL27, DEC26]), 3),
            }
        )
    if DEC26 in keys and DEC27 in keys:
        pairs.append(
            {
                "pair": "Dec27 vs Dec26",
                "corr": round(float(corr.loc[DEC27, DEC26]), 3),
            }
        )

    return {
        "n_sessions": int(len(chg)),
        "contracts": display,
        "keys": keys,
        "matrix": matrix,
        "key_pairs": pairs,
    }


def main() -> None:
    with DATA_FILE.open(encoding="utf-8") as f:
        raw = json.load(f)
    labels = contract_labels(raw)
    rates = load_rates()
    brent = load_brent()
    d = build_day_frame(rates, brent)

    dec26_col = DEC26
    thr_dec26 = [0.25, 0.5, 1.0, 2.0, 3.0]
    thr_oil = [1.0, 2.0, 3.0, 4.0]
    thr_curve = [0.25, 0.5, 1.0]

    results = {
        "generated_from": str(DATA_FILE.name),
        "n_days": len(d),
        "date_start": str(d.index.min().date()),
        "date_end": str(d.index.max().date()),
        "eps_bp": EPS,
        "definitions": {
            "steepening": f"Δ(front − back) > {EPS} bp",
            "flattening": f"Δ(front − back) < -{EPS} bp",
            "dec26_hawkish": "Dec-26 implied rate daily rise",
            "dec26_dovish": "Dec-26 implied rate daily fall",
            "oil_hawkish": "Brent daily return positive",
            "oil_dovish": "Brent daily return negative",
        },
        "spreads": {},
        "correlation": correlation_matrix(rates, labels),
    }

    for spread in ("jul27_dec26", "dec27_dec26"):
        spread_label = "Jul27−Dec26" if spread == "jul27_dec26" else "Dec27−Dec26"
        block = {
            "spread_label": spread_label,
            "by_dec26": threshold_scan(d, dec26_col, thr_dec26, spread),
            "by_curve_avg": threshold_scan(d, "curve_avg_bp", thr_curve, spread),
        }
        if brent.notna().any():
            block["by_oil"] = oil_threshold_scan(d, thr_oil, spread)
        results["spreads"][spread] = block

    OUT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print_report(results)
    print(f"\nWrote {OUT_FILE}")


def print_report(r: dict) -> None:
    print("=" * 72)
    print(f"SONIA regime analysis  {r['date_start']} → {r['date_end']}  ({r['n_days']} days)")
    print(f"Steepening = Δslope > {r['eps_bp']} bp   |   Flattening = Δslope < -{r['eps_bp']} bp")
    print("=" * 72)

    for spread_key, block in r["spreads"].items():
        print(f"\n### {block['spread_label']}")
        for section, rows in block.items():
            if section == "spread_label" or not rows:
                continue
            print(f"\n  [{section}]")
            for row in rows:
                if row["n_days"] == 0:
                    print(f"    {row['label']}: n=0")
                    continue
                print(
                    f"    {row['label']}: n={row['n_days']:2d}  "
                    f"steep {row['steepening_pct']:4.0f}%  flat {row['flattening_pct']:4.0f}%  "
                    f"mean Δslope {row['mean_dslope_bp']:+.2f} bp  "
                    f"[bear_st {row['bear_steepening_pct']:.0f}% bear_fl {row['bear_flattening_pct']:.0f}% "
                    f"bull_st {row['bull_steepening_pct']:.0f}% bull_fl {row['bull_flattening_pct']:.0f}%]"
                )

    print("\n" + "=" * 72)
    print("CORRELATION MATRIX (daily implied-rate changes, bp)")
    c = r["correlation"]
    for p in c["key_pairs"]:
        print(f"  {p['pair']}: {p['corr']:.3f}")
    print(f"\n  ({c['n_sessions']} sessions, {len(c['contracts'])} contracts)")
    # compact: show Dec26 row vs all
    keys = c["keys"]
    if DEC26 in keys:
        i = keys.index(DEC26)
        print("\n  Dec-26 daily Δ corr with each contract:")
        for j, lab in enumerate(c["contracts"]):
            print(f"    {lab:8s}  {c['matrix'][i][j]:+.3f}")


if __name__ == "__main__":
    main()
