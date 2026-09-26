"""Build a monthly-returns CSV for SPY (SPDR S&P 500 ETF) over the last 20 years from Yahoo Finance.
Authentic data source: query2.finance.yahoo.com chart API (adjusted close = total return incl. dividends).
"""
import json
import urllib.request
import time
import csv
import datetime as dt
import os
import statistics as st

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
OUT_DIRS = [d for d in ["/workspace/data", os.environ.get("CSV_OUT", "/opt/cursor/artifacts")] if d]
for d in OUT_DIRS:
    os.makedirs(d, exist_ok=True)


def fetch(symbol, interval="1mo", rng="21y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("retry", symbol, attempt, e)
            time.sleep(3)
    raise SystemExit("fetch failed " + symbol)


j = fetch("SPY")
res = j["chart"]["result"][0]
ts = res["timestamp"]
adj = res["indicators"]["adjclose"][0]["adjclose"]
close = res["indicators"]["quote"][0]["close"]

now = dt.datetime.now(dt.timezone.utc)
rows = []
for t, a, c in zip(ts, adj, close):
    if a is None:
        continue
    d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    rows.append((d, a, c))

# de-dup to one row per calendar month (keep last), sort
by_month = {}
for d, a, c in rows:
    by_month[(d.year, d.month)] = (d, a, c)
items = [by_month[k] for k in sorted(by_month)]

# keep last 241 month-ends so we get 240 monthly returns (20y)
items = items[-241:]

out_name = "SPY_monthly_returns_20y.csv"
last_idx = len(items) - 1
for out_dir in OUT_DIRS:
    out_path = os.path.join(out_dir, out_name)
    prev_adj = None
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "adj_close", "close", "monthly_return_pct", "is_partial_month"])
        for i, (d, a, c) in enumerate(items):
            ret = "" if prev_adj is None else round((a / prev_adj - 1) * 100, 4)
            partial = "yes" if (i == last_idx and d.year == now.year and d.month == now.month) else "no"
            w.writerow([d.strftime("%Y-%m"), round(a, 4), round(c, 4) if c else "", ret, partial])
            prev_adj = a
    print(f"Wrote {out_path}")

# quick summary (exclude the partial current month for clean stats)
complete = items[:-1] if (items[-1][0].year == now.year and items[-1][0].month == now.month) else items
returns = []
prev = None
for d, a, c in complete:
    if prev is not None:
        returns.append(a / prev - 1)
    prev = a
n = len(returns)
ann = (st.mean(returns) * 12) * 100
vol = (st.pstdev(returns) * (12 ** 0.5)) * 100
pos = sum(1 for r in returns if r > 0)
print(f"Rows (month-ends): {len(items)}  | monthly returns: {n}")
print(f"Period: {items[0][0].strftime('%Y-%m')} -> {items[-1][0].strftime('%Y-%m')}")
print(f"Avg monthly: {st.mean(returns)*100:.2f}%  | median: {st.median(returns)*100:.2f}%")
print(f"Annualized (avg*12) ~{ann:.1f}%  | ann vol ~{vol:.1f}%  | positive months: {pos}/{n} ({pos/n*100:.0f}%)")
print(f"Best: {max(returns)*100:.2f}%  Worst: {min(returns)*100:.2f}%")
