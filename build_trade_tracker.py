#!/usr/bin/env python3
"""Build static trade tracker HTML shells (fetch JSON at runtime — no data bake-in)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "trades_index.json"
TRADES_DIR = ROOT / "trades"

DETAIL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>__PAGE_TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--warn:#ffb84a;--bad:#ff6b6b;--good:#39d98a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px 16px 48px}
a{color:var(--acc)}
header{padding:18px;border:1px solid var(--line);border-radius:14px;background:var(--card);margin-bottom:14px}
.eyebrow{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
h1{margin:6px 0;font-size:clamp(20px,4vw,26px)}
.sub{color:var(--mut);font-size:13px;line-height:1.5}
.nav{font-size:13px;margin-bottom:12px}
.grid{display:grid;gap:12px}
@media(min-width:800px){.grid.stats{grid-template-columns:repeat(4,1fr)}.grid.two{grid-template-columns:1fr 1fr}.grid.levels{grid-template-columns:repeat(3,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.card h2{font-size:14px;margin:0 0 8px;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.stat{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums}
.stat.sm{font-size:20px}
.stat.good{color:var(--good)}.stat.bad{color:var(--bad)}.stat.neu{color:var(--ink)}
.statlbl{font-size:11px;color:var(--mut);margin-top:4px}
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th,.tbl td{padding:8px;border-bottom:1px solid var(--line);text-align:left}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums}
.chartbox{height:280px;position:relative}
.pill{display:inline-block;font-size:11px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin:4px 6px 0 0}
.pill.warn{border-color:var(--warn);color:var(--warn)}
.pill.bad{border-color:var(--bad);color:var(--bad)}
.foot{color:var(--mut);font-size:11px;margin-top:16px;line-height:1.6}
.level{border-left:3px solid var(--line);padding-left:10px}
.level.stop{border-color:var(--bad)}.level.entry{border-color:var(--acc)}.level.tp{border-color:var(--good)}
.loading{color:var(--mut);padding:24px;text-align:center}
</style>
</head>
<body>
<div class="wrap">
<div class="nav"><a href="portal.html">← Portal</a> · <a href="trade_tracker.html">All trades</a></div>
<header>
  <div class="eyebrow">Supra Fund Management · live trade</div>
  <h1 id="title">Loading…</h1>
  <div class="sub" id="subtitle"></div>
  <div id="pills"></div>
</header>
<div id="loading" class="loading">Loading trade data…</div>
<div id="content" style="display:none">
<div class="grid stats" id="stats"></div>
<div class="card" id="proxyCard" style="display:none">
  <h2>Live proxy (3M SONIA)</h2>
  <p class="sub" id="proxyNote" style="margin:0 0 10px"></p>
  <div class="grid stats" id="proxyStats"></div>
</div>
<div class="card" id="levelsCard"><h2>Entry · stop · take profit</h2><div class="grid levels" id="levels"></div></div>
<div class="card"><h2>Cumulative P&amp;L (£)</h2><div class="chartbox"><canvas id="pnlChart"></canvas></div></div>
<div class="grid two">
  <div class="card"><h2 id="mainChartTitle">Mark</h2><div class="chartbox"><canvas id="mainChart"></canvas></div></div>
  <div class="card" id="secondChartCard"><h2 id="secondChartTitle">Legs</h2><div class="chartbox"><canvas id="secondChart"></canvas></div></div>
</div>
<div class="card" id="regimeCard">
  <h2>Regime attribution (since entry)</h2>
  <table class="tbl" id="regimeTbl"><thead><tr><th>Regime</th><th>Days</th><th>Δ</th><th>P&amp;L £</th></tr></thead><tbody></tbody></table>
</div>
<div class="card">
  <h2>Daily path</h2>
  <div style="overflow:auto;max-height:320px"><table class="tbl" id="pathTbl"><thead><tr id="pathHead"></tr></thead><tbody></tbody></table></div>
</div>
</div>
<p class="foot" id="foot"></p>
</div>
<script>
const DATA_FILE = '__DATA_FILE__';
function fmtBp(v){ if(v==null||isNaN(v)) return '—'; return (v>=0?'+':'')+Number(v).toFixed(1)+' bp'; }
function fmtPct(v){ if(v==null) return '—'; return Number(v).toFixed(3)+'%'; }
function fmtGbp(v){ return (v>=0?'+':'')+'£'+Math.abs(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function cls(v){ return v>0.5?'good':v<-0.5?'bad':'neu'; }

function render(D){
  const GBP = D.trade.gbp_per_bp || 12.5;
  const isOutright = D.trade.type === 'outright';
  const L = D.levels || {};
  const pnl = D.pnl;

  document.getElementById('loading').style.display='none';
  document.getElementById('content').style.display='block';
  document.getElementById('title').textContent = D.trade.label;
  document.getElementById('subtitle').textContent = D.trade.position + ' · Entry ' + D.entry.label + ' · Mark ' + D.mark.date;
  const pills = document.getElementById('pills');
  pills.innerHTML = '<span class="pill">'+D.trade.direction+'</span><span class="pill">Bank '+D.bank_rate_pct+'%</span>'
    + (D.book_size ? '<span class="pill">'+D.book_size.position_size+'</span>' : '')
    + (D.trade.entry_locked ? '<span class="pill">Entry locked (EOD)</span>' : '<span class="pill warn">Provisional</span>')
    + '<span class="pill">Updated '+D.generated_utc+'</span>';

  if(isOutright){
    document.getElementById('levels').innerHTML = [
      ['entry','Entry',fmtPct(L.entry_rate_pct)],
      ['stop','Stop',fmtPct(L.stop_rate_pct)],
      ['tp','Take profit',fmtPct(L.take_profit_rate_pct)]
    ].map(([c,l,v])=>'<div class="level '+c+'"><div class="statlbl">'+l+'</div><div class="stat sm neu">'+v+'</div></div>').join('');
    document.getElementById('stats').innerHTML = [
      ['P&amp;L', fmtGbp(pnl.gbp), cls(pnl.gbp)],
      ['Δ rate', fmtBp(pnl.slope_bp), cls(pnl.slope_bp)],
      ['Mark', fmtPct(D.mark.rate_pct), 'neu'],
      ['To stop', fmtBp(pnl.to_stop_bp), pnl.to_stop_bp>0?'bad':'neu'],
    ].map(([l,v,c])=>'<div class="card"><div class="statlbl">'+l+'</div><div class="stat '+c+'">'+v+'</div></div>').join('');
    document.getElementById('mainChartTitle').textContent = 'Implied rate (%)';
    document.getElementById('secondChartCard').style.display='none';
  } else {
    document.getElementById('levels').innerHTML = [
      ['entry','Entry spread',fmtBp(L.entry_slope_bp)],
      ['stop','Stop',fmtBp(L.stop_slope_bp)],
      ['tp','Take profit',fmtBp(L.take_profit_slope_bp)]
    ].map(([c,l,v])=>'<div class="level '+c+'"><div class="statlbl">'+l+'</div><div class="stat sm neu">'+v+'</div></div>').join('');
    document.getElementById('stats').innerHTML = [
      ['P&amp;L', fmtGbp(pnl.gbp), cls(pnl.gbp)],
      ['Δ spread', fmtBp(pnl.slope_bp), cls(pnl.slope_bp)],
      ['Mark spread', fmtBp(D.mark.slope_bp), cls(pnl.slope_bp)],
      ['To stop', fmtBp(pnl.to_stop_bp), (D.trade.direction==='flattener'?pnl.to_stop_bp<0:pnl.to_stop_bp>0)?'bad':'neu'],
    ].map(([l,v,c])=>'<div class="card"><div class="statlbl">'+l+'</div><div class="stat '+c+'">'+v+'</div></div>').join('');
    document.getElementById('mainChartTitle').textContent = D.trade.spread_label + ' spread (bp)';
    document.getElementById('secondChartTitle').textContent = 'Implied rates (%)';
  }

  const path = D.trade_path || [];
  const labels = path.map(r=>r.date);
  const cum = path.map(r=>r.cum_pnl_gbp);
  new Chart(document.getElementById('pnlChart'), {
    type:'line',
    data:{labels,datasets:[{label:'Cum P&L £',data:cum,borderColor:'#39d98a',backgroundColor:'rgba(57,217,138,.08)',fill:true,tension:.2}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
  });

  if(isOutright){
    const rates = path.map(r=>r.rate_pct);
    const datasets = [{label:'Rate %',data:rates,borderColor:'#39d98a',pointRadius:3}];
    if(L.entry_rate_pct!=null) datasets.push({label:'Entry',data:labels.map(()=>L.entry_rate_pct),borderColor:'#4aa8ff',borderDash:[5,4],pointRadius:0});
    if(L.stop_rate_pct!=null) datasets.push({label:'Stop',data:labels.map(()=>L.stop_rate_pct),borderColor:'#ff6b6b',borderDash:[4,4],pointRadius:0});
    if(L.take_profit_rate_pct!=null) datasets.push({label:'Take profit',data:labels.map(()=>L.take_profit_rate_pct),borderColor:'#39d98a',borderDash:[4,4],pointRadius:0});
    new Chart(document.getElementById('mainChart'), {
      type:'line', data:{labels,datasets},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
    });
    document.getElementById('pathHead').innerHTML = '<th>Date</th><th>Rate %</th><th>Δ day</th><th>Cum £</th>';
    const pt = document.querySelector('#pathTbl tbody');
    [...path].reverse().forEach(r=>{
      pt.innerHTML += '<tr><td>'+r.date+'</td><td class="num">'+r.rate_pct.toFixed(3)+'</td><td class="num">'+fmtGbp(r.daily_pnl_gbp)+'</td><td class="num">'+fmtGbp(r.cum_pnl_gbp)+'</td></tr>';
    });
    document.getElementById('regimeCard').style.display='none';
  } else {
    const slopes = path.map(r=>r.slope_bp);
    const ds = [{label:'Spread bp',data:slopes,borderColor:'#ffb84a',pointRadius:3}];
    ds.push({label:'Entry',data:labels.map(()=>L.entry_slope_bp),borderColor:'#4aa8ff',borderDash:[5,4],pointRadius:0});
    if(L.stop_slope_bp!=null) ds.push({label:'Stop',data:labels.map(()=>L.stop_slope_bp),borderColor:'#ff6b6b',borderDash:[4,4],pointRadius:0});
    if(L.take_profit_slope_bp!=null) ds.push({label:'Take profit',data:labels.map(()=>L.take_profit_slope_bp),borderColor:'#39d98a',borderDash:[4,4],pointRadius:0});
    new Chart(document.getElementById('mainChart'), { type:'line', data:{labels,datasets:ds},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
    });
    new Chart(document.getElementById('secondChart'), {
      type:'line',
      data:{labels,datasets:[
        {label:D.leg_labels.quoted_long,data:path.map(r=>r.quoted_long_rate),borderColor:'#39d98a'},
        {label:D.leg_labels.quoted_short,data:path.map(r=>r.quoted_short_rate),borderColor:'#ffb84a'}
      ]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
    });
    const rt = document.querySelector('#regimeTbl tbody');
    (D.regime_attribution||[]).forEach(r=>{
      rt.innerHTML += '<tr><td>'+r.label+'</td><td class="num">'+r.days+'</td><td class="num">'+fmtBp(r.pnl_slope_bp)+'</td><td class="num">'+fmtGbp(r.pnl_gbp)+'</td></tr>';
    });
    document.getElementById('pathHead').innerHTML = '<th>Date</th><th>'+D.leg_labels.quoted_short+'</th><th>'+D.leg_labels.quoted_long+'</th><th>Spread</th><th>Δ day</th><th>Cum £</th>';
    const pt = document.querySelector('#pathTbl tbody');
    [...path].reverse().forEach(r=>{
      pt.innerHTML += '<tr><td>'+r.date+'</td><td class="num">'+r.quoted_short_rate.toFixed(3)+'</td><td class="num">'+r.quoted_long_rate.toFixed(3)+'</td><td class="num">'+r.slope_bp.toFixed(1)+'</td><td class="num">'+fmtGbp(r.daily_pnl_gbp)+'</td><td class="num">'+fmtGbp(r.cum_pnl_gbp)+'</td></tr>';
    });
  }
  document.getElementById('foot').textContent = D.trade.position + ' · £'+GBP+'/bp · Barchart EOD. Not investment advice.';

  const px = D.live_proxy;
  if(px && px.pnl_gbp != null){
    document.getElementById('proxyCard').style.display='block';
    document.getElementById('proxyNote').textContent = px.source + ' · 3M as of '+px.latest_3m_date+' (1M entry anchored). '+px.note;
    const markLbl = isOutright ? fmtPct(px.mark_rate_pct) : fmtBp(px.mark_slope_bp);
    document.getElementById('proxyStats').innerHTML = [
      ['Proxy P&amp;L', fmtGbp(px.pnl_gbp), cls(px.pnl_gbp)],
      ['Proxy mark', markLbl, cls(px.pnl_bp)],
      ['3M ref date', px.latest_3m_date, 'neu'],
      ['vs EOD P&amp;L', fmtGbp(px.pnl_gbp - pnl.gbp), cls(px.pnl_gbp - pnl.gbp)],
    ].map(([l,v,c])=>'<div class="card"><div class="statlbl">'+l+'</div><div class="stat sm '+c+'">'+v+'</div></div>').join('');
  }
}

fetch(DATA_FILE).then(r=>{
  if(!r.ok) throw new Error(r.statusText);
  return r.json();
}).then(render).catch(err=>{
  document.getElementById('loading').textContent = 'Failed to load '+DATA_FILE+': '+err.message;
});
</script>
</body>
</html>
"""

