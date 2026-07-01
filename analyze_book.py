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


def _trade_margin_gbp(trade: dict, contracts_per_leg: int, margins: dict) -> tuple[float, str]:
    """ICE indicative IM for one open trade at book sizing."""
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
    book_gbp = book_gbp_per_bp(book)
    trade_gbp = float(payload["trade"].get("gbp_per_bp", 12.5))
    scale = book_gbp / trade_gbp if trade_gbp else 1.0

    out = json.loads(json.dumps(payload))
    gbp = book_gbp_per_bp(book)
    book_contracts = int(book["contracts_per_leg"])
    out["trade"]["gbp_per_bp"] = gbp
    out["trade"]["contracts_per_leg"] = book_contracts
    out["trade"]["face_value_gbp"] = book_face_gbp(book)
    out["pnl"]["gbp"] = round(float(out["pnl"]["gbp"]) * scale, 2)
    out["pnl"]["slope_bp"] = float(out["pnl"]["slope_bp"])

    for row in out.get("trade_path", []):
        row["daily_pnl_gbp"] = round(float(row["daily_pnl_gbp"]) * scale, 2)
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
    gbp = float(payload["trade"]["gbp_per_bp"])
    pnl_gbp = float(payload["pnl"]["gbp"])
    pnl_bp = float(payload["pnl"]["slope_bp"])
    pnl_usd = pnl_gbp * fx
    t = payload["trade"]
    face = book_face_gbp(book)
    gross_gbp = 2 * face if t.get("type") != "outright" else face
    margin_gbp, margin_method = _trade_margin_gbp(
        t, int(book["contracts_per_leg"]), margins
    )
    margin_usd = margin_gbp * fx

    entry = payload.get("entry", {})
    mark = payload.get("mark", {})
    levels = payload.get("levels", {})

    row = {
        "id": t["id"],
        "label": t["label"],
        "type": t.get("type", "spread"),
        "position": t["position"],
        "direction": t["direction"],
        "entry_date": entry.get("date"),
        "mark_date": mark.get("date"),
        "contracts_per_leg": int(book["contracts_per_leg"]),
        "face_value_gbp_per_leg": face,
        "gross_notional_gbp": gross_gbp,
        "margin_ice_gbp": round(margin_gbp, 0),
        "margin_ice_usd": round(margin_usd, 0),
        "margin_method": margin_method,
        "gbp_per_bp": gbp,
        "pnl_bp": round(pnl_bp, 2),
        "pnl_gbp": round(pnl_gbp, 2),
        "pnl_usd": round(pnl_usd, 2),
        "return_on_nav_pct": round(pnl_usd / nav0 * 100, 4),
        "return_on_margin_pct": round(pnl_usd / margin_usd * 100, 2) if margin_usd else None,
        "detail_page": t.get("detail_page"),
    }

    if t.get("type") == "outright":
        row.update({
            "entry_level": levels.get("entry_rate_pct", entry.get("rate_pct")),
            "mark_level": mark.get("rate_pct"),
            "level_unit": "implied %",
        })
        row["pnl_explanation"] = (
            f"Long rates: P&L = (entry − mark) × 100 = {pnl_bp:+.1f} bp · "
            f"× £{gbp}/bp = {pnl_gbp:+.2f} GBP · × {fx} FX = ${pnl_usd:+,.0f}"
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
            f"× £{gbp}/bp = {pnl_gbp:+.2f} GBP · × {fx} FX = ${pnl_usd:+,.0f}"
        )

    return row


def aggregate_daily(trades: list[dict], book: dict) -> pd.DataFrame:
    """Sum scaled daily P&L across trades on a common calendar."""
    frames = []
    for payload in trades:
        tid = payload["trade"]["id"]
        path = payload.get("trade_path") or []
        if not path:
            continue
        df = pd.DataFrame(path)[["date", "daily_pnl_gbp"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        # First session daily_pnl is cum from entry; keep as-is from build_spread_path
        df = df.rename(columns={"daily_pnl_gbp": tid})
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    wide = pd.concat(frames, axis=1).fillna(0.0)
    wide["daily_pnl_gbp"] = wide.sum(axis=1)
    fx = float(book["gbp_usd"])
    wide["daily_pnl_usd"] = wide["daily_pnl_gbp"] * fx
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
                f"Each 1bp on a 1:1 ICE 1M SONIA calendar spread with "
                f"{book['contracts_per_leg']} contracts/leg (£{face:,.0f} face) ≈ "
                f"£{gbp}/bp ≈ ${gbp * fx:,.0f}/bp. "
                f"P&L GBP × {fx} → USD. Returns vs ${book['starting_nav_usd']:,.0f} starting NAV."
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
