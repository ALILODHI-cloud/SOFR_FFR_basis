"""Build a monthly-returns CSV for the MSCI AC Asia (ex-Japan) ETF proxy, AAXJ, from Yahoo Finance.
Authentic data source: query2.finance.yahoo.com chart API (adjusted close = total return).
"""
import json
import csv
import datetime as dt
import os

OUT_DIR = os.environ.get("CSV_OUT", "/opt/cursor/artifacts")
os.makedirs(OUT_DIR, exist_ok=True)

with open("/workspace/aaxj.json") as f:
    j = json.load(f)

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

# keep last 121 month-ends so we get 120 monthly returns (10y)
items = items[-121:]

out_path = os.path.join(OUT_DIR, "MSCI_AC_Asia_exJapan_AAXJ_monthly_returns_10y.csv")
prev_adj = None
last_idx = len(items) - 1
with open(out_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["month", "adj_close", "close", "monthly_return_pct", "is_partial_month"])
    for i, (d, a, c) in enumerate(items):
        ret = "" if prev_adj is None else round((a / prev_adj - 1) * 100, 4)
        # the final bar is partial if its month/year equals the current month/year
        partial = "yes" if (i == last_idx and d.year == now.year and d.month == now.month) else "no"
        w.writerow([d.strftime("%Y-%m"), round(a, 4), round(c, 4) if c else "", ret, partial])
        prev_adj = a

# quick summary (exclude the partial current month for clean stats)
complete = items[:-1] if (items[-1][0].year == now.year and items[-1][0].month == now.month) else items
returns = []
prev = None
for d, a, c in complete:
    if prev is not None:
        returns.append(a / prev - 1)
    prev = a
import statistics as st
n = len(returns)
ann = (st.mean(returns) * 12) * 100
vol = (st.pstdev(returns) * (12 ** 0.5)) * 100
print(f"Wrote {out_path}")
print(f"Rows (month-ends): {len(items)}  | monthly returns: {n}")
print(f"Period: {items[0][0].strftime('%Y-%m')} -> {items[-1][0].strftime('%Y-%m')}")
print(f"Avg monthly: {st.mean(returns)*100:.2f}%  | annualized ~{ann:.1f}%  | ann vol ~{vol:.1f}%")
print(f"Best: {max(returns)*100:.2f}%  Worst: {min(returns)*100:.2f}%")
