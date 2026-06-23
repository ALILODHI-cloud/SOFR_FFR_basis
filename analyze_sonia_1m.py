"""
Fetch full 1M SONIA futures curve from Barchart EOD (ICE JU*).

Writes sonia_1m_data.json for build_sonia_1m_dashboard.py.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

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

# BoE MPC announcement dates (Thursday decisions).
MPC_MEETINGS = [
  {"date": "2026-02-05", "label": "Feb MPC"},
  {"date": "2026-03-19", "label": "Mar MPC"},
  {"date": "2026-04-30", "label": "Apr MPC"},
  {"date": "2026-06-18", "label": "Jun MPC"},
  {"date": "2026-07-30", "label": "Jul MPC"},
  {"date": "2026-09-17", "label": "Sep MPC"},
  {"date": "2026-11-05", "label": "Nov MPC"},
  {"date": "2026-12-17", "label": "Dec MPC"},
  {"date": "2027-02-04", "label": "Feb MPC"},
  {"date": "2027-03-18", "label": "Mar MPC"},
  {"date": "2027-04-29", "label": "Apr MPC"},
  {"date": "2027-06-17", "label": "Jun MPC"},
  {"date": "2027-07-29", "label": "Jul MPC"},
  {"date": "2027-09-16", "label": "Sep MPC"},
  {"date": "2027-11-04", "label": "Nov MPC"},
  {"date": "2027-12-16", "label": "Dec MPC"},
]

MPC_PRICING_NOTE = (
  "Approximate meeting path from ICE 1M SONIA futures (not BoE-dated OIS / WIRP). "
  "Each meeting maps to the next month's contract as a post-decision rate proxy. "
  "Probabilities assume 25bp steps (FedWatch-style). Standard 1M futures can span "
  "multiple meetings — use Bloomberg WIRP for precise per-meeting OIS pricing."
)


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


def _ref_contract_key(meeting_date: date) -> str:
    """Month after MPC as post-meeting policy proxy (≈30-day window)."""
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


def compute_mpc_meeting_pricing(
    contracts: list[dict],
    bank_rate_pct: float,
    as_of: str | None = None,
) -> dict:
    """Map 1M SONIA strip to BoE MPC calendar with meeting-level probabilities."""
    cmap = {c["key"]: c for c in contracts}
    ref_date = date.fromisoformat(as_of) if as_of else date.today()
    latest = max(date.fromisoformat(c["latest_date"]) for c in contracts)

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

    total_easing_bp = rows[-1]["cumulative_vs_bank_bp"] if rows else 0.0
    upcoming = [r for r in rows if r["status"] != "past"]
    next_mtg = upcoming[0] if upcoming else None

    return {
        "note": MPC_PRICING_NOTE,
        "as_of": as_of or str(ref_date),
        "bank_rate_pct": bank_rate_pct,
        "total_easing_priced_bp": total_easing_bp,
        "next_meeting": next_mtg,
        "meetings": rows,
    }


def _compute_curve_evolution(
    wide: pd.DataFrame, contracts: list[dict], bank: float
) -> dict:
    """Longest date range where a stable set of contracts all have EOD."""
    keys_all = [c["key"] for c in contracts]
    label_map = {c["key"]: c for c in contracts}

    # Prefer core curve through Feb-28 if it yields more sessions than all 24.
    core_keys = [k for k in keys_all if k <= "2028-02"]
    full_common = wide[keys_all].dropna(how="any")
    core_common = wide[core_keys].dropna(how="any")

    if len(core_common) >= len(full_common):
        use_keys, use_df = core_keys, core_common
        note = (
            f"Longest common history for {len(core_keys)} contracts "
            f"(Jun-26 → Feb-28). Back 3 contracts list later on Barchart."
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
                "vs_bank_bp": round((rate - bank) * 100, 1),
            })
        history.append({"date": str(dt.date()), "points": pts})

    # Key tenor legs vs bank over same window
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
                    "vs_bank_bp": round((float(v) - bank) * 100, 1),
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

    evolution = _compute_curve_evolution(wide, contracts, BANK_RATE_PCT)

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
        "curve_evolution": evolution,
        "mpc_meeting_pricing": compute_mpc_meeting_pricing(
            contracts, BANK_RATE_PCT, BANK_RATE_AS_OF
        ),
    }


def main() -> None:
    payload = build_payload()
    out = "/workspace/sonia_1m_data.json"
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out} ({payload['n_contracts']} contracts)")


if __name__ == "__main__":
    main()
