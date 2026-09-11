#!/usr/bin/env python3
"""Build the static equity-derivatives risk dashboard."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = [ROOT / "equity_derivatives.html", ROOT / "docs" / "equity_derivatives.html"]

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="#07111f"/>
<title>Supra · Equity derivatives risk monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#07111f;--panel:#0d1b2d;--panel2:#10233a;--line:#213b59;--ink:#edf5ff;--mut:#8fa6bf;--cyan:#4fd1c5;--blue:#57a5ff;--violet:#b794f4;--orange:#ffb454;--green:#4ade80;--red:#fb7185}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 80% -10%,#17395d 0,transparent 35%),var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif}
.wrap{max-width:1320px;margin:auto;padding:18px 16px 64px}.nav{font-size:13px;margin-bottom:12px}.nav a,a{color:var(--cyan);text-decoration:none}
header{border:1px solid var(--line);background:linear-gradient(135deg,rgba(16,35,58,.98),rgba(10,24,40,.98));border-radius:18px;padding:22px;margin-bottom:14px}
.eyebrow,.section-title{font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--mut)} h1{font-size:clamp(24px,4vw,38px);margin:6px 0}.sub{color:var(--mut);font-size:13px;line-height:1.55}.pills{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.pill{border:1px solid var(--line);border-radius:99px;padding:5px 9px;color:var(--mut);font-size:11px}.pill.live{color:var(--green);border-color:rgba(74,222,128,.45)}
.grid{display:grid;gap:12px}.summary{grid-template-columns:repeat(4,1fr)}.riskgrid{grid-template-columns:1.1fr .9fr}.position-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.card,.position{background:rgba(13,27,45,.96);border:1px solid var(--line);border-radius:16px;padding:15px}.stat-label{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em}.stat{font-size:25px;font-weight:750;margin-top:5px;font-variant-numeric:tabular-nums}.sm{font-size:18px}
.section-title{margin:22px 2px 8px}.tablewrap{overflow:auto}.tbl{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}.tbl th,.tbl td{padding:8px 7px;border-bottom:1px solid rgba(33,59,89,.75);text-align:right;font-variant-numeric:tabular-nums}.tbl th{color:var(--mut);font-weight:600}.tbl th:first-child,.tbl td:first-child,.tbl th:nth-child(2),.tbl td:nth-child(2){text-align:left}
.position{padding:0;overflow:hidden}.position-head{padding:16px;background:linear-gradient(135deg,rgba(20,49,79,.9),rgba(13,27,45,.5));border-bottom:1px solid var(--line)}.position-head h2{font-size:18px;margin:4px 0 5px}.position-body{padding:14px}.mini-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.mini{background:var(--panel2);border:1px solid rgba(33,59,89,.8);border-radius:11px;padding:10px}.mini .v{font-size:16px;font-weight:700;margin-top:3px;font-variant-numeric:tabular-nums}.good{color:var(--green)}.bad{color:var(--red)}.neu{color:var(--ink)}
.callout{border-left:3px solid var(--cyan);background:rgba(79,209,197,.07);padding:10px 12px;margin:12px 0;border-radius:4px 10px 10px 4px;font-size:12px;line-height:1.55;color:#c9d9e9}.chart{height:220px;position:relative;margin-top:12px}.chart.short{height:180px}.legend-note{font-size:10px;color:var(--mut);line-height:1.45;margin-top:8px}.loading{padding:45px;text-align:center;color:var(--mut)}.err{color:var(--red)}
@media(max-width:1000px){.position-grid,.riskgrid{grid-template-columns:1fr}}@media(max-width:720px){.summary{grid-template-columns:repeat(2,1fr)}.mini-grid{grid-template-columns:repeat(2,1fr)}.wrap{padding:12px 10px 50px}.position-body{padding:10px}.stat{font-size:21px}}
</style>
</head>
<body><div class="wrap">
<div class="nav"><a href="portal.html">← Markets portal</a></div>
<header>
  <div class="eyebrow">Supra Fund Management · decision dashboard</div>
  <h1>Equity derivatives risk monitor</h1>
  <div class="sub">Leg-level Greeks, implied volatility repricing, skew, liquidity and prior-session P&amp;L attribution. Current value is shown for risk context—not trade P&amp;L, because entry premiums were not supplied.</div>
  <div class="pills" id="pills"></div>
</header>
<div id="loading" class="loading">Loading option risk…</div>
<main id="content" style="display:none">
  <div class="grid summary" id="summary"></div>
  <div class="section-title">Risk by underlying</div>
  <div class="grid riskgrid">
    <div class="card"><div class="tablewrap"><table class="tbl" id="riskTbl"><thead><tr><th>Underlying</th><th>Δ shares</th><th>Γ shares/$</th><th>Θ $/day</th><th>Vega $/vol pt</th></tr></thead><tbody></tbody></table></div></div>
    <div class="card"><div class="stat-label">Prior-session option move decomposition</div><div class="chart short"><canvas id="portfolioDecomp"></canvas></div></div>
  </div>
  <div class="section-title">Position monitors</div>
  <div class="grid position-grid" id="positions"></div>
  <p class="legend-note" id="notes"></p>
</main>
</div>
<script>
const colors=['#57a5ff','#ffb454','#b794f4','#4ade80','#fb7185'];
const money=v=>v==null?'—':(v<0?'−':'')+'$'+Math.abs(v).toLocaleString('en-US',{maximumFractionDigits:2});
const signed=(v,d=1)=>v==null?'—':(v>0?'+':'')+Number(v).toFixed(d);
const pct=(v,d=1)=>v==null?'—':Number(v).toFixed(d)+'%';
const cls=v=>v>0.01?'good':v<-.01?'bad':'neu';
const shortSym=s=>s.replace('$','').split('|').slice(0,1).join('');
const sideLabel=l=>(l.side==='long'?'Long ':'Short ')+l.strike+(l.option_type==='C'?'C':'P');
const strategy=s=>({put_debit_spread:'Put debit spread',call_debit_spread:'Call debit spread',long_call:'Long call'})[s]||s;

function decompValues(x){return ['delta_usd','gamma_usd','vega_usd','theta_usd','residual_usd'].map(k=>x[k]||0)}
function chartOpts(){return {responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#8fa6bf',boxWidth:11,font:{size:10}}}},scales:{x:{ticks:{color:'#8fa6bf',maxTicksLimit:6},grid:{color:'rgba(33,59,89,.35)'}},y:{ticks:{color:'#8fa6bf'},grid:{color:'rgba(33,59,89,.35)'}}}}}
function makeDecomp(canvas,x){
  new Chart(canvas,{type:'bar',data:{labels:['Delta','Gamma','Vega','Theta','Residual'],datasets:[{data:decompValues(x),backgroundColor:decompValues(x).map(v=>v>=0?'rgba(74,222,128,.75)':'rgba(251,113,133,.75)')}]},options:{...chartOpts(),plugins:{legend:{display:false}}}});
}
function diagnostic(p){
  const legs=p.legs, d=p.daily_decomposition||{}, q=p.quote||{}, pay=p.payoff||{};
  const spotDelta=legs[0]?.daily_decomposition?.spot_change;
  let parts=[`${p.display_underlying||p.underlying} ${signed(spotDelta,2)} on the session.`];
  if(p.iv_structure) parts.push(`Long-minus-short IV is ${signed(p.iv_structure.long_minus_short_iv_points,2)} vol pts, ${signed(p.iv_structure.daily_change_points,2)} today.`);
  else parts.push(`IV is ${pct(legs[0].current.iv_pct,2)}, ${signed(legs[0].daily_decomposition?.iv_change_points,2)} vol pts today.`);
  parts.push(`Last-price move ${money(d.actual_usd)}; delta/vega/theta explain ${money((d.delta_usd||0)+(d.vega_usd||0)+(d.theta_usd||0))} before gamma and residual.`);
  if(pay.mark_pct_of_max_payoff!=null) parts.push(`Mid marks at ${pct(pay.mark_pct_of_max_payoff)} of maximum payoff; ${pct(pay.intrinsic_pct_of_max_payoff)} is intrinsic.`);
  if(q.width_usd!=null) parts.push(`Executable spread is ${money(q.bid_usd)} / ${money(q.ask_usd)} (${money(q.width_usd)} wide).`);
  if(p.underlying==='$VIX') parts.push('VIX options reference the forward/settlement complex; spot VIX is context, not a complete pricing input.');
  return parts.join(' ');
}
function renderPosition(p,idx){
  const id='p'+idx, pay=p.payoff||{}, g=p.net_greeks, q=p.quote;
  const el=document.createElement('section'); el.className='position'; el.id=p.id;
  el.innerHTML=`<div class="position-head"><div class="eyebrow">${strategy(p.strategy)} · ${p.expiration}</div><h2>${p.label}</h2><div class="sub">${p.display_underlying||p.underlying} ${Number(p.underlying_price).toFixed(2)} · ${p.days_to_expiration} DTE · EOD ${p.as_of}</div></div>
  <div class="position-body">
    <div class="mini-grid">
      <div class="mini"><div class="stat-label">Current mid</div><div class="v">${money(q.mid_usd)}</div><div class="legend-note">${money(q.bid_usd)} / ${money(q.ask_usd)}</div></div>
      <div class="mini"><div class="stat-label">Net delta</div><div class="v ${cls(g.delta_shares)}">${signed(g.delta_shares,1)} sh</div></div>
      <div class="mini"><div class="stat-label">Theta</div><div class="v ${cls(g.theta_usd_per_day)}">${money(g.theta_usd_per_day)}/d</div></div>
      <div class="mini"><div class="stat-label">Net vega</div><div class="v ${cls(g.vega_usd_per_vol_point)}">${money(g.vega_usd_per_vol_point)}/pt</div></div>
      <div class="mini"><div class="stat-label">Net gamma</div><div class="v ${cls(g.gamma_shares_per_dollar)}">${signed(g.gamma_shares_per_dollar,2)} sh/$</div></div>
      <div class="mini"><div class="stat-label">Intrinsic</div><div class="v">${money(pay.intrinsic_value_usd)}</div></div>
      <div class="mini"><div class="stat-label">Extrinsic</div><div class="v">${money(pay.extrinsic_value_usd)}</div></div>
      <div class="mini"><div class="stat-label">Daily option move</div><div class="v ${cls(p.daily_decomposition.actual_usd)}">${money(p.daily_decomposition.actual_usd)}</div></div>
    </div>
    <div class="callout">${diagnostic(p)}</div>
    <div class="tablewrap"><table class="tbl"><thead><tr><th>Leg</th><th>Qty</th><th>Last</th><th>Bid / Mid / Ask</th><th>IV</th><th>ΔIV</th><th>Delta</th><th>Gamma</th><th>Theta $/d</th><th>Vega $/pt</th><th>Vol</th><th>OI</th></tr></thead><tbody>
    ${p.legs.map(l=>{const c=l.current,cg=c.cash_greeks,dd=l.daily_decomposition||{};return `<tr><td>${sideLabel(l)}</td><td>${l.signed_quantity>0?'+':''}${l.signed_quantity}</td><td>${money(c.last*100)}</td><td>${money(c.bid*100)} / ${money(c.midpoint*100)} / ${money(c.ask*100)}</td><td>${pct(c.iv_pct,2)}</td><td class="${cls(dd.iv_change_points)}">${signed(dd.iv_change_points,2)}</td><td>${signed(c.delta,3)}</td><td>${signed(c.gamma,4)}</td><td class="${cls(cg.theta_usd_per_day)}">${money(cg.theta_usd_per_day)}</td><td class="${cls(cg.vega_usd_per_vol_point)}">${money(cg.vega_usd_per_vol_point)}</td><td>${Number(c.volume||0).toLocaleString()}</td><td>${Number(c.open_interest||0).toLocaleString()}</td></tr>`}).join('')}
    </tbody></table></div>
    <div class="grid riskgrid">
      <div><div class="stat-label" style="margin-top:13px">Leg implied volatility</div><div class="chart"><canvas id="${id}iv"></canvas></div></div>
      <div><div class="stat-label" style="margin-top:13px">Prior-session P&amp;L decomposition</div><div class="chart"><canvas id="${id}dec"></canvas></div></div>
    </div>
  </div>`;
  document.getElementById('positions').appendChild(el);
  const allDates=[...new Set(p.legs.flatMap(l=>l.history.map(r=>r.date)))].sort().slice(-30);
  const ivSets=p.legs.map((l,j)=>{const by=Object.fromEntries(l.history.map(r=>[r.date,r.iv==null?null:r.iv*100]));return {label:sideLabel(l),data:allDates.map(d=>by[d]??null),borderColor:colors[j],pointRadius:1.8,tension:.18,spanGaps:true}});
  new Chart(document.getElementById(id+'iv'),{type:'line',data:{labels:allDates,datasets:ivSets},options:chartOpts()});
  makeDecomp(document.getElementById(id+'dec'),p.daily_decomposition);
}
function render(D){
  document.getElementById('loading').style.display='none'; document.getElementById('content').style.display='block';
  document.getElementById('pills').innerHTML=`<span class="pill live">● Barchart EOD through ${D.portfolio.as_of}</span><span class="pill">${D.portfolio.position_count} positions · ${D.positions.reduce((n,p)=>n+p.legs.length,0)} legs</span><span class="pill">Updated ${D.generated_utc}</span>`;
  const cg=D.portfolio.cross_asset_cash_greeks,dd=D.portfolio.daily_decomposition;
  document.getElementById('summary').innerHTML=[
    ['Positions',D.portfolio.position_count,'neu'],['Combined theta',money(cg.theta_usd_per_day)+'/day',cls(cg.theta_usd_per_day)],['Combined vega',money(cg.vega_usd_per_vol_point)+'/vol pt',cls(cg.vega_usd_per_vol_point)],['Prior-session option move',money(dd.actual_usd),cls(dd.actual_usd)]
  ].map(x=>`<div class="card"><div class="stat-label">${x[0]}</div><div class="stat ${x[2]}">${x[1]}</div></div>`).join('');
  const rt=document.querySelector('#riskTbl tbody');
  Object.entries(D.portfolio.risk_by_underlying).forEach(([u,g])=>rt.innerHTML+=`<tr><td>${u.replace('$','')}</td><td>${signed(g.delta_shares,1)}</td><td>${signed(g.gamma_shares_per_dollar,2)}</td><td class="${cls(g.theta_usd_per_day)}">${money(g.theta_usd_per_day)}</td><td class="${cls(g.vega_usd_per_vol_point)}">${money(g.vega_usd_per_vol_point)}</td></tr>`);
  makeDecomp(document.getElementById('portfolioDecomp'),dd);
  D.positions.forEach(renderPosition);
  document.getElementById('notes').textContent=D.notes.join(' ');
}
fetch('equity_derivatives_data.json?ts='+Date.now()).then(r=>{if(!r.ok)throw Error(r.statusText);return r.json()}).then(render).catch(e=>{const x=document.getElementById('loading');x.className='loading err';x.textContent='Could not load option risk data: '+e.message});
</script>
</body></html>"""


def main() -> None:
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(HTML, encoding="utf-8")
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
