"""
Fetch full 3M SOFR futures curve from Barchart EOD (CME SQ*).

Writes sofr_3m_data.json for build_sofr_3m_dashboard.py.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

from analyze_sonia import price_to_rate
from analyze_stir_curves import _parse_barchart_hist, fetch_barchart_batch, symbol_to_meta

FED_FUNDS_PCT = 4.125
FED_FUNDS_AS_OF = "2026-06-18"

CHAIN_URL = "https://www.barchart.com/futures/quotes/SQ*0/futures-prices"
PREFIX = "SQ"

# FOMC decision dates (Wednesday announcements).
FOMC_MEETINGS = [
    {"date": "2026-01-29", "label": "Jan FOMC"},
    {"date": "2026-03-18", "label": "Mar FOMC"},
    {"date": "2026-04-29", "label": "Apr FOMC"},
    {"date": "2026-06-18", "label": "Jun FOMC"},
    {"date": "2026-07-30", "label": "Jul FOMC"},
    {"date": "2026-09-17", "label": "Sep FOMC"},
    {"date": "2026-11-05", "label": "Nov FOMC"},
    {"date": "2026-12-10", "label": "Dec FOMC"},
    {"date": "2027-01-28", "label": "Jan FOMC"},
    {"date": "2027-03-18", "label": "Mar FOMC"},
    {"date": "2027-04-29", "label": "Apr FOMC"},
    {"date": "2027-06-17", "label": "Jun FOMC"},
    {"date": "2027-07-29", "label": "Jul FOMC"},
    {"date": "2027-09-16", "label": "Sep FOMC"},
    {"date": "2027-11-04", "label": "Nov FOMC"},
    {"date": "2027-12-09", "label": "Dec FOMC"},
]

FOMC_PRICING_NOTE = (
    "Approximate meeting path from CME 3M SOFR futures (not Fed-dated OIS / FedWatch). "
    "Each meeting maps to the next quarterly contract after the decision as a post-meeting "
    "rate proxy. Probabilities assume 25bp steps (FedWatch-style). Standard 3M futures can "
    "span multiple meetings — use CME FedWatch or OIS for precise per-meeting pricing."
)


def meta(symbol: str) -> dict | None:
    return symbol_to_meta(PREFIX, symbol)


def discover_sq_chain() -> list[str]:
    from analyze_sonia import UA
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
    print(f"Discovered {len(syms)} {PREFIX}* 3M SOFR contracts")
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


def _meeting_probs_25bp(delta_bp: float) -> dict[str, float]:
    cut = max(0.0, min(1.0, -delta_bp / 25.0))
    hike = max(0.0, min(1.0, delta_bp / 25.0))
    hold = max(0.0, 1.0 - cut - hike)
    return {
        "cut_pct": round(cut * 100, 1),
        "hold_pct": round(hold * 100, 1),
        "hike_pct": round(hike * 100, 1),
    }


def compute_fomc_meeting_pricing(
    contracts: list[dict],
    fed_funds_pct: float,
    as_of: str | None = None,
) -> dict:
    """Map 3M SOFR strip to FOMC calendar with meeting-level probabilities."""
    cmap = {c["key"]: c for c in contracts}
    ref_date = date.fromisoformat(as_of) if as_of else date.today()
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)

    rows: list[dict] = []
    prev_implied: float | None = None
    marked_next = False

    for mtg in FOMC_MEETINGS:
        mdate = date.fromisoformat(mtg["date"])
        if mdate.year > latest.year + 1:
            break
        ref_key = _ref_contract_key(mdate)
        c = cmap.get(ref_key)
        if not c:
            continue

        implied = float(c["implied_rate_pct"])
        cumulative_bp = round((implied - fed_funds_pct) * 100, 1)
        anchor = fed_funds_pct if prev_implied is None else prev_implied
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
            "cumulative_vs_fed_bp": cumulative_bp,
            "incremental_bp": incremental_bp,
            **_meeting_probs_25bp(incremental_bp),
        })

    total_easing_bp = rows[-1]["cumulative_vs_fed_bp"] if rows else 0.0
    upcoming = [r for r in rows if r["status"] != "past"]
    next_mtg = upcoming[0] if upcoming else None

    return {
        "note": FOMC_PRICING_NOTE,
        "as_of": as_of or str(ref_date),
        "fed_funds_pct": fed_funds_pct,
        "total_easing_priced_bp": total_easing_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], fed: float
) -> dict:
    """Longest date range where a stable set of contracts all have EOD."""
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
                "vs_fed_bp": round((rate - fed) * 100, 1),
            })
        history.append({"date": str(dt.date()), "points": pts})

    watch = ["2026-12", "2027-06", "2027-12"]
    legs: dict = {}
    for k in watch:
        if k not in use_df.columns:
            continue
        s = use_df[k]
        legs[k] = {
            "label": label_map[k]["label"],
            "rows": [
                {
                    "date": str(d.date()),
                    "implied_rate_pct": round(float(v), 4),
                    "vs_fed_bp": round((float(v) - fed) * 100, 1),
                }
                for d, v in s.items()
            ],
        }

    return {
        "n_contracts": len(use_keys),
        "contract_keys": use_keys,
        "n_sessions": int(len(use_df)),
        "start": str(use_df.index.min().date()),
        "end": str(use_df.index.max().date()),
        "note": note,
        "history": history,
        "watch_legs": legs,
    }


def build_payload() -> dict:
    symbols = discover_sq_chain()
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
        vs_fed_bp = (implied - FED_FUNDS_PCT) * 100.0
        contracts.append({
            **m,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_fed_bp": round(vs_fed_bp, 1),
            "vs_fed_hikes_25bp": round(vs_fed_bp / 25.0, 2),
        })
        print(f"  {sym} {m['label']}: {implied:.3f}% ({vs_fed_bp:+.1f} bp vs {FED_FUNDS_PCT}%)")

    if not contracts:
        raise RuntimeError("No 3M SOFR contracts fetched")

    wide = pd.DataFrame(series).sort_index(axis=1)
    records = []
    for dt, row in wide.iterrows():
        rec = {"date": str(dt.date())}
        for col in wide.columns:
            v = row[col]
            if pd.notna(v):
                rec[col] = round(float(v), 4)
        records.append(rec)

    evolution = _compute_curve_evolution(wide, contracts, FED_FUNDS_PCT)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD settles",
        "contract": "CME 3M SOFR (SQ*)",
        "quote_convention": "price = 100 − implied rate (%)",
        "fed_funds_pct": FED_FUNDS_PCT,
        "fed_funds_as_of": FED_FUNDS_AS_OF,
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
        "fomc_meeting_pricing": compute_fomc_meeting_pricing(
            contracts, FED_FUNDS_PCT, FED_FUNDS_AS_OF
        ),
    }


def main() -> None:
    payload = build_payload()
    out = ROOT / "sofr_3m_data.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out} ({payload['n_contracts']} contracts)")


if __name__ == "__main__":
    main()
