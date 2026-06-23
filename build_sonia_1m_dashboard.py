"""Build interactive 1M SONIA curve dashboard (frozen reference + evolution overlay)."""
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
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.1.0/dist/chartjs-plugin-annotation.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--hist:#ffb84a;--policy:#4aa8ff;--pin:#c084fc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill.live{border-color:var(--acc);color:var(--acc)}
.pill.policy{border-color:var(--policy);color:var(--policy)}
.pill.frozen{border-color:var(--acc);color:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.slope-banner{background:#1b2536;border:1px solid var(--hist);border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:14px;line-height:1.5;display:none}
.slope-banner.show{display:block}
.slope-banner strong{color:var(--hist)}
.chart-wrap{display:flex;gap:12px;align-items:stretch}
.chartbox{position:relative;flex:1;min-width:0;height:480px}
#pinTray{width:240px;max-height:480px;overflow-y:auto;flex-shrink:0}
#pinTray:empty::before{content:'Click curve points to pin contracts here. Pins stay on screen while you scrub time.';color:var(--mut);font-size:11px;display:block;padding:8px;line-height:1.45}
.pin-card{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:8px;font-size:11px;line-height:1.5}
.pin-card.pinned{border-color:var(--pin)}
.pin-card .title{font-weight:700;font-size:12px;color:var(--ink)}
.pin-card .sym{color:var(--mut)}
.pin-card .row{display:flex;justify-content:space-between;gap:8px;margin-top:4px}
.pin-card label{display:flex;align-items:center;gap:6px;margin-top:8px;color:var(--mut);cursor:pointer}
.pin-card button{margin-top:8px;background:transparent;border:1px solid var(--line);color:var(--mut);border-radius:6px;padding:3px 8px;font-size:10px;cursor:pointer}
.sliderrow{display:flex;align-items:center;gap:12px;margin:14px 0 8px;flex-wrap:wrap}
.sliderrow input[type=range]{flex:1;min-width:120px;accent-color:var(--hist)}
.sliderdate{font-size:13px;color:var(--ink);min-width:100px;font-variant-numeric:tabular-nums}
.btn{background:#1b2536;border:1px solid var(--line);color:var(--ink);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:12px}
.btn:hover{border-color:var(--acc)}
.tblwrap{max-height:320px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut)}
.foot{color:var(--mut);font-size:12px;margin-top:16px;line-height:1.6}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>1M SONIA curve · frozen reference + time travel</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill frozen">■ Frozen = latest curve</span>
    <span class="pill" style="border-color:var(--hist);color:var(--hist)">■ Amber = historical (slider)</span>
    <span class="pill policy" id="policyPill"></span>
    <span class="pill live" id="livePill" style="display:none">● Live</span>
  </div>
</header>

<div class="card">
  <h2>Curve comparison</h2>
  <p class="hint">Opens on the <b>latest</b> curve (frozen green). Scrub the slider to morph the amber line through history — green stays fixed. <b>Click</b> any point to pin a detail card (cards persist). Pin exactly two legs to see calendar slope at top. Toggle “level line” per pin only when you want a dotted horizontal.</p>

  <div id="slopeBanner" class="slope-banner"></div>

  <div class="chart-wrap">
    <div class="chartbox"><canvas id="mainChart"></canvas></div>
    <div id="pinTray"></div>
  </div>

  <div class="sliderrow">
    <button type="button" class="btn" id="playBtn">▶ Play</button>
    <button type="button" class="btn" id="toLatestBtn">Latest</button>
    <input type="range" id="dateSlider" min="0" max="0" value="0"/>
    <span class="sliderdate" id="sliderDate"></span>
  </div>
  <p class="hint" id="evoHint"></p>
</div>

<div class="card">
  <h2>All contracts (latest)</h2>
  <div class="tblwrap"><table id="tbl"><thead><tr>
    <th>Delivery</th><th>Symbol</th><th>Implied %</th><th>vs Bank</th><th>As of</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<p class="foot" id="foot"></p>
</div>
<script>
const LIVE_POLL_MS = __LIVE_POLL_MS__;
const EMBEDDED = __DATA_JSON__;
let DATA = EMBEDDED;
let mainChart = null;
let evoIdx = 0;
let playTimer = null;
let keys = [];
let frozenPts = [];
let pins = []; // {key, label, symbol, showLevelLine, color}

const PIN_COLORS = ['#c084fc','#f472b6','#22d3ee','#fb923c','#a3e635','#facc15'];

const NO_ANIM = {
  duration: 0,
  easing: 'linear',
};

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

function fmtBp(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return (v >= 0 ? '+' : '') + Number(v).toFixed(1) + ' bp';
}

function evo() {
  return DATA.curve_evolution || { history: [], contract_keys: [] };
}

function initKeysAndFrozen() {
  const e = evo();
  keys = e.contract_keys?.length ? [...e.contract_keys] : DATA.contracts.map(c => c.key).sort();
  const cmap = Object.fromEntries(DATA.contracts.map(c => [c.key, c]));
  frozenPts = keys.map(k => {
    const c = cmap[k];
    if (!c) return null;
    return {
      key: k,
      label: c.label,
      symbol: c.symbol,
      implied_rate_pct: c.implied_rate_pct,
      vs_bank_bp: c.vs_bank_bp,
    };
  }).filter(Boolean);
}

function histMap(idx) {
  const snap = evo().history[idx];
  if (!snap) return {};
  return Object.fromEntries(snap.points.map(p => [p.key, p]));
}

function histRates(idx) {
  const m = histMap(idx);
  return keys.map(k => m[k]?.implied_rate_pct ?? null);
}

function yAxisBounds() {
  const vals = frozenPts.map(p => p.implied_rate_pct);
  for (const snap of evo().history || []) {
    for (const p of snap.points || []) {
      if (keys.includes(p.key) && p.implied_rate_pct != null) vals.push(p.implied_rate_pct);
    }
  }
  vals.push(DATA.bank_rate_pct);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = Math.max(0.08, (hi - lo) * 0.12);
  return { min: lo - pad, max: hi + pad };
}

function buildAnnotations() {
  const ann = {};
  pins.forEach((pin, i) => {
    const fp = frozenPts.find(p => p.key === pin.key);
    if (!fp) return;
    const xi = keys.indexOf(pin.key);
    if (xi < 0) return;
    ann['pin_' + i] = {
      type: 'label',
      xValue: xi,
      yValue: fp.implied_rate_pct,
      xAdjust: 0,
      yAdjust: -14,
      backgroundColor: 'rgba(19,26,38,0.92)',
      borderColor: pin.color || '#c084fc',
      borderWidth: 1,
      borderRadius: 6,
      color: pin.color || '#c084fc',
      font: { size: 10, weight: 'bold' },
      content: `${pin.label} ${fp.implied_rate_pct.toFixed(3)}%`,
      padding: 4,
    };
    if (!pin.showLevelLine) return;
    ann['hline_' + i] = {
      type: 'line',
      yMin: fp.implied_rate_pct,
      yMax: fp.implied_rate_pct,
      borderColor: pin.color || '#ffb84a',
      borderDash: [5, 5],
      borderWidth: 1.5,
      label: {
        display: true,
        content: `${pin.label} level`,
        position: 'end',
        color: pin.color || '#ffb84a',
        font: { size: 10 },
        backgroundColor: 'rgba(19,26,38,0.85)',
      },
    };
  });
  return ann;
}

function pointRadiusForKey(key) {
  const pin = pins.find(p => p.key === key);
  return pin ? 9 : 5;
}

function pointColors(datasetIndex) {
  const base = datasetIndex === 0 ? '#39d98a' : '#ffb84a';
  return keys.map(k => {
    const pin = pins.find(p => p.key === k);
    return pin ? (pin.color || '#c084fc') : base;
  });
}

function updateSlopeBanner() {
  const el = document.getElementById('slopeBanner');
  if (pins.length !== 2) {
    el.classList.remove('show');
    el.innerHTML = '';
    return;
  }
  const sorted = [...pins].sort((a, b) => a.key.localeCompare(b.key));
  const [front, back] = sorted;
  const hm = histMap(evoIdx);
  const fm = Object.fromEntries(frozenPts.map(p => [p.key, p]));
  const hFront = hm[front.key]?.implied_rate_pct;
  const hBack = hm[back.key]?.implied_rate_pct;
  const fFront = fm[front.key]?.implied_rate_pct;
  const fBack = fm[back.key]?.implied_rate_pct;
  if (hFront == null || hBack == null) return;
  const histSlope = (hBack - hFront) * 100;
  const frozenSlope = (fBack != null && fFront != null) ? (fBack - fFront) * 100 : null;
  const delta = frozenSlope != null ? histSlope - frozenSlope : null;
  const date = evo().history[evoIdx]?.date || '';
  el.innerHTML = `<strong>${back.label} − ${front.label}</strong> on <strong>${date}</strong>: ` +
    `<strong>${fmtBp(histSlope)}</strong> (amber curve)` +
    (frozenSlope != null ? ` · frozen was ${fmtBp(frozenSlope)} · Δ ${fmtBp(delta)}` : '');
  el.classList.add('show');
}

function updatePinTray() {
  const tray = document.getElementById('pinTray');
  tray.innerHTML = '';
  const hm = histMap(evoIdx);
  const fm = Object.fromEntries(frozenPts.map(p => [p.key, p]));
  const hdate = evo().history[evoIdx]?.date || '';

  pins.forEach((pin, i) => {
    const h = hm[pin.key];
    const f = fm[pin.key];
    const card = document.createElement('div');
    card.className = 'pin-card pinned';
    card.style.borderColor = pin.color || 'var(--pin)';
    card.innerHTML = `
      <div class="title">${pin.label}</div>
      <div class="sym">${pin.symbol}</div>
      <div class="row"><span>Frozen (latest)</span><span>${f ? f.implied_rate_pct.toFixed(3)+'%' : '—'}</span></div>
      <div class="row"><span>Historical</span><span>${h ? h.implied_rate_pct.toFixed(3)+'%' : '—'}</span></div>
      <div class="row"><span>vs Bank ${DATA.bank_rate_pct}%</span><span>${h ? fmtBp(h.vs_bank_bp) : '—'}</span></div>
      <div class="row"><span>Δ vs frozen</span><span>${f && h ? fmtBp((h.implied_rate_pct - f.implied_rate_pct)*100) : '—'}</span></div>
      <div style="color:var(--mut);margin-top:4px">${hdate}</div>
      <label><input type="checkbox" data-i="${i}" class="lvlChk" ${pin.showLevelLine?'checked':''}/> Show level line</label>
      <button type="button" data-i="${i}" class="rmPin">Remove</button>`;
    tray.appendChild(card);
  });

  tray.querySelectorAll('.lvlChk').forEach(chk => {
    chk.onchange = () => {
      const i = +chk.dataset.i;
      pins[i].showLevelLine = chk.checked;
      applySlider(false);
    };
  });
  tray.querySelectorAll('.rmPin').forEach(btn => {
    btn.onclick = () => {
      pins.splice(+btn.dataset.i, 1);
      updatePinTray();
      updateSlopeBanner();
      applySlider(false);
    };
  });
}

function addPin(key) {
  if (pins.some(p => p.key === key)) return;
  const fp = frozenPts.find(p => p.key === key);
  if (!fp) return;
  pins.push({
    key,
    label: fp.label,
    symbol: fp.symbol,
    showLevelLine: false,
    color: PIN_COLORS[pins.length % PIN_COLORS.length],
  });
  updatePinTray();
  updateSlopeBanner();
  applySlider(false);
}

function applySlider(updateSliderUi = true) {
  const e = evo();
  if (!mainChart || !e.history?.length) return;
  const snap = e.history[evoIdx];
  if (updateSliderUi) {
    document.getElementById('dateSlider').value = evoIdx;
    document.getElementById('sliderDate').textContent = snap.date;
  }

  mainChart.data.datasets[1].data = histRates(evoIdx);
  mainChart.data.datasets[1].label = `Historical · ${snap.date}`;

  keys.forEach((k, i) => {
    const r = pointRadiusForKey(k);
    const hit = r + 14;
    mainChart.data.datasets[0].pointRadius[i] = r;
    mainChart.data.datasets[1].pointRadius[i] = r;
    mainChart.data.datasets[0].pointHitRadius[i] = hit;
    mainChart.data.datasets[1].pointHitRadius[i] = hit;
    mainChart.data.datasets[0].pointBackgroundColor[i] = pointColors(0)[i];
    mainChart.data.datasets[1].pointBackgroundColor[i] = pointColors(1)[i];
  });

  mainChart.options.plugins.annotation.annotations = buildAnnotations();
  mainChart.update('none');
  updatePinTray();
  updateSlopeBanner();
}

function buildMainChart() {
  const e = evo();
  const labels = frozenPts.map(p => p.label);
  const br = DATA.bank_rate_pct;
  const yb = yAxisBounds();
  const ctx = document.getElementById('mainChart');

  if (mainChart) mainChart.destroy();

  mainChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: `Frozen · latest`,
          data: frozenPts.map(p => p.implied_rate_pct),
          borderColor: '#39d98a',
          backgroundColor: 'rgba(57,217,138,0.06)',
          fill: false,
          tension: 0.28,
          borderWidth: 3,
          pointRadius: keys.map(k => pointRadiusForKey(k)),
          pointHitRadius: keys.map(k => pointRadiusForKey(k) + 14),
          pointBackgroundColor: pointColors(0),
          pointBorderColor: '#0b0f17',
          pointBorderWidth: 2,
          order: 1,
        },
        {
          label: `Historical`,
          data: histRates(evoIdx),
          borderColor: '#ffb84a',
          backgroundColor: 'rgba(255,184,74,0.08)',
          fill: false,
          tension: 0.28,
          borderWidth: 2,
          pointRadius: keys.map(k => pointRadiusForKey(k)),
          pointHitRadius: keys.map(k => pointRadiusForKey(k) + 14),
          pointBackgroundColor: pointColors(1),
          pointBorderColor: '#0b0f17',
          pointBorderWidth: 2,
          order: 2,
        },
        {
          label: `Bank Rate ${br}%`,
          data: labels.map(() => br),
          borderColor: '#4aa8ff',
          borderDash: [6, 4],
          pointRadius: 0,
          borderWidth: 1.5,
          fill: false,
          order: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: NO_ANIM,
      transitions: {
        active: { animation: NO_ANIM },
        resize: { animation: NO_ANIM },
      },
      interaction: { mode: 'nearest', intersect: false, axis: 'x' },
      onClick: (evt, elements, chart) => {
        let hits = elements;
        if (!hits?.length) {
          hits = chart.getElementsAtEventForMode(evt, 'nearest', { intersect: false }, true);
        }
        if (!hits?.length) return;
        const el = hits.find(h => h.datasetIndex <= 1) || hits[0];
        if (el.datasetIndex > 1) return;
        addPin(keys[el.index]);
      },
      plugins: {
        legend: { position: 'bottom', labels: { color: '#93a1b5', usePointStyle: true } },
        annotation: { annotations: buildAnnotations() },
        tooltip: {
          backgroundColor: '#131a26',
          borderColor: '#243043',
          borderWidth: 1,
          callbacks: {
            afterTitle: items => {
              const i = items[0].dataIndex;
              const k = keys[i];
              return frozenPts.find(p => p.key === k)?.symbol || '';
            },
            label: ctx => {
              const i = ctx.dataIndex;
              const k = keys[i];
              const hm = histMap(evoIdx)[k];
              const fp = frozenPts.find(p => p.key === k);
              const lines = [`${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(3)}%`];
              if (ctx.datasetIndex === 1 && fp && hm) {
                lines.push(`Δ vs frozen: ${fmtBp((hm.implied_rate_pct - fp.implied_rate_pct)*100)}`);
                lines.push(`vs Bank: ${fmtBp(hm.vs_bank_bp)}`);
              }
              if (ctx.datasetIndex === 0 && fp) {
                lines.push(`vs Bank: ${fmtBp(fp.vs_bank_bp)}`);
              }
              lines.push('Click to pin');
              return lines;
            },
          },
        },
      },
      scales: {
        y: {
          min: yb.min,
          max: yb.max,
          title: { display: true, text: 'Implied rate (%)', color: '#93a1b5' },
          ticks: { callback: v => v.toFixed(2) + '%', color: '#93a1b5' },
          grid: { color: '#243043' },
        },
        x: {
          ticks: { maxRotation: 45, color: '#93a1b5', maxTicksLimit: 22 },
          grid: { color: '#243043' },
        },
      },
    },
  });
}

