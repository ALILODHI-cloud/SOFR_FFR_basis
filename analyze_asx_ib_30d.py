"""
Fetch ASX 30-day Interbank Cash Rate futures curve from Barchart EOD (SFE IQ*).

Writes asx_ib_30d_data.json for build_asx_ib_30d_dashboard.py.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent

from analyze_sonia import UA, price_to_rate
from analyze_stir_curves import fetch_barchart_batch

CHAIN_URL = "https://www.barchart.com/futures/quotes/IQ*0/futures-prices"
PREFIX = "IQ"
RBA_CASH_RATE_URL = "https://www.rba.gov.au/statistics/cash-rate/"

MONTH_CODE = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}
MONTH_LABEL = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# RBA Monetary Policy Board — decision on second day (use decision date).
RBA_BOARD_MEETINGS = [
    {"date": "2026-02-03", "label": "Feb RBA"},
    {"date": "2026-03-17", "label": "Mar RBA"},
    {"date": "2026-05-05", "label": "May RBA"},
    {"date": "2026-06-16", "label": "Jun RBA"},
    {"date": "2026-08-11", "label": "Aug RBA"},
    {"date": "2026-09-29", "label": "Sep RBA"},
    {"date": "2026-11-03", "label": "Nov RBA"},
    {"date": "2026-12-08", "label": "Dec RBA"},
    {"date": "2027-02-09", "label": "Feb RBA"},
    {"date": "2027-03-23", "label": "Mar RBA"},
    {"date": "2027-05-04", "label": "May RBA"},
    {"date": "2027-06-22", "label": "Jun RBA"},
    {"date": "2027-08-10", "label": "Aug RBA"},
    {"date": "2027-09-28", "label": "Sep RBA"},
    {"date": "2027-11-02", "label": "Nov RBA"},
    {"date": "2027-12-14", "label": "Dec RBA"},
]

RBA_PRICING_NOTE = (
    "Approximate meeting path from ASX 30-day cash rate futures (not RBA-dated OIS). "
    "Each meeting maps to the contract month after the decision as a post-meeting rate proxy. "
    "Probabilities assume 25bp steps (FedWatch-style). Monthly IB contracts average cash "
    "over the calendar month — use OIS for precise per-meeting pricing."
)

CASH_RATE_FALLBACK_PCT = 4.35
CASH_RATE_FALLBACK_AS_OF = "2026-05-05"
# YTD window + buffer for Barchart EOD fetch.
BARCHART_HISTORY_LIMIT = 200


def history_start_date() -> date:
    """Curve evolution + change matrix from 1 Jan of the current calendar year."""
    return date(date.today().year, 1, 1)


def symbol_to_meta(symbol: str) -> dict | None:
    m = re.fullmatch(rf"{PREFIX}([FGHJKMNQUVXZ])(\d{{2}})", symbol)
    if not m:
        return None
    month = MONTH_CODE[m.group(1)]
    year = 2000 + int(m.group(2))
    ym = f"{year}-{month:02d}"
    label = f"{MONTH_LABEL[month]}-{str(year)[2:]}"
    return {
        "key": ym,
        "label": label,
        "symbol": symbol,
        "delivery_ym": ym,
        "sort_key": (year, month),
    }


def discover_iq_chain() -> list[str]:
    from playwright.sync_api import sync_playwright

    found: set[str] = set()
    pat = re.compile(rf"{PREFIX}[FGHJKMNQUVXZ]\d{{2}}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA["User-Agent"]).new_page()

        def on_resp(response) -> None:
            if response.status != 200:
                return
            try:
                body = response.text()
            except Exception:
                return
            if PREFIX in body and len(body) < 900_000:
                found.update(pat.findall(body))

        page.on("response", on_resp)
        page.goto(CHAIN_URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(2000)
        found.update(pat.findall(page.content()))
        browser.close()

    syms = sorted(found, key=lambda s: symbol_to_meta(s)["sort_key"] if symbol_to_meta(s) else (9999, 99))
    print(f"Discovered {len(syms)} {PREFIX}* ASX 30-day cash rate contracts")
    return syms


def fetch_rba_cash_rate(fallback_path: Path | None = None) -> dict:
    """Latest RBA cash rate target from rba.gov.au (fallback to committed JSON)."""
    if fallback_path and fallback_path.is_file():
        with fallback_path.open(encoding="utf-8") as f:
            prev = json.load(f)
        fallback = {
            "cash_rate_pct": float(prev.get("cash_rate_pct", CASH_RATE_FALLBACK_PCT)),
            "cash_rate_as_of": prev.get("cash_rate_as_of", CASH_RATE_FALLBACK_AS_OF),
        }
    else:
        fallback = {
            "cash_rate_pct": CASH_RATE_FALLBACK_PCT,
            "cash_rate_as_of": CASH_RATE_FALLBACK_AS_OF,
        }

    try:
        r = requests.get(RBA_CASH_RATE_URL, timeout=60, headers=UA)
        r.raise_for_status()
        rows = re.findall(
            r"<td>\s*(\d{4}-\d{2}-\d{2})\s*</td>\s*<td>\s*([\d.]+)\s*</td>",
            r.text,
            flags=re.I,
        )
        if rows:
            as_of, rate = rows[0]
            return {
                "cash_rate_pct": round(float(rate), 3),
                "cash_rate_as_of": as_of,
                "cash_rate_source": "RBA cash rate target table",
            }
    except Exception as exc:
        print(f"::warning::RBA cash rate fetch failed ({exc}); using fallback")

    return {
        **fallback,
        "cash_rate_source": "committed fallback",
    }


def _ref_contract_key(meeting_date: date) -> str:
    """Contract month after RBA decision (monthly average cash rate proxy)."""
    y, m = meeting_date.year, meeting_date.month
    if m == 12:
        return f"{y + 1}-01"
    return f"{y}-{m + 1:02d}"


def _meeting_probs_25bp(delta_bp: float) -> dict[str, float]:
    cut = max(0.0, min(1.0, -delta_bp / 25.0))
    hike = max(0.0, min(1.0, delta_bp / 25.0))
    hold = max(0.0, 1.0 - cut - hike)
    return {
        "cut_pct": round(cut * 100, 1),
        "hold_pct": round(hold * 100, 1),
        "hike_pct": round(hike * 100, 1),
    }


def compute_rba_meeting_pricing(
    contracts: list[dict],
    cash_rate_pct: float,
    as_of: str | None = None,
) -> dict:
    cmap = {c["key"]: c for c in contracts}
    ref_date = date.fromisoformat(as_of) if as_of else date.today()
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)

    rows: list[dict] = []
    prev_implied: float | None = None
    marked_next = False

    for mtg in RBA_BOARD_MEETINGS:
        mdate = date.fromisoformat(mtg["date"])
        if mdate.year > latest.year + 1:
            break
        ref_key = _ref_contract_key(mdate)
        c = cmap.get(ref_key)
        if not c:
            continue

        implied = float(c["implied_rate_pct"])
        cumulative_bp = round((implied - cash_rate_pct) * 100, 1)
        anchor = cash_rate_pct if prev_implied is None else prev_implied
        incremental_bp = round((implied - anchor) * 100, 1)
        prev_implied = implied

        if mdate <= ref_date:
            status = "past"
        elif not marked_next:
            status = "next"
            marked_next = True
        else:
            status = "upcoming"

        rows.append({
            "meeting_date": mtg["date"],
            "meeting_label": mtg["label"],
            "status": status,
            "ref_contract_key": ref_key,
            "ref_contract_label": c["label"],
            "ref_symbol": c["symbol"],
            "implied_rate_pct": round(implied, 4),
            "cumulative_vs_cash_bp": cumulative_bp,
            "incremental_bp": incremental_bp,
            **_meeting_probs_25bp(incremental_bp),
        })

    total_easing_bp = rows[-1]["cumulative_vs_cash_bp"] if rows else 0.0
    upcoming = [r for r in rows if r["status"] != "past"]
    next_mtg = upcoming[0] if upcoming else None

    return {
        "note": RBA_PRICING_NOTE,
        "as_of": as_of or str(ref_date),
        "cash_rate_pct": cash_rate_pct,
        "total_easing_priced_bp": total_easing_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], cash: float
) -> dict:
    """Rolling strip: each session shows every contract that has EOD on that date."""
    keys_all = [c["key"] for c in contracts]
    label_map = {c["key"]: c for c in contracts}

    history: list[dict] = []
    for dt, row in wide.iterrows():
        pts = []
        for k in keys_all:
            v = row.get(k)
            if pd.isna(v):
                continue
            rate = float(v)
            pts.append({
                "key": k,
                "label": label_map[k]["label"],
                "symbol": label_map[k]["symbol"],
                "implied_rate_pct": round(rate, 4),
                "vs_cash_bp": round((rate - cash) * 100, 1),
            })
        if pts:
            history.append({"date": str(dt.date()), "points": pts})

    if not history:
        return {
            "n_contracts": len(keys_all),
            "contract_keys": keys_all,
            "n_sessions": 0,
            "start": None,
            "end": None,
            "note": "No overlapping EOD history.",
            "history": [],
            "watch_legs": {},
        }

    max_legs = max(len(h["points"]) for h in history)
    note = (
        f"Rolling strip evolution (YTD): {len(history)} sessions "
        f"({history[0]['date']} → {history[-1]['date']}). "
        f"Up to {len(keys_all)} contracts on latest date; back months join as they list."
    )

    watch = ["2026-12", "2027-06", "2027-12"]
    legs: dict = {}
    for k in watch:
        if k not in wide.columns:
            continue
        s = wide[k].dropna()
        legs[k] = {
            "label": label_map[k]["label"],
            "rows": [
                {
                    "date": str(d.date()),
                    "implied_rate_pct": round(float(v), 4),
                    "vs_cash_bp": round((float(v) - cash) * 100, 1),
                }
                for d, v in s.items()
            ],
        }

    return {
        "n_contracts": len(keys_all),
        "contract_keys": keys_all,
        "n_sessions": len(history),
        "max_legs_on_strip": max_legs,
        "start": history[0]["date"],
        "end": history[-1]["date"],
        "note": note,
        "history": history,
        "watch_legs": legs,
    }


def build_payload() -> dict:
    out_path = ROOT / "asx_ib_30d_data.json"
    cash_info = fetch_rba_cash_rate(out_path if out_path.exists() else None)
    cash_rate = float(cash_info["cash_rate_pct"])
    cash_as_of = cash_info.get("cash_rate_as_of", CASH_RATE_FALLBACK_AS_OF)

    symbols = discover_iq_chain()
    print(f"Fetching EOD for {len(symbols)} contracts…")
    batch = fetch_barchart_batch(symbols, history_limit=BARCHART_HISTORY_LIMIT)

    contracts: list[dict] = []
    series: dict[str, pd.Series] = {}

    for sym in symbols:
        meta = symbol_to_meta(sym)
        if not meta:
            continue
        df = batch.get(sym)
        if df is None or df.empty:
            print(f"  SKIP {sym}")
            continue
        rates = price_to_rate(df["price"])
        key = meta["key"]
        series[key] = rates
        implied = float(rates.iloc[-1])
        vs_cash_bp = (implied - cash_rate) * 100.0
        contracts.append({
            **meta,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_cash_bp": round(vs_cash_bp, 1),
            "vs_cash_hikes_25bp": round(vs_cash_bp / 25.0, 2),
        })
        print(f"  {sym} {meta['label']}: {implied:.3f}% ({vs_cash_bp:+.1f} bp vs {cash_rate}%)")

    if not contracts:
        raise RuntimeError("No ASX IB contracts fetched")

    wide = pd.DataFrame(series).sort_index(axis=1)
    ytd_start = pd.Timestamp(history_start_date())
    wide = wide.loc[wide.index >= ytd_start]
    records = []
    for dt, row in wide.iterrows():
        rec = {"date": str(dt.date())}
        for col in wide.columns:
            v = row[col]
            if pd.notna(v):
                rec[col] = round(float(v), 4)
        records.append(rec)

    evolution = _compute_curve_evolution(wide, contracts, cash_rate)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD settles",
        "contract": "ASX 30-day Interbank Cash Rate (IQ* / IB)",
        "quote_convention": "price = 100 − implied rate (%)",
        "cash_rate_pct": cash_rate,
        "cash_rate_as_of": cash_as_of,
        "cash_rate_source": cash_info.get("cash_rate_source", "RBA"),
        "history_start": str(history_start_date()),
        "n_contracts": len(contracts),
        "contracts": contracts,
        "timeseries": {
            "dates": [str(d.date()) for d in wide.index],
            "columns": list(wide.columns),
            "rows": records,
            "n_sessions": int(len(wide)),
            "start": str(wide.index.min().date()),
            "end": str(wide.index.max().date()),
        },
        "curve_evolution": evolution,
        "rba_meeting_pricing": compute_rba_meeting_pricing(
            contracts, cash_rate, cash_as_of
        ),
    }


def main() -> None:
    payload = build_payload()
    out = ROOT / "asx_ib_30d_data.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out} ({payload['n_contracts']} contracts)")


if __name__ == "__main__":
    main()
