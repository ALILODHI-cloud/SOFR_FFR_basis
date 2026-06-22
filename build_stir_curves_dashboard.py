"""Build self-contained STIR curves dashboard from stir_curves_data.json."""
import json
import shutil

with open("stir_curves_data.json", encoding="utf-8") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>STIR Curves · SOFR · SONIA · €STR</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;
  --sofr:#4aa8ff;--sonia:#39d98a;--estr:#ffb84a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:22px 4px 10px}
.stat{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.statlbl{color:var(--mut);font-size:12px;margin-top:4px}
.grid{display:grid;gap:14px}
@media(min-width:800px){.cols-3{grid-template-columns:repeat(3,1fr)}}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.chartbox{position:relative;height:320px}
.chartbox.sm{height:260px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:8px;border-bottom:1px solid var(--line);text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut);font-weight:600}
.foot{color:var(--mut);font-size:12px;margin-top:20px;line-height:1.6}
.legend{display:flex;gap:16px;font-size:12px;color:var(--mut);margin-bottom:8px;flex-wrap:wrap}
.legend i{display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>STIR forward curves · Jun-26 → Dec-28</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill">Source: Barchart EOD</span>
    <span class="pill">3M SOFR (SQ*) · CME</span>
    <span class="pill">3M SONIA (J8*) · ICE</span>
    <span class="pill">3M €STR (EB*) · CME</span>
  </div>
</header>

<div class="card">
  <h2>Current curve (implied rate, %)</h2>
  <p class="hint">Latest EOD settle per contract. Futures quoted 100 − rate.</p>
  <div class="legend">
    <span><i style="background:var(--sofr)"></i>3M SOFR</span>
    <span><i style="background:var(--sonia)"></i>3M SONIA</span>
    <span><i style="background:var(--estr)"></i>3M €STR</span>
  </div>
  <div class="chartbox"><canvas id="curveChart"></canvas></div>
</div>

<div class="card">
  <h2>Current levels</h2>
  <div style="overflow-x:auto"><table id="levelsTbl"><thead><tr>
    <th>Delivery</th><th>3M SOFR</th><th>3M SONIA</th><th>3M €STR</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<div class="sectitle">Calendar slopes · over time</div>

<div class="card">
  <h2>Dec-28 − Jun-27 slope (bp)</h2>
  <p class="hint" id="slopeMainHint">Implied rate(Dec-28) − implied rate(Jun-27), in bp. Negative = cuts priced from Jun-27 peak to Dec-28.</p>
  <div class="grid cols-3" id="slopeStats"></div>
  <div class="chartbox" style="margin-top:12px"><canvas id="slopeJun27Chart"></canvas></div>
</div>

<div class="card">
  <h2>Other calendar slopes · current vs history</h2>
  <div style="overflow-x:auto"><table id="spreadTbl"><thead><tr>
    <th>Spread</th><th>3M SOFR</th><th>3M SONIA</th><th>3M €STR</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<div class="card">
  <h2>Dec-28 − Jun-26 slope over time (bp)</h2>
  <p class="hint" id="slopeJun26Hint"></p>
  <div class="chartbox sm"><canvas id="slopeJun26Chart"></canvas></div>
</div>

<div class="card">
  <h2>Dec-27 − Dec-26 slope over time (bp)</h2>
  <p class="hint" id="slopeDecHint"></p>
  <div class="chartbox sm"><canvas id="slopeDecChart"></canvas></div>
</div>

<div class="sectitle">Implied rates · over time (by contract)</div>
  <p class="hint" id="sofrHint"></p>
  <div class="chartbox sm"><canvas id="sofrTs"></canvas></div>
</div>

<div class="card">
  <h2>3M SONIA · implied rate over time</h2>
  <p class="hint" id="soniaHint"></p>
  <div class="chartbox sm"><canvas id="soniaTs"></canvas></div>
</div>

<div class="card">
  <h2>3M €STR · implied rate over time</h2>
  <p class="hint" id="estrHint"></p>
  <div class="chartbox sm"><canvas id="estrTs"></canvas></div>
</div>

<p class="foot" id="foot"></p>
</div>
<script>
const DATA = __DATA_JSON__;
const COLORS = {sofr_3m:'#4aa8ff', sonia_3m:'#39d98a', estr_3m:'#ffb84a'};
const MONTHS = DATA.curve_months.map(m => m.label);

function byCurve(key) {
  const c = DATA.curves[key];
  if (!c) return {};
  const o = {};
  c.contracts.forEach(x => { o[x.key] = x.implied_rate_pct; });
  return o;
}

function latestEnd() {
  return Object.values(DATA.curves).map(c => c.history_end).filter(Boolean).sort().pop();
}

document.getElementById('asof').textContent =
  `Generated ${DATA.generated_utc}. Latest history through ${latestEnd()}.`;

const sofr = byCurve('sofr_3m');
const sonia = byCurve('sonia_3m');
const estr = byCurve('estr_3m');
const keys = DATA.curve_months.map(m => m.ym);

const curveDatasets = [
  {label:'3M SOFR', data: keys.map(k => sofr[k] ?? null), borderColor: COLORS.sofr_3m, backgroundColor: COLORS.sofr_3m, tension:.25, pointRadius:4},
  {label:'3M SONIA', data: keys.map(k => sonia[k] ?? null), borderColor: COLORS.sonia_3m, backgroundColor: COLORS.sonia_3m, tension:.25, pointRadius:4},
  {label:'3M €STR', data: keys.map(k => estr[k] ?? null), borderColor: COLORS.estr_3m, backgroundColor: COLORS.estr_3m, tension:.25, pointRadius:4},
];

new Chart(document.getElementById('curveChart'), {
  type:'line',
  data:{labels: MONTHS, datasets: curveDatasets},
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{legend:{display:false}, tooltip:{callbacks:{label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(3)}%`}}},
    scales:{
      y:{title:{display:true,text:'Implied rate (%)'}, ticks:{callback:v=>v.toFixed(2)+'%'}},
      x:{title:{display:true,text:'Contract delivery'}}
    }
  }
});

const tbody = document.querySelector('#levelsTbl tbody');
DATA.curve_months.forEach(m => {
  const tr = document.createElement('tr');
  const fmt = v => v == null ? '—' : v.toFixed(3)+'%';
  tr.innerHTML = `<td>${m.label}</td><td class="num">${fmt(sofr[m.ym])}</td><td class="num">${fmt(sonia[m.ym])}</td><td class="num">${fmt(estr[m.ym])}</td>`;
  tbody.appendChild(tr);
});

function tsChart(canvasId, curveKey, hintId) {
  const ts = DATA.timeseries[curveKey];
  const meta = DATA.curves[curveKey];
  document.getElementById(hintId).textContent =
    `${meta.label}: ${ts.n_sessions} sessions, ${ts.start} → ${ts.end}.`;
  const cols = ts.columns;
  const labels = ts.dates;
  const palette = ['#4aa8ff','#39d98a','#ffb84a','#ff6b6b','#c084fc','#22d3ee','#f472b6','#a3e635','#fb923c','#94a3b8','#fcd34d'];
  const datasets = cols.map((col, i) => {
    const lab = (meta.contracts.find(c => c.key === col) || {}).label || col;
    return {
      label: lab,
      data: ts.rows.map(r => r[col] ?? null),
      borderColor: palette[i % palette.length],
      borderWidth: i >= cols.length - 3 ? 2.5 : 1.2,
      pointRadius: 0,
      tension: 0.15,
    };
  });
  new Chart(document.getElementById(canvasId), {
    type:'line',
    data:{labels, datasets},
    options:{
      responsive:true, maintainAspectRatio:false,
      interaction:{mode:'index', intersect:false},
      plugins:{legend:{position:'bottom', labels:{boxWidth:10, font:{size:10}}}},
      scales:{
        y:{title:{display:true,text:'Implied rate (%)'}},
        x:{ticks:{maxTicksLimit:8}}
      }
    }
  });
}

tsChart('sofrTs', 'sofr_3m', 'sofrHint');
tsChart('soniaTs', 'sonia_3m', 'soniaHint');
tsChart('estrTs', 'estr_3m', 'estrHint');

const SPREAD_COLORS = {sofr_3m: COLORS.sofr_3m, sonia_3m: COLORS.sonia_3m, estr_3m: COLORS.estr_3m};
const CURVE_ORDER = ['sofr_3m', 'sonia_3m', 'estr_3m'];

function spreadChart(canvasId, spreadId, hintId, tall) {
  const sp = DATA.calendar_spreads?.[spreadId];
  if (!sp) return;
  const datasets = [];
  let minStart = null, maxEnd = null;
  CURVE_ORDER.forEach(k => {
    const s = sp.by_curve?.[k];
    if (!s) return;
    datasets.push({
      label: s.label,
      data: s.rows.map(r => r.slope_bp),
      borderColor: SPREAD_COLORS[k],
      backgroundColor: SPREAD_COLORS[k],
      pointRadius: 0,
      borderWidth: 2,
      tension: 0.15,
    });
    if (!minStart || s.start < minStart) minStart = s.start;
    if (!maxEnd || s.end > maxEnd) maxEnd = s.end;
  });
  if (!datasets.length) return;
  const labels = sp.by_curve[CURVE_ORDER.find(k => sp.by_curve[k])].rows.map(r => r.date);
  if (hintId) {
    document.getElementById(hintId).textContent =
      `${sp.label}: ${labels.length} sessions, ${minStart} → ${maxEnd}.`;
  }
  new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(1)} bp` } },
      },
      scales: {
        y: { title: { display: true, text: 'Slope (bp)' }, ticks: { callback: v => v + ' bp' } },
        x: { ticks: { maxTicksLimit: 8 } },
      },
    },
  });
}

