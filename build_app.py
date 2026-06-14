"""Generate a single-file, responsive web app (index.html) with embedded data."""
import json

with open("basis_data.json") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>FFR&minus;SOFR Basis &middot; July Trade Monitor</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%F0%9F%93%88</text></svg>"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0b0f17; --card:#131a26; --card2:#0f1521; --line:#243043; --ink:#e8eef7;
  --mut:#93a1b5; --acc:#39d98a; --acc2:#4aa8ff; --warn:#ffb84a; --bad:#ff6b6b; --good:#39d98a;
  --chip:#1b2536;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--acc2);text-decoration:none}
.wrap{max-width:1100px;margin:0 auto;padding:16px 16px 64px}
header{padding:22px 18px;border:1px solid var(--line);border-radius:18px;
  background:linear-gradient(160deg,#16203200,#1a2740);margin-bottom:16px;
  background-color:var(--card)}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(20px,5vw,30px);margin:6px 0 4px;line-height:1.15}
.sub{color:var(--mut);font-size:14px}
.verdict{margin-top:14px;padding:14px 16px;border-radius:14px;background:#0f2a1e;
  border:1px solid #1f5a3f;font-size:15px;line-height:1.5}
.verdict b{color:var(--good)}
.grid{display:grid;gap:14px}
@media(min-width:760px){.cols-3{grid-template-columns:repeat(3,1fr)}.cols-2{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.card h2{font-size:15px;margin:0 0 2px;letter-spacing:.02em}
.card .hint{color:var(--mut);font-size:12.5px;margin:0 0 12px}
.stat{font-size:30px;font-weight:700;line-height:1.05}
.stat.green{color:var(--good)} .stat.amber{color:var(--warn)} .stat.red{color:var(--bad)} .stat.blue{color:var(--acc2)}
.statlbl{color:var(--mut);font-size:12px;margin-top:2px}
.kpis{display:flex;flex-wrap:wrap;gap:18px;margin-top:6px}
.kpi{min-width:90px}
.chartbox{position:relative;width:100%;height:260px}
.chartbox.tall{height:300px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);
  margin:26px 4px 10px}
.row{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px dashed var(--line);font-size:14px}
.row:last-child{border-bottom:0}
.row .v{font-variant-numeric:tabular-nums;font-weight:600}
.pos{color:var(--good)} .neg{color:var(--bad)}
.bull li{margin:7px 0;line-height:1.5}
.bull li b{color:var(--ink)}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;background:var(--chip);
  color:var(--mut);border:1px solid var(--line);margin:2px 4px 2px 0}
.src{font-size:12px;color:var(--mut)}
.tradebox{border:1px solid #2a3c5a;background:linear-gradient(180deg,#101a2c,#0e1626);border-radius:16px;padding:16px}
.legline{display:flex;gap:8px;align-items:center;margin:6px 0;font-size:14px}
.dot{width:10px;height:10px;border-radius:50%;flex:0 0 auto}
.foot{color:var(--mut);font-size:12px;margin-top:26px;line-height:1.6}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--chip);border:1px solid var(--line);
  padding:6px 12px;border-radius:30px;font-size:12.5px;color:var(--mut)}
.btn{cursor:pointer;background:var(--chip);color:var(--ink);border:1px solid var(--line);
  padding:8px 14px;border-radius:10px;font-size:13px}
.btn:active{transform:scale(.98)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}
.note{font-size:12px;color:var(--mut);margin-top:8px}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="eyebrow">Supra Fund Management &middot; Money Markets</div>
  <h1>FFR&minus;SOFR Basis &mdash; Monthly Average Distribution &amp; July Trade</h1>
  <div class="sub" id="asof"></div>
  <div class="verdict" id="verdict"></div>
  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
    <span class="pill">Source: NY Fed reference rates (mirrors FRED EFFR/SOFR)</span>
    <span class="pill" id="rangepill"></span>
    <button class="btn" id="refresh">&#x21bb; Try live refresh</button>
  </div>
