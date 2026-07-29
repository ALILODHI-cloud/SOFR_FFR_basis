"""Build combined 1M ESTR + 1M SONIA dashboard in vs-policy (bp) space."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with (ROOT / "estr_1m_data.json").open(encoding="utf-8") as f:
    estr = json.load(f)
with (ROOT / "sonia_1m_data.json").open(encoding="utf-8") as f:
    sonia = json.load(f)

deposit = float(estr["deposit_facility_pct"])
bank = float(sonia["bank_rate_pct"])

estr_map = {c["key"]: c for c in estr["contracts"]}
sonia_map = {c["key"]: c for c in sonia["contracts"]}
common_keys = sorted(set(estr_map) & set(sonia_map))


def vs_policy_bp(implied_pct: float, policy_pct: float) -> float:
    return round((implied_pct - policy_pct) * 100, 1)


basis_strip = []
for k in common_keys:
    e = estr_map[k]
    s = sonia_map[k]
    estr_vs = e.get("vs_deposit_bp")
    if estr_vs is None:
        estr_vs = vs_policy_bp(e["implied_rate_pct"], deposit)
    sonia_vs = s.get("vs_bank_bp")
    if sonia_vs is None:
        sonia_vs = vs_policy_bp(s["implied_rate_pct"], bank)
    # Relative pricing: how much more/less ESTR has priced vs its policy
    # compared with SONIA vs Bank Rate.
    relative_bp = round(float(estr_vs) - float(sonia_vs), 1)
    basis_strip.append({
        "key": k,
        "label": e["label"],
        "estr_symbol": e["symbol"],
        "sonia_symbol": s["symbol"],
        "estr_pct": e["implied_rate_pct"],
        "sonia_pct": s["implied_rate_pct"],
        "estr_vs_policy_bp": float(estr_vs),
        "sonia_vs_policy_bp": float(sonia_vs),
        "relative_bp": relative_bp,  # (ESTR−deposit) − (SONIA−Bank Rate)
        "estr_date": e["latest_date"],
        "sonia_date": s["latest_date"],
    })

estr_ts = {row["date"]: row for row in estr.get("timeseries", {}).get("rows", [])}
sonia_ts = {row["date"]: row for row in sonia.get("timeseries", {}).get("rows", [])}
common_dates = sorted(set(estr_ts) & set(sonia_ts))

basis_history: dict[str, list[dict]] = {k: [] for k in common_keys}
for dt in common_dates:
    er, sr = estr_ts[dt], sonia_ts[dt]
    for k in common_keys:
        if k in er and k in sr:
            e_vs = vs_policy_bp(er[k], deposit)
            s_vs = vs_policy_bp(sr[k], bank)
            basis_history[k].append({
                "date": dt,
                "estr_pct": er[k],
                "sonia_pct": sr[k],
                "estr_vs_policy_bp": e_vs,
                "sonia_vs_policy_bp": s_vs,
                "relative_bp": round(e_vs - s_vs, 1),
            })

estr_hist = {h["date"]: h for h in (estr.get("curve_evolution") or {}).get("history", [])}
sonia_hist = {h["date"]: h for h in (sonia.get("curve_evolution") or {}).get("history", [])}
evo_dates = sorted(set(estr_hist) & set(sonia_hist))
curve_evolution = []
for dt in evo_dates:
    ep = {p["key"]: p for p in estr_hist[dt]["points"]}
    sp = {p["key"]: p for p in sonia_hist[dt]["points"]}
    keys = sorted(set(ep) & set(sp))
    if not keys:
        continue
    pts = []
    for k in keys:
        e_imp = ep[k]["implied_rate_pct"]
        s_imp = sp[k]["implied_rate_pct"]
        e_vs = ep[k].get("vs_deposit_bp")
        if e_vs is None:
            e_vs = vs_policy_bp(e_imp, deposit)
        s_vs = sp[k].get("vs_bank_bp")
        if s_vs is None:
            s_vs = vs_policy_bp(s_imp, bank)
        pts.append({
            "key": k,
            "label": ep[k]["label"],
            "estr_pct": e_imp,
            "sonia_pct": s_imp,
            "estr_vs_policy_bp": float(e_vs),
            "sonia_vs_policy_bp": float(s_vs),
            "relative_bp": round(float(e_vs) - float(s_vs), 1),
        })
    curve_evolution.append({"date": dt, "points": pts})

payload = {
    "generated_utc": max(
        estr.get("generated_utc", ""),
        sonia.get("generated_utc", ""),
    ),
    "estr_as_of": max((c["latest_date"] for c in estr["contracts"]), default=None),
    "sonia_as_of": max((c["latest_date"] for c in sonia["contracts"]), default=None),
    "deposit_facility_pct": deposit,
    "bank_rate_pct": bank,
    "unit": "bp_vs_policy",
    "estr_contracts": estr["contracts"],
    "sonia_contracts": sonia["contracts"],
    "common_keys": common_keys,
    "basis_strip": basis_strip,
    "basis_history": basis_history,
    "curve_evolution": curve_evolution,
    "note": (
        f"All levels vs current policy: ECB deposit {deposit:.2f}% and BoE Bank Rate {bank:.2f}%. "
        "Curve points = implied − policy (bp). "
        "Relative = (ESTR − deposit) − (SONIA − Bank Rate) in bp — how much more/less "
        "the €STR strip has priced vs ECB policy than SONIA has vs Bank Rate."
    ),
}

DATA_JSON = json.dumps(payload)
(ROOT / "estr_sonia_1m_data.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>1M ESTR vs SONIA · bp vs policy</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--estr:#ffb84a;--sonia:#4aa8ff;--basis:#c084fc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill.estr{border-color:var(--estr);color:var(--estr)}
.pill.sonia{border-color:var(--sonia);color:var(--sonia)}
.pill.basis{border-color:var(--basis);color:var(--basis)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.chartbox{position:relative;height:380px}
.chartbox.sm{height:260px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .k{font-size:11px;color:var(--mut)}
.kpi .v{font-size:17px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;margin-bottom:12px}
.controls label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.controls select{background:#1b2536;border:1px solid var(--line);color:var(--ink);padding:8px 10px;border-radius:8px;font-size:14px;min-width:140px}
.sliderrow{display:flex;align-items:center;gap:12px;margin:12px 0 4px;flex-wrap:wrap}
.sliderrow input[type=range]{flex:1;min-width:120px;accent-color:var(--estr)}
.sliderdate{font-size:13px;min-width:100px;font-variant-numeric:tabular-nums}
.btn{background:#1b2536;border:1px solid var(--line);color:var(--ink);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:12px}
.btn:hover{border-color:var(--acc)}
.tblwrap{overflow:auto;max-height:420px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut);font-weight:500;font-size:11px;text-transform:uppercase}
tr.sel td{background:rgba(192,132,252,.08)}
.pos{color:var(--acc)}.neg{color:#f87171}
.foot{color:var(--mut);font-size:12px;margin-top:16px;line-height:1.6}
a{color:var(--sonia);text-decoration:none}
@media(max-width:720px){.chartbox{height:300px}.chartbox.sm{height:220px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p style="margin:0 0 10px;font-size:13px"><a href="portal.html" style="color:#93a1b5">← Markets portal</a>
    · <a href="estr_1m_dashboard.html" style="color:#93a1b5">1M €STR</a>
    · <a href="sonia_1m_dashboard.html" style="color:#93a1b5">1M SONIA</a></p>
  <h1>1M ESTR vs SONIA · bp vs policy</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill estr">■ ESTR − ECB deposit</span>
    <span class="pill sonia">■ SONIA − Bank Rate</span>
    <span class="pill basis">■ Relative = ESTR gap − SONIA gap</span>
  </div>
</header>

<div class="kpis" id="kpis"></div>

<div class="card">
  <h2>Priced change vs current policy (bp)</h2>
  <p class="hint">Each curve is implied rate minus its own current policy rate. Zero = priced at policy. Scrub shared history.</p>
  <div class="chartbox"><canvas id="curveChart"></canvas></div>
  <div class="sliderrow">
    <button class="btn" type="button" id="btnLatest">Latest</button>
    <input type="range" id="evoSlider" min="0" max="0" value="0"/>
    <span class="sliderdate" id="evoDate">—</span>
  </div>
</div>

<div class="card">
  <h2>Relative strip: (ESTR−deposit) − (SONIA−Bank Rate)</h2>
  <p class="hint" id="basisNote"></p>
  <div class="chartbox sm"><canvas id="basisStripChart"></canvas></div>
</div>

<div class="card">
  <h2>Pick a pair</h2>
  <p class="hint">Any overlapping month. Shows each leg’s bp vs its policy, then the relative gap. Optional second month = calendar of that relative.</p>
  <div class="controls">
    <label>Month
      <select id="pairSelect"></select>
    </label>
    <label>Compare to (optional calendar)
      <select id="pairSelect2"><option value="">— none —</option></select>
    </label>
  </div>
  <div class="kpis" id="pairKpis"></div>
  <div class="chartbox sm"><canvas id="pairHistChart"></canvas></div>
</div>

<div class="card">
  <h2>Full overlapping strip (vs policy)</h2>
  <div class="tblwrap">
    <table>
      <thead><tr>
        <th>Month</th><th>ESTR</th><th>SONIA</th>
        <th class="num">ESTR vs dep</th><th class="num">SONIA vs BR</th>
        <th class="num">Relative</th>
      </tr></thead>
      <tbody id="stripRows"></tbody>
    </table>
  </div>
</div>

<p class="foot">Barchart finalized EOD · Gaps use current ECB deposit and BoE Bank Rate for all history · Not investment advice.</p>
</div>
<script>
const DATA = __DATA_JSON__;
const strip = DATA.basis_strip || [];
const evo = DATA.curve_evolution || [];
const hist = DATA.basis_history || {};
const deposit = DATA.deposit_facility_pct;
const bank = DATA.bank_rate_pct;

document.getElementById('asof').textContent =
  `ESTR as of ${DATA.estr_as_of || '—'} · SONIA as of ${DATA.sonia_as_of || '—'} · dep ${Number(deposit).toFixed(2)}% · Bank Rate ${Number(bank).toFixed(2)}% · ${DATA.generated_utc || ''}`;
document.getElementById('basisNote').textContent = DATA.note || '';

const front = strip[0];
const mid = strip.find(r => r.label === 'Dec-26') || strip[Math.floor(strip.length/2)];
const back = strip[strip.length-1];
document.getElementById('kpis').innerHTML = [
  ['ECB deposit', `${Number(deposit).toFixed(2)}%`],
  ['BoE Bank Rate', `${Number(bank).toFixed(2)}%`],
  ['Front relative', front ? `${front.label} · ${fmtBp(front.relative_bp)}` : '—'],
  ['Dec-26 relative', mid ? `${fmtBp(mid.relative_bp)}` : '—'],
  ['Far relative', back ? `${back.label} · ${fmtBp(back.relative_bp)}` : '—'],
].map(([k,v]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');

function fmtBp(x){
  if (x == null || Number.isNaN(x)) return '—';
  const n = Number(x);
  return (n > 0 ? '+' : '') + n.toFixed(1) + ' bp';
}
function clsBp(x){ return x > 0 ? 'pos' : x < 0 ? 'neg' : ''; }

let evoIdx = Math.max(0, evo.length - 1);
const slider = document.getElementById('evoSlider');
slider.max = Math.max(0, evo.length - 1);
slider.value = evoIdx;

function evoPoints(){
  if (!evo.length) {
    return strip.map(r => ({
      key:r.key,label:r.label,
      estr_vs_policy_bp:r.estr_vs_policy_bp,
      sonia_vs_policy_bp:r.sonia_vs_policy_bp,
      relative_bp:r.relative_bp
    }));
  }
  return evo[evoIdx].points;
}

const frozen = strip.map(r => ({...r}));

const curveChart = new Chart(document.getElementById('curveChart'), {
  type: 'line',
  data: {
    labels: frozen.map(p => p.label),
    datasets: [
      { label: 'ESTR vs deposit (frozen)', data: frozen.map(p => p.estr_vs_policy_bp), borderColor: '#ffb84a', fill: false, tension: 0.15, pointRadius: 3, borderWidth: 2 },
      { label: 'SONIA vs Bank Rate (frozen)', data: frozen.map(p => p.sonia_vs_policy_bp), borderColor: '#4aa8ff', fill: false, tension: 0.15, pointRadius: 3, borderWidth: 2 },
      { label: 'ESTR hist', data: frozen.map(p => p.estr_vs_policy_bp), borderColor: 'rgba(255,184,74,0.55)', borderDash: [5,4], fill: false, tension: 0.15, pointRadius: 2, borderWidth: 2 },
      { label: 'SONIA hist', data: frozen.map(p => p.sonia_vs_policy_bp), borderColor: 'rgba(74,168,255,0.55)', borderDash: [5,4], fill: false, tension: 0.15, pointRadius: 2, borderWidth: 2 },
      { label: 'Policy (0)', data: frozen.map(() => 0), borderColor: '#64748b', borderDash: [2,3], pointRadius: 0, borderWidth: 1, fill: false },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { labels: { color: '#93a1b5' } } },
    scales: {
      x: { ticks: { color: '#93a1b5', maxRotation: 55 }, grid: { color: '#243043' } },
      y: { ticks: { color: '#93a1b5' }, grid: { color: '#243043' }, title: { display: true, text: 'bp vs policy', color: '#93a1b5' } }
    }
  }
});

function refreshCurve(){
  const pts = evoPoints();
  const hmap = Object.fromEntries(pts.map(p => [p.key, p]));
  curveChart.data.labels = frozen.map(p => p.label);
  curveChart.data.datasets[0].data = frozen.map(p => p.estr_vs_policy_bp);
  curveChart.data.datasets[1].data = frozen.map(p => p.sonia_vs_policy_bp);
  curveChart.data.datasets[2].data = frozen.map(p => hmap[p.key]?.estr_vs_policy_bp ?? null);
  curveChart.data.datasets[3].data = frozen.map(p => hmap[p.key]?.sonia_vs_policy_bp ?? null);
  curveChart.data.datasets[4].data = frozen.map(() => 0);
  curveChart.update('none');
  document.getElementById('evoDate').textContent = evo.length ? evo[evoIdx].date : (DATA.estr_as_of || 'latest');

  basisStripChart.data.labels = frozen.map(p => p.label);
  basisStripChart.data.datasets[0].data = frozen.map(p => hmap[p.key]?.relative_bp ?? p.relative_bp);
  basisStripChart.update('none');
}

const basisStripChart = new Chart(document.getElementById('basisStripChart'), {
  type: 'line',
  data: {
    labels: frozen.map(p => p.label),
    datasets: [{
      label: 'Relative (bp)',
      data: frozen.map(p => p.relative_bp),
      borderColor: '#c084fc',
      backgroundColor: 'rgba(192,132,252,0.12)',
      fill: true,
      tension: 0.15,
      pointRadius: 3,
      pointBackgroundColor: '#c084fc',
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#93a1b5', maxRotation: 55 }, grid: { color: '#243043' } },
      y: { ticks: { color: '#93a1b5' }, grid: { color: '#243043' }, title: { display: true, text: 'bp', color: '#93a1b5' } }
    }
  }
});

slider.addEventListener('input', () => { evoIdx = Number(slider.value); refreshCurve(); });
document.getElementById('btnLatest').onclick = () => {
  evoIdx = Math.max(0, evo.length - 1);
  slider.value = evoIdx;
  refreshCurve();
};

const sel = document.getElementById('pairSelect');
const sel2 = document.getElementById('pairSelect2');
strip.forEach(r => {
  const o = document.createElement('option');
  o.value = r.key; o.textContent = `${r.label} · ${r.estr_symbol}/${r.sonia_symbol}`;
  sel.appendChild(o);
  const o2 = document.createElement('option');
  o2.value = r.key; o2.textContent = r.label;
  sel2.appendChild(o2);
});
const defaultKey = strip.find(r => r.label === 'Dec-26')?.key || strip[0]?.key;
if (defaultKey) sel.value = defaultKey;

const pairHistChart = new Chart(document.getElementById('pairHistChart'), {
  type: 'line',
  data: { labels: [], datasets: [] },
  options: {
    responsive: true, maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { labels: { color: '#93a1b5' } } },
    scales: {
      x: { ticks: { color: '#93a1b5', maxTicksLimit: 10 }, grid: { color: '#243043' } },
      y: { ticks: { color: '#93a1b5' }, grid: { color: '#243043' }, title: { display: true, text: 'bp', color: '#93a1b5' } }
    }
  }
});

function refreshPair(){
  const k = sel.value;
  const k2 = sel2.value;
  const row = strip.find(r => r.key === k);
  const row2 = k2 ? strip.find(r => r.key === k2) : null;
  const series = hist[k] || [];
  const series2 = k2 ? (hist[k2] || []) : [];

  const latest = series.length ? series[series.length - 1] : null;
  const first = series.length ? series[0] : null;
  const chg = latest && first ? latest.relative_bp - first.relative_bp : null;
  const cal = row && row2 ? row2.relative_bp - row.relative_bp : null;

  document.getElementById('pairKpis').innerHTML = [
    ['Selected', row ? row.label : '—'],
    [`ESTR vs dep ${Number(deposit).toFixed(2)}%`, row ? fmtBp(row.estr_vs_policy_bp) : '—'],
    [`SONIA vs BR ${Number(bank).toFixed(2)}%`, row ? fmtBp(row.sonia_vs_policy_bp) : '—'],
    ['Relative', row ? fmtBp(row.relative_bp) : '—'],
    ['Relative Δ (hist)', chg != null ? fmtBp(chg) : '—'],
    ['Calendar relative', cal != null ? `${row2.label} − ${row.label}: ${fmtBp(cal)}` : '—'],
  ].map(([a,b]) => `<div class="kpi"><div class="k">${a}</div><div class="v">${b}</div></div>`).join('');

  const dates = series.map(p => p.date);
  const ds = [
    {
      label: `${row?.label || k} ESTR vs dep`,
      data: series.map(p => p.estr_vs_policy_bp),
      borderColor: '#ffb84a', fill: false, tension: 0.15, pointRadius: 0, borderWidth: 2,
    },
    {
      label: `${row?.label || k} SONIA vs BR`,
      data: series.map(p => p.sonia_vs_policy_bp),
      borderColor: '#4aa8ff', fill: false, tension: 0.15, pointRadius: 0, borderWidth: 2,
    },
    {
      label: `${row?.label || k} relative`,
      data: series.map(p => p.relative_bp),
      borderColor: '#c084fc', backgroundColor: 'rgba(192,132,252,0.1)', fill: true,
      tension: 0.15, pointRadius: 0, borderWidth: 2,
    },
  ];
  if (k2 && series2.length) {
    const map2 = Object.fromEntries(series2.map(p => [p.date, p.relative_bp]));
    ds.push({
      label: `${row2.label} relative`,
      data: dates.map(d => map2[d] ?? null),
      borderColor: '#39d98a', fill: false, tension: 0.15, pointRadius: 0, borderWidth: 2,
    });
    ds.push({
      label: `${row2.label} − ${row.label} relative`,
      data: dates.map(d => map2[d] != null ? map2[d] - (series.find(p=>p.date===d)?.relative_bp ?? 0) : null),
      borderColor: '#f87171', borderDash: [4,3], fill: false, tension: 0.15, pointRadius: 0, borderWidth: 2,
    });
  }
  pairHistChart.data.labels = dates;
  pairHistChart.data.datasets = ds;
  pairHistChart.update();

  document.querySelectorAll('#stripRows tr').forEach(tr => {
    tr.classList.toggle('sel', tr.dataset.key === k || tr.dataset.key === k2);
  });
}

sel.addEventListener('change', refreshPair);
sel2.addEventListener('change', refreshPair);

document.getElementById('stripRows').innerHTML = strip.map(r => `
  <tr data-key="${r.key}">
    <td>${r.label}</td>
    <td>${r.estr_symbol}</td>
    <td>${r.sonia_symbol}</td>
    <td class="num ${clsBp(r.estr_vs_policy_bp)}">${fmtBp(r.estr_vs_policy_bp)}</td>
    <td class="num ${clsBp(r.sonia_vs_policy_bp)}">${fmtBp(r.sonia_vs_policy_bp)}</td>
    <td class="num ${clsBp(r.relative_bp)}">${fmtBp(r.relative_bp)}</td>
  </tr>`).join('');

document.querySelectorAll('#stripRows tr').forEach(tr => {
  tr.style.cursor = 'pointer';
  tr.onclick = () => { sel.value = tr.dataset.key; refreshPair(); };
});

refreshCurve();
refreshPair();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA_JSON__", DATA_JSON)
for name in ("estr_sonia_1m_dashboard.html", "docs/estr_sonia_1m_dashboard.html"):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"Wrote {path}")

print(f"Overlap {len(common_keys)} · dep {deposit}% · bank {bank}%")
if basis_strip:
    r = basis_strip[0]
    print(
        f"Front {r['label']}: ESTR {r['estr_vs_policy_bp']:+.1f} / "
        f"SONIA {r['sonia_vs_policy_bp']:+.1f} → relative {r['relative_bp']:+.1f} bp"
    )
    d = next((x for x in basis_strip if x["label"] == "Dec-26"), None)
    if d:
        print(
            f"Dec-26: ESTR {d['estr_vs_policy_bp']:+.1f} / "
            f"SONIA {d['sonia_vs_policy_bp']:+.1f} → relative {d['relative_bp']:+.1f} bp"
        )
