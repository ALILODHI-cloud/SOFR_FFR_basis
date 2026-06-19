"""
1-Month SONIA Dec27–Dec26 slope monitor (UK STIR).

Fetches:
  - ICE 1M SONIA futures Dec-26 / Dec-27 settles (Barchart JUZ26 / JUZ27 via browser session)
  - Spot SONIA (Bank of England IUDSOIA)
  - Brent front-month (Yahoo BZ=F)

Computes (last ~50 business days):
  - Slope in rate space: implied_rate(Dec27) − implied_rate(Dec26), in bp
  - Rolling 30-day correlation: daily slope change vs Brent daily % return
  - Cash–futures basis: Dec26 implied rate − spot SONIA, in bp
  - Annualised stdev of daily basis changes (30-day rolling, √252)

Writes sonia_dashboard_data.json for build_sonia_dashboard.py.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

WINDOW_DAYS = 50
ROLL_CORR = 30
ROLL_VOL = 30
ANN_FACTOR = np.sqrt(252)
# Calendar-spread entry marker on dashboard (EOD settle date).
TRADE_ENTRY_DATE = "2026-06-05"
TRADE_ENTRY = {
    "date": TRADE_ENTRY_DATE,
    "short_label": "Fri 5 Jun 2026",
    "position": "Long JUZ26 / Short JUZ27 (1:1)",
}
# Latest session to include. None = today (Barchart EOD capped to feed max).
DATA_END: date | None = None
BARCHART_LIMIT = 200
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
BOE_CSV = (
    "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
    "?csv.x=yes&Datefrom={start}&Dateto={end}&SeriesCodes=IUDSOIA&UsingCodes=Y&VPD=Y"
)


def boe_date(d: date) -> str:
    return d.strftime("%d/%b/%Y")


def fetch_sonia_spot(start: date, end: date) -> pd.Series:
    url = BOE_CSV.format(start=boe_date(start), end=boe_date(end))
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    from io import StringIO

    df = pd.read_csv(StringIO(raw))
    col = [c for c in df.columns if c != "DATE"][0]
    s = pd.Series(
        {
            pd.to_datetime(r["DATE"], format="%d %b %Y"): float(r[col])
            for _, r in df.iterrows()
            if str(r["DATE"]).strip()
        },
        name="sonia_pct",
    ).sort_index()
    s.index = s.index.normalize()
    return s


def fetch_yahoo_daily(symbol: str, range_: str = "6mo") -> pd.Series:
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&range={range_}"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    res = payload["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]["close"]
    out = {}
    for t, c in zip(ts, q):
        if c is None:
            continue
        out[pd.Timestamp.fromtimestamp(t, tz="UTC").tz_convert(None).normalize()] = float(c)
    return pd.Series(out, name=symbol).sort_index()


def fetch_barchart_eod(symbol: str, limit: int = BARCHART_LIMIT) -> pd.DataFrame:
    """Pull EOD history + latest Barchart quote for one contract."""
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
        page.goto(
            f"https://www.barchart.com/futures/quotes/{symbol}",
            wait_until="networkidle",
            timeout=90_000,
        )
        quote = page.evaluate(
            """() => {
              const html = document.documentElement.innerHTML;
              const m = html.match(/"symbol":"SYMBOL"[^}]{0,800}/);
              const block = m ? m[0] : '';
              const price = block.match(/"lastPrice":([0-9.]+)/);
              const t = block.match(/"tradeTime":"([^"]+)"/);
              const session = html.match(/sessionDateDisplayLong[^A-Za-z0-9]+([A-Za-z]{3}, [^<]+)/);
              return {
                lastPrice: price ? +price[1] : null,
                tradeTime: t ? t[1] : null,
                sessionLabel: session ? session[1] : null,
              };
            }""".replace("SYMBOL", symbol)
        )
        browser.close()

    if not hist or "data" not in hist:
        raise RuntimeError(f"No Barchart history returned for {symbol}")

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

    if quote.get("lastPrice") and quote.get("tradeTime"):
        qd = pd.to_datetime(quote["tradeTime"])
        recs.append({"date": qd, "price": float(quote["lastPrice"])})

    df = pd.DataFrame(recs).drop_duplicates("date", keep="last").set_index("date").sort_index()
    df.index = df.index.normalize()
    print(
        f"  {symbol}: {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}"
        + (f" (quote session: {quote.get('sessionLabel')})" if quote.get("sessionLabel") else "")
    )
    return df


def price_to_rate(price: pd.Series) -> pd.Series:
    """ICE STIR quote: price = 100 − rate (%)."""
    return 100.0 - price


def rolling_corr(a: pd.Series, b: pd.Series, window: int) -> pd.Series:
    return a.rolling(window).corr(b)


def classify_curve_move(d26: float, d27: float, dslope: float, eps: float = 0.25) -> str:
    """Classify daily Dec26/Dec27 rate changes (bp). dslope = d27 - d26."""
    if abs(dslope) < eps:
        return "unchanged"
    if dslope > 0:  # steepening
        if d26 > eps and d27 > eps:
            return "bear_steepening"
        if d26 < -eps and d27 < -eps:
            return "bull_steepening"
        return "mixed_steepening"
    # flattening
    if d26 > eps and d27 > eps:
        return "bear_flattening"
    if d26 < -eps and d27 < -eps:
        return "bull_flattening"
    return "mixed_flattening"


def compute_trade_stats(tail: pd.DataFrame, entry_date: str) -> dict | None:
    """P&L and risk stats for Long Dec26 / Short Dec27 from entry EOD to latest."""
    GBP_PER_BP = 12.50
    FACE = 500_000.0
    GROSS = 2 * FACE
    MARGIN_RATE = 0.004
    MARGIN = GROSS * MARGIN_RATE
    RF = 0.035

    if entry_date not in tail.index.strftime("%Y-%m-%d"):
        return None

    sub = tail.loc[tail.index >= pd.Timestamp(entry_date)].copy()
    if len(sub) < 2:
        return None

    sub["d26_bp"] = sub["dec26_rate"].diff() * 100.0
    sub["d27_bp"] = sub["dec27_rate"].diff() * 100.0
    sub["dslope_bp"] = sub["slope_bp"].diff()
    sub["pnl_gbp"] = sub["dslope_bp"] * GBP_PER_BP

    entry_row = sub.iloc[0]
    exit_row = sub.iloc[-1]
    d26_tot = float(exit_row["dec26_rate"] - entry_row["dec26_rate"]) * 100.0
    d27_tot = float(exit_row["dec27_rate"] - entry_row["dec27_rate"]) * 100.0
    dslope_tot = float(exit_row["slope_bp"] - entry_row["slope_bp"])
    pnl_gbp = dslope_tot * GBP_PER_BP

    daily = sub.iloc[1:].copy()
    daily["regime"] = [
        classify_curve_move(float(a), float(b), float(c))
        for a, b, c in zip(daily["d26_bp"], daily["d27_bp"], daily["dslope_bp"])
    ]

    regimes = [
        "bear_steepening",
        "bull_steepening",
        "bear_flattening",
        "bull_flattening",
        "mixed_steepening",
        "mixed_flattening",
        "unchanged",
    ]
    regime_labels = {
        "bear_steepening": "Bear steepening",
        "bull_steepening": "Bull steepening",
        "bear_flattening": "Bear flattening",
        "bull_flattening": "Bull flattening",
        "mixed_steepening": "Mixed steepening",
        "mixed_flattening": "Mixed flattening",
        "unchanged": "Unchanged",
    }
    attribution = []
    for key in regimes:
        mask = daily["regime"] == key
        if not mask.any():
            continue
        bp = float(daily.loc[mask, "dslope_bp"].sum())
        attribution.append(
            {
                "regime": key,
                "label": regime_labels[key],
                "days": int(mask.sum()),
                "pnl_slope_bp": round(bp, 2),
                "pnl_gbp": round(bp * GBP_PER_BP, 2),
            }
        )
    attribution.sort(key=lambda x: abs(x["pnl_gbp"]), reverse=True)

    overall_regime = classify_curve_move(d26_tot, d27_tot, dslope_tot, eps=0.5)
    if dslope_tot > 0.5:
        overall_label = regime_labels.get(overall_regime, overall_regime)
    elif dslope_tot < -0.5:
        overall_label = regime_labels.get(overall_regime, overall_regime)
    else:
        overall_label = "Flat"

    rets = (daily["pnl_gbp"] / MARGIN).values
    n = len(rets)
    cal_days = (sub.index[-1] - sub.index[0]).days
    total_margin_ret = pnl_gbp / MARGIN
    cagr_margin = (1 + total_margin_ret) ** (365.25 / cal_days) - 1 if cal_days > 0 else None
    ann_ret_margin = total_margin_ret * (252 / n) if n else None
    vol_ann_margin = float(daily["pnl_gbp"].std(ddof=1) / MARGIN * np.sqrt(252)) if n > 1 else None
    sharpe = (
        (ann_ret_margin - RF) / vol_ann_margin
        if ann_ret_margin is not None and vol_ann_margin and vol_ann_margin > 0
        else None
    )

    cum = daily["pnl_gbp"].cumsum()
    max_dd = float((cum - cum.cummax()).min()) if n else 0.0

    steepening_pnl_bp = float(
        daily.loc[daily["dslope_bp"] > 0, "dslope_bp"].sum()
    ) if n else 0.0
    flattening_pnl_bp = float(
        daily.loc[daily["dslope_bp"] < 0, "dslope_bp"].sum()
    ) if n else 0.0

    def leg_detail(side: str, prefix: str, rate_chg_bp: float, spread_pnl_bp: float) -> dict:
        e_rate = float(entry_row[f"{prefix}_rate"])
        x_rate = float(exit_row[f"{prefix}_rate"])
        e_px = float(entry_row[f"{prefix}_px"])
        x_px = float(exit_row[f"{prefix}_px"])
        px_chg = x_px - e_px
        return {
            "contract": "JUZ26" if prefix == "dec26" else "JUZ27",
            "label": "Dec-26" if prefix == "dec26" else "Dec-27",
            "side": side,
            "entry_rate_pct": round(e_rate, 4),
            "exit_rate_pct": round(x_rate, 4),
            "rate_chg_bp": round(rate_chg_bp, 2),
            "entry_px": round(e_px, 4),
            "exit_px": round(x_px, 4),
            "px_chg": round(px_chg, 4),
            "price_return_pct": round(px_chg / e_px * 100, 4),
            "spread_pnl_bp": round(spread_pnl_bp, 2),
            "spread_pnl_gbp": round(spread_pnl_bp * GBP_PER_BP, 2),
        }

    trade_path = []
    for idx, r in sub.iterrows():
        trade_path.append(
            {
                "date": idx.strftime("%Y-%m-%d"),
                "dec26_rate": round(float(r["dec26_rate"]), 4),
                "dec27_rate": round(float(r["dec27_rate"]), 4),
                "slope_bp": round(float(r["slope_bp"]), 2),
                "cum_pnl_gbp": round(float((r["slope_bp"] - entry_row["slope_bp"]) * GBP_PER_BP), 2),
            }
        )

    return {
        "entry_date": entry_date,
        "exit_date": sub.index[-1].strftime("%Y-%m-%d"),
        "session_days": n,
        "calendar_days": cal_days,
        "pnl_slope_bp": round(dslope_tot, 2),
        "pnl_gbp_per_pair": round(pnl_gbp, 2),
        "return_gross_pct": round(pnl_gbp / GROSS * 100, 4),
        "return_margin_pct": round(total_margin_ret * 100, 2),
        "margin_assumed_gbp": round(MARGIN, 0),
        "cagr_margin_pct": round(cagr_margin * 100, 1) if cagr_margin is not None else None,
        "vol_ann_margin_pct": round(vol_ann_margin * 100, 1) if vol_ann_margin else None,
        "sharpe_ann": round(sharpe, 2) if sharpe is not None else None,
        "risk_free_pct": RF * 100,
        "max_drawdown_gbp": round(max_dd, 2),
        "legs": {
            "dec26": leg_detail("Long", "dec26", d26_tot, -d26_tot),
            "dec27": leg_detail("Short", "dec27", d27_tot, d27_tot),
        },
        "leg_pnl_bp": {
            "long_dec26": round(-d26_tot, 2),
            "short_dec27": round(d27_tot, 2),
        },
        "slope_reconciliation": {
            "dec27_minus_dec26_bp": round(d27_tot - d26_tot, 2),
            "entry_slope_bp": round(float(entry_row["slope_bp"]), 2),
            "exit_slope_bp": round(float(exit_row["slope_bp"]), 2),
        },
        "trade_path": trade_path,
        "overall_move": {
            "regime": overall_regime,
            "label": overall_label,
            "dec26_bp": round(d26_tot, 1),
            "dec27_bp": round(d27_tot, 1),
            "slope_bp": round(dslope_tot, 1),
        },
        "pnl_from_steepening_bp": round(steepening_pnl_bp, 2),
        "pnl_from_flattening_bp": round(flattening_pnl_bp, 2),
        "regime_attribution": attribution,
        "dominant_regime": attribution[0] if attribution else None,
    }


def main() -> dict:
    end = DATA_END or date.today()
    start = end - timedelta(days=220)

    dec26 = fetch_barchart_eod("JUZ26")
    dec27 = fetch_barchart_eod("JUZ27")
    sonia = fetch_sonia_spot(start, end + timedelta(days=5))
    brent = fetch_yahoo_daily("BZ=F", "6mo")

    dec26 = dec26.rename(columns={"price": "dec26_px"})
    dec27 = dec27.rename(columns={"price": "dec27_px"})

    df = dec26.join(dec27, how="inner")
    barchart_last = df.index.max().date()
    end = min(end, barchart_last) if DATA_END is None else end
    df = df[df.index <= pd.Timestamp(end)]
    df = df.join(sonia, how="left")
    df = df.join(brent.rename("brent"), how="left")
    df = df.dropna(subset=["dec26_px", "dec27_px"])

    # Forward-fill weekend gaps on spot / Brent onto futures dates
    df["sonia_pct"] = df["sonia_pct"].ffill()
    df["brent"] = df["brent"].ffill()
    df = df.dropna(subset=["sonia_pct", "brent"])

    df["dec26_rate"] = price_to_rate(df["dec26_px"])
    df["dec27_rate"] = price_to_rate(df["dec27_px"])
    df["slope_bp"] = (df["dec27_rate"] - df["dec26_rate"]) * 100.0
    df["basis_bp"] = (df["dec26_rate"] - df["sonia_pct"]) * 100.0

    df["slope_chg_bp"] = df["slope_bp"].diff()
    df["basis_chg_bp"] = df["basis_bp"].diff()
    df["brent_ret_pct"] = df["brent"].pct_change() * 100.0

    df["roll_corr_30"] = rolling_corr(df["slope_chg_bp"], df["brent_ret_pct"], ROLL_CORR)
    df["basis_vol_ann"] = df["basis_chg_bp"].rolling(ROLL_VOL).std() * ANN_FACTOR

    tail = df.tail(WINDOW_DAYS).copy()

    def row_dict(idx, r):
        return {
            "date": idx.strftime("%Y-%m-%d"),
            "dec26_px": round(float(r["dec26_px"]), 4),
            "dec27_px": round(float(r["dec27_px"]), 4),
            "dec26_rate": round(float(r["dec26_rate"]), 4),
            "dec27_rate": round(float(r["dec27_rate"]), 4),
            "slope_bp": round(float(r["slope_bp"]), 2),
            "basis_bp": round(float(r["basis_bp"]), 2),
            "brent": round(float(r["brent"]), 2),
            "roll_corr_30": None if pd.isna(r["roll_corr_30"]) else round(float(r["roll_corr_30"]), 3),
            "basis_vol_ann": None if pd.isna(r["basis_vol_ann"]) else round(float(r["basis_vol_ann"]), 2),
        }

    daily = [row_dict(idx, r) for idx, r in tail.iterrows()]
    last = daily[-1]

    trade_entry = dict(TRADE_ENTRY)
    entry_rows = [r for r in daily if r["date"] == TRADE_ENTRY_DATE]
    if entry_rows:
        er = entry_rows[0]
        trade_entry["slope_bp"] = er["slope_bp"]
        trade_entry["dec26_rate"] = er["dec26_rate"]
        trade_entry["dec27_rate"] = er["dec27_rate"]
        trade_entry["in_window"] = True
        trade_entry["pnl_slope_bp"] = round(last["slope_bp"] - er["slope_bp"], 2)
        stats = compute_trade_stats(tail, TRADE_ENTRY_DATE)
        if stats:
            trade_entry["stats"] = stats
    else:
        trade_entry["in_window"] = False

    summary = {
        "slope_bp": last["slope_bp"],
        "basis_bp": last["basis_bp"],
        "roll_corr_30": last["roll_corr_30"],
        "basis_vol_ann": last["basis_vol_ann"],
        "brent": last["brent"],
        "dec26_rate": last["dec26_rate"],
        "dec27_rate": last["dec27_rate"],
        "slope_mean_50d": round(float(tail["slope_bp"].mean()), 2),
        "slope_std_50d": round(float(tail["slope_bp"].std(ddof=1)), 2),
        "basis_mean_50d": round(float(tail["basis_bp"].mean()), 2),
        "n_days": len(daily),
        "start": daily[0]["date"],
        "end": daily[-1]["date"],
    }

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "definitions": {
            "slope_bp": (
                "Implied 1M SONIA rate (Dec-27) minus implied rate (Dec-26), in bp. "
                "Futures quoted 100 − rate; rates computed in % then scaled to bp."
            ),
            "basis_bp": "Dec-26 futures implied rate minus spot SONIA fixing, in bp (cash–futures basis).",
            "roll_corr_30": (
                "30-business-day rolling correlation of daily slope change (bp) "
                "vs Brent daily % return."
            ),
            "basis_vol_ann": (
                f"{ROLL_VOL}-day rolling stdev of daily basis changes (bp), annualised ×√252."
            ),
        },
        "contracts": {"dec26": "JUZ26 (ICE 1M SONIA Dec-26)", "dec27": "JUZ27 (ICE 1M SONIA Dec-27)"},
        "sources": {
            "futures": "Barchart EOD settles (ICE 1M SONIA JUZ26 / JUZ27)",
            "sonia": "Bank of England IUDSOIA",
            "brent": "Yahoo Finance BZ=F",
        },
        "data_end": barchart_last.isoformat(),
        "fetched_on": date.today().isoformat(),
        "trade_entry": trade_entry,
        "summary": summary,
        "daily": daily,
    }
    with open("sonia_dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(
        f"Wrote sonia_dashboard_data.json — {summary['n_days']} days "
        f"({summary['start']} → {summary['end']}), slope {summary['slope_bp']:+.1f}bp"
    )
    return out


if __name__ == "__main__":
    main()
