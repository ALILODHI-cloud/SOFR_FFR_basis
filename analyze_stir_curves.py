"""
Fetch Jun-2026 → Dec-2028 STIR curves from Barchart EOD:
  - 3M SOFR (CME, SQ*)
  - 3M SONIA (ICE, J8*)
  - 3M €STR (CME, EB*)

Writes stir_curves_data.json for build_stir_curves_dashboard.py.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from analyze_sonia import BARCHART_LIMIT, UA, fetch_barchart_eod, price_to_rate

# Quarterly contracts from Jun-2026 through Dec-2028 (IMM H/M/U/Z).
CURVE_MONTHS = [
    ("2026-06", "M26", "Jun-26"),
    ("2026-09", "U26", "Sep-26"),
    ("2026-12", "Z26", "Dec-26"),
    ("2027-03", "H27", "Mar-27"),
    ("2027-06", "M27", "Jun-27"),
    ("2027-09", "U27", "Sep-27"),
    ("2027-12", "Z27", "Dec-27"),
    ("2028-03", "H28", "Mar-28"),
    ("2028-06", "M28", "Jun-28"),
    ("2028-09", "U28", "Sep-28"),
    ("2028-12", "Z28", "Dec-28"),
]

CURVES = {
    "sofr_3m": {
        "label": "3M SOFR",
        "exchange": "CME",
        "prefix": "SQ",
        "tenor": "3M compounded SOFR",
    },
    "sonia_3m": {
        "label": "3M SONIA",
        "exchange": "ICE",
        "prefix": "J8",
        "tenor": "3M compounded SONIA",
    },
    "estr_3m": {
        "label": "3M €STR",
        "exchange": "CME",
        "prefix": "EB",
        "tenor": "3M compounded €STR",
    },
}

HISTORY_LIMIT = 200


def _parse_barchart_hist(hist: dict, symbol: str) -> pd.DataFrame:
    if not hist or "data" not in hist:
        raise RuntimeError(f"No Barchart history for {symbol}")
    recs = []
    for row in hist["data"]:
        raw = row.get("raw") or {}
        d = raw.get("tradeTime") or row.get("tradeTime")
        if not d:
            continue
        px = raw.get("lastPrice")
        if px is None:
            px = float(str(row.get("lastPrice", "")).replace(",", ""))
        recs.append({"date": pd.to_datetime(d), "price": float(px)})
    df = pd.DataFrame(recs).drop_duplicates("date", keep="last").set_index("date").sort_index()
    df.index = df.index.normalize()
    return df


def fetch_barchart_hist_only(symbol: str, limit: int = HISTORY_LIMIT) -> pd.DataFrame:
    """Historical EOD only (skip slow quote-page networkidle)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA["User-Agent"]).new_page()
        with page.expect_response(
            lambda r: "historical/get" in r.url and symbol in r.url and r.status == 200,
            timeout=90_000,
        ) as hist_resp:
            page.goto(
                f"https://www.barchart.com/futures/quotes/{symbol}/price-history/historical",
                wait_until="domcontentloaded",
                timeout=90_000,
            )
        hist = hist_resp.value.json()
        browser.close()
    return _parse_barchart_hist(hist, symbol)


def fetch_barchart_batch(symbols: list[str], limit: int = HISTORY_LIMIT) -> dict[str, pd.DataFrame]:
    """Fetch many symbols in one browser session."""
    from playwright.sync_api import sync_playwright

    out: dict[str, pd.DataFrame] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA["User-Agent"]).new_page()
        for sym in symbols:
            try:
                with page.expect_response(
                    lambda r, s=sym: "historical/get" in r.url and s in r.url and r.status == 200,
                    timeout=90_000,
                ) as hist_resp:
                    page.goto(
                        f"https://www.barchart.com/futures/quotes/{sym}/price-history/historical",
                        wait_until="domcontentloaded",
                        timeout=90_000,
                    )
                out[sym] = _parse_barchart_hist(hist_resp.value.json(), sym)
            except Exception as exc:
                print(f"  batch miss {sym}: {exc}")
        browser.close()
    return out


