"""Build interactive 1M SONIA curve dashboard."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with (ROOT / "sonia_1m_data.json").open(encoding="utf-8") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)
LIVE_POLL_MS = 60_000

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>1M SONIA Curve Live</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--policy:#4aa8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill.live{border-color:var(--acc);color:var(--acc)}
.pill.policy{border-color:var(--policy);color:var(--policy)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.chartbox{position:relative;height:420px}
.chartbox.sm{height:300px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:22px 4px 10px}
.sliderrow{display:flex;align-items:center;gap:12px;margin:12px 0}
.sliderrow input[type=range]{flex:1;accent-color:var(--acc)}
.sliderdate{font-size:13px;color:var(--ink);min-width:108px;font-variant-numeric:tabular-nums}
.playbtn{background:#1b2536;border:1px solid var(--line);color:var(--ink);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut)}
.tblwrap{max-height:360px;overflow:auto}
.foot{color:var(--mut);font-size:12px;margin-top:16px;line-height:1.6}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>1M SONIA forward curve</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill">Barchart EOD · ICE JU*</span>
    <span class="pill policy" id="policyPill"></span>
    <span class="pill" id="countPill"></span>
    <span class="pill live" id="livePill" style="display:none">● Live</span>
    <span class="pill" id="refreshPill" style="display:none"></span>
  </div>
</header>

<div class="card">
  <h2>Implied SONIA rate by delivery month</h2>
  <p class="hint">Hover any point for implied rate and change vs Bank Rate (3.75%). Positive bp = market prices SONIA above policy.</p>
  <div class="chartbox"><canvas id="curveChart"></canvas></div>
</div>

<div class="sectitle">Curve evolution · longest common history</div>

<div class="card">
  <h2>Historical curve shape</h2>
  <p class="hint" id="evoHint"></p>
  <div class="sliderrow">
    <button type="button" class="playbtn" id="playBtn">▶ Play</button>
    <input type="range" id="dateSlider" min="0" max="0" value="0"/>
    <span class="sliderdate" id="sliderDate"></span>
  </div>
  <div class="chartbox"><canvas id="evoChart"></canvas></div>
</div>

<div class="card">
  <h2>Key tenors vs Bank Rate over time (bp)</h2>
  <p class="hint">Dec-26, Jun-27, Dec-27 implied change vs 3.75% on the same common sample.</p>
  <div class="chartbox sm"><canvas id="legsChart"></canvas></div>
</div>

<div class="card">
  <h2>All contracts</h2>
  <div class="tblwrap"><table id="tbl"><thead><tr>
    <th>Delivery</th><th>Symbol</th><th>Implied %</th><th>vs Bank (bp)</th><th>≈ hikes (25bp)</th><th>As of</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<p class="foot" id="foot"></p>
</div>
<script>
const LIVE_POLL_MS = __LIVE_POLL_MS__;
const EMBEDDED = __DATA_JSON__;
let DATA = EMBEDDED;
let chart, evoChart, legsChart;
let evoIdx = 0;
let playTimer = null;

function isLiveMode() {
  return location.protocol.startsWith('http');
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

function sortedContracts() {
  return [...DATA.contracts].sort((a,b) => a.delivery_ym.localeCompare(b.delivery_ym));
}

function fmtBp(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(1) + ' bp';
}

function renderHeader(status) {
  const br = DATA.bank_rate_pct;
  document.getElementById('asof').textContent =
    `Data ${DATA.generated_utc} · ${DATA.n_contracts} contracts · history through ${DATA.timeseries?.end || '—'}` +
    (status?.last_refresh_utc ? ` · server refresh ${status.last_refresh_utc}` : '');
  document.getElementById('policyPill').textContent = `BoE Bank Rate ${br}%`;
  document.getElementById('countPill').textContent = `${DATA.n_contracts} JU* contracts`;
  if (isLiveMode()) {
    document.getElementById('livePill').style.display = 'inline-block';
    const rp = document.getElementById('refreshPill');
    if (status?.refreshing) {
      rp.style.display = 'inline-block';
      rp.textContent = '↻ Updating Barchart…';
    } else if (status?.next_refresh_utc) {
      rp.style.display = 'inline-block';
      rp.textContent = `Next fetch ~${status.next_refresh_utc}`;
    }
  }
}

function renderTable() {
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  sortedContracts().forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${c.label}</td><td>${c.symbol}</td>
      <td class="num">${c.implied_rate_pct.toFixed(3)}%</td>
      <td class="num">${fmtBp(c.vs_bank_bp)}</td>
      <td class="num">${c.vs_bank_hikes_25bp >= 0 ? '+' : ''}${c.vs_bank_hikes_25bp.toFixed(2)}</td>
      <td>${c.latest_date}</td>`;
    tbody.appendChild(tr);
  });
}

function renderChart() {
  const list = sortedContracts();
  const labels = list.map(c => c.label);
  const rates = list.map(c => c.implied_rate_pct);
  const br = DATA.bank_rate_pct;

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('curveChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Implied 1M SONIA rate',
        data: rates,
        borderColor: '#39d98a',
        backgroundColor: 'rgba(57,217,138,0.12)',
        fill: true,
        tension: 0.28,
        pointRadius: 6,
        pointHoverRadius: 9,
        pointBackgroundColor: '#39d98a',
        pointBorderColor: '#0b0f17',
        pointBorderWidth: 2,
      }, {
        label: 'Bank Rate (policy)',
        data: labels.map(() => br),
        borderColor: '#4aa8ff',
        borderDash: [6, 4],
        pointRadius: 0,
        borderWidth: 2,
        fill: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'nearest', intersect: true },
      plugins: {
        legend: { position: 'bottom', labels: { color: '#93a1b5' } },
        tooltip: {
          backgroundColor: '#131a26',
          borderColor: '#243043',
          borderWidth: 1,
          titleColor: '#e8eef7',
          bodyColor: '#e8eef7',
          padding: 12,
          displayColors: false,
          filter: item => item.datasetIndex === 0,
          callbacks: {
            title: items => {
              const i = items[0].dataIndex;
              const c = list[i];
              return `${c.label} · ${c.symbol}`;
            },
            label: () => '',
            afterBody: items => {
              const i = items[0].dataIndex;
              const c = list[i];
              const lines = [
                `Implied rate: ${c.implied_rate_pct.toFixed(3)}%`,
                `Bank Rate: ${br}%`,
                `Change vs policy: ${fmtBp(c.vs_bank_bp)}`,
                `≈ ${c.vs_bank_hikes_25bp >= 0 ? '+' : ''}${c.vs_bank_hikes_25bp.toFixed(2)} × 25bp moves`,
                `EOD: ${c.latest_date}`,
              ];
              return lines;
            },
          },
        },
      },
      scales: {
        y: {
          title: { display: true, text: 'Implied rate (%)', color: '#93a1b5' },
          ticks: { callback: v => v.toFixed(2) + '%', color: '#93a1b5' },
          grid: { color: '#243043' },
        },
        x: {
          ticks: { maxRotation: 45, color: '#93a1b5', autoSkip: list.length > 20, maxTicksLimit: 24 },
          grid: { color: '#243043' },
        },
      },
    },
  });
}

function renderEvolution() {
  const evo = DATA.curve_evolution;
  if (!evo || !evo.history?.length) {
    document.getElementById('evoHint').textContent = 'No common history available.';
    return;
  }

  document.getElementById('evoHint').textContent =
    `${evo.note} · ${evo.n_sessions} sessions · ${evo.start} → ${evo.end}`;

  const slider = document.getElementById('dateSlider');
  slider.max = evo.history.length - 1;
  evoIdx = evo.history.length - 1;
  slider.value = evoIdx;
  document.getElementById('sliderDate').textContent = evo.history[evoIdx].date;

  const br = DATA.bank_rate_pct;
  const drawSnap = (idx) => {
    const snap = evo.history[idx];
    const pts = snap.points;
    if (evoChart) evoChart.destroy();
    evoChart = new Chart(document.getElementById('evoChart'), {
      type: 'line',
      data: {
        labels: pts.map(p => p.label),
        datasets: [{
          label: `Curve ${snap.date}`,
          data: pts.map(p => p.implied_rate_pct),
          borderColor: '#39d98a',
          backgroundColor: 'rgba(57,217,138,0.12)',
          fill: true,
          tension: 0.28,
          pointRadius: 5,
          pointHoverRadius: 8,
        }, {
          label: 'Bank Rate',
          data: pts.map(() => br),
          borderColor: '#4aa8ff',
          borderDash: [6, 4],
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: true },
        plugins: {
          legend: { position: 'bottom', labels: { color: '#93a1b5', font: { size: 11 } } },
          tooltip: {
            displayColors: false,
            filter: item => item.datasetIndex === 0,
            callbacks: {
              title: items => {
                const p = pts[items[0].dataIndex];
                return `${p.label} · ${p.symbol} · ${snap.date}`;
              },
              label: () => '',
              afterBody: items => {
                const p = pts[items[0].dataIndex];
                return [
                  `Implied: ${p.implied_rate_pct.toFixed(3)}%`,
                  `vs Bank ${br}%: ${fmtBp(p.vs_bank_bp)}`,
                  `≈ ${(p.vs_bank_bp/25 >= 0 ? '+' : '')}${(p.vs_bank_bp/25).toFixed(2)} hikes`,
                ];
              },
            },
          },
        },
        scales: {
          y: { title: { display: true, text: 'Implied rate (%)', color: '#93a1b5' }, ticks: { color: '#93a1b5' } },
          x: { ticks: { maxRotation: 45, color: '#93a1b5', maxTicksLimit: 21 } },
        },
      },
    });
  };

  drawSnap(evoIdx);
  slider.oninput = () => {
    evoIdx = +slider.value;
    document.getElementById('sliderDate').textContent = evo.history[evoIdx].date;
    drawSnap(evoIdx);
  };

  document.getElementById('playBtn').onclick = () => {
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
      document.getElementById('playBtn').textContent = '▶ Play';
      return;
    }
    evoIdx = 0;
    document.getElementById('playBtn').textContent = '⏸ Pause';
    playTimer = setInterval(() => {
      if (evoIdx >= evo.history.length) {
        clearInterval(playTimer);
        playTimer = null;
        document.getElementById('playBtn').textContent = '▶ Play';
        return;
      }
      slider.value = evoIdx;
      document.getElementById('sliderDate').textContent = evo.history[evoIdx].date;
      drawSnap(evoIdx);
      evoIdx++;
    }, 150);
  };

  const legs = evo.watch_legs || {};
  const colors = {'2026-12':'#ffb84a','2027-06':'#39d98a','2027-12':'#4aa8ff'};
  const datasets = Object.entries(legs).map(([k, leg]) => ({
    label: leg.label,
    data: leg.rows.map(r => r.vs_bank_bp),
    borderColor: colors[k] || '#ccc',
    pointRadius: 0,
    borderWidth: 2,
    tension: 0.15,
  }));
  const dates = legs['2026-12']?.rows.map(r => r.date) || [];
  if (legsChart) legsChart.destroy();
  legsChart = new Chart(document.getElementById('legsChart'), {
    type: 'line',
    data: { labels: dates, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#93a1b5' } },
        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${fmtBp(ctx.parsed.y)}` } },
      },
      scales: {
        y: { title: { display: true, text: 'vs Bank Rate (bp)', color: '#93a1b5' } },
        x: { ticks: { maxTicksLimit: 8, color: '#93a1b5' } },
      },
    },
  });
}

function renderAll(status) {
  renderHeader(status);
  renderChart();
  renderEvolution();
  renderTable();
  document.getElementById('foot').textContent =
    'ICE 1M SONIA futures (JU*), Barchart EOD. Hover curve points for implied rate and bp vs Bank Rate. Not investment advice.';
}

async function poll() {
  try {
    const [d, s] = await Promise.all([fetchData(), fetchStatus()]);
    DATA = d;
    renderAll(s);
  } catch (e) { console.warn(e); }
}

renderAll(null);
if (isLiveMode()) {
  setInterval(poll, LIVE_POLL_MS);
  setInterval(async () => {
    const s = await fetchStatus();
    renderHeader(s);
  }, 15000);
}
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON).replace("__LIVE_POLL_MS__", str(LIVE_POLL_MS))

for name in ("sonia_1m_dashboard.html", "docs/sonia_1m_dashboard.html"):
    (ROOT / name).write_text(HTML, encoding="utf-8")
    print(f"Wrote {name}")