function renderSlopeStats() {
  const sp = DATA.calendar_spreads?.dec28_minus_jun27;
  if (!sp) return;
  const el = document.getElementById('slopeStats');
  CURVE_ORDER.forEach(k => {
    const s = sp.by_curve?.[k];
    if (!s) return;
    const div = document.createElement('div');
    div.className = 'card';
    div.style.padding = '12px';
    div.style.margin = '0';
    const cls = s.current_bp >= 0 ? 'stat amber' : 'stat green';
    div.innerHTML = `<div class="${cls}">${s.current_bp >= 0 ? '+' : ''}${s.current_bp.toFixed(1)} bp</div>
      <div class="statlbl">${s.label} · ${s.current_date}<br>Range ${s.min_bp} to ${s.max_bp} bp</div>`;
    el.appendChild(div);
  });
}

function renderSpreadTable() {
  const tbody = document.querySelector('#spreadTbl tbody');
  Object.values(DATA.calendar_spreads || {}).forEach(sp => {
    const tr = document.createElement('tr');
    const cell = k => {
      const s = sp.by_curve?.[k];
      return s ? `${s.current_bp >= 0 ? '+' : ''}${s.current_bp.toFixed(1)} bp` : '—';
    };
    tr.innerHTML = `<td>${sp.label}</td><td class="num">${cell('sofr_3m')}</td><td class="num">${cell('sonia_3m')}</td><td class="num">${cell('estr_3m')}</td>`;
    tbody.appendChild(tr);
  });
}

renderSlopeStats();
renderSpreadTable();
spreadChart('slopeJun27Chart', 'dec28_minus_jun27', null, true);
spreadChart('slopeJun26Chart', 'dec28_minus_jun26', 'slopeJun26Hint', false);
spreadChart('slopeDecChart', 'dec27_minus_dec26', 'slopeDecHint', false);

document.getElementById('foot').textContent =
  'All three curves are 3-month quarterly STIR futures (SOFR SQ*, SONIA J8*, €STR EB*) from Barchart EOD. ' +
  'Not investment advice.';
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON)

for path in ("stir_curves_dashboard.html", "docs/stir_curves_dashboard.html"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML)
    print(f"Wrote {path}")
