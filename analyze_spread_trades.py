#!/usr/bin/env python3
"""Track SONIA outright legs and calendar-spread trades from Barchart / sonia_1m_data."""
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
SOFR_3M = ROOT / "sofr_3m_data.json"
STIR_3M = ROOT / "stir_curves_data.json"


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


def pnl_outright_bp(entry_rate: float, mark_rate: float, direction: str) -> float:
    """Long rates: profit when implied rate falls."""
    delta = (entry_rate - mark_rate) * 100.0
    if direction == "short":
        return -delta
    return delta


def snap_from_sonia(symbol: str) -> dict | None:
    if not SONIA_1M.exists():
        return None
    with SONIA_1M.open(encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("contracts", []):
        if c.get("symbol") == symbol:
            return {
                "symbol": symbol,
                "date": c.get("latest_date", ""),
                "price": round(float(c["price"]), 4),
                "implied_rate_pct": round(float(c["implied_rate_pct"]), 4),
            }
    return None


def snap_from_sofr(symbol: str) -> dict | None:
    if not SOFR_3M.exists():
        return None
    with SOFR_3M.open(encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("contracts", []):
        if c.get("symbol") == symbol:
            return {
                "symbol": symbol,
                "date": c.get("latest_date", ""),
                "price": round(float(c["price"]), 4),
                "implied_rate_pct": round(float(c["implied_rate_pct"]), 4),
            }
    return None


def series_from_sofr(keys: list[str]) -> pd.DataFrame | None:
    if not SOFR_3M.exists():
        return None
    with SOFR_3M.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("timeseries", {}).get("rows", [])
    if not rows:
        return None
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    cols = [k for k in keys if k in df.columns]
    if not cols:
        return None
    return df[cols].dropna(how="all").astype(float).sort_index()


def fetch_leg(symbol: str) -> tuple[pd.DataFrame, dict]:
    snap_fallback = snap_from_sofr if symbol.startswith("SQ") else snap_from_sonia
    try:
        df = fetch_barchart_eod(symbol)
        rates = price_to_rate(df["price"])
        latest = df.iloc[-1]
        snap = {
            "symbol": symbol,
            "date": str(df.index[-1].date()),
            "price": round(float(latest["price"]), 4),
            "implied_rate_pct": round(float(rates.iloc[-1]), 4),
        }
        return df, snap
    except Exception as exc:
        label = "sofr_3m_data" if symbol.startswith("SQ") else "sonia_1m_data"
        print(f"  ::warning::{symbol} Barchart fetch failed ({exc}); using {label} snapshot")
        snap = snap_fallback(symbol)
        if snap is None:
            raise
        return pd.DataFrame(), snap


def series_3m_sonia() -> pd.DataFrame | None:
    if not STIR_3M.exists():
        return None
    with STIR_3M.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("timeseries", {}).get("sonia_3m", {}).get("rows", [])
    if not rows:
        return None
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df.astype(float).sort_index()


def rate_on_or_before(series: pd.Series, dt: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    sub = series.loc[:dt].dropna()
    if sub.empty:
        return None
    ts = sub.index[-1]
    return ts, float(sub.iloc[-1])


def build_live_proxy(
    cfg: dict,
    entry_date: pd.Timestamp,
    entry_1m: dict[str, float],
    q_long_key: str,
    q_short_key: str | None,
    direction: str,
    gbp: float,
    trade_type: str,
) -> dict | None:
    """Indicative intraday mark via 3M SONIA Δ applied to 1M entry (same delivery months)."""
    if not cfg.get("live_proxy", {}).get("enabled", True):
        return None
    s3 = series_3m_sonia()
    if s3 is None:
        return None

    latest_dt = s3.index[-1]
    legs: dict[str, dict] = {}
    entry_3m_ref: pd.Timestamp | None = None
    for key in entry_1m:
        if key not in s3.columns:
            continue
        e = rate_on_or_before(s3[key], entry_date)
        if e is None:
            continue
        entry_3m_dt, entry_3m = e
        entry_3m_ref = entry_3m_dt
        latest_3m = float(s3[key].iloc[-1])
        proxy = float(entry_1m[key]) + (latest_3m - entry_3m)
        legs[key] = {
            "entry_3m_rate_pct": round(entry_3m, 4),
            "latest_3m_rate_pct": round(latest_3m, 4),
            "proxy_1m_rate_pct": round(proxy, 4),
            "delta_3m_bp": round((latest_3m - entry_3m) * 100, 2),
        }

    if not legs:
        return None

    out: dict = {
        "source": "3M SONIA (J8*) · change applied to 1M entry",
        "note": "Indicative only. Official P&L uses 1M EOD (JU*). 3M levels differ from 1M; leg deltas ~0.99 corr (Jun-27).",
        "entry_3m_date": str(entry_3m_ref.date()) if entry_3m_ref is not None else str(entry_date.date()),
        "latest_3m_date": str(latest_dt.date()),
        "legs": legs,
    }

    if trade_type == "outright":
        key = next(iter(entry_1m))
        proxy_rate = legs[key]["proxy_1m_rate_pct"]
        pnl_bp = pnl_outright_bp(float(entry_1m[key]), proxy_rate, direction)
        out["mark_rate_pct"] = proxy_rate
        out["pnl_bp"] = round(pnl_bp, 2)
        out["pnl_gbp"] = round(pnl_bp * gbp, 2)
    else:
        if q_long_key not in legs or (q_short_key and q_short_key not in legs):
            return out
        entry_slope = quoted_slope_bp(entry_1m, q_long_key, q_short_key or q_long_key)
        proxy_rates = {k: legs[k]["proxy_1m_rate_pct"] for k in legs}
        proxy_slope = quoted_slope_bp(proxy_rates, q_long_key, q_short_key or q_long_key)
        pnl_bp = pnl_slope_bp(entry_slope, proxy_slope, direction)
        out["mark_slope_bp"] = round(proxy_slope, 2)
        out["pnl_bp"] = round(pnl_bp, 2)
        out["pnl_gbp"] = round(pnl_bp * gbp, 2)

    return out


def series_from_sonia(keys: list[str]) -> pd.DataFrame | None:
    if not SONIA_1M.exists():
        return None
    with SONIA_1M.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data["timeseries"]["rows"]
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    cols = [k for k in keys if k in df.columns]
    if not cols:
        return None
    return df[cols].dropna(how="all").astype(float).sort_index()


def ensure_spread_entry(
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
    cfg["entry"] = {
        "date": entry_date,
        "label": cfg.get("entry_label", entry_date),
        "short": short_snap,
        "long": long_snap,
        "slope_bp": round(slope, 2),
        "captured_utc": utc_now(),
        "source": "barchart_live",
    }
    if short_snap["date"] == entry_date and long_snap["date"] == entry_date:
        cfg["entry"]["source"] = "barchart_eod"
        cfg["entry_locked"] = True
    save_cfg(cfg_path, cfg)
    return cfg


def leg_vs_fed(leg: dict, policy_rate: float | None) -> dict:
    out = dict(leg)
    if policy_rate is not None and leg.get("implied_rate_pct") is not None:
        out["vs_fed_bp"] = round((float(leg["implied_rate_pct"]) - policy_rate) * 100, 1)
    return out


def build_spread_path(
    tail: pd.DataFrame,
    entry_slope: float,
    pnl_per_bp: float,
    direction: str,
    q_long_key: str,
    q_short_key: str,
    daily_pnl_key: str = "daily_pnl_gbp",
) -> list[dict]:
    path = []
    prev_cum = 0.0
    for i, (dt, row) in enumerate(tail.iterrows()):
        leg_rates = {k: float(row[k]) for k in row.index}
        q_slope = quoted_slope_bp(leg_rates, q_long_key, q_short_key)
        dslope = pnl_slope_bp(entry_slope, q_slope, direction)
        cum = dslope * pnl_per_bp
        daily = cum if i == 0 else cum - prev_cum
        prev_cum = cum
        row = {
            "date": str(dt.date()),
            "quoted_long_rate": round(leg_rates[q_long_key], 4),
            "quoted_short_rate": round(leg_rates[q_short_key], 4),
            "slope_bp": round(q_slope, 2),
            "dslope_bp": round(dslope, 2),
            "cum_pnl_gbp": round(cum, 2),
            daily_pnl_key: round(daily, 2),
        }
        if daily_pnl_key == "daily_pnl_usd":
            row["cum_pnl_usd"] = round(cum, 2)
        elif daily_pnl_key == "daily_pnl_eur":
            row["cum_pnl_eur"] = round(cum, 2)
        path.append(row)
    return path


def build_outright_path(
    tail: pd.Series,
    entry_rate: float,
    gbp_per_bp: float,
    direction: str,
) -> list[dict]:
    path = []
    prev_cum = 0.0
    for i, (dt, rate) in enumerate(tail.items()):
        pnl_bp = pnl_outright_bp(entry_rate, float(rate), direction)
        cum = pnl_bp * gbp_per_bp
        daily = cum if i == 0 else cum - prev_cum
        prev_cum = cum
        path.append(
            {
                "date": str(dt.date()),
                "rate_pct": round(float(rate), 4),
                "pnl_bp": round(pnl_bp, 2),
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


def analyze_outright(cfg_path: Path) -> dict:
    cfg = load_cfg(cfg_path)
    gbp = float(cfg["gbp_per_bp"])
    direction = cfg.get("direction", "long")
    symbol = cfg["symbol"]
    key = cfg["contract_key"]
    levels = cfg.get("levels") or {}

    print(f"[{cfg['trade_id']}] Fetching {symbol}…")
    df, snap = fetch_leg(symbol)
    entry = cfg.get("entry") or {}
    entry_rate = float(levels.get("entry_rate_pct", entry.get("rate_pct", snap["implied_rate_pct"])))
    entry_date = pd.Timestamp(cfg["entry_date"])

    hist = series_from_sonia([key])
    if hist is None:
        hist = pd.DataFrame(index=pd.DatetimeIndex([]))
    if not df.empty and "price" in df.columns:
        for dt, px in df["price"].items():
            hist.loc[pd.Timestamp(dt).normalize(), key] = float(price_to_rate(pd.Series([px])).iloc[0])
    hist = hist.sort_index()

    tail = hist.loc[hist.index >= entry_date, key].dropna()
    if tail.empty:
        tail = pd.Series([entry_rate], index=[entry_date])

    mark_rate = float(tail.iloc[-1])
    pnl_bp = pnl_outright_bp(entry_rate, mark_rate, direction)
    pnl_gbp = pnl_bp * gbp

    path = build_outright_path(tail, entry_rate, gbp, direction)
    stop = levels.get("stop_rate_pct")
    tp = levels.get("take_profit_rate_pct")
    live_proxy = build_live_proxy(
        cfg, entry_date, {key: entry_rate}, key, None, direction, gbp, "outright"
    )

    return {
        "generated_utc": utc_now(),
        "trade": {
            "id": cfg["trade_id"],
            "type": "outright",
            "label": cfg["label"],
            "position": cfg["position"],
            "direction": direction,
            "spread_label": cfg.get("contract_label", symbol),
            "contract_label": cfg.get("contract_label"),
            "symbol": symbol,
            "entry_locked": cfg.get("entry_locked", False),
            "gbp_per_bp": gbp,
            "detail_page": cfg.get("detail_page", f"trade_{cfg['trade_id']}.html"),
        },
        "levels": levels,
        "bank_rate_pct": BANK_RATE_PCT,
        "bank_rate_as_of": BANK_RATE_AS_OF,
        "entry": {
            "date": cfg["entry_date"],
            "label": cfg.get("entry_label", cfg["entry_date"]),
            "rate_pct": entry_rate,
            "leg": entry.get("leg", snap),
            "slope_bp": None,
        },
        "mark": {
            "date": str(tail.index[-1].date()),
            "rate_pct": round(mark_rate, 4),
            "leg": snap,
            "slope_bp": None,
            "updated_utc": utc_now(),
        },
        "pnl": {
            "slope_bp": round(pnl_bp, 2),
            "gbp": round(pnl_gbp, 2),
            "to_stop_bp": round((float(stop) - mark_rate) * 100, 2) if stop is not None else None,
            "to_tp_bp": round((float(tp) - mark_rate) * 100, 2) if tp is not None else None,
        },
        "trade_path": path,
        "regime_attribution": [],
        "market_note_url": cfg.get("market_note_url", ""),
        "leg_labels": {"quoted_long": cfg.get("contract_label", symbol), "quoted_short": ""},
        "live_proxy": live_proxy,
    }


def analyze_spread(cfg_path: Path) -> dict:
    cfg = load_cfg(cfg_path)
    market = cfg.get("market", "sonia_1m")
    currency = cfg.get("currency", "GBP")
    direction = cfg.get("direction", "steepener")
    long_sym = cfg["long_symbol"]
    short_sym = cfg["short_symbol"]
    long_key = cfg["long_key"]
    short_key = cfg["short_key"]
    q_long_key, q_short_key, spread_label = quoted_keys(cfg)
    keys = list({long_key, short_key, q_long_key, q_short_key})
    levels = cfg.get("levels") or {}

    if market == "sofr_3m":
        pnl_per_bp = float(cfg["usd_per_bp"])
        daily_pnl_key = "daily_pnl_usd"
        series_fn = series_from_sofr
        policy_rate = None
        policy_as_of = None
        if SOFR_3M.exists():
            with SOFR_3M.open(encoding="utf-8") as f:
                sofr_meta = json.load(f)
            policy_rate = sofr_meta.get("fed_funds_pct")
            policy_as_of = sofr_meta.get("fed_funds_as_of")
    elif market == "estr_1m":
        pnl_per_bp = float(cfg["eur_per_bp"])
        daily_pnl_key = "daily_pnl_eur"
        series_fn = lambda _keys: None
        policy_rate = float(cfg.get("ecb_deposit_pct", 2.0))
        policy_as_of = cfg.get("ecb_deposit_as_of")
    else:
        pnl_per_bp = float(cfg["gbp_per_bp"])
        daily_pnl_key = "daily_pnl_gbp"
        series_fn = series_from_sonia
        policy_rate = BANK_RATE_PCT
        policy_as_of = BANK_RATE_AS_OF

    print(f"[{cfg['trade_id']}] Fetching {long_sym} / {short_sym}…")
    short_df, short_snap = fetch_leg(short_sym)
    long_df, long_snap = fetch_leg(long_sym)
    leg_rates = {short_key: short_snap["implied_rate_pct"], long_key: long_snap["implied_rate_pct"]}
    cfg = ensure_spread_entry(cfg_path, cfg, leg_rates, short_snap, long_snap, q_long_key, q_short_key)
    entry = cfg["entry"]
    entry_date = pd.Timestamp(entry["date"])
    entry_slope = float(levels.get("entry_slope_bp", entry["slope_bp"]))

    hist = series_fn(keys)
    if hist is None:
        hist = pd.DataFrame(index=pd.DatetimeIndex([]))

    for df, key in [(short_df, short_key), (long_df, long_key)]:
        if df.empty or "price" not in df.columns:
            continue
        for dt, px in df["price"].items():
            hist.loc[pd.Timestamp(dt).normalize(), key] = float(price_to_rate(pd.Series([px])).iloc[0])
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
    pnl_native = pnl_slope * pnl_per_bp

    qs = cfg.get("quoted_spread") or {}
    path = build_spread_path(
        tail, entry_slope, pnl_per_bp, direction, q_long_key, q_short_key, daily_pnl_key
    )
    regimes = regime_stats(tail, direction, pnl_per_bp, q_long_key, q_short_key)

    stop = levels.get("stop_slope_bp")
    tp = levels.get("take_profit_slope_bp")
    leg_by_key = {cfg["long_key"]: entry["long"], cfg["short_key"]: entry["short"]}
    entry_1m_rates = {
        q_long_key: float(leg_by_key[q_long_key]["implied_rate_pct"]),
        q_short_key: float(leg_by_key[q_short_key]["implied_rate_pct"]),
    }
    live_proxy = None
    if market == "sonia_1m":
        live_proxy = build_live_proxy(
            cfg, entry_date, entry_1m_rates, q_long_key, q_short_key, direction, pnl_per_bp, "spread"
        )

    trade_row = {
        "id": cfg["trade_id"],
        "type": "spread",
        "label": cfg["label"],
        "position": cfg["position"],
        "direction": direction,
        "spread_label": spread_label,
        "long_symbol": cfg.get("long_symbol"),
        "short_symbol": cfg.get("short_symbol"),
        "market": market,
        "currency": currency,
        "entry_locked": cfg.get("entry_locked", False),
        "detail_page": cfg.get("detail_page", f"trade_{cfg['trade_id']}.html"),
    }
    if market == "sofr_3m":
        trade_row["usd_per_bp"] = pnl_per_bp
        trade_row["face_value_usd"] = float(cfg.get("face_value_usd", 1_000_000))
    elif market == "estr_1m":
        trade_row["eur_per_bp"] = pnl_per_bp
        trade_row["face_value_eur"] = float(cfg.get("face_value_eur", 250_000))
    else:
        trade_row["gbp_per_bp"] = pnl_per_bp

    pnl_row = {
        "slope_bp": round(pnl_slope, 2),
        "quoted_long_leg_bp": round((mark_leg_rates[q_long_key] - leg_rates[q_long_key]) * 100, 2),
        "quoted_short_leg_bp": round((mark_leg_rates[q_short_key] - leg_rates[q_short_key]) * 100, 2),
        "to_stop_bp": round(float(stop) - mark_slope, 2) if stop is not None else None,
        "to_tp_bp": round(float(tp) - mark_slope, 2) if tp is not None else None,
    }
    if currency == "USD":
        pnl_row["usd"] = round(pnl_native, 2)
        pnl_row["gbp"] = 0.0
    elif currency == "EUR":
        pnl_row["eur"] = round(pnl_native, 2)
        pnl_row["gbp"] = 0.0
    else:
        pnl_row["gbp"] = round(pnl_native, 2)

    entry_out = dict(entry)
    if market == "sofr_3m" and policy_rate is not None:
        entry_out["fed_funds_mid_pct"] = policy_rate
        entry_out["fed_funds_as_of"] = policy_as_of
        if entry.get("long"):
            entry_out["long"] = leg_vs_fed(entry["long"], policy_rate)
        if entry.get("short"):
            entry_out["short"] = leg_vs_fed(entry["short"], policy_rate)
    elif market == "estr_1m" and policy_rate is not None:
        entry_out["ecb_deposit_pct"] = policy_rate
        entry_out["ecb_deposit_as_of"] = policy_as_of
        if entry.get("long"):
            entry_out["long"] = leg_vs_fed(entry["long"], policy_rate)
        if entry.get("short"):
            entry_out["short"] = leg_vs_fed(entry["short"], policy_rate)

    return {
        "generated_utc": utc_now(),
        "trade": trade_row,
        "levels": levels,
        "bank_rate_pct": policy_rate,
        "bank_rate_as_of": policy_as_of,
        "entry": entry_out,
        "mark": {
            "date": str(tail.index[-1].date()),
            "short": leg_vs_fed(short_snap, policy_rate),
            "long": leg_vs_fed(long_snap, policy_rate),
            "slope_bp": round(mark_slope, 2),
            "updated_utc": utc_now(),
        },
        "pnl": pnl_row,
        "trade_path": path,
        "regime_attribution": regimes,
        "market_note_url": cfg.get("market_note_url", ""),
        "leg_labels": {
            "quoted_long": qs.get("long_label", q_long_key),
            "quoted_short": qs.get("short_label", q_short_key),
        },
        "live_proxy": live_proxy,
    }


def analyze_trade(cfg_path: Path) -> dict:
    cfg = load_cfg(cfg_path)
    if cfg.get("trade_type") == "outright":
        return analyze_outright(cfg_path)
    return analyze_spread(cfg_path)


def index_row(payload: dict) -> dict:
    t = payload["trade"]
    levels = payload.get("levels") or {}
    pnl_bp = float(payload["pnl"]["slope_bp"])
    currency = t.get("currency", "GBP")
    if currency == "USD":
        pnl_display = float(payload["pnl"].get("usd", 0))
        trade_per_bp = float(t.get("usd_per_bp", 25))
    elif currency == "EUR":
        pnl_display = float(payload["pnl"].get("eur", 0))
        trade_per_bp = float(t.get("eur_per_bp", 25))
    else:
        pnl_display = float(payload["pnl"]["gbp"])
        trade_per_bp = float(t.get("gbp_per_bp", 12.5))
    book_size = None
    if (ROOT / "book.json").is_file():
        from analyze_book import book_size_for_trade, load_book, trade_book_sizing

        book = load_book()
        book_size = book_size_for_trade(t, book)
        sizing = trade_book_sizing(t, book)
        scale = sizing["pnl_per_bp"] / trade_per_bp if trade_per_bp else 1.0
        pnl_display = round(pnl_display * scale, 2)
    row = {
        "id": t["id"],
        "type": t.get("type", "spread"),
        "label": t["label"],
        "position": t["position"],
        "direction": t["direction"],
        "spread_label": t["spread_label"],
        "market": t.get("market", "sonia_1m"),
        "currency": currency,
        "entry_locked": t["entry_locked"],
        "detail_page": t["detail_page"],
        "data_file": f"{t['id']}_trade_data.json",
        "pnl_gbp": pnl_display if currency == "GBP" else None,
        "pnl_usd": pnl_display if currency == "USD" else None,
        "pnl_eur": pnl_display if currency == "EUR" else None,
        "pnl_slope_bp": pnl_bp,
    }
    if book_size:
        row.update({
            "contracts_per_leg": book_size["contracts_per_leg"],
            "gross_notional_gbp": book_size["gross_notional_gbp"],
            "gbp_per_bp": book_size["gbp_per_bp"],
            "position_size": book_size["position_size"],
        })
    if t.get("type") == "outright":
        row["entry_rate_pct"] = levels.get("entry_rate_pct", payload["entry"].get("rate_pct"))
        row["mark_rate_pct"] = payload["mark"].get("rate_pct")
        row["stop_rate_pct"] = levels.get("stop_rate_pct")
        row["take_profit_rate_pct"] = levels.get("take_profit_rate_pct")
        row["entry_slope_bp"] = None
        row["mark_slope_bp"] = None
    else:
        row["entry_slope_bp"] = levels.get("entry_slope_bp", payload["entry"].get("slope_bp"))
        row["mark_slope_bp"] = payload["mark"].get("slope_bp")
        row["stop_slope_bp"] = levels.get("stop_slope_bp")
        row["take_profit_slope_bp"] = levels.get("take_profit_slope_bp")
        row["entry_rate_pct"] = None
        row["mark_rate_pct"] = None
    return row


def main() -> None:
    configs = sorted(TRADES_DIR.glob("*.json"))
    if not configs:
        raise SystemExit(f"No trade configs in {TRADES_DIR}")

    index = {"generated_utc": utc_now(), "trades": []}
    payloads: list[dict] = []
    for cfg_path in configs:
        payload = analyze_trade(cfg_path)
        if (ROOT / "book.json").is_file():
            from analyze_book import book_size_for_trade

            payload["book_size"] = book_size_for_trade(payload["trade"])
        payloads.append(payload)
        out = ROOT / f"{payload['trade']['id']}_trade_data.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        t = payload["trade"]
        if t.get("type") == "outright":
            print(
                f"  Entry {payload['entry']['rate_pct']:.3f}% → mark {payload['mark']['rate_pct']:.3f}% | "
                f"P&L {payload['pnl']['gbp']:+.1f} GBP → {out.name}"
            )
        else:
            pnl = payload["pnl"]
            if payload["trade"].get("currency") == "USD":
                pnl_txt = f"{pnl.get('usd', 0):+.1f} USD"
            elif payload["trade"].get("currency") == "EUR":
                pnl_txt = f"{pnl.get('eur', 0):+.1f} EUR"
            else:
                pnl_txt = f"{pnl.get('gbp', 0):+.1f} GBP"
            print(
                f"  Entry {payload['entry']['slope_bp']:+.1f} bp → mark {payload['mark']['slope_bp']:+.1f} bp | "
                f"P&L {pnl_txt} → {out.name}"
            )
        index["trades"].append(index_row(payload))

    index_path = ROOT / "trades_index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Wrote {index_path} ({len(index['trades'])} trades)")

    if (ROOT / "book.json").is_file():
        from analyze_book import build_book_summary

        summary = build_book_summary(payloads)
        (ROOT / "book_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        m = summary["metrics"]
        print(
            f"  Book NAV ${m['nav_usd']:,.0f} · MTD {m['mtd_return_pct']:+.2f}% · "
            f"YTD {m['ytd_return_pct']:+.2f}% · 30d vol {m['vol_ann_30d_pct']}%"
        )

    from build_trade_tracker import sync_trade_json_to_docs

    sync_trade_json_to_docs()


if __name__ == "__main__":
    main()
