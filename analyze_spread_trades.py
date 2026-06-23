#!/usr/bin/env python3
"""Track SONIA calendar-spread trades from Barchart / sonia_1m_data."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyze_sonia import (
    BANK_RATE_AS_OF,
    BANK_RATE_PCT,
    classify_curve_move,
    fetch_barchart_eod,
    price_to_rate,
)

ROOT = Path(__file__).resolve().parent
TRADES_DIR = ROOT / "trades"
SONIA_1M = ROOT / "sonia_1m_data.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_cfg(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_cfg(path: Path, cfg: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def quoted_keys(cfg: dict) -> tuple[str, str, str]:
    qs = cfg.get("quoted_spread") or {}
    long_key = qs.get("long_key", cfg["long_key"])
    short_key = qs.get("short_key", cfg["short_key"])
    label = qs.get("label", cfg["label"])
    return long_key, short_key, label


def quoted_slope_bp(leg_rates: dict[str, float], q_long_key: str, q_short_key: str) -> float:
    return (leg_rates[q_long_key] - leg_rates[q_short_key]) * 100.0


def pnl_slope_bp(entry_slope: float, mark_slope: float, direction: str) -> float:
    if direction == "flattener":
        return entry_slope - mark_slope
    return mark_slope - entry_slope


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


def series_from_sonia(keys: list[str]) -> pd.DataFrame | None:
    if not SONIA_1M.exists():
        return None
    with SONIA_1M.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data["timeseries"]["rows"]
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    cols = [k for k in keys if k in df.columns]
    if len(cols) < 2:
        return None
    return df[cols].dropna().astype(float).sort_index()


def ensure_entry(
    cfg_path: Path,
    cfg: dict,
    leg_rates: dict[str, float],
    short_snap: dict,
    long_snap: dict,
    q_long_key: str,
    q_short_key: str,
) -> dict:
    entry_date = cfg["entry_date"]
    if cfg.get("entry"):
        if cfg.get("entry_locked"):
            return cfg
        if short_snap["date"] == entry_date and long_snap["date"] == entry_date:
            cfg["entry_locked"] = True
            cfg["entry"]["source"] = "barchart_eod"
            save_cfg(cfg_path, cfg)
        return cfg

    slope = quoted_slope_bp(leg_rates, q_long_key, q_short_key)
    entry = {
        "date": entry_date,
        "label": cfg.get("entry_label", entry_date),
        "short": short_snap,
        "long": long_snap,
        "slope_bp": round(slope, 2),
        "captured_utc": utc_now(),
        "source": "barchart_live",
    }
    cfg["entry"] = entry
    if short_snap["date"] == entry_date and long_snap["date"] == entry_date:
        cfg["entry"]["source"] = "barchart_eod"
        cfg["entry_locked"] = True
    save_cfg(cfg_path, cfg)
    return cfg


def build_path(
    tail: pd.DataFrame,
    entry_slope: float,
    gbp_per_bp: float,
    direction: str,
    q_long_key: str,
    q_short_key: str,
) -> list[dict]:
    path = []
    prev_cum = 0.0
    for i, (dt, row) in enumerate(tail.iterrows()):
        leg_rates = {k: float(row[k]) for k in row.index}
        q_slope = quoted_slope_bp(leg_rates, q_long_key, q_short_key)
        dslope = pnl_slope_bp(entry_slope, q_slope, direction)
        cum = dslope * gbp_per_bp
        daily = cum if i == 0 else cum - prev_cum
        prev_cum = cum
        path.append(
            {
                "date": str(dt.date()),
                "quoted_long_rate": round(leg_rates[q_long_key], 4),
                "quoted_short_rate": round(leg_rates[q_short_key], 4),
                "slope_bp": round(q_slope, 2),
                "dslope_bp": round(dslope, 2),
                "cum_pnl_gbp": round(cum, 2),
                "daily_pnl_gbp": round(daily, 2),
            }
        )
    return path


def regime_stats(
    tail: pd.DataFrame,
    direction: str,
    gbp: float,
    q_long_key: str,
    q_short_key: str,
) -> list[dict]:
    if len(tail) < 2:
        return []
    d = tail.copy()
    d["q_long"] = d[q_long_key]
    d["q_short"] = d[q_short_key]
    d["d_short"] = d["q_short"].diff() * 100
    d["d_long"] = d["q_long"].diff() * 100
    d["dslope"] = (d["q_long"] - d["q_short"]).diff() * 100
    if direction == "flattener":
        d["dslope"] = -d["dslope"]
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
                "pnl_gbp": round(v["pnl_bp"] * gbp, 2),
            }
        )
    out.sort(key=lambda x: abs(x["pnl_gbp"]), reverse=True)
    return out


def analyze_trade(cfg_path: Path) -> dict:
    cfg = load_cfg(cfg_path)
    gbp = float(cfg["gbp_per_bp"])
    direction = cfg.get("direction", "steepener")
    long_sym = cfg["long_symbol"]
    short_sym = cfg["short_symbol"]
    long_key = cfg["long_key"]
    short_key = cfg["short_key"]
    q_long_key, q_short_key, spread_label = quoted_keys(cfg)
    keys = list({long_key, short_key, q_long_key, q_short_key})

    print(f"[{cfg['trade_id']}] Fetching {long_sym} / {short_sym}…")
    short_df, short_snap = fetch_leg(short_sym)
    long_df, long_snap = fetch_leg(long_sym)
    leg_rates = {short_key: short_snap["implied_rate_pct"], long_key: long_snap["implied_rate_pct"]}
    cfg = ensure_entry(cfg_path, cfg, leg_rates, short_snap, long_snap, q_long_key, q_short_key)
    entry = cfg["entry"]
    entry_date = pd.Timestamp(entry["date"])
    entry_slope = float(entry["slope_bp"])

    hist = series_from_sonia(keys)
    if hist is None:
        hist = pd.DataFrame(index=pd.DatetimeIndex([]))

    for df, key in [(short_df, short_key), (long_df, long_key)]:
        for dt, px in df["price"].items():
            dt = pd.Timestamp(dt).normalize()
            hist.loc[dt, key] = float(price_to_rate(pd.Series([px])).iloc[0])
    hist = hist.sort_index()

    tail = hist.loc[hist.index >= entry_date].copy()
    if tail.empty:
        tail = pd.DataFrame(
            {short_key: [leg_rates[short_key]], long_key: [leg_rates[long_key]]},
            index=[entry_date],
        )

    latest = tail.iloc[-1]
    mark_leg_rates = {k: float(latest[k]) for k in keys if k in latest.index}
    mark_slope = quoted_slope_bp(mark_leg_rates, q_long_key, q_short_key)
    pnl_slope = pnl_slope_bp(entry_slope, mark_slope, direction)
    pnl_gbp = pnl_slope * gbp

    mark = {
        "date": str(tail.index[-1].date()),
        "short": short_snap,
        "long": long_snap,
        "slope_bp": round(mark_slope, 2),
        "updated_utc": utc_now(),
    }

    qs = cfg.get("quoted_spread") or {}
    path = build_path(tail, entry_slope, gbp, direction, q_long_key, q_short_key)
    regimes = regime_stats(tail, direction, gbp, q_long_key, q_short_key)

    entry_long = leg_rates[q_long_key]
    entry_short = leg_rates[q_short_key]

    payload = {
        "generated_utc": utc_now(),
        "trade": {
            "id": cfg["trade_id"],
            "label": cfg["label"],
            "position": cfg["position"],
            "direction": direction,
            "spread_label": spread_label,
            "entry_locked": cfg.get("entry_locked", False),
            "gbp_per_bp": gbp,
            "detail_page": cfg.get("detail_page", f"trade_{cfg['trade_id']}.html"),
        },
        "bank_rate_pct": BANK_RATE_PCT,
        "bank_rate_as_of": BANK_RATE_AS_OF,
        "entry": entry,
        "mark": mark,
        "pnl": {
            "slope_bp": round(pnl_slope, 2),
            "gbp": round(pnl_gbp, 2),
            "quoted_long_leg_bp": round((mark_leg_rates[q_long_key] - entry_long) * 100, 2),
            "quoted_short_leg_bp": round((mark_leg_rates[q_short_key] - entry_short) * 100, 2),
        },
        "trade_path": path,
        "regime_attribution": regimes,
        "market_note_url": cfg.get(
            "market_note_url",
            "https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_15/body.md",
        ),
        "leg_labels": {
            "quoted_long": qs.get("long_label", q_long_key),
            "quoted_short": qs.get("short_label", q_short_key),
        },
    }
    return payload


def main() -> None:
    configs = sorted(TRADES_DIR.glob("*.json"))
    if not configs:
        raise SystemExit(f"No trade configs in {TRADES_DIR}")

    index = {"generated_utc": utc_now(), "trades": []}
    for cfg_path in configs:
        payload = analyze_trade(cfg_path)
        out = ROOT / f"{payload['trade']['id']}_trade_data.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"  Entry {payload['entry']['slope_bp']:+.1f} bp → mark {payload['mark']['slope_bp']:+.1f} bp | "
            f"P&L {payload['pnl']['gbp']:+.1f} GBP → {out.name}"
        )
        index["trades"].append(
            {
                "id": payload["trade"]["id"],
                "label": payload["trade"]["label"],
                "position": payload["trade"]["position"],
                "direction": payload["trade"]["direction"],
                "spread_label": payload["trade"]["spread_label"],
                "entry_slope_bp": payload["entry"]["slope_bp"],
                "mark_slope_bp": payload["mark"]["slope_bp"],
                "pnl_gbp": payload["pnl"]["gbp"],
                "pnl_slope_bp": payload["pnl"]["slope_bp"],
                "entry_locked": payload["trade"]["entry_locked"],
                "detail_page": payload["trade"]["detail_page"],
                "data_file": out.name,
            }
        )

    index_path = ROOT / "trades_index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Wrote {index_path} ({len(index['trades'])} trades)")


if __name__ == "__main__":
    main()
