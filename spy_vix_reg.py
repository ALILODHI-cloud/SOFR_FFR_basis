"""Regression of SPY daily change on VIX daily change. Data: Yahoo Finance daily, ~10y."""
import json, urllib.request, time, os, datetime as dt
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
OUT = "/opt/cursor/artifacts"
os.makedirs(OUT, exist_ok=True)

def fetch(symbol, rng="10y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={rng}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.load(r)
            res = j["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]["close"]
            adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q)
            out = {}
            for t, a, c in zip(ts, adj, q):
                val = a if a is not None else c
                if val is None:
                    continue
                out[dt.datetime.utcfromtimestamp(t).date()] = val  # key by calendar date
            return out
        except Exception as e:
            print("retry", symbol, attempt, e); time.sleep(3)
    raise SystemExit("fetch failed " + symbol)

spy = fetch("SPY")
vix = fetch("%5EVIX")
dates = sorted(set(spy) & set(vix))
S = np.array([spy[t] for t in dates], float)
V = np.array([vix[t] for t in dates], float)

spy_ret = np.diff(S) / S[:-1] * 100.0          # SPY daily % return
dvix_pts = np.diff(V)                            # VIX daily change (points)
dvix_pct = np.diff(V) / V[:-1] * 100.0           # VIX daily % change

def reg(y, x, label, xunit):
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta; e = y - yhat
    n, k = X.shape
    s2 = (e @ e) / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    r2 = 1 - (e @ e) / np.sum((y - y.mean()) ** 2)
    corr = np.corrcoef(x, y)[0, 1]
    print(f"\n=== {label} (n={n}) ===")
    print(f"  alpha = {beta[0]:+.4f}  (t={beta[0]/se[0]:.2f})")
    print(f"  beta  = {beta[1]:+.4f} % per {xunit}  (t={beta[1]/se[1]:.2f})")
    print(f"  R^2   = {r2:.3f}   corr = {corr:.3f}")
    return beta, r2, corr

print(f"Period: {dates[0]} -> {dates[-1]}  ({len(dates)} trading days)")
b1, r2_1, c1 = reg(spy_ret, dvix_pts, "SPY daily % return  ON  VIX daily change (points)", "+1 VIX pt")
b2, r2_2, c2 = reg(spy_ret, dvix_pct, "SPY daily % return  ON  VIX daily % change", "+1% VIX")

# scatter + fit for the primary (points) spec
plt.rcParams.update({"figure.facecolor": "#0e1117", "axes.facecolor": "#0e1117",
    "savefig.facecolor": "#0e1117", "text.color": "#e6e6e6", "axes.labelcolor": "#e6e6e6",
    "xtick.color": "#b8b8b8", "ytick.color": "#b8b8b8", "axes.edgecolor": "#3a3f4b",
    "axes.grid": True, "grid.color": "#222631"})
fig, ax = plt.subplots(figsize=(9, 6))
ax.scatter(dvix_pts, spy_ret, s=7, alpha=0.35, color="#3b82f6")
xs = np.linspace(dvix_pts.min(), dvix_pts.max(), 100)
ax.plot(xs, b1[0] + b1[1] * xs, color="#ef4444", lw=2.5,
        label=f"SPY% = {b1[0]:+.3f} {b1[1]:+.3f}·ΔVIX\nR²={r2_1:.2f}, corr={c1:.2f}, n={len(spy_ret)}")
ax.axhline(0, color="#8b949e", lw=0.8); ax.axvline(0, color="#8b949e", lw=0.8)
ax.set_xlabel("VIX daily change (points)"); ax.set_ylabel("SPY daily return (%)")
ax.set_title(f"SPY daily return vs VIX daily change ({dates[0].year}–{dates[-1].year})")
ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "spy_vix_scatter.png"), dpi=140)
print("\nwrote", os.path.join(OUT, "spy_vix_scatter.png"))

# write tidy CSV
import csv
with open(os.path.join(OUT, "spy_vix_daily_changes.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "spy_close", "vix_close", "spy_ret_pct", "vix_chg_pts", "vix_chg_pct"])
    for i in range(len(spy_ret)):
        w.writerow([dates[i+1], round(S[i+1],4), round(V[i+1],4),
                    round(spy_ret[i],4), round(dvix_pts[i],4), round(dvix_pct[i],4)])
print("wrote", os.path.join(OUT, "spy_vix_daily_changes.csv"))
