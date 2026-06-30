"""Build interactive 3M SOFR curve dashboard (frozen reference + evolution overlay)."""
from __future__ import annotations

import json
from pathlib import Path

from analyze_sofr_3m import compute_fomc_meeting_pricing

ROOT = Path(__file__).resolve().parent
with (ROOT / "sofr_3m_data.json").open(encoding="utf-8") as f:
    data = json.load(f)

if "fomc_meeting_pricing" not in data:
    data["fomc_meeting_pricing"] = compute_fomc_meeting_pricing(
        data["contracts"], data["fed_funds_pct"], data.get("fed_funds_as_of")
    )

DATA_JSON = json.dumps(data)
LIVE_POLL_MS = 60_000

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>3M SOFR Curve Live</title>
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
.fomc-summary{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}
.fomc-stat{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:140px}
.fomc-stat .k{font-size:11px;color:var(--mut)}
.fomc-stat .v{font-size:18px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
.fomc-chartbox{position:relative;height:220px;margin-bottom:12px}
.probbar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:#1b2536;min-width:90px}
.probbar span{display:block;height:100%}
.prob-cut{background:#39d98a}
.prob-hold{background:#64748b}
.prob-hike{background:#f87171}
tr.fomc-next td{background:rgba(57,217,138,0.06)}
tr.fomc-past td{color:var(--mut)}
.chg-wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:10px}
#chgTbl{font-size:11px;white-space:nowrap}
#chgTbl th,#chgTbl td{padding:5px 7px}
#chgTbl thead th{position:sticky;top:0;background:#1b2536;z-index:2;box-shadow:0 1px 0 var(--line)}
#chgTbl .sticky-col{position:sticky;left:0;background:var(--card);z-index:1;font-weight:600}
#chgTbl thead .sticky-col{z-index:3;background:#1b2536}
#chgTbl tr.row-hi td{background:rgba(255,184,74,0.08)}
#chgTbl tr.row-hi .sticky-col{background:#1a2233}
#chgTbl td.chg-up{color:#f87171}
#chgTbl td.chg-up-strong{color:#fca5a5;font-weight:700}
#chgTbl td.chg-dn{color:var(--acc)}
#chgTbl td.chg-dn-strong{color:#6ee7a8;font-weight:700}
#chgTbl td.chg-flat{color:var(--mut)}
#chgTbl th.slope-col{border-left:1px solid var(--line);color:var(--hist)}
#chgTbl td.slope-col{border-left:1px solid var(--line);font-weight:600}
.viewbar{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:12px 0 0;flex-wrap:wrap}
.viewbar span.lbl{font-size:11px;color:var(--mut);letter-spacing:.06em;text-transform:uppercase}
.viewtoggle{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#1b2536}
.viewtoggle button{background:transparent;border:0;color:var(--mut);padding:7px 14px;font-size:12px;cursor:pointer;line-height:1}
.viewtoggle button.active{background:var(--acc);color:#0b0f17;font-weight:700}
.viewtoggle button:not(.active):hover{color:var(--ink)}
body.view-phone .wrap{padding:12px 12px calc(48px + env(safe-area-inset-bottom))}
body.view-phone header{padding:14px}
body.view-phone .hint.long{display:none}
body.view-phone .chart-wrap{flex-direction:column}
body.view-phone .chartbox{height:min(52vw, 340px);min-height:260px}
body.view-phone #pinTray{width:100%;max-height:none;display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}
body.view-phone #pinTray:empty::before{min-width:100%}
body.view-phone .pin-card{min-width:168px;margin-bottom:0;flex-shrink:0}
body.view-phone .fomc-chartbox{height:180px}
body.view-phone .fomc-stat{min-width:calc(50% - 6px);flex:1 1 calc(50% - 6px)}
body.view-phone .sliderrow{gap:8px}
body.view-phone .sliderrow .btn{flex:1;min-width:0;padding:10px 8px}
body.view-phone .sliderrow input[type=range]{min-width:100%;order:3;flex-basis:100%}
body.view-phone .sliderdate{order:4;width:100%;text-align:center}
body.view-phone .tblwrap{max-height:240px}
body.view-phone .chg-wrap{max-height:360px}
body.view-phone h1{font-size:20px}
body.view-phone .pill{font-size:11px;padding:4px 8px}
@media (max-width: 720px){
  .chart-wrap{flex-direction:column}
  .chartbox{height:min(52vw, 340px);min-height:260px}
  #pinTray{width:100%;max-height:none;display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}
  #pinTray:empty::before{min-width:100%}
  .pin-card{min-width:168px;margin-bottom:0;flex-shrink:0}
  .fomc-chartbox{height:180px}
  .fomc-stat{min-width:calc(50% - 6px);flex:1 1 calc(50% - 6px)}
  .hint.long{display:none}
  .sliderrow .btn{flex:1}
  .sliderrow input[type=range]{min-width:100%;order:3;flex-basis:100%}
  .sliderdate{order:4;width:100%;text-align:center}
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>3M SOFR curve · frozen reference + time travel</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill frozen">■ Frozen = latest curve</span>
    <span class="pill" style="border-color:var(--hist);color:var(--hist)">■ Amber = historical (slider)</span>
    <span class="pill policy" id="policyPill"></span>
    <span class="pill live" id="livePill" style="display:none">● Live</span>
  </div>
  <div class="viewbar">
    <span class="lbl">Layout</span>
    <div class="viewtoggle" role="group" aria-label="Layout">
      <button type="button" id="viewDesktopBtn" aria-pressed="false">Desktop</button>
      <button type="button" id="viewPhoneBtn" aria-pressed="false">Phone</button>
    </div>
  </div>
</header>

<div class="card">
  <h2>Curve comparison</h2>
  <p class="hint long">Opens on the <b>latest</b> curve (frozen green). Scrub the slider to morph the amber line through history — green stays fixed. <b>Click</b> any point to pin a detail card (cards persist). Pin exactly two legs to see calendar slope at top. Toggle “level line” per pin only when you want a dotted horizontal.</p>
  <p class="hint" style="display:none" id="hintShort">Green = latest · amber = slider date · tap curve to pin · two pins = slope</p>

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
  <h2>FOMC meeting pricing (from 3M SOFR strip)</h2>
  <p class="hint" id="fomcNote"></p>
  <div class="fomc-summary" id="fomcSummary"></div>
  <div class="fomc-chartbox"><canvas id="fomcChart"></canvas></div>
  <div class="tblwrap"><table id="fomcTbl"><thead><tr>
    <th>Meeting</th><th>Ref 3M</th><th>Implied %</th><th>Cum vs Fed</th><th>Δ at meeting</th><th>Cut</th><th>Hold</th><th>Hike</th><th>Probs</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<div class="card">
  <h2>All contracts (latest)</h2>
  <div class="tblwrap"><table id="tbl"><thead><tr>
    <th>Delivery</th><th>Symbol</th><th>Implied %</th><th>vs Bank</th><th>As of</th>
  </tr></thead><tbody></tbody></table></div>
</div>

<div class="card">
  <h2>Daily changes (bp) · all contracts</h2>
  <p class="hint" id="chgHint">Session-over-session Δ in implied rate (bp). Green = rate down (cuts priced in); red = rate up. Weekends omitted — each row is vs the prior listed session. Highlighted row = slider date on the evolution chart.</p>
  <div class="chg-wrap"><table id="chgTbl"><thead><tr></tr></thead><tbody></tbody></table></div>
</div>

<p class="foot" id="foot"></p>
</div>
<script>
const LIVE_POLL_MS = __LIVE_POLL_MS__;
const EMBEDDED = __DATA_JSON__;
let DATA = EMBEDDED;
let mainChart = null;
let fomcChart = null;
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
  const h = location.hostname;
  if (h === 'localhost' || h === '127.0.0.1') return true;
  if (h.endsWith('.devtunnels.ms')) return true;
  if (h.endsWith('.trycloudflare.com')) return true;
  return false;
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
      vs_fed_bp: c.vs_fed_bp,
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
  vals.push(DATA.fed_funds_pct);
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
      <div class="row"><span>vs Bank ${DATA.fed_funds_pct}%</span><span>${h ? fmtBp(h.vs_fed_bp) : '—'}</span></div>
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
  renderChgTable();
}

function buildMainChart() {
  const e = evo();
  const labels = frozenPts.map(p => p.label);
  const br = DATA.fed_funds_pct;
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
          label: `Fed funds ${br}%`,
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
                lines.push(`vs Bank: ${fmtBp(hm.vs_fed_bp)}`);
              }
              if (ctx.datasetIndex === 0 && fp) {
                lines.push(`vs Bank: ${fmtBp(fp.vs_fed_bp)}`);
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
  document.getElementById('policyPill').textContent = `Fed ${DATA.fed_funds_pct}%`;
  if (isLiveMode()) document.getElementById('livePill').style.display = 'inline-block';
}

function renderFomcPanel() {
  const fomc = DATA.fomc_meeting_pricing;
  if (!fomc?.meetings?.length) return;

  document.getElementById('fomcNote').textContent = fomc.note || '';

  const sum = document.getElementById('fomcSummary');
  const nxt = fomc.next_meeting;
  sum.innerHTML = `
    <div class="fomc-stat"><div class="k">Fed funds</div><div class="v">${fomc.fed_funds_pct.toFixed(2)}%</div></div>
    <div class="fomc-stat"><div class="k">Total easing priced</div><div class="v">${fmtBp(fomc.total_easing_priced_bp)}</div></div>
    ${nxt ? `<div class="fomc-stat"><div class="k">Next: ${nxt.meeting_label}</div><div class="v">${fmtBp(nxt.incremental_bp)}</div><div class="k" style="margin-top:4px">${nxt.cut_pct}% cut · ${nxt.hold_pct}% hold · ${nxt.hike_pct}% hike</div></div>` : ''}`;

  const tbody = document.querySelector('#fomcTbl tbody');
  tbody.innerHTML = '';
  fomc.meetings.forEach(m => {
    const tr = document.createElement('tr');
    if (m.status === 'next') tr.className = 'fomc-next';
    if (m.status === 'past') tr.className = 'fomc-past';
    tr.innerHTML = `
      <td>${m.meeting_date.slice(5)} · ${m.meeting_label}</td>
      <td>${m.ref_contract_label} <span style="color:var(--mut)">${m.ref_symbol}</span></td>
      <td class="num">${m.implied_rate_pct.toFixed(3)}%</td>
      <td class="num">${fmtBp(m.cumulative_vs_fed_bp)}</td>
      <td class="num">${fmtBp(m.incremental_bp)}</td>
      <td class="num">${m.cut_pct}%</td>
      <td class="num">${m.hold_pct}%</td>
      <td class="num">${m.hike_pct}%</td>
      <td><div class="probbar" title="cut / hold / hike">
        <span class="prob-cut" style="width:${m.cut_pct}%"></span>
        <span class="prob-hold" style="width:${m.hold_pct}%"></span>
        <span class="prob-hike" style="width:${m.hike_pct}%"></span>
      </div></td>`;
    tbody.appendChild(tr);
  });

  const upcoming = fomc.meetings.filter(m => m.status !== 'past');
  const labels = upcoming.map(m => m.meeting_date.slice(5));
  const cum = upcoming.map(m => m.cumulative_vs_fed_bp);
  const inc = upcoming.map(m => m.incremental_bp);
  const ctx = document.getElementById('fomcChart');
  if (fomcChart) fomcChart.destroy();
  fomcChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Cumulative vs Bank (bp)',
          data: cum,
          type: 'line',
          borderColor: '#4aa8ff',
          backgroundColor: 'rgba(74,168,255,0.1)',
          borderWidth: 2,
          pointRadius: 4,
          yAxisID: 'y',
          order: 0,
        },
        {
          label: 'Δ at meeting (bp)',
          data: inc,
          backgroundColor: inc.map(v => v < 0 ? 'rgba(57,217,138,0.75)' : v > 0 ? 'rgba(248,113,113,0.75)' : 'rgba(100,116,139,0.75)'),
          borderWidth: 0,
          yAxisID: 'y',
          order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: NO_ANIM,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#93a1b5', usePointStyle: true } },
      },
      scales: {
        y: {
          title: { display: true, text: 'Basis points', color: '#93a1b5' },
          ticks: { color: '#93a1b5', callback: v => (v > 0 ? '+' : '') + v },
          grid: { color: '#243043' },
        },
        x: { ticks: { color: '#93a1b5' }, grid: { color: '#243043' } },
      },
    },
  });
}

function renderTable() {
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  [...DATA.contracts].sort((a,b) => a.delivery_ym.localeCompare(b.delivery_ym)).forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${c.label}</td><td>${c.symbol}</td><td class="num">${c.implied_rate_pct.toFixed(3)}%</td><td class="num">${fmtBp(c.vs_fed_bp)}</td><td>${c.latest_date}</td>`;
    tbody.appendChild(tr);
  });
}

function chgCellClass(bp) {
  if (bp == null || Number.isNaN(bp)) return 'chg-flat';
  if (bp >= 8) return 'chg-up-strong';
  if (bp >= 0.5) return 'chg-up';
  if (bp <= -8) return 'chg-dn-strong';
  if (bp <= -0.5) return 'chg-dn';
  return 'chg-flat';
}

function fmtChgBp(bp) {
  if (bp == null || Number.isNaN(bp)) return '—';
  if (Math.abs(bp) < 0.05) return '0.0';
  return (bp > 0 ? '+' : '') + bp.toFixed(1);
}

function buildDailyChgRows() {
  const ts = DATA.timeseries;
  if (!ts?.rows?.length) return null;
  const cols = ts.columns?.length
    ? ts.columns
    : [...DATA.contracts].sort((a, b) => a.delivery_ym.localeCompare(b.delivery_ym)).map(c => c.key);
  const labelMap = Object.fromEntries(DATA.contracts.map(c => [c.key, c.label]));
  const rows = [];
  for (let i = 1; i < ts.rows.length; i++) {
    const prev = ts.rows[i - 1];
    const cur = ts.rows[i];
    const rec = { date: cur.date, prevDate: prev.date, vals: {} };
    cols.forEach(k => {
      if (cur[k] != null && prev[k] != null) {
        rec.vals[k] = Math.round((cur[k] - prev[k]) * 1000) / 10;
      }
    });
    if (cur['2026-12'] != null && prev['2026-12'] != null && cur['2027-12'] != null && prev['2027-12'] != null) {
      const slopePrev = (prev['2027-12'] - prev['2026-12']) * 100;
      const slopeCur = (cur['2027-12'] - cur['2026-12']) * 100;
      rec.slopeChg = Math.round((slopeCur - slopePrev) * 10) / 10;
    }
    rows.push(rec);
  }
  return { cols, labelMap, rows: rows.reverse() };
}

function renderChgTable() {
  const pack = buildDailyChgRows();
  const thead = document.querySelector('#chgTbl thead tr');
  const tbody = document.querySelector('#chgTbl tbody');
  const hint = document.getElementById('chgHint');
  if (!pack) {
    thead.innerHTML = '';
    tbody.innerHTML = '<tr><td colspan="99" style="color:var(--mut)">No timeseries in data.</td></tr>';
    return;
  }

  const sliderDate = evo().history?.[evoIdx]?.date || DATA.timeseries?.end || '';
  hint.textContent =
    `Session-over-session Δ (bp) · ${pack.rows.length} sessions · ${pack.cols.length} contracts · ${DATA.timeseries.start} → ${DATA.timeseries.end}. Green = rate down; red = rate up. Highlight = ${sliderDate || 'latest'}.`;

  thead.innerHTML =
    '<th class="sticky-col">Date</th>' +
    pack.cols.map(k => `<th class="num" title="${k}">${pack.labelMap[k] || k}</th>`).join('') +
    '<th class="num slope-col" title="Δ(Dec27−Dec26 spread)">Δ slope</th>';

  tbody.innerHTML = '';
  pack.rows.forEach(row => {
    const tr = document.createElement('tr');
    if (row.date === sliderDate) tr.className = 'row-hi';
    let html = `<td class="sticky-col" title="vs ${row.prevDate}">${row.date}</td>`;
    pack.cols.forEach(k => {
      const bp = row.vals[k];
      html += `<td class="num ${chgCellClass(bp)}">${fmtChgBp(bp)}</td>`;
    });
    html += `<td class="num slope-col ${chgCellClass(row.slopeChg)}">${fmtChgBp(row.slopeChg)}</td>`;
    tr.innerHTML = html;
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
  renderFomcPanel();
  renderChgTable();
}

async function poll() {
  try {
    const [d, s] = await Promise.all([fetchData(), fetchStatus()]);
    DATA = d;
    renderAll(s, false);
  } catch (e) { console.warn(e); }
}

const VIEW_KEY = 'sofr3m_layout';
const MQ_PHONE = window.matchMedia('(max-width: 720px)');

function getViewPref() {
  const saved = localStorage.getItem(VIEW_KEY);
  if (saved === 'phone' || saved === 'desktop') return saved;
  return MQ_PHONE.matches ? 'phone' : 'desktop';
}

function applyViewMode(pref) {
  const phone = pref === 'phone';
  document.body.classList.toggle('view-phone', phone);
  const desk = document.getElementById('viewDesktopBtn');
  const mob = document.getElementById('viewPhoneBtn');
  const shortHint = document.getElementById('hintShort');
  if (desk) {
    desk.classList.toggle('active', !phone);
    desk.setAttribute('aria-pressed', String(!phone));
  }
  if (mob) {
    mob.classList.toggle('active', phone);
    mob.setAttribute('aria-pressed', String(phone));
  }
  if (shortHint) shortHint.style.display = phone ? 'block' : 'none';
  requestAnimationFrame(() => {
    if (mainChart) mainChart.resize();
    if (fomcChart) fomcChart.resize();
  });
}

function setViewMode(pref) {
  localStorage.setItem(VIEW_KEY, pref);
  applyViewMode(pref);
}

document.getElementById('viewDesktopBtn')?.addEventListener('click', () => setViewMode('desktop'));
document.getElementById('viewPhoneBtn')?.addEventListener('click', () => setViewMode('phone'));
MQ_PHONE.addEventListener('change', () => {
  if (!localStorage.getItem(VIEW_KEY)) applyViewMode(MQ_PHONE.matches ? 'phone' : 'desktop');
});
window.addEventListener('resize', () => {
  if (mainChart) mainChart.resize();
  if (fomcChart) fomcChart.resize();
});

applyViewMode(getViewPref());
renderAll(null, true);
if (isLiveMode()) {
  setInterval(poll, LIVE_POLL_MS);
}
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON).replace("__LIVE_POLL_MS__", str(LIVE_POLL_MS))

for name in ("sofr_3m_dashboard.html", "docs/sofr_3m_dashboard.html"):
    (ROOT / name).write_text(HTML, encoding="utf-8")
    print(f"Wrote {name}")