</header>

<div class="sectitle">1 &middot; Where &minus;1bp sits in the distribution</div>
<div class="grid cols-3">
  <div class="card">
    <h2>Percentile of &minus;1bp</h2>
    <p class="hint">Share of historical monthly averages below the priced level</p>
    <div class="stat amber" id="pctile"></div>
    <div class="statlbl" id="pctileSub"></div>
  </div>
  <div class="card">
    <h2>Distribution center</h2>
    <p class="hint">Since SOFR inception (Apr 2018)</p>
    <div class="kpis">
      <div class="kpi"><div class="stat green" id="mean"></div><div class="statlbl">Mean (bp)</div></div>
      <div class="kpi"><div class="stat green" id="median"></div><div class="statlbl">Median (bp)</div></div>
      <div class="kpi"><div class="stat blue" id="std"></div><div class="statlbl">Std (bp)</div></div>
    </div>
    <div class="note" id="rangeNote"></div>
  </div>
  <div class="card">
    <h2>Right now</h2>
    <p class="hint">Latest print &amp; recent run-rate</p>
    <div class="kpis">
      <div class="kpi"><div class="stat" id="lastDaily"></div><div class="statlbl" id="lastDailyLbl"></div></div>
      <div class="kpi"><div class="stat" id="l3m"></div><div class="statlbl">Last 3m avg (bp)</div></div>
    </div>
  </div>
</div>

<div class="card" style="margin-top:14px">
  <h2>Distribution of monthly-average FFR&minus;SOFR (1bp bins)</h2>
  <p class="hint">Each bar = number of months. Markers show the priced &minus;1bp and the historical mean.</p>
  <div class="chartbox tall"><canvas id="hist"></canvas></div>
</div>

<div class="sectitle">2 &middot; History since SOFR inception</div>
<div class="card">
  <h2>Monthly-average basis (bp), Apr 2018 &rarr; now</h2>
  <p class="hint">EFFR minus SOFR. Negative = SOFR rich / funding pressure. The last point is month-to-date.</p>
  <div class="chartbox tall"><canvas id="ts"></canvas></div>
</div>

<div class="sectitle">3 &middot; Autocorrelation &mdash; does the past predict the future?</div>
<div class="grid cols-2">
  <div class="card">
    <h2>Autocorrelation (ACF) &amp; partial (PACF)</h2>
    <p class="hint">Bars beyond the dashed 95% band are statistically significant.</p>
    <div class="chartbox"><canvas id="acf"></canvas></div>
  </div>
  <div class="card">
    <h2>Predictive regressions</h2>
    <p class="hint">Next month's average regressed on the recent past.</p>
    <div class="row"><span>Last month &rarr; next month &nbsp;<span class="tag">AR(1)</span></span><span class="v" id="ar1b"></span></div>
    <div class="row"><span>&nbsp;&nbsp;t&nbsp;stat / R&sup2;</span><span class="v" id="ar1t"></span></div>
    <div class="row"><span>Trailing 3m avg &rarr; next month</span><span class="v" id="t3b"></span></div>
    <div class="row"><span>&nbsp;&nbsp;t&nbsp;stat / R&sup2;</span><span class="v" id="t3t"></span></div>
    <div class="row"><span><b>Implied July forecast</b> (AR1 / 3m model)</span><span class="v" id="fc"></span></div>
    <div class="note" id="acfNote"></div>
  </div>
</div>

<div class="sectitle">4 &middot; July seasonality</div>
<div class="grid cols-2">
  <div class="card">
    <h2>July monthly average by year (bp)</h2>
    <p class="hint">How the basis has behaved specifically in July.</p>
    <div class="chartbox"><canvas id="july"></canvas></div>
  </div>
  <div class="card">
    <h2>July readout</h2>
    <div id="julyTable"></div>
  </div>
</div>

