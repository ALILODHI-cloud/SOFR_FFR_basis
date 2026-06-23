"""
Fetch full 1M SONIA futures curve from Barchart EOD (ICE JU*).

Writes sonia_1m_data.json for build_sonia_1m_dashboard.py.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import pandas as pd

from analyze_sonia import UA, price_to_rate
from analyze_stir_curves import _parse_barchart_hist, fetch_barchart_batch

BANK_RATE_PCT = 3.75
BANK_RATE_AS_OF = "2026-06-18"

CHAIN_URL = "https://www.barchart.com/futures/quotes/JU*0/futures-prices"
PREFIX = "JU"

MONTH_CODE = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}
MONTH_LABEL = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


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


def discover_ju_chain() -> list[str]:
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
    print(f"Discovered {len(syms)} {PREFIX}* 1M SONIA contracts")
    return syms


def build_payload() -> dict:
    symbols = discover_ju_chain()
    print(f"Fetching EOD for {len(symbols)} contracts…")
    batch = fetch_barchart_batch(symbols)

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
        vs_bank_bp = (implied - BANK_RATE_PCT) * 100.0
        contracts.append({
            **meta,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(implied, 4),
            "vs_bank_bp": round(vs_bank_bp, 1),
            "vs_bank_hikes_25bp": round(vs_bank_bp / 25.0, 2),
        })
        print(f"  {sym} {meta['label']}: {implied:.3f}% ({vs_bank_bp:+.1f} bp vs {BANK_RATE_PCT}%)")

    if not contracts:
        raise RuntimeError("No 1M SONIA contracts fetched")

    wide = pd.DataFrame(series).sort_index(axis=1)
    records = []
    for dt, row in wide.iterrows():
        rec = {"date": str(dt.date())}
        for col in wide.columns:
            v = row[col]
            if pd.notna(v):
                rec[col] = round(float(v), 4)
        records.append(rec)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD settles",
        "contract": "ICE 1M SONIA (JU*)",
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
    }


def main() -> None:
    payload = build_payload()
    out = "/workspace/sonia_1m_data.json"
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out} ({payload['n_contracts']} contracts)")


if __name__ == "__main__":
    main()
