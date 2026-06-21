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
            "slope_chg_bp": None
            if pd.isna(r["slope_chg_bp"])
            else round(float(r["slope_chg_bp"]), 2),
            "basis_bp": round(float(r["basis_bp"]), 2),
            "brent": round(float(r["brent"]), 2),
            "roll_corr_30": None if pd.isna(r["roll_corr_30"]) else round(float(r["roll_corr_30"]), 3),
            "basis_vol_ann": None if pd.isna(r["basis_vol_ann"]) else round(float(r["basis_vol_ann"]), 2),
        }

    daily = [row_dict(idx, r) for idx, r in tail.iterrows()]
    last = daily[-1]

    chg = tail["slope_chg_bp"].dropna()
    abs_chg = chg.abs()
    latest_chg = tail["slope_chg_bp"].iloc[-1]
    top_moves = []
    moves_df = tail.dropna(subset=["slope_chg_bp"]).copy()
    moves_df["abs_chg"] = moves_df["slope_chg_bp"].abs()
    for idx, r in moves_df.nlargest(5, "abs_chg").iterrows():
        top_moves.append(
            {
                "date": idx.strftime("%Y-%m-%d"),
                "slope_chg_bp": round(float(r["slope_chg_bp"]), 2),
                "slope_bp": round(float(r["slope_bp"]), 2),
            }
        )

    summary = {
        "slope_bp": last["slope_bp"],
        "slope_chg_bp": None if pd.isna(latest_chg) else round(float(latest_chg), 2),
        "slope_chg_rank": None
        if pd.isna(latest_chg)
        else int((abs_chg >= abs(float(latest_chg))).sum()),
        "slope_chg_n": int(len(chg)),
        "slope_chg_mean_50d": round(float(chg.mean()), 2),
        "slope_chg_std_50d": round(float(chg.std(ddof=1)), 2) if len(chg) > 1 else None,
        "slope_chg_p90_abs": round(float(abs_chg.quantile(0.9)), 2) if len(chg) else None,
        "top_slope_moves": top_moves,
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
            "slope_chg_bp": (
                "Day-over-day change in the Dec27−Dec26 slope (bp). "
                "Large moves are highlighted vs the 50-session window."
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