function setupSlider() {
  const e = evo();
  const slider = document.getElementById('dateSlider');
  if (!e.history?.length) return;

  slider.max = e.history.length - 1;
  evoIdx = e.history.length - 1; // start at latest (overlaps frozen)
  slider.value = evoIdx;
  document.getElementById('sliderDate').textContent = e.history[evoIdx].date;
  document.getElementById('evoHint').textContent =
    `${e.note || ''} · ${e.n_sessions} sessions · ${e.start} → ${e.end}`;

  slider.oninput = () => {
    evoIdx = +slider.value;
    applySlider(true);
  };
  slider.onchange = slider.oninput;

  document.getElementById('toLatestBtn').onclick = () => {
    evoIdx = e.history.length - 1;
    applySlider(true);
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
      if (evoIdx >= e.history.length - 1) {
        clearInterval(playTimer);
        playTimer = null;
        document.getElementById('playBtn').textContent = '▶ Play';
        return;
      }
      evoIdx++;
      applySlider(true);
    }, 120);
  };
}

function renderHeader(status) {
  document.getElementById('asof').textContent =
    `Data ${DATA.generated_utc}` + (status?.last_refresh_utc ? ` · refresh ${status.last_refresh_utc}` : '');
  document.getElementById('policyPill').textContent = `BoE ${DATA.bank_rate_pct}%`;
  if (isLiveMode()) document.getElementById('livePill').style.display = 'inline-block';
}