HUB_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>Supra · Live trade tracker</title>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--warn:#ffb84a;--bad:#ff6b6b;--good:#39d98a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:20px 16px 64px}
a{color:var(--acc);text-decoration:none}
header{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:20px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
h1{margin:8px 0 6px;font-size:clamp(22px,4vw,30px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.nav{font-size:13px;margin-bottom:14px}
.grid{display:grid;gap:14px}
@media(min-width:700px){.grid{grid-template-columns:1fr 1fr}}
.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;color:inherit;transition:border-color .15s}
.card:hover{border-color:var(--acc)}
.card h2{margin:0 0 6px;font-size:16px}
.card p{margin:0 0 10px;color:var(--mut);font-size:13px;line-height:1.45}
.row{display:flex;justify-content:space-between;gap:12px;font-size:13px;margin:4px 0}
.row span:last-child{font-variant-numeric:tabular-nums;font-weight:600}
.good{color:var(--good)}.bad{color:var(--bad)}
.pill{display:inline-block;font-size:11px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin-right:6px}
.foot{color:var(--mut);font-size:11px;margin-top:20px}
.loading{color:var(--mut);padding:24px;text-align:center}
</style>
</head>
<body>
<div class="wrap">
<div class="nav"><a href="portal.html">← Portal</a></div>
<header>
  <div class="eyebrow">Supra Fund Management</div>
  <h1>Live trade tracker</h1>
  <div class="sub" id="bookLine">Loading book…</div>
</header>
<div id="bookBar" class="card" style="display:none;margin-bottom:14px;padding:14px"></div>
<div id="loading" class="loading">Loading trades…</div>
<div class="grid" id="tradeGrid"></div>
<p class="foot" id="foot"></p>
</div>
<script>
function fmtBp(v){ if(v==null) return '—'; return (v>=0?'+':'')+Number(v).toFixed(1)+' bp'; }
function fmtPct(v){ if(v==null) return '—'; return Number(v).toFixed(2)+'%'; }
function fmtGbp(v){ return (v>=0?'+':'')+'£'+Math.abs(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function cls(v){ return v>0.5?'good':v<-0.5?'bad':''; }

fetch('book_summary.json').then(r=>r.json()).then(B=>{
  const m = B.metrics;
  document.getElementById('bookLine').textContent =
    'Book NAV $'+m.nav_usd.toLocaleString()+' · MTD '+fmtPct(m.mtd_return_pct)+' · YTD '+fmtPct(m.ytd_return_pct);
  const bar = document.getElementById('bookBar');
  bar.style.display='block';
  bar.innerHTML = '<div class="row"><span>Total P&amp;L</span><span class="'+cls(m.total_pnl_usd)+'">'+(m.total_pnl_usd>=0?'+':'')+'$'+Math.abs(m.total_pnl_usd).toLocaleString()+'</span></div>'
    +'<div class="row"><span>30d ann. vol</span><span>'+(m.vol_ann_30d_pct!=null?m.vol_ann_30d_pct.toFixed(1)+'%':'—')+'</span></div>';
}).catch(()=>{ document.getElementById('bookLine').textContent = 'Barchart marks weekdays'; });

fetch('trades_index.json').then(r=>{
  if(!r.ok) throw new Error(r.statusText);
  return r.json();
}).then(INDEX=>{
  document.getElementById('loading').style.display='none';
  const grid = document.getElementById('tradeGrid');
  INDEX.trades.forEach(t=>{
    const isO = t.type === 'outright';
    const entryRow = isO
      ? '<div class="row"><span>Entry rate</span><span>'+fmtPct(t.entry_rate_pct)+'</span></div>'
        + '<div class="row"><span>Stop / TP</span><span>'+fmtPct(t.stop_rate_pct)+' / '+fmtPct(t.take_profit_rate_pct)+'</span></div>'
      : '<div class="row"><span>'+t.spread_label+' entry</span><span>'+fmtBp(t.entry_slope_bp)+'</span></div>'
        + '<div class="row"><span>Stop / TP</span><span>'+fmtBp(t.stop_slope_bp)+' / '+fmtBp(t.take_profit_slope_bp)+'</span></div>';
    const markRow = isO
      ? '<div class="row"><span>Mark</span><span>'+fmtPct(t.mark_rate_pct)+'</span></div>'
      : '<div class="row"><span>Mark spread</span><span>'+fmtBp(t.mark_slope_bp)+'</span></div>';
    grid.innerHTML += '<a class="card" href="'+t.detail_page+'"><h2>'+t.label+'</h2><p>'+t.position+'</p>'
      + (t.position_size ? '<p style="font-size:12px;color:var(--mut);margin:0 0 8px">'+t.position_size+'</p>' : '')
      + '<span class="pill">'+t.direction+'</span>'
      + entryRow + markRow
      + '<div class="row"><span>P&amp;L</span><span class="'+cls(t.pnl_gbp)+'">'+fmtGbp(t.pnl_gbp)+'</span></div></a>';
  });
  document.getElementById('foot').textContent = 'Updated '+INDEX.generated_utc+' · Not investment advice.';
}).catch(err=>{
  document.getElementById('loading').textContent = 'Failed to load trades_index.json: '+err.message;
});
</script>
</body>
</html>
"""

PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Supra · Markets Portal</title>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--policy:#4aa8ff;--warn:#ffb84a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:20px 16px 64px}
header{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:20px}
.eyebrow{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
h1{margin:6px 0;font-size:clamp(22px,4vw,30px)}
h2{margin:0 0 8px;font-size:16px}
.sub{color:var(--mut);font-size:13px;line-height:1.5}
.grid{display:grid;gap:14px}
@media(min-width:700px){.grid.cols-2{grid-template-columns:1fr 1fr}.grid.cols-4{grid-template-columns:repeat(4,1fr)}}
.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;text-decoration:none;color:inherit}
.card.featured{border-color:rgba(57,217,138,.35)}
.card.book{border-color:rgba(74,168,255,.35);margin-bottom:4px}
.pill{display:inline-block;font-size:11px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin:4px 6px 0 0}
.pill.live{border-color:var(--acc);color:var(--acc)}
.good{color:#39d98a}.bad{color:#ff6b6b}
.loading{color:var(--mut);padding:12px}
.statgrid{display:grid;gap:10px;margin:14px 0}
@media(min-width:600px){.statgrid{grid-template-columns:repeat(4,1fr)}}
.stat{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:12px}
.stat .k{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.stat .v{font-size:22px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}
.stat .v.sm{font-size:15px}
.tbl{width:100%;border-collapse:collapse;font-size:12px;margin-top:12px}
.tbl th,.tbl td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums}
.tbl th{color:var(--mut);font-weight:600}
.conv{font-size:11px;color:var(--mut);line-height:1.55;margin-top:10px;padding:10px;background:#1b2536;border-radius:8px;border:1px solid var(--line)}
.section{margin:20px 0 8px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}
</style>
</head>
<body><div class="wrap">
<header>
  <div class="eyebrow">Supra Fund Management</div>
  <h1>Markets portal</h1>
  <p class="sub">STIR book simulation · live dashboards · trade trackers</p>
</header>

<div id="bookSection" class="loading">Loading total book…</div>

<div class="section">Open positions</div>
<div class="grid cols-2">
  <a class="card featured" href="trade_tracker.html"><h2>Live trade tracker</h2><p>All positions · detail pages · daily path</p></a>
  <div id="tradeCards" class="loading">Loading trade P&amp;L…</div>
</div>

<div class="section">Curve dashboards</div>
<div class="grid cols-2">
  <a class="card" href="sonia_1m_dashboard.html"><h2>1M SONIA curve live</h2></a>
  <a class="card" href="sofr_3m_dashboard.html"><h2>3M SOFR curve live</h2></a>
  <a class="card" href="sonia_dashboard.html"><h2>Dec27−Dec26 monitor</h2></a>
</div>
</div>
<script>
function fmtUsd(v){ if(v==null||isNaN(v)) return '—'; const s=v>=0?'+':''; return s+'$'+Math.abs(v).toLocaleString('en-US',{maximumFractionDigits:0}); }
function fmtPct(v){ if(v==null||isNaN(v)) return '—'; return (v>=0?'+':'')+Number(v).toFixed(2)+'%'; }
function fmtGbp(v){ if(v==null||isNaN(v)) return '—'; return (v>=0?'+':'')+'£'+Math.abs(v).toLocaleString('en-GB',{maximumFractionDigits:0}); }
function cls(v){ return v>0.5?'good':v<-0.5?'bad':''; }

const BOOK_FALLBACK = __BOOK_FALLBACK__;

function renderBook(B){
  const el = document.getElementById('bookSection');
  const m = B.metrics;
  const bk = B.book;
  const c = bk.conventions;
  const marginUsd = bk.total_margin_ice_usd != null ? bk.total_margin_ice_usd : bk.total_margin_assumed_usd;
  let tradeRows = '';
  B.trades.forEach(t=>{
    tradeRows += '<tr><td>'+t.label+'</td><td class="num" style="font-size:11px;color:var(--mut)">'+(t.position_size||'—')+'</td><td>'+t.direction+'</td><td class="num">'+t.entry_date+'</td>'
      +'<td class="num">'+t.pnl_bp+' bp</td><td class="num">'+fmtGbp(t.pnl_gbp)+'</td>'
      +'<td class="num '+cls(t.pnl_usd)+'">'+fmtUsd(t.pnl_usd)+'</td>'
      +'<td class="num">'+fmtPct(t.return_on_nav_pct)+'</td></tr>';
  });
  el.className = 'card book';
  el.innerHTML = '<div class="eyebrow">Total book · simulated</div>'
    +'<h2 style="margin-top:8px">'+bk.label+'</h2>'
    +'<p class="sub">Starting NAV <strong>$'+bk.starting_nav_usd.toLocaleString()+'</strong> · '
    +bk.contracts_per_leg+' ICE 1M SONIA contracts/leg (£'+(bk.face_value_gbp_per_leg/1e6).toFixed(1)+'M face) · '
    +'£'+bk.gbp_per_bp+'/bp · FX '+bk.gbp_usd+' · as of '+m.as_of+'</p>'
  +'<div class="statgrid">'
    +'<div class="stat"><div class="k">NAV</div><div class="v">$'+m.nav_usd.toLocaleString('en-US',{maximumFractionDigits:0})+'</div></div>'
    +'<div class="stat"><div class="k">Total P&amp;L</div><div class="v '+cls(m.total_pnl_usd)+'">'+fmtUsd(m.total_pnl_usd)+'</div></div>'
    +'<div class="stat"><div class="k">MTD return</div><div class="v '+cls(m.mtd_return_pct)+'">'+fmtPct(m.mtd_return_pct)+'</div><div class="k" style="margin-top:4px">'+fmtUsd(m.mtd_pnl_usd)+'</div></div>'
    +'<div class="stat"><div class="k">YTD return</div><div class="v '+cls(m.ytd_return_pct)+'">'+fmtPct(m.ytd_return_pct)+'</div><div class="k" style="margin-top:4px">'+fmtUsd(m.ytd_pnl_usd)+'</div></div>'
    +'<div class="stat"><div class="k">30d ann. vol</div><div class="v sm">'+(m.vol_ann_30d_pct!=null?m.vol_ann_30d_pct.toFixed(1)+'%':'—')+'</div></div>'
    +'<div class="stat"><div class="k">30d Sharpe</div><div class="v sm">'+(m.sharpe_ann_30d!=null?m.sharpe_ann_30d.toFixed(2):'—')+'</div></div>'
    +'<div class="stat"><div class="k">Max drawdown</div><div class="v sm bad">'+fmtUsd(m.max_drawdown_usd)+'</div></div>'
    +'<div class="stat"><div class="k">ICE indicative IM</div><div class="v sm">$'+(marginUsd||0).toLocaleString()+'</div><div class="k" style="margin-top:4px">'+bk.margin_utilisation_pct+'% of NAV</div></div>'
  +'</div>'
  +'<table class="tbl"><thead><tr><th>Trade</th><th>Size</th><th>Dir</th><th>Entry</th><th>Δ</th><th>P&amp;L £</th><th>P&amp;L $</th><th>% NAV</th></tr></thead><tbody>'+tradeRows+'</tbody></table>'
  +'<div class="conv"><strong>Conventions.</strong> '+c.product+' · '+c.quote+' · '
    +'£'+c.bp_value_gbp_per_pair_per_contract+'/bp per contract per 1:1 pair → <strong>£'+bk.gbp_per_bp+'/bp</strong> at book size. '
    +c.bp_formula+' Tick '+c.tick_size_price+' (= £'+c.tick_value_gbp_per_contract+'/contract). '
    +c.margin_note+'<br><br><strong>P&amp;L bridge:</strong> '+B.pnl_bridge.note+'</div>'
  +'<p class="sub" style="margin-top:10px">Updated '+B.generated_utc+' · Not investment advice.</p>';
}

fetch('book_summary.json').then(r=>{ if(!r.ok) throw new Error(r.statusText); return r.json(); }).then(renderBook).catch(()=>{
  if (BOOK_FALLBACK) renderBook(BOOK_FALLBACK);
  else document.getElementById('bookSection').textContent = 'Book summary unavailable — run analyze_spread_trades.py';
});

fetch('trades_index.json').then(r=>r.json()).then(INDEX=>{
  const el = document.getElementById('tradeCards');
  el.className = '';
  el.innerHTML = '';
  INDEX.trades.forEach(t=>{
    const pnlCls = t.pnl_gbp > 0.5 ? 'good' : t.pnl_gbp < -0.5 ? 'bad' : '';
    el.innerHTML += '<a class="card featured" href="'+t.detail_page+'"><h2>'+t.label+'</h2><p>'+t.position+'</p>'
      + (t.position_size ? '<p style="font-size:12px;color:var(--mut);margin:0 0 8px">'+t.position_size+'</p>' : '')
      + '<span class="pill live">● '+t.direction+'</span>'
      + '<span style="display:block;margin-top:10px;font-size:13px">P&amp;L <span class="'+pnlCls+'">'+(t.pnl_gbp>=0?'+':'')+'£'+Math.abs(t.pnl_gbp).toLocaleString('en-GB',{maximumFractionDigits:0})+'</span></span></a>';
  });
}).catch(()=>{
  document.getElementById('tradeCards').textContent = 'Trade data unavailable';
});
</script>
</body></html>"""


def trade_configs() -> list[dict]:
    configs = []
    for path in sorted(TRADES_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            configs.append(json.load(f))
    return configs


def build_portal_html() -> str:
    book_path = ROOT / "book_summary.json"
    fallback = "null"
    if book_path.exists():
        fallback = json.dumps(json.loads(book_path.read_text(encoding="utf-8")))
    return PORTAL_HTML.replace("__BOOK_FALLBACK__", fallback)


def main() -> None:
    outputs: list[tuple[str, str]] = [
        ("trade_tracker.html", HUB_HTML),
        ("portal.html", build_portal_html()),
    ]

    for cfg in trade_configs():
        data_file = f"{cfg['trade_id']}_trade_data.json"
        page = DETAIL_HTML.replace("__PAGE_TITLE__", f"{cfg['label']} · live tracker").replace(
            "__DATA_FILE__", data_file
        )
        outputs.append((cfg["detail_page"], page))

    stale = [
        "trade_jul27_dec26.html",
        "trade_jul27_dec27.html",
        "jul27_dec26_steepener_trade_data.json",
        "jul27_dec27_flattener_trade_data.json",
    ]
    for name in stale:
        for prefix in ("", "docs/"):
            p = ROOT / prefix / name
            if p.exists():
                p.unlink()
                print(f"Removed stale {p}")

    for name, html in outputs:
        for prefix in ("", "docs/"):
            out = ROOT / prefix / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            print(f"Wrote {out}")

    if INDEX_FILE.exists():
        sync_trade_json_to_docs()


def sync_trade_json_to_docs() -> None:
    """Copy trade JSON into docs/ for GitHub Pages."""
    docs = ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INDEX_FILE, docs / "trades_index.json")
    with INDEX_FILE.open(encoding="utf-8") as f:
        index = json.load(f)
    for t in index.get("trades", []):
        src = ROOT / t["data_file"]
        if src.exists():
            shutil.copy2(src, docs / t["data_file"])
    book_summary = ROOT / "book_summary.json"
    if book_summary.exists():
        shutil.copy2(book_summary, docs / "book_summary.json")
    ice_margins = ROOT / "ice_sonia_margins.json"
    if ice_margins.exists():
        shutil.copy2(ice_margins, docs / "ice_sonia_margins.json")
    book_cfg = ROOT / "book.json"
    if book_cfg.exists():
        shutil.copy2(book_cfg, docs / "book.json")
    print(f"Synced trade JSON → {docs}")


if __name__ == "__main__":
    main()
