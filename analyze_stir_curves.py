"""
Fetch full 3M STIR curves from Barchart EOD (all listed quarterly contracts):
  - 3M SOFR (CME, SQ*)
  - 3M SONIA (ICE, J8*)
  - 3M €STR (CME, EB*)

Discovers active contracts from each Barchart futures chain, then batch-fetches EOD history.
Writes stir_curves_data.json for build_stir_curves_dashboard.py / serve_stir_live.py.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyze_sonia import UA, price_to_rate, drop_incomplete_barchart_session

ROOT = Path(__file__).resolve().parent

CURVES = {
    "sofr_3m": {
        "label": "3M SOFR",
        "exchange": "CME",
        "prefix": "SQ",
        "chain_url": "https://www.barchart.com/futures/quotes/SQ*0/futures-prices",
        "tenor": "3M compounded SOFR",
    },
    "sonia_3m": {
        "label": "3M SONIA",
        "exchange": "ICE",
        "prefix": "J8",
        "chain_url": "https://www.barchart.com/futures/quotes/J8*0/futures-prices",
        "tenor": "3M compounded SONIA",
    },
    "estr_3m": {
        "label": "3M €STR",
        "exchange": "CME",
        "prefix": "EB",
        "chain_url": "https://www.barchart.com/futures/quotes/EB*0/futures-prices",
        "tenor": "3M compounded €STR",
    },
}

HISTORY_LIMIT = 200
MONTH_CODE = {"H": 3, "M": 6, "U": 9, "Z": 12}
MONTH_LABEL = {3: "Mar", 6: "Jun", 9: "Sep", 12: "Dec"}

# Calendar spreads tracked over time (back − front, in bp).
CALENDAR_SPREADS = [
    {"id": "dec28_minus_jun27", "label": "Dec-28 − Jun-27", "back": "2028-12", "front": "2027-06"},
    {"id": "dec28_minus_jun26", "label": "Dec-28 − Jun-26", "back": "2028-12", "front": "2026-06"},
    {"id": "dec27_minus_dec26", "label": "Dec-27 − Dec-26", "back": "2027-12", "front": "2026-12"},
]


def symbol_to_meta(prefix: str, symbol: str) -> dict | None:
    m = re.fullmatch(rf"{re.escape(prefix)}([HMUZ])(\d{{2}})", symbol)
    if not m:
        return None
    month = MONTH_CODE[m.group(1)]
    year = 2000 + int(m.group(2))
    ym = f"{year}-{month:02d}"
    label = f"{MONTH_LABEL[month]}-{str(year)[2:]}"
    return {"key": ym, "label": label, "symbol": symbol, "delivery_ym": ym, "sort_key": (year, month)}


def discover_chain_symbols(prefix: str, chain_url: str) -> list[str]:
    """Scrape Barchart futures chain page for all listed quarterly symbols."""
    from playwright.sync_api import sync_playwright

    found: set[str] = set()
    pat = re.compile(rf"{re.escape(prefix)}[HMUZ]\d{{2}}")

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
            if prefix in body and len(body) < 800_000:
                found.update(pat.findall(body))

        page.on("response", on_resp)
        page.goto(chain_url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(1500)
        html = page.content()
        found.update(pat.findall(html))
        browser.close()

    def sort_key(sym: str) -> tuple[int, int]:
        meta = symbol_to_meta(prefix, sym)
        return meta["sort_key"] if meta else (9999, 99)

    syms = sorted(found, key=sort_key)
    print(f"  Discovered {len(syms)} {prefix}* contracts on Barchart")
    return syms


def _parse_barchart_hist(hist: dict, symbol: str) -> pd.DataFrame:
    """Parse Barchart historical/get payload into a daily price series.

    Barchart's historical API exposes ``lastPrice`` (not a separate settle field).
    For *completed* sessions that is the EOD print we want. For the *current*
    session it can be a live/incomplete bar — those are dropped so curve
    dashboards and trade marks only use finalized EOD rows.
    """
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
        vol = raw.get("volume")
        if vol is None:
            vol_raw = row.get("volume")
            if vol_raw not in (None, ""):
                try:
                    vol = float(str(vol_raw).replace(",", ""))
                except ValueError:
                    vol = None
        recs.append(
            {
                "date": pd.to_datetime(d),
                "price": float(px),
                "volume": float(vol) if vol is not None else float("nan"),
            }
        )
    df = pd.DataFrame(recs).drop_duplicates("date", keep="last").set_index("date").sort_index()
    df.index = df.index.normalize()
    df = drop_incomplete_barchart_session(df, symbol)
    return df[["price"]]


def fetch_barchart_batch(
    symbols: list[str],
    timeout_ms: int = 60_000,
    history_limit: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch EOD history for many symbols in one browser session."""
    from playwright.sync_api import sync_playwright

    out: dict[str, pd.DataFrame] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA["User-Agent"]).new_page()

        if history_limit is not None:

            def _bump_limit(route) -> None:
                url = route.request.url
                if "historical/get" in url:
                    route.continue_(
                        url=re.sub(r"limit=\d+", f"limit={history_limit}", url)
                    )
                else:
                    route.continue_()

            page.route("**/*", _bump_limit)

        for i, sym in enumerate(symbols, 1):
            try:
                with page.expect_response(
                    lambda r, s=sym: "historical/get" in r.url and s in r.url and r.status == 200,
                    timeout=timeout_ms,
                ) as hist_resp:
                    page.goto(
                        f"https://www.barchart.com/futures/quotes/{sym}/price-history/historical",
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                out[sym] = _parse_barchart_hist(hist_resp.value.json(), sym)
                if i % 10 == 0:
                    print(f"    … fetched {i}/{len(symbols)}")
            except Exception as exc:
                print(f"    miss {sym}: {str(exc)[:80]}")
        browser.close()
    return out


def fetch_curve(
    curve_key: str, cfg: dict, batch: dict[str, pd.DataFrame], symbols: list[str]
) -> tuple[dict, pd.DataFrame, list[dict]]:
    prefix = cfg["prefix"]
    contracts: list[dict] = []
    series: dict[str, pd.Series] = {}
    curve_months: list[dict] = []

    for sym in symbols:
        meta = symbol_to_meta(prefix, sym)
        if not meta:
            continue
        df = batch.get(sym)
        if df is None or df.empty:
            continue
        rates = price_to_rate(df["price"])
        key = meta["key"]
        series[key] = rates
        latest = rates.iloc[-1]
        c = {
            **meta,
            "latest_date": str(rates.index[-1].date()),
            "price": round(float(df["price"].iloc[-1]), 4),
            "implied_rate_pct": round(float(latest), 4),
        }
        contracts.append(c)
        curve_months.append({"ym": key, "code": sym[len(prefix) :], "label": meta["label"], "symbol": sym})
        print(f"  {sym} ({meta['label']}): {len(df)} rows → {rates.index[-1].date()} @ {latest:.3f}%")

    if not series:
        raise RuntimeError(f"No contracts fetched for {curve_key}")

    wide = pd.DataFrame(series).sort_index(axis=1)
    curve_meta = {
        **cfg,
        "contracts": contracts,
        "n_contracts": len(contracts),
        "history_start": str(wide.index.min().date()),
        "history_end": str(wide.index.max().date()),
        "n_sessions": int(len(wide)),
    }
    return curve_meta, wide, curve_months


def compute_calendar_spreads(all_wide: dict[str, pd.DataFrame]) -> dict:
    out: dict = {}
    for spread in CALENDAR_SPREADS:
        sid = spread["id"]
        back, front = spread["back"], spread["front"]
        entry: dict = {"label": spread["label"], "back_key": back, "front_key": front, "by_curve": {}}
        for curve_key, wide in all_wide.items():
            if back not in wide.columns or front not in wide.columns:
                continue
            slope = (wide[back] - wide[front]).dropna() * 100.0
            if slope.empty:
                continue
            rows = [{"date": str(dt.date()), "slope_bp": round(float(v), 2)} for dt, v in slope.items()]
            entry["by_curve"][curve_key] = {
                "label": CURVES[curve_key]["label"],
                "current_bp": round(float(slope.iloc[-1]), 2),
                "current_date": str(slope.index[-1].date()),
                "min_bp": round(float(slope.min()), 2),
                "max_bp": round(float(slope.max()), 2),
                "n_sessions": int(len(slope)),
                "start": str(slope.index.min().date()),
                "end": str(slope.index.max().date()),
                "rows": rows,
            }
        out[sid] = entry
    return out


def build_payload() -> dict:
    print("Discovering full 3M STIR chains on Barchart…")
    all_symbols: list[str] = []
    symbols_by_curve: dict[str, list[str]] = {}
    for key, cfg in CURVES.items():
        syms = discover_chain_symbols(cfg["prefix"], cfg["chain_url"])
        symbols_by_curve[key] = syms
        all_symbols.extend(syms)

    all_symbols = list(dict.fromkeys(all_symbols))
    print(f"\nBatch EOD fetch: {len(all_symbols)} contracts…")
    batch = fetch_barchart_batch(all_symbols)

    payload: dict = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart historical lastPrice (finalized EOD sessions only)",
        "quote_convention": "price = 100 − implied rate (%)",
        "curve_months": [],
        "curves": {},
        "timeseries": {},
        "current_snapshot": [],
        "discovery": {k: {"n_listed": len(v), "symbols": v} for k, v in symbols_by_curve.items()},
    }

    all_wide: dict[str, pd.DataFrame] = {}
    union_months: dict[str, dict] = {}

    for key, cfg in CURVES.items():
        print(f"\n{cfg['label']} ({cfg['prefix']}*)")
        meta, wide, months = fetch_curve(key, cfg, batch, symbols_by_curve[key])
        payload["curves"][key] = meta
        all_wide[key] = wide
        for m in months:
            union_months.setdefault(m["ym"], m)
        for c in meta["contracts"]:
            payload["current_snapshot"].append({"curve": key, "curve_label": meta["label"], **c})

    payload["curve_months"] = [
        union_months[k] for k in sorted(union_months, key=lambda x: (x[:4], x[5:]))
    ]

    overlap_idx: pd.DatetimeIndex | None = None
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

    payload["calendar_spreads"] = compute_calendar_spreads(all_wide)
    print(f"\nDone: {len(overlap_idx)} overlap sessions across curves")
    return payload


def main() -> None:
    payload = build_payload()
    out = ROOT / "stir_curves_data.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
