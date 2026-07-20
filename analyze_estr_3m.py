"""
Fetch full 3M €STR futures curve from Barchart EOD (CME EB*).

Writes estr_3m_data.json for build_estr_3m_dashboard.py.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

from analyze_sonia import UA, price_to_rate
from analyze_stir_curves import fetch_barchart_batch, symbol_to_meta
from analyze_estr_1m import (
    ECB_GOVERNING_COUNCIL,
    ECB_PRICING_NOTE,
    DEPOSIT_FACILITY_PCT,
    DEPOSIT_FACILITY_AS_OF,
    fetch_deposit_rate,
    _meeting_probs_25bp,
)

CHAIN_URL = "https://www.barchart.com/futures/quotes/EB*0/futures-prices"
PREFIX = "EB"

ECB_3M_PRICING_NOTE = (
    "Approximate meeting path from CME 3M €STR futures (not ECB-dated OIS / WIRP). "
    "Each meeting maps to the next quarterly contract after the decision as a "
    "post-meeting rate proxy. Probabilities assume 25bp steps. Standard 3M futures "
    "can span multiple meetings — use Bloomberg WIRP for precise per-meeting OIS pricing."
)


def meta(symbol: str) -> dict | None:
    return symbol_to_meta(PREFIX, symbol)


def discover_eb_chain() -> list[str]:
    from playwright.sync_api import sync_playwright

    found: set[str] = set()
    pat = re.compile(rf"{PREFIX}[HMUZ]\d{{2}}")

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

    syms = sorted(found, key=lambda s: meta(s)["sort_key"] if meta(s) else (9999, 99))
    print(f"Discovered {len(syms)} {PREFIX}* 3M €STR contracts")
    return syms


def _ref_contract_key(meeting_date: date) -> str:
    """Quarter after meeting month as post-decision policy proxy."""
    y, m = meeting_date.year, meeting_date.month
    if m == 12:
        y, m = y + 1, 1
    else:
        m += 1
    quarter = min(12, ((m - 1) // 3 + 1) * 3)
    return f"{y}-{quarter:02d}"


def compute_ecb_meeting_pricing_3m(
    contracts: list[dict],
    deposit_pct: float,
    as_of: str | None = None,
) -> dict:
    cmap = {c["key"]: c for c in contracts}
    ref_date = date.fromisoformat(as_of) if as_of else date.today()
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)

    rows: list[dict] = []
    prev_implied: float | None = None
    marked_next = False

    for mtg in ECB_GOVERNING_COUNCIL:
        mdate = date.fromisoformat(mtg["date"])
        if mdate.year > latest.year + 1:
            break
        ref_key = _ref_contract_key(mdate)
        c = cmap.get(ref_key)
        if not c:
            continue

        implied = float(c["implied_rate_pct"])
        cumulative_bp = round((implied - deposit_pct) * 100, 1)
        anchor = deposit_pct if prev_implied is None else prev_implied
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
            "cumulative_vs_deposit_bp": cumulative_bp,
            "incremental_bp": incremental_bp,
            **_meeting_probs_25bp(incremental_bp),
        })

    total_bp = rows[-1]["cumulative_vs_deposit_bp"] if rows else 0.0
    upcoming = [r for r in rows if r["status"] != "past"]
    next_mtg = upcoming[0] if upcoming else None

    return {
        "note": ECB_3M_PRICING_NOTE,
        "as_of": as_of or str(ref_date),
        "deposit_facility_pct": deposit_pct,
        "total_easing_priced_bp": total_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
        "calendar": ECB_GOVERNING_COUNCIL,
        "calendar_source": "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], deposit: float
) -> dict:
    keys_all = [c["key"] for c in contracts]
    label_map = {c["key"]: c for c in contracts}

    core_keys = [k for k in keys_all if k <= "2028-12"]
    full_common = wide[keys_all].dropna(how="any")
    core_common = wide[core_keys].dropna(how="any")

    if len(core_common) >= len(full_common):
        use_keys, use_df = core_keys, core_common
        note = (
            f"Longest common history for {len(core_keys)} contracts "
            f"(through Dec-28). Far-dated contracts list later on Barchart."
        )
    else:
        use_keys, use_df = keys_all, full_common
        note = f"Common history for all {len(keys_all)} listed contracts."

    history: list[dict] = []
    for dt, row in use_df.iterrows():
        pts = []
        for k in use_keys:
            rate = float(row[k])
            pts.append({
                "key": k,
                "label": label_map[k]["label"],
                "symbol": label_map[k]["symbol"],
                "implied_rate_pct": round(rate, 4),
                "vs_deposit_bp": round((rate - deposit) * 100, 1),
            })
        history.append({"date": str(dt.date()), "points": pts})

    return {
        "n_contracts": len(use_keys),
        "contract_keys": use_keys,
        "n_sessions": int(len(use_df)),
        "start": str(use_df.index.min().date()) if len(use_df) else None,
        "end": str(use_df.index.max().date()) if len(use_df) else None,
        "note": note,
        "history": history,
    }


def build_payload() -> dict:
    out_path = ROOT / "estr_3m_data.json"
    dep = fetch_deposit_rate(out_path)
    # Prefer committed 2.25 if present; else module default.
    deposit = float(dep["deposit_facility_pct"])
    deposit_as_of = dep.get("deposit_facility_as_of", DEPOSIT_FACILITY_AS_OF)

    symbols = discover_eb_chain()
    print(f"Fetching EOD for {len(symbols)} contracts…")
    batch = fetch_barchart_batch(symbols)

    contracts: list[dict] = []
    series: dict[str, pd.Series] = {}

    for sym in symbols:
        m = meta(sym)
        if not m:
            continue
        df = batch.get(sym)
        if df is None or df.empty:
            print(f"  SKIP {sym}")
            continue
        rates = price_to_rate(df["price"])
        key = m["key"]
        series[key] = rates
        implied = float(rates.iloc[-1])
        vs_dep_bp = (implied - deposit) * 100.0
        contracts.append({
            **m,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_deposit_bp": round(vs_dep_bp, 1),
            "vs_deposit_hikes_25bp": round(vs_dep_bp / 25.0, 2),
        })
        print(f"  {sym} {m['label']}: {implied:.3f}% ({vs_dep_bp:+.1f} bp vs {deposit}%)")

    if not contracts:
        raise RuntimeError("No 3M €STR contracts fetched")

    # QoQ bp change along the strip
    for i, c in enumerate(contracts):
        if i == 0:
            c["bp_change"] = None
        else:
            c["bp_change"] = round(
                (c["implied_rate_pct"] - contracts[i - 1]["implied_rate_pct"]) * 100, 1
            )

    wide = pd.DataFrame(series).sort_index(axis=1)
    records = []
    for dt, row in wide.iterrows():
        rec = {"date": str(dt.date())}
        for col in wide.columns:
            v = row[col]
            if pd.notna(v):
                rec[col] = round(float(v), 4)
        records.append(rec)

    evolution = _compute_curve_evolution(wide, contracts, deposit)
    pricing = compute_ecb_meeting_pricing_3m(contracts, deposit, deposit_as_of)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart historical lastPrice (finalized EOD sessions only)",
        "contract": "CME 3M €STR (EB*)",
        "quote_convention": "price = 100 − implied rate (%)",
        "deposit_facility_pct": deposit,
        "deposit_facility_as_of": deposit_as_of,
        "deposit_facility_source": dep.get("deposit_facility_source", "committed fallback"),
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
        "ecb_meeting_pricing": pricing,
        "ecb_calendar": ECB_GOVERNING_COUNCIL,
        "ecb_calendar_source": "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
        "ecb_pricing_note_1m": ECB_PRICING_NOTE,
    }


def main() -> None:
    payload = build_payload()
    out = ROOT / "estr_3m_data.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out} ({payload['n_contracts']} contracts)")


if __name__ == "__main__":
    main()
