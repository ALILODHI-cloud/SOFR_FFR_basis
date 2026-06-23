#!/usr/bin/env python3
"""Track Jul27−Dec26 SONIA steepener P&L from Barchart / sonia_1m_data."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_sonia import (
    BANK_RATE_AS_OF,
    BANK_RATE_PCT,
    classify_curve_move,
    fetch_barchart_eod,
    price_to_rate,
)

ROOT = Path(__file__).resolve().parent
TRADE_CFG = ROOT / "trades" / "jul27_dec26_steepener.json"
SONIA_1M = ROOT / "sonia_1m_data.json"
OUT = ROOT / "jul27_dec26_trade_data.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_cfg() -> dict:
    with TRADE_CFG.open(encoding="utf-8") as f:
        return json.load(f)


def save_cfg(cfg: dict) -> None:
    with TRADE_CFG.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def fetch_leg(symbol: str) -> tuple[pd.DataFrame, dict]:
    df = fetch_barchart_eod(symbol)
    rates = price_to_rate(df["price"])
    latest = df.iloc[-1]
    return df, {
        "symbol": symbol,
        "date": str(df.index[-1].date()),
        "price": round(float(latest["price"]), 4),
        "implied_rate_pct": round(float(rates.iloc[-1]), 4),
    }


def series_from_sonia(long_key: str, short_key: str) -> pd.DataFrame | None:
    if not SONIA_1M.exists():
        return None
    with SONIA_1M.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data["timeseries"]["rows"]
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    if long_key not in df.columns or short_key not in df.columns:
        return None
    sub = df[[short_key, long_key]].dropna().astype(float)
    sub.columns = ["short_rate", "long_rate"]
    sub["slope_bp"] = (sub["long_rate"] - sub["short_rate"]) * 100.0
    return sub.sort_index()


def ensure_entry(cfg: dict, short_snap: dict, long_snap: dict) -> dict:
    """Capture entry on first run or when entry_date not yet in history."""
    entry_date = cfg["entry_date"]
    if cfg.get("entry_locked") and cfg.get("entry"):
        return cfg

    entry = {
        "date": entry_date,
        "label": cfg.get("entry_label", entry_date),
        "short": short_snap,
        "long": long_snap,
        "slope_bp": round((long_snap["implied_rate_pct"] - short_snap["implied_rate_pct"]) * 100, 2),
        "captured_utc": utc_now(),
        "source": "barchart_live",
    }
    cfg["entry"] = entry
    if short_snap["date"] == entry_date and long_snap["date"] == entry_date:
        cfg["entry"]["source"] = "barchart_eod"
        cfg["entry_locked"] = True
    save_cfg(cfg)
    return cfg


def build_path(tail: pd.DataFrame, entry_slope: float, gbp_per_bp: float) -> list[dict]:
    path = []
    for dt, row in tail.iterrows():
        slope = float(row["slope_bp"])
        dslope = slope - entry_slope
        path.append(
            {
                "date": str(dt.date()),
                "short_rate": round(float(row["short_rate"]), 4),
                "long_rate": round(float(row["long_rate"]), 4),
                "slope_bp": round(slope, 2),
                "dslope_bp": round(dslope, 2),
                "cum_pnl_gbp": round(dslope * gbp_per_bp, 2),
                "daily_pnl_gbp": None,
            }
        )
    for i in range(1, len(path)):
        path[i]["daily_pnl_gbp"] = round(path[i]["cum_pnl_gbp"] - path[i - 1]["cum_pnl_gbp"], 2)
    if path:
        path[0]["daily_pnl_gbp"] = round(path[0]["cum_pnl_gbp"], 2)
    return path


def regime_stats(tail: pd.DataFrame) -> list[dict]:
    if len(tail) < 2:
        return []
    d = tail.copy()
    d["d_short"] = d["short_rate"].diff() * 100
    d["d_long"] = d["long_rate"].diff() * 100
    d["dslope"] = d["slope_bp"].diff()
    daily = d.iloc[1:]
    labels = {
        "bear_steepening": "Bear steepening",
        "bull_steepening": "Bull steepening",
        "bear_flattening": "Bear flattening",
        "bull_flattening": "Bull flattening",
        "mixed_steepening": "Mixed steepening",
        "mixed_flattening": "Mixed flattening",
        "unchanged": "Unchanged",
    }
    counts: dict[str, dict] = {}
    for _, r in daily.iterrows():
        key = classify_curve_move(float(r["d_short"]), float(r["d_long"]), float(r["dslope"]))
        counts.setdefault(key, {"days": 0, "pnl_bp": 0.0})
        counts[key]["days"] += 1
        counts[key]["pnl_bp"] += float(r["dslope"])
    out = []
    for key, v in counts.items():
        out.append(
            {
                "regime": key,
                "label": labels.get(key, key),
                "days": v["days"],
                "pnl_slope_bp": round(v["pnl_bp"], 2),
                "pnl_gbp": round(v["pnl_bp"] * 12.5, 2),
            }
        )
    out.sort(key=lambda x: abs(x["pnl_gbp"]), reverse=True)
    return out


def main() -> None:
    cfg = load_cfg()
    gbp = float(cfg["gbp_per_bp"])
    long_sym = cfg["long_symbol"]
    short_sym = cfg["short_symbol"]
    long_key = cfg["long_key"]
    short_key = cfg["short_key"]

    print(f"Fetching {long_sym} / {short_sym}…")
    short_df, short_snap = fetch_leg(short_sym)
    long_df, long_snap = fetch_leg(long_sym)
    cfg = ensure_entry(cfg, short_snap, long_snap)
    entry = cfg["entry"]
    entry_date = pd.Timestamp(entry["date"])
    entry_slope = float(entry["slope_bp"])

    hist = series_from_sonia(long_key, short_key)
    if hist is None:
        hist = pd.DataFrame(columns=["short_rate", "long_rate", "slope_bp"])
        hist.index = pd.to_datetime(hist.index)

    for df, col in [(short_df, "short_rate"), (long_df, "long_rate")]:
        for dt, px in df["price"].items():
            dt = pd.Timestamp(dt).normalize()
            hist.loc[dt, col] = float(price_to_rate(pd.Series([px])).iloc[0])
    hist = hist.sort_index()
    hist["slope_bp"] = (hist["long_rate"] - hist["short_rate"]) * 100.0

    tail = hist.loc[hist.index >= entry_date].copy()
    if tail.empty:
        tail = pd.DataFrame(
            {
                "short_rate": [entry["short"]["implied_rate_pct"]],
                "long_rate": [entry["long"]["implied_rate_pct"]],
                "slope_bp": [entry_slope],
            },
            index=[entry_date],
        )

    latest = tail.iloc[-1]
    mark_slope = float(latest["slope_bp"])
    pnl_slope_bp = mark_slope - entry_slope
    pnl_gbp = pnl_slope_bp * gbp

    mark = {
        "date": str(tail.index[-1].date()),
        "short": short_snap,
        "long": long_snap,
        "slope_bp": round(mark_slope, 2),
        "updated_utc": utc_now(),
    }

    path = build_path(tail, entry_slope, gbp)
    regimes = regime_stats(tail)

    payload = {
        "generated_utc": utc_now(),
        "trade": {
            "id": cfg["trade_id"],
            "label": cfg["label"],
            "position": cfg["position"],
            "entry_locked": cfg.get("entry_locked", False),
        },
        "bank_rate_pct": BANK_RATE_PCT,
        "bank_rate_as_of": BANK_RATE_AS_OF,
        "entry": entry,
        "mark": mark,
        "pnl": {
            "slope_bp": round(pnl_slope_bp, 2),
            "gbp": round(pnl_gbp, 2),
            "short_leg_bp": round((float(latest["short_rate"]) - entry["short"]["implied_rate_pct"]) * 100, 2),
            "long_leg_bp": round((float(latest["long_rate"]) - entry["long"]["implied_rate_pct"]) * 100, 2),
        },
        "trade_path": path,
        "regime_attribution": regimes,
        "market_note_url": "https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_15/body.md",
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Entry slope {entry_slope:+.1f} bp → mark {mark_slope:+.1f} bp | P&L {pnl_gbp:+.1f} GBP")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
