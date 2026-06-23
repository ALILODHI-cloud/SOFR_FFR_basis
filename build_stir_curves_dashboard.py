"""Build STIR curves dashboard (static + live-polling)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "stir_curves_data.json"

with DATA_PATH.open(encoding="utf-8") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)
LIVE_POLL_MS = 60_000

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>STIR Curves Live · 3M SOFR · SONIA · €STR</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;
  --sofr:#4aa8ff;--sonia:#39d98a;--estr:#ffb84a;--live:#39d98a;--warn:#ffb84a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill.live{border-color:var(--live);color:var(--live)}
.pill.warn{border-color:var(--warn);color:var(--warn)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:22px 4px 10px}
.stat{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.statlbl{color:var(--mut);font-size:12px;margin-top:4px}
.grid{display:grid;gap:14px}
@media(min-width:800px){.cols-3{grid-template-columns:repeat(3,1fr)}}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.chartbox{position:relative;height:340px}
.chartbox.sm{height:280px}
.chartbox.xl{height:400px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut);font-weight:600;position:sticky;top:0;background:var(--card)}
.tblwrap{max-height:420px;overflow:auto}
.foot{color:var(--mut);font-size:12px;margin-top:20px;line-height:1.6}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>STIR forward curves · full 3M chain</h1>
  <div class="sub" id="asof"></div>
  <div id="pills">
    <span class="pill">Barchart EOD</span>
    <span class="pill" id="countPill"></span>
    <span class="pill live" id="livePill" style="display:none">● Live</span>
    <span class="pill warn" id="refreshPill" style="display:none"></span>
  </div>
</header>

<div class="sectitle">Full curves · every listed 3M contract</div>

<div class="card">
  <h2 id="sofrCurveTitle">3M SOFR</h2>
  <p class="hint">All listed SQ* quarterly contracts on Barchart.</p>
  <div class="chartbox xl"><canvas id="sofrCurve"></canvas></div>
</div>
<div class="card">
  <h2 id="soniaCurveTitle">3M SONIA</h2>
  <p class="hint">All listed J8* quarterly contracts on Barchart.</p>
  <div class="chartbox xl"><canvas id="soniaCurve"></canvas></div>
</div>
<div class="card">
  <h2 id="estrCurveTitle">3M €STR</h2>
  <p class="hint">All listed EB* quarterly contracts on Barchart.</p>
  <div class="chartbox xl"><canvas id="estrCurve"></canvas></div>
</div>

<div class="card">
  <h2>All contracts · current implied rate (%)</h2>
  <div class="tblwrap"><table id="allTbl"><thead><tr>
    <th>Curve</th><th>Symbol</th><th>Delivery</th><th>Rate</th><th>As of</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<div class="sectitle">Calendar slopes · over time</div>

<div class="card">
  <h2>Dec-28 − Jun-27 slope (bp)</h2>
  <div class="grid cols-3" id="slopeStats"></div>
  <div class="chartbox" style="margin-top:12px"><canvas id="slopeJun27Chart"></canvas></div>
</div>

<div class="card">
  <h2>Other calendar slopes (current)</h2>
  <table id="spreadTbl"><thead><tr>
    <th>Spread</th><th>3M SOFR</th><th>3M SONIA</th><th>3M €STR</th>
  </tr></thead><tbody></tbody></table>
</div>

<div class="card"><h2>Dec-28 − Jun-26 slope over time</h2>
  <p class="hint" id="slopeJun26Hint"></p>
  <div class="chartbox sm"><canvas id="slopeJun26Chart"></canvas></div>
</div>

<div class="card"><h2>Dec-27 − Dec-26 slope over time</h2>
  <p class="hint" id="slopeDecHint"></p>
  <div class="chartbox sm"><canvas id="slopeDecChart"></canvas></div>
</div>

<div class="sectitle">Implied rates · over time (every contract)</div>

<div class="card"><h2>3M SOFR · history</h2><p class="hint" id="sofrHint"></p>
  <div class="chartbox sm"><canvas id="sofrTs"></canvas></div></div>
<div class="card"><h2>3M SONIA · history</h2><p class="hint" id="soniaHint"></p>
  <div class="chartbox sm"><canvas id="soniaTs"></canvas></div></div>
<div class="card"><h2>3M €STR · history</h2><p class="hint" id="estrHint"></p>
  <div class="chartbox sm"><canvas id="estrTs"></canvas></div></div>

<p class="foot" id="foot"></p>
</div>
<script>
const LIVE_POLL_MS = __LIVE_POLL_MS__;
const EMBEDDED = __DATA_JSON__;
const COLORS = {sofr_3m:'#4aa8ff', sonia_3m:'#39d98a', estr_3m:'#ffb84a'};
const CURVE_ORDER = ['sofr_3m','sonia_3m','estr_3m'];
const charts = {};

function isLiveMode() {
  return location.protocol.startsWith('http') && location.pathname !== '/file:';
}

async function fetchData() {
  if (!isLiveMode()) return EMBEDDED;
  const r = await fetch('/api/data?' + Date.now());
  if (!r.ok) throw new Error('API ' + r.status);
  return r.json();
}

async function fetchStatus() {
  if (!isLiveMode()) return null;
  try {
    const r = await fetch('/api/status?' + Date.now());
    return r.ok ? r.json() : null;
  } catch { return null; }
}

function contractList(curveKey) {
  const c = DATA.curves[curveKey];
  if (!c) return [];
  return [...c.contracts].sort((a,b) => a.key.localeCompare(b.key));
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function singleCurveChart(canvasId, curveKey, color) {
  destroyChart(canvasId);
  const list = contractList(curveKey);
  const labels = list.map(c => c.label);
  const meta = DATA.curves[curveKey];
  document.getElementById(canvasId.replace('Curve','CurveTitle').replace('sofr','sofr').replace('sonia','sonia').replace('estr','estr'));
  const titleEl = document.getElementById(curveKey === 'sofr_3m' ? 'sofrCurveTitle' : curveKey === 'sonia_3m' ? 'soniaCurveTitle' : 'estrCurveTitle');
  if (titleEl) titleEl.textContent = `${meta.label} · ${list.length} contracts`;

  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: meta.label,
        data: list.map(c => c.implied_rate_pct),
        borderColor: color,
        backgroundColor: color + '33',
        fill: true,
        tension: 0.25,
        pointRadius: list.length > 20 ? 2 : 4,
        pointHoverRadius: 5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${labels[ctx.dataIndex]}: ${ctx.parsed.y?.toFixed(3)}%` } },
      },
      scales: {
        y: { title: { display: true, text: 'Implied rate (%)' }, ticks: { callback: v => v.toFixed(2) + '%' } },
        x: { ticks: { maxRotation: 45, autoSkip: list.length > 24, maxTicksLimit: list.length > 24 ? 18 : 40 } },
      },
    },
  });
}

function renderAllTable() {
  const tbody = document.querySelector('#allTbl tbody');
  tbody.innerHTML = '';
  CURVE_ORDER.forEach(k => {
    contractList(k).forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${DATA.curves[k].label}</td><td>${c.symbol}</td><td>${c.label}</td>
        <td class="num">${c.implied_rate_pct.toFixed(3)}%</td><td>${c.latest_date}</td>`;
      tbody.appendChild(tr);
    });
  });
}

function tsChart(canvasId, curveKey, hintId) {
  destroyChart(canvasId);
  const ts = DATA.timeseries[curveKey];
  const meta = DATA.curves[curveKey];
  if (!ts || !meta) return;
  document.getElementById(hintId).textContent =
    `${meta.label}: ${meta.n_contracts} contracts · ${ts.n_sessions} sessions (${ts.start} → ${ts.end})`;
  const cols = ts.columns;
  const n = cols.length;
  const datasets = cols.map((col, i) => {
    const lab = (meta.contracts.find(c => c.key === col) || {}).label || col;
    const hue = (i / Math.max(n, 1)) * 280;
    return {
      label: lab,
      data: ts.rows.map(r => r[col] ?? null),
      borderColor: `hsl(${hue}, 65%, 58%)`,
      borderWidth: 1,
      pointRadius: 0,
      tension: 0.12,
    };
  });
  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: { labels: ts.dates, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        y: { title: { display: true, text: 'Implied rate (%)' } },
        x: { ticks: { maxTicksLimit: 8 } },
      },
    },
  });
}

function spreadChart(canvasId, spreadId, hintId) {
  destroyChart(canvasId);
  const sp = DATA.calendar_spreads?.[spreadId];
  if (!sp) return;
  const datasets = [];
  let ref = null;
  CURVE_ORDER.forEach(k => {
    const s = sp.by_curve?.[k];
    if (!s) return;
    if (!ref) ref = s;
    datasets.push({
      label: s.label,
      data: s.rows.map(r => r.slope_bp),
      borderColor: COLORS[k],
      pointRadius: 0,
      borderWidth: 2,
      tension: 0.15,
    });
  });
  if (!datasets.length || !ref) return;
  if (hintId) {
    document.getElementById(hintId).textContent =
      `${sp.label}: ${ref.n_sessions} sessions, ${ref.start} → ${ref.end}`;
  }
  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'line',
    data: { labels: ref.rows.map(r => r.date), datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(1)} bp` } },
      },
      scales: {
        y: { title: { display: true, text: 'Slope (bp)' } },
        x: { ticks: { maxTicksLimit: 8 } },
      },
    },
  });
}

function renderSlopeStats() {
  const el = document.getElementById('slopeStats');
  el.innerHTML = '';
  const sp = DATA.calendar_spreads?.dec28_minus_jun27;
  if (!sp) return;
  CURVE_ORDER.forEach(k => {
    const s = sp.by_curve?.[k];
    if (!s) return;
    const div = document.createElement('div');
    div.className = 'card';
    div.style.cssText = 'padding:12px;margin:0';
    const cls = s.current_bp >= 0 ? 'stat' : 'stat';
    div.style.color = s.current_bp >= 0 ? 'var(--warn)' : 'var(--live)';
    div.innerHTML = `<div class="${cls}">${s.current_bp >= 0 ? '+' : ''}${s.current_bp.toFixed(1)} bp</div>
      <div class="statlbl">${s.label}<br>${s.current_date} · range ${s.min_bp} to ${s.max_bp}</div>`;
    el.appendChild(div);
  });
}

function renderSpreadTable() {
  const tbody = document.querySelector('#spreadTbl tbody');
  tbody.innerHTML = '';
  Object.values(DATA.calendar_spreads || {}).forEach(sp => {
    const tr = document.createElement('tr');
    const cell = k => {
      const s = sp.by_curve?.[k];
      return s ? `${s.current_bp >= 0 ? '+' : ''}${s.current_bp.toFixed(1)} bp` : '—';
    };
    tr.innerHTML = `<td>${sp.label}</td><td class="num">${cell('sofr_3m')}</td>
      <td class="num">${cell('sonia_3m')}</td><td class="num">${cell('estr_3m')}</td>`;
    tbody.appendChild(tr);
  });
}

let DATA = EMBEDDED;

function latestEnd() {
  return Object.values(DATA.curves).map(c => c.history_end).filter(Boolean).sort().pop() || '—';
}

function totalContracts() {
  return CURVE_ORDER.reduce((n, k) => n + (DATA.curves[k]?.n_contracts || 0), 0);
}

function renderHeader(status) {
  const live = isLiveMode();
  document.getElementById('asof').textContent =
    `Data ${DATA.generated_utc} · history through ${latestEnd()}` +
    (status?.last_refresh_utc ? ` · server refresh ${status.last_refresh_utc}` : '');
  document.getElementById('countPill').textContent =
    `${totalContracts()} contracts (SOFR ${DATA.curves.sofr_3m?.n_contracts||0} · SONIA ${DATA.curves.sonia_3m?.n_contracts||0} · €STR ${DATA.curves.estr_3m?.n_contracts||0})`;
  const livePill = document.getElementById('livePill');
  const refreshPill = document.getElementById('refreshPill');
  if (live) {
    livePill.style.display = 'inline-block';
    if (status?.refreshing) {
      refreshPill.style.display = 'inline-block';
      refreshPill.textContent = '↻ Refreshing Barchart…';
    } else {
      refreshPill.style.display = status?.next_refresh_utc ? 'inline-block' : 'none';
      refreshPill.textContent = status?.next_refresh_utc ? `Next fetch ~${status.next_refresh_utc}` : '';
    }
  }
}

function renderAll() {
  renderHeader(window._status);
  singleCurveChart('sofrCurve', 'sofr_3m', COLORS.sofr_3m);
  singleCurveChart('soniaCurve', 'sonia_3m', COLORS.sonia_3m);
  singleCurveChart('estrCurve', 'estr_3m', COLORS.estr_3m);
  renderAllTable();
  renderSlopeStats();
  renderSpreadTable();
  spreadChart('slopeJun27Chart', 'dec28_minus_jun27', null);
  spreadChart('slopeJun26Chart', 'dec28_minus_jun26', 'slopeJun26Hint');
  spreadChart('slopeDecChart', 'dec27_minus_dec26', 'slopeDecHint');
  tsChart('sofrTs', 'sofr_3m', 'sofrHint');
  tsChart('soniaTs', 'sonia_3m', 'soniaHint');
  tsChart('estrTs', 'estr_3m', 'estrHint');
  document.getElementById('foot').textContent =
    'Full 3M STIR chains: SOFR SQ*, SONIA J8*, €STR EB* · Barchart EOD. Not investment advice.';
}

async function poll() {
  try {
    const [d, s] = await Promise.all([fetchData(), fetchStatus()]);
    DATA = d;
    window._status = s;
    renderAll();
  } catch (e) {
    console.warn('poll failed', e);
  }
}

renderAll();
if (isLiveMode()) {
  setInterval(poll, LIVE_POLL_MS);
  setInterval(async () => { window._status = await fetchStatus(); renderHeader(window._status); }, 15000);
}
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON).replace("__LIVE_POLL_MS__", str(LIVE_POLL_MS))

for name in ("stir_curves_dashboard.html", "docs/stir_curves_dashboard.html"):
    out = ROOT / name
    out.write_text(HTML, encoding="utf-8")
    print(f"Wrote {out}")