<div class="sectitle">5 &middot; The trade &mdash; long July FFR&minus;SOFR (sell the &minus;1bp)</div>
<div class="tradebox">
  <div class="grid cols-3" style="margin-bottom:6px">
    <div class="card" style="background:var(--card2)"><div class="statlbl">Priced now</div><div class="stat amber">&minus;1.0 bp</div></div>
    <div class="card" style="background:var(--card2)"><div class="statlbl">Fair value (Barclays)</div><div class="stat green">+2 bp</div></div>
    <div class="card" style="background:var(--card2)"><div class="statlbl">Our model July E[&middot;]</div><div class="stat green" id="tradeFc"></div></div>
  </div>
  <p style="margin:6px 2px 2px;line-height:1.55">
    <b>View:</b> Go <b>long July FFR&minus;SOFR</b> (i.e. long Barclays "SOFR/FF") at an entry of <b>&minus;1bp</b>,
    targeting <b>+2bp</b>. The market is paying you to take the side that history, mean-reversion and the funding
    backdrop all favour.</p>

  <div class="grid cols-2" style="margin-top:8px">
    <div class="card">
      <h2>Why it works &mdash; our data</h2>
      <ul class="bull" id="ourCase"></ul>
    </div>
    <div class="card">
      <h2>Why it works &mdash; Barclays money markets</h2>
      <ul class="bull">
        <li><b>"Soft funding is an everything story"</b> (5 Jun): abundant cash (MMF &gt;$8trn), expanded dealer
          intermediation post-SLR reform, and softer leverage demand make smooth repo "durable over the months ahead."</li>
        <li><b>TGA / reserves tailwind:</b> TGA stays low for much of July; Barclays estimates <b>average July reserves
          slightly above June</b> (~$3.0&ndash;3.1trn), keeping funding soft even as the TGA peaks late in the month.</li>
        <li><b>Bill supply fear is overdone:</b> "SOFR has historically shown low sensitivity to net bill supply";
          the July build is methodical and back-loaded.</li>
        <li><b>Leg-by-leg fair value (11 Jun):</b> SOFR &asymp; &minus;6bp vs IORB, FF &asymp; &minus;4bp &rarr;
          <b>SOFR/FF fair value +2bp</b> (upside to +3bp if funds stickier) vs <b>&minus;1bp</b> priced.</li>
        <li><b>Explicit reco:</b> "we recommend going long July SOFR/FF (entry &minus;1.0bp) targeting +2bp."</li>
      </ul>
      <div class="src" style="margin-top:6px">Barclays <i>Global Rates Weekly</i>: "In the hot seat" (11 Jun 2026),
        "Shifting gears" (5 Jun), "Hope springs eternal" (28 May).</div>
    </div>
  </div>

  <div class="card" style="margin-top:8px">
    <h2>Risks</h2>
    <ul class="bull">
      <li>Quarter-end (June) funding pressure spills into early July.</li>
      <li>Earlier / larger-than-expected bill issuance ramp drains reserves and cheapens SOFR late in July.</li>
      <li>Sharp pickup in leverage demand (rates rally &rarr; convexity flows) tightens repo.</li>
      <li>Tail precedent: Sep&ndash;Dec 2025 saw the basis collapse to &minus;7 to &minus;12bp on an acute funding squeeze &mdash;
        the left tail is fat, so size accordingly.</li>
    </ul>
  </div>
</div>

<div class="foot" id="foot"></div>

</div>
<script>
const DATA = __DATA__;
const f1=(x)=>(x>=0?'+':'')+x.toFixed(1);
const f2=(x)=>(x>=0?'+':'')+x.toFixed(2);
const css=(v)=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const C={ink:css('--ink'),mut:css('--mut'),line:css('--line'),acc:css('--acc'),acc2:css('--acc2'),
  warn:css('--warn'),bad:css('--bad'),good:css('--good')};
