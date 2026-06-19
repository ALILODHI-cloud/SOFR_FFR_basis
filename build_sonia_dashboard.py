"""Build self-contained SONIA slope / basis dashboard from sonia_dashboard_data.json."""
import json

with open("sonia_dashboard_data.json", encoding="utf-8") as f:
    data = json.load(f)

DATA_JSON = json.dumps(data)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>1M SONIA Dec27&minus;Dec26 Slope &amp; Basis Monitor</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%C2%A3</text></svg>"/>
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
.wrap{max-width:1200px;margin:0 auto;padding:16px 16px 64px}
header{padding:22px 18px;border:1px solid var(--line);border-radius:18px;
  background:linear-gradient(160deg,#16203200,#1a2740);margin-bottom:16px;background-color:var(--card)}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(20px,5vw,30px);margin:6px 0 4px;line-height:1.15}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.grid{display:grid;gap:14px}
@media(min-width:900px){.cols-4{grid-template-columns:repeat(4,1fr)}.cols-5{grid-template-columns:repeat(5,1fr)}.cols-2{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.card h2{font-size:15px;margin:0 0 2px}
.card .hint{color:var(--mut);font-size:12.5px;margin:0 0 12px;line-height:1.45}
.stat{font-size:28px;font-weight:700;line-height:1.05;font-variant-numeric:tabular-nums}
.stat.green{color:var(--good)} .stat.amber{color:var(--warn)} .stat.red{color:var(--bad)} .stat.blue{color:var(--acc2)}
.statlbl{color:var(--mut);font-size:12px;margin-top:4px}
.chartbox{position:relative;width:100%;height:280px}
.chartbox.tall{height:320px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:22px 4px 10px}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--chip);border:1px solid var(--line);
  padding:6px 12px;border-radius:30px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.foot{color:var(--mut);font-size:12px;margin-top:24px;line-height:1.65}
.note{font-size:12px;color:var(--mut);margin-top:8px}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="eyebrow">Supra Fund Management &middot; UK Rates</div>
  <h1>1M SONIA Dec-27 &minus; Dec-26 Slope &amp; Basis Monitor</h1>
  <div class="sub" id="asof"></div>
  <div style="margin-top:12px">
    <span class="pill" id="rangePill"></span>
    <span class="pill">Futures: ICE 1M SONIA (JUZ26 / JUZ27)</span>
    <span class="pill">Spot: BoE SONIA</span>
    <span class="pill">Oil: Brent (BZ=F)</span>
  </div>
</header>

<div class="sectitle">Latest</div>
<div class="grid cols-5">
  <div class="card">
    <h2>Dec-26 implied</h2>
    <p class="hint">1M SONIA fut rate (%)</p>
    <div class="stat blue" id="kDec26"></div>
    <div class="statlbl" id="kDec26Sub"></div>
  </div>
  <div class="card">
    <h2>Dec-27 implied</h2>
    <p class="hint">1M SONIA fut rate (%)</p>
    <div class="stat blue" id="kDec27"></div>
    <div class="statlbl" id="kDec27Sub"></div>
  </div>
  <div class="card">
    <h2>Dec27 &minus; Dec26 slope</h2>
    <p class="hint">Rate-space spread (bp)</p>
    <div class="stat" id="kSlope"></div>
    <div class="statlbl" id="kSlopeSub"></div>
  </div>
  <div class="card">
    <h2>Cash&ndash;futures basis</h2>
    <p class="hint">Dec26 implied &minus; spot SONIA (bp)</p>
    <div class="stat" id="kBasis"></div>
    <div class="statlbl" id="kBasisSub"></div>
  </div>
  <div class="card">
    <h2>30d corr vs Brent</h2>
    <p class="hint">Daily slope &Delta; vs Brent % &Delta;</p>
    <div class="stat amber" id="kCorr"></div>
    <div class="statlbl">Rolling 30 business days</div>
  </div>
  <div class="card">
    <h2>Basis vol (ann.)</h2>
    <p class="hint">Stdev of daily basis &Delta;, &times;&radic;252</p>
    <div class="stat green" id="kVol"></div>
    <div class="statlbl">30-day rolling (bp)</div>
  </div>
</div>

<div class="sectitle">Implied rates (rate space)</div>
<div class="card">
  <h2>1M SONIA Dec-26 &amp; Dec-27 implied rates &mdash; last <span id="winLbl"></span> sessions</h2>
  <p class="hint">ICE futures quoted as 100 &minus; rate; plotted here as implied % rates (not prices). Hover for date &amp; value.</p>
  <div class="chartbox tall"><canvas id="ratesChart"></canvas></div>
</div>

<div class="sectitle">Dec27 &minus; Dec26 slope (rate space)</div>
<div class="card">
  <h2>Calendar slope = Dec-27 rate &minus; Dec-26 rate</h2>
  <p class="hint">Spread in rate space (bp). Positive = Dec-27 implied above Dec-26. Hover for date &amp; value.</p>
  <div class="chartbox tall"><canvas id="slopeChart"></canvas></div>
</div>

<div class="sectitle">Macro link</div>
<div class="card">
  <h2>Rolling 30-day correlation: slope change vs Brent</h2>
  <p class="hint">Correlation of daily slope change (bp) with Brent daily % return. Needs 30 observations to populate.</p>
  <div class="chartbox tall"><canvas id="corrChart"></canvas></div>
</div>

<div class="sectitle">Basis &amp; risk</div>
<div class="grid cols-2">
  <div class="card">
    <h2>Dec26 cash&ndash;futures basis (bp)</h2>
    <p class="hint">Futures implied rate minus same-day spot SONIA fixing.</p>
    <div class="chartbox"><canvas id="basisChart"></canvas></div>
  </div>
  <div class="card">
    <h2>Annualised vol of daily basis changes</h2>
    <p class="hint">30-day rolling stdev of daily basis changes, scaled to a one-year horizon (&times;&radic;252).</p>
    <div class="chartbox"><canvas id="volChart"></canvas></div>
  </div>
</div>

<div class="foot" id="foot"></div>
</div>

<script>
const DATA = __DATA__;
const f2 = (x) => (x == null || Number.isNaN(x)) ? '—' : ((x >= 0 ? '+' : '') + x.toFixed(2));
const f3 = (x) => (x == null || Number.isNaN(x)) ? '—' : x.toFixed(3);
const f1 = (x) => (x == null || Number.isNaN(x)) ? '—' : ((x >= 0 ? '+' : '') + x.toFixed(1));
const fRate = (x) => (x == null || Number.isNaN(x)) ? '—' : x.toFixed(3) + '%';
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const C = {ink:css('--ink'),mut:css('--mut'),line:css('--line'),acc:css('--acc'),acc2:css('--acc2'),
  warn:css('--warn'),bad:css('--bad'),good:css('--good')};
Chart.defaults.color = C.mut;
Chart.defaults.font.family = "-apple-system,Segoe UI,Roboto,sans-serif";
Chart.defaults.borderColor = C.line;

const D = DATA.daily;
const labels = D.map(r => r.date);
const s = DATA.summary;

document.getElementById('asof').textContent =
  `Barchart EOD through ${s.end} (pulled ${DATA.generated_utc}). ` +
  `Dec26 ${s.dec26_rate.toFixed(3)}%, Dec27 ${s.dec27_rate.toFixed(3)}%, Brent $${s.brent.toFixed(2)}.`;
document.getElementById('rangePill').textContent = `${s.n_days} sessions · ${s.start} → ${s.end}`;
document.getElementById('winLbl').textContent = s.n_days;

document.getElementById('kDec26').textContent = fRate(s.dec26_rate);
document.getElementById('kDec26Sub').textContent = `JUZ26 · px ${D.at(-1).dec26_px.toFixed(3)}`;
document.getElementById('kDec27').textContent = fRate(s.dec27_rate);
document.getElementById('kDec27Sub').textContent = `JUZ27 · px ${D.at(-1).dec27_px.toFixed(3)}`;

const kSlope = document.getElementById('kSlope');
kSlope.textContent = f1(s.slope_bp) + ' bp';
kSlope.className = 'stat ' + (s.slope_bp >= 0 ? 'green' : 'red');
document.getElementById('kSlopeSub').textContent =
  `= ${fRate(s.dec27_rate)} − ${fRate(s.dec26_rate)} · 50d μ ${f1(s.slope_mean_50d)}`;

const kBasis = document.getElementById('kBasis');
kBasis.textContent = f1(s.basis_bp) + ' bp';
kBasis.className = 'stat ' + (s.basis_bp >= 0 ? 'green' : 'red');
document.getElementById('kBasisSub').textContent = `50d mean ${f1(s.basis_mean_50d)} bp`;

document.getElementById('kCorr').textContent = s.roll_corr_30 == null ? '—' : f3(s.roll_corr_30);
document.getElementById('kVol').textContent = s.basis_vol_ann == null ? '—' : f1(s.basis_vol_ann) + ' bp';

const tipOpts = (digits=2, suffix='') => ({
  mode: 'index',
  intersect: false,
  callbacks: {
    title: (items) => items[0].label,
    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y == null ? '—' : ctx.parsed.y.toFixed(digits) + suffix}`
  }
});

const lineOpts = (yLabel, suggestedMin, suggestedMax, tip=tipOpts()) => ({
  maintainAspectRatio: false,
  interaction: {mode: 'index', intersect: false},
  plugins: {
    legend: {display: false},
    tooltip: tipOpts
  },
  scales: {
    x: {ticks: {maxTicksLimit: 10, autoSkip: true}, grid: {display: false}},
    y: {
      title: {display: true, text: yLabel},
      grid: {color: C.line},
      suggestedMin, suggestedMax
    }
  }
});

new Chart(document.getElementById('ratesChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [
      {
        label: 'Dec-26 rate (%)',
        data: D.map(r => r.dec26_rate),
        borderColor: C.acc2,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.15
      },
      {
        label: 'Dec-27 rate (%)',
        data: D.map(r => r.dec27_rate),
        borderColor: C.warn,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.15
      }
    ]
  },
  options: {
    maintainAspectRatio: false,
    interaction: {mode: 'index', intersect: false},
    plugins: {
      legend: {position: 'top'},
      tooltip: tipOpts(3, '%')
    },
    scales: {
      x: {ticks: {maxTicksLimit: 10, autoSkip: true}, grid: {display: false}},
      y: {title: {display: true, text: 'implied rate (%)'}, grid: {color: C.line}}
    }
  }
});

new Chart(document.getElementById('slopeChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Slope (bp)',
      data: D.map(r => r.slope_bp),
      borderColor: C.acc2,
      backgroundColor: 'rgba(74,168,255,.12)',
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.15,
      fill: true
    }]
  },
  options: lineOpts('bp', undefined, undefined, tipOpts(2, ' bp')),
  plugins: [{id: 'zero', afterDraw: (ch) => {
    const {ctx, chartArea: a, scales} = ch;
    const yp = scales.y.getPixelForValue(0);
    ctx.save(); ctx.strokeStyle = C.mut; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(a.left, yp); ctx.lineTo(a.right, yp); ctx.stroke();
    ctx.fillStyle = C.mut; ctx.font = '10px sans-serif'; ctx.fillText('0', a.left + 4, yp - 3);
    ctx.restore();
  }}]
});

new Chart(document.getElementById('corrChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: '30d corr',
      data: D.map(r => r.roll_corr_30),
      borderColor: C.warn,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.15,
      spanGaps: true
    }]
  },
  options: {
    ...lineOpts('correlation', -1, 1, tipOpts(3)),
    plugins: {
      legend: {display: false},
      tooltip: {
        ...tipOpts(3),
        callbacks: {
          title: (items) => items[0].label,
          label: (ctx) => `30d corr: ${ctx.parsed.y == null ? '—' : ctx.parsed.y.toFixed(3)}`
        }
      }
    }
  },
  plugins: [{id: 'bands', afterDraw: (ch) => {
    const {ctx, chartArea: a, scales} = ch;
    [-0.5, 0, 0.5].forEach(v => {
      const yp = scales.y.getPixelForValue(v);
      ctx.save(); ctx.strokeStyle = v === 0 ? C.mut : 'rgba(147,161,181,.35)'; ctx.setLineDash([3,3]);
      ctx.beginPath(); ctx.moveTo(a.left, yp); ctx.lineTo(a.right, yp); ctx.stroke(); ctx.restore();
    });
  }}]
});

new Chart(document.getElementById('basisChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Basis (bp)',
      data: D.map(r => r.basis_bp),
      borderColor: C.acc,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.15,
      fill: {target: 'origin', above: 'rgba(57,217,138,.08)', below: 'rgba(255,107,107,.10)'}
    }]
  },
  options: lineOpts('bp', undefined, undefined, tipOpts(2, ' bp'))
});

new Chart(document.getElementById('volChart'), {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Ann. vol (bp)',
      data: D.map(r => r.basis_vol_ann),
      borderColor: C.good,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 5,
      tension: 0.15,
      spanGaps: true
    }]
  },
  options: lineOpts('bp (ann.)', 0, undefined, tipOpts(2, ' bp'))
});

document.getElementById('foot').innerHTML =
  `<b>Definitions.</b> ${DATA.definitions.slope_bp} ` +
  `${DATA.definitions.basis_bp} ` +
  `${DATA.definitions.roll_corr_30} ` +
  `${DATA.definitions.basis_vol_ann} ` +
  `<b>Sources.</b> ${DATA.sources.futures}; ${DATA.sources.sonia}; ${DATA.sources.brent}. ` +
  `<b>Not investment advice.</b>`;
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JSON)
with open("sonia_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Wrote sonia_dashboard.html", len(html), "bytes")