function renderTable() {
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  [...DATA.contracts].sort((a,b) => a.delivery_ym.localeCompare(b.delivery_ym)).forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${c.label}</td><td>${c.symbol}</td><td class="num">${c.implied_rate_pct.toFixed(3)}%</td><td class="num">${fmtBp(c.vs_bank_bp)}</td><td>${c.latest_date}</td>`;
    tbody.appendChild(tr);
  });
}

function renderAll(status, rebuildChart = false) {
  const savedPins = [...pins];
  const savedIdx = evoIdx;
  renderHeader(status);
  initKeysAndFrozen();
  if (rebuildChart || !mainChart) {
    pins = savedPins.filter(p => keys.includes(p.key));
    buildMainChart();
    setupSlider();
    evoIdx = Math.min(savedIdx, (evo().history?.length || 1) - 1);
    applySlider(true);
  } else {
    mainChart.data.datasets[0].data = frozenPts.map(p => p.implied_rate_pct);
    applySlider(true);
  }
  renderTable();
}

async function poll() {
  try {
    const [d, s] = await Promise.all([fetchData(), fetchStatus()]);
    DATA = d;
    renderAll(s, false);
  } catch (e) { console.warn(e); }
}

renderAll(null, true);
if (isLiveMode()) {
  setInterval(poll, LIVE_POLL_MS);
}
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON).replace("__LIVE_POLL_MS__", str(LIVE_POLL_MS))

for name in ("sonia_1m_dashboard.html", "docs/sonia_1m_dashboard.html"):
    (ROOT / name).write_text(HTML, encoding="utf-8")
    print(f"Wrote {name}")
