"""Generate presentation charts for the FFR-SOFR basis analysis from basis_data.json."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

OUT = os.environ.get("CHART_OUT", "/opt/cursor/artifacts")
os.makedirs(OUT, exist_ok=True)

d = json.load(open("/workspace/basis_data.json"))
s = d["stats"]
monthly = d["monthly"]
vals = np.array([m["v"] for m in monthly])
yms = [m["ym"] for m in monthly]
PRICED = -1.0

# Style
plt.rcParams.update({
    "figure.facecolor": "#0e1117", "axes.facecolor": "#0e1117",
    "savefig.facecolor": "#0e1117", "text.color": "#e6e6e6",
    "axes.labelcolor": "#e6e6e6", "xtick.color": "#b8b8b8", "ytick.color": "#b8b8b8",
    "axes.edgecolor": "#3a3f4b", "font.size": 12, "axes.titlesize": 14,
    "axes.grid": True, "grid.color": "#222631", "grid.linewidth": 0.8,
})
GREEN, RED, BLUE, AMBER = "#22c55e", "#ef4444", "#3b82f6", "#f59e0b"


def savefig(fig, name):
    p = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(p, dpi=140)
    plt.close(fig)
    print("wrote", p)


# 1. Distribution histogram
fig, ax = plt.subplots(figsize=(9, 5))
bins = np.arange(np.floor(vals.min()), np.ceil(vals.max()) + 1, 1.0)
ax.hist(vals, bins=bins, color=BLUE, alpha=0.75, edgecolor="#0e1117")
ax.axvline(PRICED, color=RED, lw=2.5, label=f"Priced -1bp  (~{s['percentile_rank_of_priced']:.0f}th pctile)")
ax.axvline(s["mean"], color=GREEN, lw=2, ls="--", label=f"Mean +{s['mean']:.2f}bp")
ax.axvline(s["median"], color=AMBER, lw=2, ls=":", label=f"Median +{s['median']:.2f}bp")
ax.set_title(f"Distribution of monthly-avg FFR-SOFR (EFFR-SOFR), {s['start']}\u2013{s['end']}  (n={s['n_months']})")
ax.set_xlabel("Monthly average basis (bp)")
ax.set_ylabel("Number of months")
ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6")
ax.annotate(f"~70% of months\nprinted ABOVE -1bp", xy=(PRICED, 0), xytext=(3.5, ax.get_ylim()[1]*0.7),
            color="#e6e6e6", fontsize=11, ha="left",
            arrowprops=dict(arrowstyle="->", color="#8b949e"))
savefig(fig, "chart1_distribution.png")

# 2. Time series of monthly basis
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(vals))
ax.plot(x, vals, color=BLUE, lw=1.4)
ax.fill_between(x, vals, PRICED, where=(vals >= PRICED), color=GREEN, alpha=0.18)
ax.fill_between(x, vals, PRICED, where=(vals < PRICED), color=RED, alpha=0.18)
ax.axhline(PRICED, color=RED, lw=1.8, ls="--", label="Priced -1bp")
ax.axhline(0, color="#8b949e", lw=1)
# July markers
jul_idx = [i for i, ym in enumerate(yms) if ym.endswith("-07")]
ax.scatter(jul_idx, vals[jul_idx], color=AMBER, zorder=5, s=45, label="July prints")
ticks = list(range(0, len(vals), 12))
ax.set_xticks(ticks)
ax.set_xticklabels([yms[i][:4] for i in ticks])
ax.set_title("Monthly-average FFR-SOFR basis since SOFR inception")
ax.set_ylabel("Basis (bp)")
ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6", loc="lower left")
savefig(fig, "chart2_timeseries.png")

# 3. ACF / PACF
acf = [d["acf"][f"lag_{k}"] for k in range(1, 13)]
pacf = [d["pacf"][f"lag_{k}"] for k in range(1, 13)]
ci = 1.96 / np.sqrt(s["n_months"])
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for ax, series, title in [(axes[0], acf, "Autocorrelation (ACF)"), (axes[1], pacf, "Partial autocorrelation (PACF)")]:
    lags = np.arange(1, 13)
    ax.bar(lags, series, color=BLUE, width=0.6)
    ax.axhline(ci, color=RED, ls="--", lw=1, label="95% band")
    ax.axhline(-ci, color=RED, ls="--", lw=1)
    ax.axhline(0, color="#8b949e", lw=1)
    ax.set_title(title)
    ax.set_xlabel("Lag (months)")
    ax.set_xticks(lags)
    ax.xaxis.set_minor_locator(MultipleLocator(1))
axes[0].set_ylabel("Correlation")
axes[0].legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6")
fig.suptitle(f"Persistence: AR(1) \u03b2={d['regressions']['ar1']['beta_lag1']:.2f}  |  trailing-3m \u03b2={d['regressions']['trailing3m']['beta_avg3']:.2f}",
             color="#e6e6e6", fontsize=13)
savefig(fig, "chart3_autocorr.png")

# 4. July seasonality
jy = d["july"]
fig, ax = plt.subplots(figsize=(9, 5))
colors = [GREEN if v >= PRICED else RED for v in jy["values"]]
ax.bar(jy["years"], jy["values"], color=colors, alpha=0.85)
ax.axhline(PRICED, color=RED, lw=1.8, ls="--", label="Priced -1bp")
ax.axhline(jy["mean"], color=GREEN, lw=1.8, ls=":", label=f"July mean +{jy['mean']:.2f}bp")
ax.axhline(0, color="#8b949e", lw=1)
ax.set_title("July FFR-SOFR monthly average, by year")
ax.set_ylabel("Basis (bp)")
ax.legend(facecolor="#161b22", edgecolor="#3a3f4b", labelcolor="#e6e6e6")
savefig(fig, "chart4_july.png")

print("done")
