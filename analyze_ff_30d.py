"""
Fetch CME 30-day Fed Funds futures curve from Barchart EOD (ZQ*).

Writes ff_30d_data.json for build_ff_30d_dashboard.py.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

from analyze_sonia import UA, price_to_rate
from analyze_sofr_3m import FOMC_MEETINGS, fetch_fed_funds_midpoint
from analyze_stir_curves import fetch_barchart_batch
from curve_chain import strip_symbols
from curve_snapshot import write_snapshot

CHAIN_URL = "https://www.barchart.com/futures/quotes/ZQ*0/futures-prices"
PREFIX = "ZQ"
# Below this many scraped symbols the chain page is assumed challenged.
MIN_CHAIN = 8
SYNTH_CHAIN = 36

MONTH_CODE = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}
MONTH_LABEL = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

FOMC_PRICING_NOTE = (
    "Approximate meeting path from CME 30-day Fed Funds futures (not Fed-dated OIS / FedWatch). "
    "Each meeting maps to the contract month after the decision as a post-meeting rate proxy. "
    "Probabilities assume 25bp steps (FedWatch-style). Monthly FF contracts average EFFR "
    "over the calendar month — use CME FedWatch or OIS for precise per-meeting pricing."
)

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


def discover_zq_chain() -> list[str]:
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

    if len(found) < MIN_CHAIN:
        print(
            f"Chain scrape returned {len(found)} {PREFIX}* symbols "
            f"(min {MIN_CHAIN}); adding synthesized strip"
        )
        found.update(strip_symbols(PREFIX, SYNTH_CHAIN))

    syms = sorted(found, key=lambda s: symbol_to_meta(s)["sort_key"] if symbol_to_meta(s) else (9999, 99))
    print(f"Discovered {len(syms)} {PREFIX}* 30-day Fed Funds contracts")
    return syms


def _ref_contract_key(meeting_date: date) -> str:
    """Contract month after FOMC decision (monthly average EFFR proxy)."""
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


def compute_fomc_meeting_pricing(
    contracts: list[dict],
    fed_funds_pct: float,
    as_of: str | None = None,
) -> dict:
    cmap = {c["key"]: c for c in contracts}
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)
    ref_date = max(date.today(), latest)

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
        "as_of": str(latest),
        "fed_funds_pct": fed_funds_pct,
        "total_easing_priced_bp": total_easing_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], fed: float
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
                "vs_fed_bp": round((rate - fed) * 100, 1),
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
                    "vs_fed_bp": round((float(v) - fed) * 100, 1),
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


def _fed_fallback_path() -> Path | None:
    ff_path = ROOT / "ff_30d_data.json"
    if ff_path.is_file():
        return ff_path
    sofr_path = ROOT / "sofr_3m_data.json"
    if sofr_path.is_file():
        return sofr_path
    return None


def build_payload() -> dict:
    fed = fetch_fed_funds_midpoint(_fed_fallback_path())
    fed_mid = float(fed["fed_funds_pct"])

    symbols = discover_zq_chain()
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
        vs_fed_bp = (implied - fed_mid) * 100.0
        contracts.append({
            **meta,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_fed_bp": round(vs_fed_bp, 1),
            "vs_fed_hikes_25bp": round(vs_fed_bp / 25.0, 2),
        })
        print(f"  {sym} {meta['label']}: {implied:.3f}% ({vs_fed_bp:+.1f} bp vs {fed_mid}%)")

    if not contracts:
        raise RuntimeError("No 30-day Fed Funds contracts fetched")

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

    evolution = _compute_curve_evolution(wide, contracts, fed_mid)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD settles",
        "contract": "CME 30-day Fed Funds (ZQ*)",
        "quote_convention": "price = 100 − implied rate (%)",
        **fed,
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
        "fomc_meeting_pricing": compute_fomc_meeting_pricing(
            contracts, fed_mid, fed.get("fed_funds_as_of")
        ),
    }


def main() -> None:
    payload = build_payload()
    write_snapshot(payload, ROOT / "ff_30d_data.json", min_contracts=8)


if __name__ == "__main__":
    main()