def fetch_curve(
    curve_key: str, cfg: dict, batch: dict[str, pd.DataFrame]
) -> tuple[dict, pd.DataFrame]:
    """Return per-contract metadata and wide rate DataFrame (columns = contract keys)."""
    contracts: list[dict] = []
    series: dict[str, pd.Series] = {}

    for ym, code, label in CURVE_MONTHS:
        sym = f"{cfg['prefix']}{code}"
        used_sym = sym
        df = batch.get(sym)
        if df is None and cfg.get("fallback_prefix"):
            used_sym = f"{cfg['fallback_prefix']}{code}"
            df = batch.get(used_sym)
        if df is None or df.empty:
            print(f"  SKIP {sym}")
            continue

        rates = price_to_rate(df["price"])
        key = ym
        series[key] = rates
        latest = rates.iloc[-1]
        contracts.append(
            {
                "key": key,
                "label": label,
                "symbol": used_sym,
                "delivery_ym": ym,
                "latest_date": str(rates.index[-1].date()),
                "price": round(float(df["price"].iloc[-1]), 4),
                "implied_rate_pct": round(float(latest), 4),
            }
        )
        print(
            f"  {used_sym} ({label}): {len(df)} rows → "
            f"{rates.index[-1].date()} @ {latest:.3f}%"
        )

    if not series:
        raise RuntimeError(f"No contracts fetched for {curve_key}")

    wide = pd.DataFrame(series).sort_index()
    meta = {
        **cfg,
        "contracts": contracts,
        "n_contracts": len(contracts),
        "history_start": str(wide.index.min().date()),
        "history_end": str(wide.index.max().date()),
        "n_sessions": int(len(wide)),
    }
    return meta, wide


def main() -> None:
    print("Fetching STIR curves from Barchart (Jun-26 → Dec-28)…")
    all_syms: list[str] = []
    for cfg in CURVES.values():
        for _ym, code, _label in CURVE_MONTHS:
            all_syms.append(f"{cfg['prefix']}{code}")
    all_syms = list(dict.fromkeys(all_syms))
    print(f"Batch fetch: {len(all_syms)} symbols…")
    batch = fetch_barchart_batch(all_syms)

    payload: dict = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD settles",
        "quote_convention": "price = 100 − implied rate (%)",
        "curve_months": [{"ym": ym, "code": code, "label": label} for ym, code, label in CURVE_MONTHS],
        "curves": {},
        "timeseries": {},
        "current_snapshot": [],
    }

    all_wide: dict[str, pd.DataFrame] = {}
    for key, cfg in CURVES.items():
        print(f"\n{cfg['label']} ({cfg['prefix']}*)")
        meta, wide = fetch_curve(key, cfg, batch)
        payload["curves"][key] = meta
        all_wide[key] = wide

        # Latest snapshot row for cross-currency table (aligned on delivery month)
        for c in meta["contracts"]:
            payload["current_snapshot"].append(
                {
                    "curve": key,
                    "curve_label": meta["label"],
                    **c,
                }
            )

    # Common overlap for time-series heatmap / small-multiples
    overlap_idx = None
    for wide in all_wide.values():
        overlap_idx = wide.index if overlap_idx is None else overlap_idx.intersection(wide.index)
    overlap_idx = overlap_idx.sort_values() if overlap_idx is not None else pd.DatetimeIndex([])

    for key, wide in all_wide.items():
        sub = wide.loc[overlap_idx] if len(overlap_idx) else wide
        records = []
        for dt, row in sub.iterrows():
            rec = {"date": str(dt.date())}
            for col in sub.columns:
                v = row[col]
                if pd.notna(v):
                    rec[col] = round(float(v), 4)
            records.append(rec)
        payload["timeseries"][key] = {
            "dates": [str(d.date()) for d in sub.index],
            "columns": list(sub.columns),
            "rows": records,
            "n_sessions": int(len(sub)),
            "start": str(sub.index.min().date()) if len(sub) else None,
            "end": str(sub.index.max().date()) if len(sub) else None,
        }

    out = "/workspace/stir_curves_data.json"
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {out} ({len(overlap_idx)} overlap sessions)")


if __name__ == "__main__":
    main()
