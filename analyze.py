"""
FFR - SOFR basis: monthly-average distribution + autocorrelation analysis.
Data: FRED (no API key needed via fredgraph.csv).
  EFFR = Effective Federal Funds Rate (daily)   -> FRED series 'EFFR'
  SOFR = Secured Overnight Financing Rate (daily)-> FRED series 'SOFR'
Basis (bp) = (EFFR - SOFR) * 100  == Barclays "SOFR/FF" (FF - SOFR) convention.
"""
import json
import numpy as np
import pandas as pd
import requests

# NY Fed reference-rate API (FRED mirrors these exact series; NY Fed is the source).
NYFED = "https://markets.newyorkfed.org/api/rates/{group}/{rate}/search.json?startDate=2018-04-01&endDate=2026-12-31"
PRICED = -1.0  # current market price for July FFR-SOFR (Barclays "entry -1.0bp")
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(name, group, rate):
    url = NYFED.format(group=group, rate=rate)
    r = requests.get(url, timeout=60, headers=HEADERS)
    r.raise_for_status()
    rows = r.json()["refRates"]
    s = pd.Series(
        {pd.to_datetime(d["effectiveDate"]): float(d["percentRate"]) for d in rows},
        name=name,
    ).sort_index()
    return s


def main():
    effr = fetch("EFFR", "unsecured", "effr")
    sofr = fetch("SOFR", "secured", "sofr")

    df = pd.concat([effr, sofr], axis=1).dropna()
    df = df[df.index >= "2018-04-03"]  # SOFR inception
    df["basis_bp"] = (df["EFFR"] - df["SOFR"]) * 100.0

    # Monthly averages (calendar month mean of daily basis)
    m = df["basis_bp"].resample("MS").mean().dropna()
    m_df = m.to_frame("basis_bp")
    m_df["ym"] = m_df.index.strftime("%Y-%m")
    monthly = list(zip(m_df["ym"], m_df["basis_bp"].round(3)))

    arr = m.values.astype(float)
    n = len(arr)

    # ---- Distribution stats ----
    pct_below_minus1 = float((arr < PRICED).mean() * 100)
    pct_at_or_below = float((arr <= PRICED).mean() * 100)
    # percentile rank of -1 (interpolated)
    rank = float((np.sum(arr < PRICED) + 0.5 * np.sum(arr == PRICED)) / n * 100)
    stats = {
        "n_months": int(n),
        "start": m_df["ym"].iloc[0],
        "end": m_df["ym"].iloc[-1],
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p05": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "priced": PRICED,
        "pct_months_below_priced": pct_below_minus1,
        "percentile_rank_of_priced": rank,
        "current_month_basis": float(arr[-1]),
        "last3m_avg": float(np.mean(arr[-3:])),
    }

    # ---- Histogram (1bp bins) ----
    lo = np.floor(arr.min())
    hi = np.ceil(arr.max())
    bins = np.arange(lo, hi + 1.0, 1.0)
    counts, edges = np.histogram(arr, bins=bins)
    hist = [{"bin_lo": float(edges[i]), "bin_hi": float(edges[i + 1]), "count": int(counts[i])}
            for i in range(len(counts))]

    # ---- Autocorrelation ----
    def acf(x, lag):
        x = np.asarray(x, float)
        x = x - x.mean()
        denom = np.sum(x * x)
        return float(np.sum(x[:-lag] * x[lag:]) / denom) if lag > 0 else 1.0

    acfs = {f"lag_{k}": acf(arr, k) for k in range(1, 13)}

    # Partial autocorrelation via Durbin-Levinson
    def pacf(x, nlags):
        r = [acf(x, k) for k in range(0, nlags + 1)]
        phi = np.zeros((nlags + 1, nlags + 1))
        pac = [1.0]
        phi[1, 1] = r[1]
        pac.append(r[1])
        for k in range(2, nlags + 1):
            num = r[k] - sum(phi[k - 1, j] * r[k - j] for j in range(1, k))
            den = 1 - sum(phi[k - 1, j] * r[j] for j in range(1, k))
            phi[k, k] = num / den
            for j in range(1, k):
                phi[k, j] = phi[k - 1, j] - phi[k, k] * phi[k - 1, k - j]
            pac.append(float(phi[k, k]))
        return pac[1:]

    pac = pacf(arr, 12)
    pacfs = {f"lag_{k+1}": float(pac[k]) for k in range(len(pac))}

    # ---- Predictive regressions ----
    def ols(y, X):
        y = np.asarray(y, float)
        X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ beta
        resid = y - yhat
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot
        dof = len(y) - X.shape[1]
        sigma2 = ss_res / dof
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
        tstat = beta / se
        return beta, se, tstat, r2, len(y)

    # (a) AR(1): month_t on month_{t-1}
    y1 = arr[1:]
    x1 = arr[:-1]
    b1, se1, t1, r2_1, n1 = ols(y1, [x1])

    # (b) month_t on trailing 3-month average (t-1,t-2,t-3)
    roll3 = pd.Series(arr).rolling(3).mean().values  # avg of t-2..t (incl t)
    # trailing prior 3 months avg predicting t:
    prior3 = pd.Series(arr).shift(1).rolling(3).mean().values  # avg of t-1,t-2,t-3
    mask = ~np.isnan(prior3)
    yb = arr[mask]
    xb = prior3[mask]
    b3, se3, t3, r2_3, n3 = ols(yb, [xb])

    regressions = {
        "ar1": {"const": b1[0], "beta_lag1": b1[1], "t_lag1": t1[1], "r2": r2_1, "n": n1},
        "trailing3m": {"const": b3[0], "beta_avg3": b3[1], "t_avg3": t3[1], "r2": r2_3, "n": n3},
    }

    # ---- July seasonality ----
    jul = m[m.index.month == 7]
    july = {"years": [d.strftime("%Y") for d in jul.index],
            "values": [round(float(v), 3) for v in jul.values],
            "mean": float(jul.mean()), "median": float(jul.median())}

    # ---- recent 24m series for app ----
    recent = [{"ym": ym, "v": float(v)} for ym, v in monthly[-36:]]

    out = {
        "generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "definition": "basis_bp = (EFFR - SOFR) * 100  (FFR minus SOFR, Barclays SOFR/FF convention)",
        "stats": stats,
        "histogram": hist,
        "monthly": [{"ym": ym, "v": float(v)} for ym, v in monthly],
        "recent": recent,
        "acf": acfs,
        "pacf": pacfs,
        "regressions": regressions,
        "july": july,
        "last_daily": {
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "EFFR": float(df["EFFR"].iloc[-1]),
            "SOFR": float(df["SOFR"].iloc[-1]),
            "basis_bp": float(df["basis_bp"].iloc[-1]),
        },
    }

    with open("basis_data.json", "w") as f:
        json.dump(out, f, indent=2)

    # console summary
    print(f"Months: {n} ({stats['start']} -> {stats['end']})")
    print(f"Mean={stats['mean']:.2f}bp  Median={stats['median']:.2f}bp  Std={stats['std']:.2f}bp")
    print(f"Min={stats['min']:.2f}  Max={stats['max']:.2f}  P05={stats['p05']:.2f}  P95={stats['p95']:.2f}")
    print(f"Priced={PRICED}bp -> percentile rank {rank:.1f}%  ({pct_below_minus1:.1f}% of months below)")
    print(f"AR(1) beta={b1[1]:.3f} (t={t1[1]:.2f}) R2={r2_1:.3f}")
    print(f"Trailing-3m beta={b3[1]:.3f} (t={t3[1]:.2f}) R2={r2_3:.3f}")
    print(f"ACF lag1={acfs['lag_1']:.3f} lag2={acfs['lag_2']:.3f} lag3={acfs['lag_3']:.3f}")
    print(f"PACF lag1={pacfs['lag_1']:.3f} lag2={pacfs['lag_2']:.3f} lag3={pacfs['lag_3']:.3f}")
    print(f"July mean={july['mean']:.2f}bp values={list(zip(july['years'], july['values']))}")
    print(f"Last daily {out['last_daily']}")


if __name__ == "__main__":
    main()
