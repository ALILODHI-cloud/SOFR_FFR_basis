"""
Fetch full 3M SONIA futures curve from Barchart EOD (ICE J8*).

Writes sonia_3m_data.json for build_sonia_3m_dashboard.py.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

from analyze_sonia import UA, price_to_rate
from analyze_sonia_1m import BANK_RATE_AS_OF, BANK_RATE_PCT, MPC_MEETINGS, _meeting_probs_25bp
from analyze_stir_curves import fetch_barchart_batch, symbol_to_meta
from curve_chain import strip_symbols
from curve_snapshot import write_snapshot

CHAIN_URL = "https://www.barchart.com/futures/quotes/J8*0/futures-prices"
PREFIX = "J8"
MIN_CHAIN = 8
SYNTH_CHAIN = 28

MPC_3M_PRICING_NOTE = (
    "Approximate meeting path from ICE 3M SONIA futures (not BoE-dated OIS / WIRP). "
    "Each meeting maps to the next quarterly contract after the decision as a "
    "post-meeting rate proxy. Probabilities assume 25bp steps. Standard 3M futures "
    "can span multiple meetings — use Bloomberg WIRP for precise per-meeting OIS pricing."
)


def meta(symbol: str) -> dict | None:
    return symbol_to_meta(PREFIX, symbol)


def discover_j8_chain() -> list[str]:
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

    if len(found) < MIN_CHAIN:
        print(
            f"Chain scrape returned {len(found)} {PREFIX}* symbols "
            f"(min {MIN_CHAIN}); adding synthesized strip"
        )
        found.update(strip_symbols(PREFIX, SYNTH_CHAIN, quarterly=True))

    syms = sorted(found, key=lambda s: meta(s)["sort_key"] if meta(s) else (9999, 99))
    print(f"Discovered {len(syms)} {PREFIX}* 3M SONIA contracts")
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


def compute_mpc_meeting_pricing_3m(
    contracts: list[dict],
    bank_rate_pct: float,
    as_of: str | None = None,
) -> dict:
    cmap = {c["key"]: c for c in contracts}
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)
    ref_date = max(date.today(), latest)

    rows: list[dict] = []
    prev_implied: float | None = None
    marked_next = False

    for mtg in MPC_MEETINGS:
        mdate = date.fromisoformat(mtg["date"])
        if mdate.year > latest.year + 1:
            break
        ref_key = _ref_contract_key(mdate)
        c = cmap.get(ref_key)
        if not c:
            continue

        implied = float(c["implied_rate_pct"])
        cumulative_bp = round((implied - bank_rate_pct) * 100, 1)
        anchor = bank_rate_pct if prev_implied is None else prev_implied
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
            "cumulative_vs_bank_bp": cumulative_bp,
            "incremental_bp": incremental_bp,
            **_meeting_probs_25bp(incremental_bp),
        })

    total_bp = rows[-1]["cumulative_vs_bank_bp"] if rows else 0.0
    upcoming = [r for r in rows if r["status"] != "past"]
    next_mtg = upcoming[0] if upcoming else None

    return {
        "note": MPC_3M_PRICING_NOTE,
        "as_of": str(latest),
        "bank_rate_pct": bank_rate_pct,
        "bank_rate_as_of": as_of,
        "total_easing_priced_bp": total_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], bank: float
) -> dict:
    keys_all = [c["key"] for c in contracts]
    label_map = {c["key"]: c for c in contracts}
    last_key = keys_all[-1] if keys_all else ""
    note = (
        f"Full listed 3M SONIA strip ({len(keys_all)} contracts through "
        f"{last_key or 'n/a'}). Later deliveries have shorter history; "
        "the amber line skips missing points."
    )

    history: list[dict] = []
    for dt, row in wide.iterrows():
        pts = []
        for k in keys_all:
            if k not in wide.columns:
                continue
            v = row[k]
            if pd.isna(v):
                continue
            rate = float(v)
            pts.append({
                "key": k,
                "label": label_map[k]["label"],
                "symbol": label_map[k]["symbol"],
                "implied_rate_pct": round(rate, 4),
                "vs_bank_bp": round((rate - bank) * 100, 1),
            })
        if pts:
            history.append({"date": str(dt.date()), "points": pts})

    return {
        "n_contracts": len(keys_all),
        "contract_keys": keys_all,
        "n_sessions": int(len(history)),
        "start": history[0]["date"] if history else None,
        "end": history[-1]["date"] if history else None,
        "note": note,
        "history": history,
    }


def build_payload() -> dict:
    symbols = discover_j8_chain()
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
        vs_bank_bp = (implied - BANK_RATE_PCT) * 100.0
        contracts.append({
            **m,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_bank_bp": round(vs_bank_bp, 1),
            "vs_bank_hikes_25bp": round(vs_bank_bp / 25.0, 2),
        })
        print(f"  {sym} {m['label']}: {implied:.3f}% ({vs_bank_bp:+.1f} bp vs {BANK_RATE_PCT}%)")

    if not contracts:
        raise RuntimeError("No 3M SONIA contracts fetched")

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

    evolution = _compute_curve_evolution(wide, contracts, BANK_RATE_PCT)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart historical lastPrice (finalized EOD sessions only)",
        "contract": "ICE 3M SONIA (J8*)",
        "quote_convention": "price = 100 − implied rate (%)",
        "bank_rate_pct": BANK_RATE_PCT,
        "bank_rate_as_of": BANK_RATE_AS_OF,
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
        "mpc_meeting_pricing": compute_mpc_meeting_pricing_3m(
            contracts, BANK_RATE_PCT, BANK_RATE_AS_OF
        ),
    }


def main() -> None:
    payload = build_payload()
    write_snapshot(payload, ROOT / "sonia_3m_data.json", min_contracts=8)


if __name__ == "__main__":
    main()
