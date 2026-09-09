"""Build the ICE 3M SONIA (SFI) calendar + fly dashboard."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "sfi_structures_data.json").read_text(encoding="utf-8"))
DATA_JSON = json.dumps(DATA)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SFI Z6/Z7/Z8 calendars</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--hist:#ffb84a;--bad:#f87171;--pol:#4aa8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:12px}
.stat{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stat .k{font-size:11px;color:var(--mut)}
.stat .v{font-size:20px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
.stat .s{font-size:11px;color:var(--mut);margin-top:4px}
.trade{border-color:var(--hist);background:#1a2230}
.trade .v{color:var(--hist);font-size:18px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut);font-weight:600}
tr.hi td{background:rgba(255,184,74,0.08)}
.up{color:var(--bad)}
.dn{color:var(--acc)}
.chartbox{position:relative;height:360px}
.foot{color:var(--mut);font-size:12px;margin-top:16px;line-height:1.6}
a{color:var(--pol)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>SFI calendars · Z6 / M7 / Z7 / Z8</h1>
  <p class="sub" id="sub"></p>
  <div>
    <span class="pill">ICE 3M SONIA · J8*</span>
    <a class="pill" href="sonia_1m_dashboard.html">1M SONIA curve →</a>
  </div>
</header>

<div class="card trade" id="tradeCard"></div>

<div class="card">
  <h2>Latest structure levels</h2>
  <p class="hint" id="lvlHint"></p>
  <div class="grid" id="lvlGrid"></div>
</div>

<div class="card">
  <h2>Sharpest move by horizon</h2>
  <p class="hint">Change in bp from the nearest session ~N months ago to the latest EOD. Highlighted cell = largest |Δ| in that row.</p>
  <div style="overflow:auto"><table id="hTbl"><thead></thead><tbody></tbody></table></div>
</div>

<div class="card">
  <h2>Last six months</h2>
  <p class="hint">Rate-space calendars (later − earlier) and the 1:-2:1 fly (belly richness).</p>
  <div class="chartbox"><canvas id="sfiChart"></canvas></div>
</div>

<p class="foot" id="foot"></p>
</div>
<script>
const D = __DATA_JSON__;
const ORDER = ['z6_z7','z6_m7','m7_z7','z7_z8','fly'];
const LABELS = Object.fromEntries(D.structures.map(s => [s.id, s.label]));
const COLORS = {z6_z7:'#4aa8ff', z6_m7:'#22d3ee', m7_z7:'#a3e635', z7_z8:'#c084fc', fly:'#ffb84a'};

function fmt(bp, signed=true){
  if (bp == null || Number.isNaN(bp)) return '—';
  const n = Number(bp);
  return (signed && n>0 ? '+' : '') + n.toFixed(1);
}
function cls(bp){
  if (bp == null) return '';
  return bp > 0.05 ? 'up' : bp < -0.05 ? 'dn' : '';
}

document.getElementById('sub').textContent =
  `As of ${D.as_of} EOD · ${D.n_sessions} sessions from ${D.history_start} · ${D.source}`;

const tn = D.trade_note || {};
document.getElementById('tradeCard').innerHTML =
  `<h2>Advisable trade</h2>
   <div class="v">${tn.action || '—'}</div>
   <p class="hint" style="margin-top:8px">${tn.position ? '<b>'+tn.position+'</b><br>' : ''}${tn.rationale || ''}
   ${tn.entry_bp!=null ? '<br>Mark '+fmt(tn.entry_bp)+' bp · target '+fmt(tn.target_bp)+' · stop '+fmt(tn.stop_bp) : ''}</p>`;

document.getElementById('lvlHint').textContent = D.quote_note || '';
document.getElementById('lvlGrid').innerHTML = D.structures.map(s =>
  `<div class="stat">
     <div class="k">${s.label}</div>
     <div class="v">${fmt(s.last_bp)}</div>
     <div class="s">${s.formula}<br>${s.pctile.toFixed(0)}th pctile · 1y ${fmt(s.min_bp)} / ${fmt(s.max_bp)}</div>
   </div>`
).join('');

const ht = document.querySelector('#hTbl thead');
const hb = document.querySelector('#hTbl tbody');
ht.innerHTML = '<tr><th>Horizon</th><th>From</th>' +
  ORDER.map(id => `<th class="num">${LABELS[id]}</th>`).join('') +
  '<th>Sharpest</th></tr>';
hb.innerHTML = D.horizons.map(h => {
  const cells = ORDER.map(id => {
    const v = h.changes_bp[id];
    const hi = id === h.sharpest_id ? ' hi' : '';
    return `<td class="num ${cls(v)}${hi}">${fmt(v)}</td>`;
  }).join('');
  return `<tr><td>${h.horizon}</td><td>${h.from_date}</td>${cells}<td>${LABELS[h.sharpest_id]} ${fmt(h.sharpest_bp)}</td></tr>`;
}).join('');

const cutoff = new Date(D.as_of);
cutoff.setMonth(cutoff.getMonth() - 6);
const labels = [];
const series = Object.fromEntries(ORDER.map(id => [id, []]));
const byId = Object.fromEntries(D.structures.map(s => [s.id, s]));
const dates = byId.fly.rows.map(r => r.date).filter(d => d >= cutoff.toISOString().slice(0,10));
const dateSet = new Set(dates);
ORDER.forEach(id => {
  const map = Object.fromEntries(byId[id].rows.map(r => [r.date, r.bp]));
  dates.forEach(d => series[id].push(map[d] ?? null));
});

new Chart(document.getElementById('sfiChart'), {
  type: 'line',
  data: {
    labels: dates,
    datasets: ORDER.map(id => ({
      label: LABELS[id],
      data: series[id],
      borderColor: COLORS[id],
      backgroundColor: 'transparent',
      borderWidth: id === 'fly' ? 2.6 : 1.8,
      pointRadius: 0,
      tension: 0.2,
      spanGaps: true,
    })),
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {mode: 'index', intersect: false},
    plugins: {
      legend: {labels: {color: '#e8eef7', boxWidth: 12}},
      tooltip: {callbacks: {label: c => ` ${c.dataset.label}: ${fmt(c.parsed.y)} bp`}},
    },
    scales: {
      x: {ticks: {color: '#93a1b5', maxTicksLimit: 8}, grid: {color: '#243043'}},
      y: {title: {display: true, text: 'bp', color: '#93a1b5'}, ticks: {color: '#93a1b5'}, grid: {color: '#243043'}},
    },
  },
});

document.getElementById('foot').innerHTML =
  `Legs: ${D.legs.map(l => `${l.code} ${l.symbol} ${l.implied_rate_pct.toFixed(3)}%`).join(' · ')}.
   1M SONIA listed strip does not quote Dec-28 (JUZ28) on Barchart; end-2028 is this 3M SFI Z8.
   <a href="sonia_1m_dashboard.html">1M curve</a> · <a href="portal.html">Portal</a>`;
</script>
</body>
</html>
""".replace("__DATA_JSON__", DATA_JSON)

for name in ("sonia_sfi_spreads.html", "docs/sonia_sfi_spreads.html"):
    (ROOT / name).write_text(HTML, encoding="utf-8")
    print(f"Wrote {name}")