Chart.defaults.color=C.mut; Chart.defaults.font.family="-apple-system,Segoe UI,Roboto,sans-serif";
Chart.defaults.borderColor=C.line;

function render(D){
  const s=D.stats;
  document.getElementById('asof').textContent=
    `Monthly average of EFFR \u2212 SOFR, daily data through ${D.last_daily.date}. Data generated ${D.generated_utc}.`;
  document.getElementById('rangepill').textContent=`${s.n_months} months \u00b7 ${s.start} \u2192 ${s.end}`;

  // forecasts
  const ar1=D.regressions.ar1, t3=D.regressions.trailing3m;
  const fcAR=ar1.const+ar1.beta_lag1*s.current_month_basis;       // July | June
  const fcT3=t3.const+t3.beta_avg3*s.last3m_avg;                  // July | Apr-Jun avg

  // verdict
  const above=100-s.percentile_rank_of_priced;
  document.getElementById('verdict').innerHTML=
    `The market prices July FFR&minus;SOFR at <b>&minus;1bp</b>. Since SOFR began, that sits at only the `+
    `<b>${s.percentile_rank_of_priced.toFixed(0)}th percentile</b> of monthly averages &mdash; the basis has printed `+
    `<b>above &minus;1bp in ~${above.toFixed(0)}% of months</b>, with a positive mean (${f2(s.mean)}bp) and median `+
    `(${f2(s.median)}bp). Strong month-to-month persistence (AR(1) \u03b2=${ar1.beta_lag1.toFixed(2)}) plus a firm recent `+
    `run-rate point to a July average of roughly <b>${f1(fcT3)}bp</b> &mdash; comfortably above the priced level. `+
    `<b>Lean long July FFR&minus;SOFR.</b>`;

  // section 1 cards
  const pe=document.getElementById('pctile'); pe.textContent=s.percentile_rank_of_priced.toFixed(0)+'th';
  document.getElementById('pctileSub').innerHTML=
    `${s.pct_months_below_priced.toFixed(0)}% of months below &minus;1bp \u00b7 ${above.toFixed(0)}% above`;
  document.getElementById('mean').textContent=f2(s.mean);
  document.getElementById('median').textContent=f2(s.median);
  document.getElementById('std').textContent=s.std.toFixed(2);
  document.getElementById('rangeNote').innerHTML=
    `Range ${f1(s.min)} to ${f1(s.max)}bp \u00b7 P5 ${f1(s.p05)} / P25 ${f1(s.p25)} / P75 ${f1(s.p75)} / P95 ${f1(s.p95)}`;
  const ld=document.getElementById('lastDaily'); ld.textContent=f1(D.last_daily.basis_bp);
  ld.className='stat '+(D.last_daily.basis_bp>=0?'green':'red');
  document.getElementById('lastDailyLbl').textContent=`Daily ${D.last_daily.date} (bp)`;
  const l3=document.getElementById('l3m'); l3.textContent=f2(s.last3m_avg);
  l3.className='stat '+(s.last3m_avg>=0?'green':'red');

  // section 3 regressions
  document.getElementById('ar1b').innerHTML=`\u03b2 = <span class="${ar1.beta_lag1>=0?'pos':'neg'}">${ar1.beta_lag1.toFixed(3)}</span>`;
  document.getElementById('ar1t').textContent=`t=${ar1.t_lag1.toFixed(1)} \u00b7 R\u00b2=${ar1.r2.toFixed(2)}`;
  document.getElementById('t3b').innerHTML=`\u03b2 = <span class="${t3.beta_avg3>=0?'pos':'neg'}">${t3.beta_avg3.toFixed(3)}</span>`;
  document.getElementById('t3t').textContent=`t=${t3.t_avg3.toFixed(1)} \u00b7 R\u00b2=${t3.r2.toFixed(2)}`;
  document.getElementById('fc').innerHTML=`<span class="pos">${f1(fcAR)} / ${f1(fcT3)} bp</span>`;
  document.getElementById('acfNote').innerHTML=
    `Persistence is real and decays by ~lag 2 (PACF lag1 ${D.pacf.lag_1.toFixed(2)}, lag2 ${D.pacf.lag_2.toFixed(2)}, `+
    `lag3 ${D.pacf.lag_3.toFixed(2)}): last month and the trailing quarter both carry information, deeper lags add little.`;
  document.getElementById('tradeFc').textContent=f1(fcT3)+' bp';

  // our-case bullets
  document.getElementById('ourCase').innerHTML=[
    `<b>&minus;1bp is cheap:</b> only the ${s.percentile_rank_of_priced.toFixed(0)}th percentile of ${s.n_months} months; ~${above.toFixed(0)}% printed higher.`,
    `<b>Positive central tendency:</b> mean ${f2(s.mean)}bp, median ${f2(s.median)}bp &mdash; the distribution is centred above zero, not at &minus;1.`,
    `<b>Persistence:</b> AR(1) \u03b2=${ar1.beta_lag1.toFixed(2)} (t=${ar1.t_lag1.toFixed(1)}); trailing-3m \u03b2=${t3.beta_avg3.toFixed(2)} (t=${t3.t_avg3.toFixed(1)}). The past forecasts the future.`,
    `<b>Firm run-rate:</b> last 3m average ${f2(s.last3m_avg)}bp and May ${'+4.3'}bp \u2192 model July E[\u00b7] = ${f1(fcAR)}/${f1(fcT3)}bp, both above &minus;1.`,
    `<b>Asymmetry:</b> entry &minus;1 vs target +2 is ~3bp upside against a base rate where most months sit higher.`
  ].map(x=>`<li>${x}</li>`).join('');

  // ---- charts ----
  const H=D.histogram;
  const centers=H.map(b=>(b.bin_lo+b.bin_hi)/2);
  const barCol=H.map(b=>{
    if(s.priced>=b.bin_lo && s.priced<b.bin_hi) return C.warn;
    if(s.mean>=b.bin_lo && s.mean<b.bin_hi) return C.good;
    return 'rgba(74,168,255,.55)';
  });
  new Chart(document.getElementById('hist'),{type:'bar',
    data:{labels:centers.map(c=>c.toFixed(0)),datasets:[{data:H.map(b=>b.count),backgroundColor:barCol,
      borderRadius:3,categoryPercentage:.96,barPercentage:1.0}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},
      tooltip:{callbacks:{title:(t)=>`${t[0].label} to ${(+t[0].label+1)} bp`,label:(c)=>`${c.parsed.y} months`}}},
      scales:{x:{title:{display:true,text:'FFR\u2212SOFR monthly avg (bp)  \u2014  amber=\u22121 priced, green=mean'},
        grid:{display:false}},y:{title:{display:true,text:'months'},grid:{color:C.line}}}}});

  const M=D.monthly;
  new Chart(document.getElementById('ts'),{type:'line',
    data:{labels:M.map(p=>p.ym),datasets:[{data:M.map(p=>p.v),borderColor:C.acc2,
      borderWidth:1.6,pointRadius:0,tension:.15,fill:{target:'origin',above:'rgba(57,217,138,.10)',below:'rgba(255,107,107,.12)'}}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},
      tooltip:{callbacks:{label:(c)=>`${f2(c.parsed.y)} bp`}},
      annotation:false},
      scales:{x:{ticks:{maxTicksLimit:10,autoSkip:true},grid:{display:false}},
        y:{grid:{color:C.line},title:{display:true,text:'bp'}}}},
    plugins:[{id:'lines',afterDraw:(ch)=>{const{ctx,chartArea:a,scales}=ch;
      [[s.priced,C.warn,'\u22121 priced'],[0,C.mut,'0'],[s.mean,C.good,'mean']].forEach(([y,col,lab])=>{
        const yp=scales.y.getPixelForValue(y);ctx.save();ctx.strokeStyle=col;ctx.setLineDash([4,4]);
        ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(a.left,yp);ctx.lineTo(a.right,yp);ctx.stroke();
        ctx.setLineDash([]);ctx.fillStyle=col;ctx.font='10px sans-serif';ctx.fillText(lab,a.left+4,yp-3);ctx.restore();});}}]});

  const lags=Array.from({length:12},(_,i)=>i+1);
  const band=1.96/Math.sqrt(s.n_months);
  new Chart(document.getElementById('acf'),{type:'bar',
    data:{labels:lags,datasets:[
      {label:'ACF',data:lags.map(k=>D.acf['lag_'+k]),backgroundColor:'rgba(74,168,255,.75)',borderRadius:2},
      {label:'PACF',data:lags.map(k=>D.pacf['lag_'+k]),backgroundColor:'rgba(57,217,138,.7)',borderRadius:2}]},
    options:{maintainAspectRatio:false,plugins:{legend:{position:'top'}},
      scales:{x:{title:{display:true,text:'lag (months)'},grid:{display:false}},
        y:{grid:{color:C.line},suggestedMin:-0.2,suggestedMax:1}}},
    plugins:[{id:'band',afterDraw:(ch)=>{const{ctx,chartArea:a,scales}=ch;[band,-band].forEach(b=>{
      const yp=scales.y.getPixelForValue(b);ctx.save();ctx.strokeStyle=C.warn;ctx.setLineDash([3,3]);
      ctx.beginPath();ctx.moveTo(a.left,yp);ctx.lineTo(a.right,yp);ctx.stroke();ctx.restore();});}}]});

  const J=D.july;
  new Chart(document.getElementById('july'),{type:'bar',
    data:{labels:J.years,datasets:[{data:J.values,backgroundColor:J.values.map(v=>v>=0?'rgba(57,217,138,.8)':'rgba(255,107,107,.8)'),borderRadius:3}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:(c)=>f2(c.parsed.y)+' bp'}}},
      scales:{x:{grid:{display:false}},y:{grid:{color:C.line},title:{display:true,text:'bp'}}}},
    plugins:[{id:'z',afterDraw:(ch)=>{const{ctx,chartArea:a,scales}=ch;const yp=scales.y.getPixelForValue(-1);
      ctx.save();ctx.strokeStyle=C.warn;ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(a.left,yp);ctx.lineTo(a.right,yp);ctx.stroke();
      ctx.fillStyle=C.warn;ctx.font='10px sans-serif';ctx.fillText('\u22121 priced',a.left+4,yp-3);ctx.restore();}}]});

  // july table
  let rows=J.years.map((y,i)=>`<div class="row"><span>July ${y}</span><span class="v ${J.values[i]>=0?'pos':'neg'}">${f2(J.values[i])} bp</span></div>`).join('');
  rows+=`<div class="row"><span><b>Mean / Median</b></span><span class="v">${f2(J.mean)} / ${f2(J.median)} bp</span></div>`;
  rows+=`<div class="row"><span><b>Model July E[\u00b7] (AR1 / 3m)</b></span><span class="v pos">${f1(fcAR)} / ${f1(fcT3)} bp</span></div>`;
  document.getElementById('julyTable').innerHTML=rows;

  document.getElementById('foot').innerHTML=
    `<b>Definition.</b> ${D.definition}. Positive = funds above SOFR (funding soft); negative = SOFR rich (funding tight). `+
    `<b>Data.</b> NY Fed published EFFR &amp; SOFR (identical to FRED series). Monthly figures are calendar-month means of daily fixings; `+
    `the latest month is month-to-date. <b>Method.</b> Percentile = share of monthly averages below &minus;1bp; ACF/PACF and OLS on the monthly series; `+
    `forecasts apply the fitted AR(1) and trailing-3m models to the latest data. <b>Not investment advice.</b> `+
    `Trade rationale synthesises Barclays Global Rates Weekly money-market sections (28 May, 5 Jun, 11 Jun 2026).`;
}

