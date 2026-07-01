#!/usr/bin/env python3
"""Aggregate STIR book P&L, NAV, MTD/YTD returns, and rolling vol in USD."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BOOK_FILE = ROOT / "book.json"
ANN_FACTOR = np.sqrt(252)
ROLL_VOL = 30

from ice_sonia_margin import (
    load_margins,
    margin_note,
    margin_outright_long_gbp,
    margin_spread_gbp,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_book() -> dict:
    with BOOK_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def book_gbp_per_bp(book: dict) -> float:
    return float(book["conventions"]["bp_value_gbp_per_pair_per_contract"]) * int(book["contracts_per_leg"])


def book_face_gbp(book: dict) -> float:
    return float(book["face_value_gbp_per_contract"]) * int(book["contracts_per_leg"])


def format_position_size(
    trade_type: str,
    contracts_per_leg: int,
    face_per_leg: float,
    pnl_per_bp: float,
    currency: str = "GBP",
) -> str:
    """Human-readable book sizing for UI."""
    sym = "£" if currency == "GBP" else "$"
    face_m = face_per_leg / 1e6
    if trade_type == "outright":
        return f"{contracts_per_leg} lots · {sym}{face_m:.1f}M face · {sym}{pnl_per_bp:g}/bp"
    gross_m = 2 * face_per_leg / 1e6
    return (
        f"{contracts_per_leg} lots/leg · {sym}{face_m:.1f}M face/leg · "
        f"{sym}{gross_m:.1f}M gross · {sym}{pnl_per_bp:g}/bp"
    )


def trade_book_sizing(trade: dict, book: dict | None = None) -> dict:
    """Per-trade book economics (currency-aware)."""
    book = book or load_book()
    market = trade.get("market", "sonia_1m")
    currency = trade.get("currency", "GBP")
    trade_type = trade.get("type", "spread")

    if market == "sofr_3m":
        contracts = int(book.get("sofr_contracts_per_leg", book["contracts_per_leg"]))
        face_c = float(book.get("sofr_face_value_usd_per_contract", 1_000_000))
        per_bp_c = float(book.get("sofr_usd_per_bp_per_contract", 25))
        face = face_c * contracts
        pnl_per_bp = per_bp_c * contracts
        gross = face if trade_type == "outright" else 2 * face
        return {
            "market": market,
            "currency": "USD",
            "contracts_per_leg": contracts,
            "face_value_per_leg": face,
            "face_value_per_contract": face_c,
            "gross_notional": gross,
            "pnl_per_bp": pnl_per_bp,
            "position_size": format_position_size(trade_type, contracts, face, pnl_per_bp, "USD"),
        }

    contracts = int(book["contracts_per_leg"])
    face_c = float(book["face_value_gbp_per_contract"])
    per_bp_c = float(book["conventions"]["bp_value_gbp_per_pair_per_contract"])
    face = face_c * contracts
    pnl_per_bp = per_bp_c * contracts
    gross = face if trade_type == "outright" else 2 * face
    return {
        "market": market,
        "currency": "GBP",
        "contracts_per_leg": contracts,
        "face_value_per_leg": face,
        "face_value_per_contract": face_c,
        "gross_notional": gross,
        "pnl_per_bp": pnl_per_bp,
        "position_size": format_position_size(trade_type, contracts, face, pnl_per_bp, "GBP"),
    }


def book_size_for_trade(trade: dict, book: dict | None = None) -> dict:
    sizing = trade_book_sizing(trade, book)
    out = {
        "contracts_per_leg": sizing["contracts_per_leg"],
        "gross_notional_gbp": sizing["gross_notional"],
        "gbp_per_bp": sizing["pnl_per_bp"],
        "position_size": sizing["position_size"],
        "currency": sizing["currency"],
    }
    if sizing["currency"] == "USD":
        out["face_value_usd_per_leg"] = sizing["face_value_per_leg"]
        out["usd_per_bp"] = sizing["pnl_per_bp"]
        out["gross_notional_usd"] = sizing["gross_notional"]
    else:
        out["face_value_gbp_per_leg"] = sizing["face_value_per_leg"]
    return out


def _trade_margin_gbp(trade: dict, contracts_per_leg: int, margins: dict) -> tuple[float, str]:
    """ICE indicative IM for one open trade at book sizing (SONIA only)."""
    if trade.get("market") == "sofr_3m":
        return 0.0, "cme_not_configured"
    if trade.get("type") == "outright":
        expiry = trade.get("contract_label") or _expiry_from_symbol(trade.get("symbol"))
        if not expiry:
            raise KeyError(f"Outright trade {trade.get('id')} missing contract_label")
        return margin_outright_long_gbp(expiry, contracts_per_leg, margins)

  # spread: long_expiry / short_expiry from trade config fields
    long_exp = trade.get("long_expiry") or _expiry_from_symbol(trade.get("long_symbol"))
    short_exp = trade.get("short_expiry") or _expiry_from_symbol(trade.get("short_symbol"))
    if not long_exp or not short_exp:
        raise KeyError(f"Spread trade {trade.get('id')} missing expiry labels")
    return margin_spread_gbp(long_exp, short_exp, contracts_per_leg, margins)


def _expiry_from_symbol(symbol: str | None) -> str | None:
    if not symbol or len(symbol) < 5:
        return None
    month_code = symbol[2]
    year_suffix = symbol[3:]
    months = {
        "F": "Jan", "G": "Feb", "H": "Mar", "J": "Apr", "K": "May", "M": "Jun",
        "N": "Jul", "Q": "Aug", "U": "Sep", "V": "Oct", "X": "Nov", "Z": "Dec",
    }
    label = months.get(month_code)
    if not label:
        return None
    return f"{label}-{year_suffix}"


def scale_trade_payload(payload: dict, book: dict) -> dict:
    """Scale trade P&L to book contract sizing."""
    t = payload["trade"]
    sizing = trade_book_sizing(t, book)
    trade_per_bp = float(t.get("usd_per_bp") or t.get("gbp_per_bp") or 12.5)
    scale = sizing["pnl_per_bp"] / trade_per_bp if trade_per_bp else 1.0
    daily_key = "daily_pnl_usd" if sizing["currency"] == "USD" else "daily_pnl_gbp"

    out = json.loads(json.dumps(payload))
    out["trade"]["contracts_per_leg"] = sizing["contracts_per_leg"]
    out["trade"]["currency"] = sizing["currency"]
    if sizing["currency"] == "USD":
        out["trade"]["usd_per_bp"] = sizing["pnl_per_bp"]
        out["trade"]["face_value_usd_per_leg"] = sizing["face_value_per_leg"]
        if "usd" in out["pnl"]:
            out["pnl"]["usd"] = round(float(out["pnl"]["usd"]) * scale, 2)
    else:
        out["trade"]["gbp_per_bp"] = sizing["pnl_per_bp"]
        out["trade"]["face_value_gbp_per_leg"] = sizing["face_value_per_leg"]
        out["pnl"]["gbp"] = round(float(out["pnl"]["gbp"]) * scale, 2)
    out["pnl"]["slope_bp"] = float(out["pnl"]["slope_bp"])

    for row in out.get("trade_path", []):
        if daily_key in row:
            row[daily_key] = round(float(row[daily_key]) * scale, 2)
        if "cum_pnl_gbp" in row:
            row["cum_pnl_gbp"] = round(float(row["cum_pnl_gbp"]) * scale, 2)

    for row in out.get("regime_attribution", []):
        row["pnl_gbp"] = round(float(row["pnl_gbp"]) * scale, 2)

    if out.get("live_proxy") and out["live_proxy"].get("pnl_gbp") is not None:
        out["live_proxy"]["pnl_gbp"] = round(float(out["live_proxy"]["pnl_gbp"]) * scale, 2)

    return out


def trade_breakdown(payload: dict, book: dict, margins: dict) -> dict:
    """Per-trade economics with USD conversion and return contribution."""
    fx = float(book["gbp_usd"])
    nav0 = float(book["starting_nav_usd"])
    t = payload["trade"]
    sizing = trade_book_sizing(t, book)
    currency = sizing["currency"]
    pnl_per_bp = sizing["pnl_per_bp"]
    pnl_bp = float(payload["pnl"]["slope_bp"])

    if currency == "USD":
        pnl_native = float(payload["pnl"].get("usd", 0))
        pnl_usd = pnl_native
        pnl_gbp = None
    else:
        pnl_native = float(payload["pnl"]["gbp"])
        pnl_gbp = pnl_native
        pnl_usd = pnl_native * fx

    margin_gbp, margin_method = _trade_margin_gbp(
        t, int(sizing["contracts_per_leg"]), margins
    )
    margin_usd = margin_gbp * fx

    entry = payload.get("entry", {})
    mark = payload.get("mark", {})
    levels = payload.get("levels", {})

    row = {
        "id": t["id"],
        "label": t["label"],
        "type": t.get("type", "spread"),
        "market": t.get("market", "sonia_1m"),
        "currency": currency,
        "position": t["position"],
        "direction": t["direction"],
        "entry_date": entry.get("date"),
        "mark_date": mark.get("date"),
        "contracts_per_leg": sizing["contracts_per_leg"],
        "gross_notional": sizing["gross_notional"],
        "position_size": sizing["position_size"],
        "pnl_per_bp": pnl_per_bp,
        "margin_ice_gbp": round(margin_gbp, 0),
        "margin_ice_usd": round(margin_usd, 0),
        "margin_method": margin_method,
        "pnl_bp": round(pnl_bp, 2),
        "pnl_usd": round(pnl_usd, 2),
        "return_on_nav_pct": round(pnl_usd / nav0 * 100, 4),
        "return_on_margin_pct": round(pnl_usd / margin_usd * 100, 2) if margin_usd else None,
        "detail_page": t.get("detail_page"),
    }
    if currency == "GBP":
        row["pnl_gbp"] = round(pnl_gbp, 2)
        row["face_value_gbp_per_leg"] = sizing["face_value_per_leg"]
        row["gross_notional_gbp"] = sizing["gross_notional"]
    else:
        row["face_value_usd_per_leg"] = sizing["face_value_per_leg"]
        row["gross_notional_usd"] = sizing["gross_notional"]

    if t.get("type") == "outright":
        row.update({
            "entry_level": levels.get("entry_rate_pct", entry.get("rate_pct")),
            "mark_level": mark.get("rate_pct"),
            "level_unit": "implied %",
        })
        row["pnl_explanation"] = (
            f"Long rates: P&L = (entry − mark) × 100 = {pnl_bp:+.1f} bp · "
            f"× ${pnl_per_bp}/bp = ${pnl_native:+,.0f}"
            if currency == "USD"
            else
            f"Long rates: P&L = (entry − mark) × 100 = {pnl_bp:+.1f} bp · "
            f"× £{pnl_per_bp}/bp = £{pnl_native:+,.2f} · × {fx} FX = ${pnl_usd:+,.0f}"
        )
    else:
        row.update({
            "entry_level": levels.get("entry_slope_bp", entry.get("slope_bp")),
            "mark_level": mark.get("slope_bp"),
            "level_unit": "spread bp",
            "spread_label": t.get("spread_label"),
        })
        row["pnl_explanation"] = (
            f"{t['direction'].title()}: Δspread = {pnl_bp:+.1f} bp · "
            f"× ${pnl_per_bp}/bp = ${pnl_native:+,.0f}"
            if currency == "USD"
            else
            f"{t['direction'].title()}: Δspread = {pnl_bp:+.1f} bp · "
            f"× £{pnl_per_bp}/bp = £{pnl_native:+,.2f} · × {fx} FX = ${pnl_usd:+,.0f}"
        )

    return row


def aggregate_daily(trades: list[dict], book: dict) -> pd.DataFrame:
    """Sum scaled daily P&L across trades on a common calendar (USD-native)."""
    frames = []
    for payload in trades:
        tid = payload["trade"]["id"]
        path = payload.get("trade_path") or []
        if not path:
            continue
        currency = payload["trade"].get("currency", "GBP")
        daily_col = "daily_pnl_usd" if currency == "USD" else "daily_pnl_gbp"
        if daily_col not in (path[0] if path else {}):
            daily_col = "daily_pnl_gbp"
        df = pd.DataFrame(path)[["date", daily_col]].copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        fx = float(book["gbp_usd"])
        if currency == "USD":
            df["daily_pnl_usd"] = df[daily_col]
        else:
            df["daily_pnl_usd"] = df[daily_col] * fx
        df = df.rename(columns={"daily_pnl_usd": tid})
        frames.append(df[[tid]])

    if not frames:
        return pd.DataFrame()

    wide = pd.concat(frames, axis=1).fillna(0.0)
    wide["daily_pnl_usd"] = wide.sum(axis=1)
    fx = float(book["gbp_usd"])
    wide["daily_pnl_gbp"] = wide["daily_pnl_usd"] / fx
    return wide


def compute_returns(daily: pd.DataFrame, book: dict) -> dict:
    nav0 = float(book["starting_nav_usd"])
    fx = float(book["gbp_usd"])
    book_start = pd.Timestamp(book["book_start_date"])

    if daily.empty:
        return {
            "nav_usd": nav0,
            "total_pnl_usd": 0.0,
            "mtd_pnl_usd": 0.0,
            "ytd_pnl_usd": 0.0,
            "mtd_return_pct": 0.0,
            "ytd_return_pct": 0.0,
            "total_return_pct": 0.0,
            "vol_ann_30d_pct": None,
            "sharpe_ann_30d": None,
            "max_drawdown_usd": 0.0,
        }

    daily = daily.sort_index()
    cum_usd = daily["daily_pnl_usd"].cumsum()
    nav = nav0 + cum_usd
    latest_nav = float(nav.iloc[-1])
    total_pnl = latest_nav - nav0

    latest_dt = daily.index[-1]
    mtd_start = pd.Timestamp(latest_dt.year, latest_dt.month, 1)
    ytd_start = pd.Timestamp(latest_dt.year, 1, 1)

    nav_mtd_start = nav0 + daily.loc[(daily.index >= book_start) & (daily.index < mtd_start), "daily_pnl_usd"].sum()
    nav_ytd_start = nav0 + daily.loc[(daily.index >= book_start) & (daily.index < ytd_start), "daily_pnl_usd"].sum()

    mtd_pnl = float(daily.loc[daily.index >= mtd_start, "daily_pnl_usd"].sum())
    ytd_pnl = float(daily.loc[daily.index >= ytd_start, "daily_pnl_usd"].sum())

    mtd_ret = mtd_pnl / nav_mtd_start * 100 if nav_mtd_start else 0.0
    ytd_ret = ytd_pnl / nav_ytd_start * 100 if nav_ytd_start else 0.0
    total_ret = total_pnl / nav0 * 100

    # Daily returns on NAV
    nav_series = nav0 + daily["daily_pnl_usd"].cumsum().shift(fill_value=0)
    nav_prev = nav_series.shift(1).fillna(nav0)
    daily_ret = daily["daily_pnl_usd"] / nav_prev

    tail = daily_ret.tail(ROLL_VOL)
    vol_ann = float(tail.std(ddof=1) * ANN_FACTOR * 100) if len(tail) > 1 else None
    rf = float(book.get("risk_free_pct", 3.5)) / 100
    ann_ret = float(tail.mean() * 252) if len(tail) else None
    sharpe = (ann_ret - rf) / (vol_ann / 100) if vol_ann and vol_ann > 0 and ann_ret is not None else None

    dd = cum_usd - cum_usd.cummax()
    max_dd = float(dd.min()) if len(dd) else 0.0

    return {
        "nav_usd": round(latest_nav, 2),
        "total_pnl_usd": round(total_pnl, 2),
        "total_pnl_gbp": round(total_pnl / fx, 2),
        "mtd_pnl_usd": round(mtd_pnl, 2),
        "ytd_pnl_usd": round(ytd_pnl, 2),
        "mtd_return_pct": round(mtd_ret, 3),
        "ytd_return_pct": round(ytd_ret, 3),
        "total_return_pct": round(total_ret, 3),
        "vol_ann_30d_pct": round(vol_ann, 2) if vol_ann is not None else None,
        "sharpe_ann_30d": round(sharpe, 2) if sharpe is not None else None,
        "max_drawdown_usd": round(max_dd, 2),
        "as_of": str(latest_dt.date()),
    }


def build_book_summary(trade_payloads: list[dict]) -> dict:
    book = load_book()
    fx = float(book["gbp_usd"])
    gbp = book_gbp_per_bp(book)
    face = book_face_gbp(book)
    margins = load_margins()

    scaled = [scale_trade_payload(p, book) for p in trade_payloads]
    breakdown = [trade_breakdown(p, book, margins) for p in scaled]
    breakdown.sort(key=lambda x: x.get("entry_date") or "")
    daily = aggregate_daily(scaled, book)
    metrics = compute_returns(daily, book)

    total_margin_gbp = sum(b["margin_ice_gbp"] for b in breakdown)
    total_margin_usd = sum(b["margin_ice_usd"] for b in breakdown)
    conv = dict(book["conventions"])
    conv["margin_note"] = margin_note(margins)

    daily_rows = []
    if not daily.empty:
        cum = 0.0
        nav0 = float(book["starting_nav_usd"])
        for dt, row in daily.iterrows():
            cum += float(row["daily_pnl_usd"])
            daily_rows.append({
                "date": str(dt.date()),
                "daily_pnl_gbp": round(float(row["daily_pnl_gbp"]), 2),
                "daily_pnl_usd": round(float(row["daily_pnl_usd"]), 2),
                "cum_pnl_usd": round(cum, 2),
                "nav_usd": round(nav0 + cum, 2),
                **{c: round(float(row[c]), 2) for c in daily.columns if c not in ("daily_pnl_gbp", "daily_pnl_usd")},
            })

    return {
        "generated_utc": utc_now(),
        "book": {
            "id": book["book_id"],
            "label": book["label"],
            "starting_nav_usd": book["starting_nav_usd"],
            "book_start_date": book["book_start_date"],
            "gbp_usd": fx,
            "gbp_usd_as_of": book.get("gbp_usd_as_of"),
            "contracts_per_leg": book["contracts_per_leg"],
            "face_value_gbp_per_leg": face,
            "gbp_per_bp": gbp,
            "conventions": conv,
            "margin_source": margins["source"],
            "total_margin_ice_gbp": round(total_margin_gbp, 0),
            "total_margin_ice_usd": round(total_margin_usd, 0),
            "margin_utilisation_pct": round(total_margin_usd / metrics["nav_usd"] * 100, 1),
        },
        "metrics": metrics,
        "trades": breakdown,
        "daily": daily_rows,
        "pnl_bridge": {
            "starting_nav_usd": book["starting_nav_usd"],
            "total_pnl_usd": metrics["total_pnl_usd"],
            "ending_nav_usd": metrics["nav_usd"],
            "fx_gbp_usd": fx,
            "note": (
                "Mixed STIR book: ICE 1M SONIA legs in GBP (× FX → USD); "
                "CME 3M SOFR legs in USD-native. "
                f"SONIA book clip ≈ {book['contracts_per_leg']} lots/leg · "
                f"SOFR book clip ≈ {book.get('sofr_contracts_per_leg', book['contracts_per_leg'])} lots/leg. "
                f"Returns vs ${book['starting_nav_usd']:,.0f} starting NAV."
            ),
        },
    }


def main() -> None:
    from analyze_spread_trades import TRADES_DIR, analyze_trade, load_cfg

    payloads = []
    for cfg_path in sorted(TRADES_DIR.glob("*.json")):
        payloads.append(analyze_trade(cfg_path))

    summary = build_book_summary(payloads)
    out = ROOT / "book_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    m = summary["metrics"]
    print(
        f"  NAV ${m['nav_usd']:,.0f} · MTD {m['mtd_return_pct']:+.2f}% · "
        f"YTD {m['ytd_return_pct']:+.2f}% · vol30 {m['vol_ann_30d_pct']}%"
    )


if __name__ == "__main__":
    main()
