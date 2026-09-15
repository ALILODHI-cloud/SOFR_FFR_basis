"""Generate a single-file, responsive dashboard (spy_vol.html) for SPY realized
monthly volatility, with data embedded from spy_vol_data.json."""
import json

with open("spy_vol_data.json") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>SPY Realized Monthly Volatility &middot; 20-Year History</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%F0%9F%93%89</text></svg>"/>
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
  background:linear-gradient(160deg,#16203200,#1a2740);margin-bottom:16px;background-color:var(--card)}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(20px,5vw,30px);margin:6px 0 4px;line-height:1.15}
.sub{color:var(--mut);font-size:14px}
.verdict{margin-top:14px;padding:14px 16px;border-radius:14px;background:#2a1a0f;
  border:1px solid #5a3f1f;font-size:15px;line-height:1.5}
.verdict b{color:var(--warn)}
.grid{display:grid;gap:14px}
@media(min-width:760px){.cols-3{grid-template-columns:repeat(3,1fr)}.cols-2{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.card h2{font-size:15px;margin:0 0 2px;letter-spacing:.02em}
.card .hint{color:var(--mut);font-size:12.5px;margin:0 0 12px}
.stat{font-size:30px;font-weight:700;line-height:1.05}
.stat.amber{color:var(--warn)} .stat.red{color:var(--bad)} .stat.blue{color:var(--acc2)} .stat.green{color:var(--good)}
.statlbl{color:var(--mut);font-size:12px;margin-top:2px}
.chartbox{position:relative;width:100%;height:300px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:26px 4px 10px}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--chip);border:1px solid var(--line);
  padding:6px 12px;border-radius:30px;font-size:12.5px;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}
tr.win td{color:var(--warn);font-weight:700}
.foot{color:var(--mut);font-size:12px;margin-top:26px;line-height:1.6}
.note{font-size:12px;color:var(--mut);margin-top:8px}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="eyebrow">Supra Fund Management &middot; Equity Volatility</div>
  <h1>SPY Realized Monthly Volatility &mdash; 20-Year History</h1>
  <div class="sub" id="asof"></div>
  <div class="verdict" id="verdict"></div>
  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
    <span class="pill" id="srcpill"></span>
    <span class="pill" id="rangepill"></span>
  </div>
</header>

<div class="grid cols-3">
  <div class="card"><div class="stat amber" id="kHi"></div><div class="statlbl" id="kHiLbl"></div></div>
  <div class="card"><div class="stat blue" id="kRunner"></div><div class="statlbl" id="kRunnerLbl"></div></div>
  <div class="card"><div class="stat green" id="kMed"></div><div class="statlbl">Median monthly realized vol (annualized)</div></div>
</div>

<div class="sectitle">Realized volatility through time (annualized)</div>
<div class="card"><div class="chartbox"><canvas id="ts"></canvas></div>
  <div class="note">Each point = one calendar month's annualized close-to-close realized vol, <code>sqrt(252/n &middot; &sum;r&sup2;)</code>, from daily SPY log returns.</div>
</div>

<div class="sectitle">Top 10 most volatile months</div>
<div class="card">
  <table id="tbl">
    <thead><tr><th>#</th><th>Month</th><th>Realized vol (ann.)</th><th>Std-based (ann.)</th><th>Days</th></tr></thead>
    <tbody></tbody>
  </table>
</div>

<div class="foot" id="foot"></div>

</div>
<script>
const DATA = __DATA__;
const pct = x => (x*100).toFixed(1) + '%';
const MN = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function label(ym){const [y,m]=ym.split('-');return MN[parseInt(m,10)]+' '+y;}

document.getElementById('asof').textContent = 'Generated '+DATA.generated_utc+' \u00b7 daily close-to-close log returns';
document.getElementById('srcpill').textContent = 'Source: '+DATA.source;
const w = DATA.window;
document.getElementById('rangepill').textContent = w.first_month+' \u2192 '+w.last_month+' ('+w.n_months+' months)';

const hi = DATA.highest;
document.getElementById('verdict').innerHTML =
  'Over the trailing 20 years, the highest SPY realized monthly volatility was in <b>'+label(hi.ym)+
  '</b> at <b>'+pct(hi.rv_ann)+'</b> annualized ('+pct(hi.rv_month)+' for the month, '+hi.n+' trading days).';

document.getElementById('kHi').textContent = pct(hi.rv_ann);
document.getElementById('kHiLbl').innerHTML = '<b style="color:var(--warn)">'+label(hi.ym)+'</b> &mdash; highest realized vol';
const runner = DATA.top10[1];
document.getElementById('kRunner').textContent = pct(runner.rv_ann);
document.getElementById('kRunnerLbl').innerHTML = '<b style="color:var(--acc2)">'+label(runner.ym)+'</b> &mdash; runner-up';
const rv = DATA.months.map(m=>m.rv_ann).sort((a,b)=>a-b);
const med = rv[Math.floor(rv.length/2)];
document.getElementById('kMed').textContent = pct(med);

// time series
const labels = DATA.months.map(m=>m.ym);
const series = DATA.months.map(m=>+(m.rv_ann*100).toFixed(2));
const grid = '#243043', mut='#93a1b5';
new Chart(document.getElementById('ts'),{
  type:'line',
  data:{labels,datasets:[{data:series,borderColor:'#4aa8ff',backgroundColor:'rgba(74,168,255,.12)',
    borderWidth:1.5,pointRadius:0,fill:true,tension:.2}]},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:false},tooltip:{callbacks:{
      title:i=>label(i[0].label),label:c=>'Realized vol: '+c.parsed.y.toFixed(1)+'%'}}},
    scales:{x:{ticks:{color:mut,maxTicksLimit:10,autoSkip:true},grid:{color:grid}},
      y:{ticks:{color:mut,callback:v=>v+'%'},grid:{color:grid}}}}
});

// table
const tb = document.querySelector('#tbl tbody');
DATA.top10.forEach((m,i)=>{
  const tr=document.createElement('tr'); if(i===0)tr.className='win';
  tr.innerHTML='<td>'+(i+1)+'</td><td>'+label(m.ym)+'</td><td>'+pct(m.rv_ann)+'</td><td>'+pct(m.std_ann)+'</td><td>'+m.n+'</td>';
  tb.appendChild(tr);
});

document.getElementById('foot').innerHTML =
  'Realized volatility is annualized from daily close-to-close log returns within each calendar month '+
  '(<code>rv_ann = sqrt(252/n &middot; &sum;r&sup2;)</code>; the std-based column uses <code>std(r)&middot;sqrt(252)</code>). '+
  'Window: '+w.first_price_date+' \u2192 '+w.last_price_date+', '+w.trading_days_used+' daily returns. '+
  'Data: '+DATA.source+'.';
</script>
</body>
</html>"""

html = HTML.replace("__DATA__", DATA_JSON)
with open("spy_vol.html", "w") as f:
    f.write(html)
print("Wrote spy_vol.html (" + str(len(html)) + " bytes)")