render(DATA);

// optional live refresh straight from NY Fed (works where CORS allows)
document.getElementById('refresh').addEventListener('click',async(e)=>{
  const btn=e.target; btn.textContent='\u2026 fetching'; btn.disabled=true;
  try{
    const base='https://markets.newyorkfed.org/api/rates/';
    const [se,un]=await Promise.all([
      fetch(base+'secured/sofr/search.json?startDate=2018-04-01&endDate=2030-12-31').then(r=>r.json()),
      fetch(base+'unsecured/effr/search.json?startDate=2018-04-01&endDate=2030-12-31').then(r=>r.json())]);
    const sofr={},effr={};
    se.refRates.forEach(d=>sofr[d.effectiveDate]=+d.percentRate);
    un.refRates.forEach(d=>effr[d.effectiveDate]=+d.percentRate);
    const dates=Object.keys(effr).filter(d=>sofr[d]!=null&&d>='2018-04-03').sort();
    const daily=dates.map(d=>({d,b:(effr[d]-sofr[d])*100}));
    // monthly means
    const mm={}; daily.forEach(x=>{const k=x.d.slice(0,7);(mm[k]=mm[k]||[]).push(x.b);});
    const months=Object.keys(mm).sort();
    const monthly=months.map(k=>({ym:k,v:mm[k].reduce((a,b)=>a+b,0)/mm[k].length}));
    const arr=monthly.map(m=>m.v);const n=arr.length;
    const mean=arr.reduce((a,b)=>a+b,0)/n;const sd=Math.sqrt(arr.reduce((a,b)=>a+(b-mean)**2,0)/(n-1));
    const sorted=[...arr].sort((a,b)=>a-b);const q=p=>sorted[Math.min(n-1,Math.floor(p/100*n))];
    const below=arr.filter(v=>v< -1).length/n*100;
    const acf=k=>{const m=mean;let num=0,den=0;for(let i=0;i<n;i++)den+=(arr[i]-m)**2;for(let i=0;i<n-k;i++)num+=(arr[i]-m)*(arr[i+k]-m);return num/den;};
    const D2=JSON.parse(JSON.stringify(DATA));
    D2.last_daily={date:daily.at(-1).d,EFFR:effr[daily.at(-1).d],SOFR:sofr[daily.at(-1).d],basis_bp:daily.at(-1).b};
    D2.monthly=monthly; D2.histogram=DATA.histogram; // keep histogram bins from build
    Object.assign(D2.stats,{n_months:n,start:months[0],end:months.at(-1),mean,median:q(50),std:sd,
      min:sorted[0],max:sorted[n-1],p05:q(5),p25:q(25),p75:q(75),p95:q(95),
      pct_months_below_priced:below,percentile_rank_of_priced:below,
      current_month_basis:arr.at(-1),last3m_avg:(arr.at(-1)+arr.at(-2)+arr.at(-3))/3});
    // rebuild histogram 1bp bins
    const lo=Math.floor(sorted[0]),hi=Math.ceil(sorted[n-1]);const hist=[];
    for(let b=lo;b<hi;b++)hist.push({bin_lo:b,bin_hi:b+1,count:arr.filter(v=>v>=b&&v<b+1).length});
    D2.histogram=hist;
    for(let k=1;k<=12;k++){D2.acf['lag_'+k]=acf(k);}
    D2.generated_utc=new Date().toISOString().slice(0,16).replace('T',' ')+' UTC (live)';
    document.querySelectorAll('canvas').forEach(c=>{const ch=Chart.getChart(c);if(ch)ch.destroy();});
    render(D2);
    btn.textContent='\u2713 live data loaded';
  }catch(err){
    btn.textContent='live blocked \u2014 showing embedded data'; 
  }finally{setTimeout(()=>{btn.disabled=false;},500);}
});
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JSON)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Wrote index.html", len(html), "bytes")
