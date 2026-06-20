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
  --chip:#1b2536; --entry:#ff8c42;
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
@media(min-width:900px){.cols-4{grid-template-columns:repeat(4,1fr)}.cols-5{grid-template-columns:repeat(5,1fr)}.cols-2{grid-template-columns:repeat(2,1fr)}.cols-3{grid-template-columns:repeat(3,1fr)}.cols-6{grid-template-columns:repeat(6,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px}
.card h2{font-size:15px;margin:0 0 2px}
.card .hint{color:var(--mut);font-size:12.5px;margin:0 0 12px;line-height:1.45}
.stat{font-size:28px;font-weight:700;line-height:1.05;font-variant-numeric:tabular-nums}
.stat.green{color:var(--good)} .stat.amber{color:var(--warn)} .stat.red{color:var(--bad)} .stat.blue{color:var(--acc2)}
.statlbl{color:var(--mut);font-size:12px;margin-top:4px}
.stat.sm{font-size:22px}
.card.trade{border-color:rgba(255,140,66,.35);background:linear-gradient(165deg,var(--card),rgba(255,140,66,.04))}
.regimetable{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.regimetable th,.regimetable td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
.regimetable td.num{text-align:right;font-variant-numeric:tabular-nums}
.regimetable tfoot td{font-weight:700;border-top:2px solid var(--line);padding-top:10px}
.regimetable .tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600}
.tag-bear-steep{background:rgba(255,107,107,.15);color:#ff8a8a}
.tag-bull-steep{background:rgba(57,217,138,.15);color:#5eeaa0}
.tag-bear-flat{background:rgba(255,184,74,.15);color:#ffc966}
.tag-bull-flat{background:rgba(74,168,255,.15);color:#7ec0ff}
.tag-mixed{background:rgba(147,161,181,.15);color:#b0bdd0}
.driversummary{font-size:13px;line-height:1.55;color:var(--ink);margin:0 0 12px;padding:10px 12px;background:var(--card2);border-radius:10px;border:1px solid var(--line)}
.card.policy{border-color:rgba(74,168,255,.25)}
.pill-policy{border-color:var(--acc2);color:var(--acc2);background:rgba(74,168,255,.1)}
.chartbox{position:relative;width:100%;height:280px}
.chartbox.tall{height:320px}
.sectitle{font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:22px 4px 10px}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--chip);border:1px solid var(--line);
  padding:6px 12px;border-radius:30px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill-entry{border-color:var(--entry);color:var(--entry);background:rgba(255,140,66,.12);font-weight:600}
.chartlegend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--mut);margin:0 0 10px}
.chartlegend span{display:inline-flex;align-items:center;gap:6px}
.chartlegend .swatch{width:22px;height:0;border-top:2px dashed var(--entry)}
.chartlegend .dot{width:6px;height:6px;border-radius:50%;background:var(--entry);border:1px solid var(--bg)}
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
    <span class="pill pill-entry" id="entryPill"></span>
    <span class="pill pill-policy" id="policyPill"></span>
    <span class="pill">Futures: ICE 1M SONIA (JUZ26 / JUZ27)</span>
    <span class="pill">Spot: BoE SONIA</span>
    <span class="pill">Oil: Brent (BZ=F)</span>
  </div>
</header>

<div class="sectitle">Forward pricing vs Bank Rate</div>
<div class="card policy">
  <h2>Cuts / hikes priced in Dec-26 &amp; Dec-27 futures</h2>
  <p class="hint">Versus BoE <b>Bank Rate 3.75%</b> (held 18 Jun 2026). Positive bp = implied SONIA <b>above</b> policy (fewer cuts / higher rates priced); negative = cuts priced.</p>
  <div id="policySummary" class="driversummary"></div>
  <div class="grid cols-4" id="policyKpiGrid"></div>
  <table class="regimetable" id="policyPathTbl" style="margin-top:14px">
    <thead><tr><th>Point on path</th><th class="num">Rate (%)</th><th class="num">vs Bank Rate (bp)</th><th>Market read</th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="chartbox tall" style="margin-top:14px"><canvas id="policyChart"></canvas></div>
</div>

<div class="sectitle" id="tradeSectionTitle" style="display:none">Your trade &middot; since entry</div>
<div class="grid cols-3" id="tradeStatsGrid" style="display:none"></div>
<div class="card trade" id="legBreakdownCard" style="display:none">
  <h2>Leg rate changes &mdash; entry to mark</h2>
  <p class="hint">Implied rate (%) and ICE futures price at entry (Fri 5 Jun EOD) vs latest. Spread P&amp;L = short Dec27 contribution + long Dec26 contribution.</p>
  <table class="regimetable" id="legTbl">
    <thead><tr>
      <th>Leg</th><th>Side</th>
      <th class="num">Entry rate</th><th class="num">Exit rate</th><th class="num">Rate &Delta;</th>
      <th class="num">Entry px</th><th class="num">Exit px</th><th class="num">Px &Delta;</th>
      <th class="num">Spread P&amp;L</th>
    </tr></thead>
    <tbody></tbody>
    <tfoot id="legTblFoot"></tfoot>
  </table>
  <div class="grid cols-2" style="margin-top:14px">
    <div class="chartbox" style="height:240px"><canvas id="legRatesChart"></canvas></div>
    <div class="chartbox" style="height:240px"><canvas id="tradePathChart"></canvas></div>
  </div>
</div>
<div class="grid cols-2" id="tradeDetailGrid" style="display:none">
  <div class="card trade">
    <h2>P&amp;L driver &mdash; curve regime</h2>
    <p class="hint">Daily slope &Delta; attributed to bear/bull steepening or flattening (Dec26 vs Dec27 rate moves).</p>
    <div id="driverSummary" class="driversummary"></div>
    <div class="chartbox" style="height:220px"><canvas id="regimeChart"></canvas></div>
  </div>
  <div class="card trade">
    <h2>Regime breakdown</h2>
    <p class="hint">Session-level attribution of slope P&amp;L (£ per 1:1 contract pair).</p>
    <table class="regimetable" id="regimeTbl">
      <thead><tr><th>Regime</th><th class="num">Days</th><th class="num">P&amp;L (bp)</th><th class="num">P&amp;L (£)</th></tr></thead>
      <tbody></tbody>
    </table>
    <p class="note" id="tradeRiskNote"></p>
  </div>
</div>

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
  <p class="hint">ICE futures quoted as 100 &minus; rate. Thin orange dashed line = entry (Fri 5 Jun); small dot on entry session only.</p>
  <div class="chartlegend"><span><i class="swatch"></i> Entry</span></div>
  <div class="chartbox tall"><canvas id="ratesChart"></canvas></div>
</div>

<div class="sectitle">Dec27 &minus; Dec26 slope (rate space)</div>
<div class="card">
  <h2>Calendar slope = Dec-27 rate &minus; Dec-26 rate</h2>
  <p class="hint">Spread in rate space (bp). Orange vertical line marks your Fri 5 Jun entry @ <span id="entrySlopeLbl"></span>.</p>
  <div class="chartbox tall"><canvas id="slopeChart"></canvas></div>
</div>

<div class="sectitle">Macro link</div>
<div class="card">
  <h2>Rolling 30-day correlation: slope change vs Brent</h2>
  <p class="hint">Correlation of daily slope change (bp) with Brent daily % return. Orange line = entry date.</p>
  <div class="chartbox tall"><canvas id="corrChart"></canvas></div>
</div>

<div class="sectitle">Basis &amp; risk</div>
<div class="grid cols-2">
  <div class="card">
    <h2>Dec26 cash&ndash;futures basis (bp)</h2>
    <p class="hint">Futures implied rate minus same-day spot SONIA fixing. Orange line = entry.</p>
    <div class="chartbox"><canvas id="basisChart"></canvas></div>
  </div>
  <div class="card">
    <h2>Annualised vol of daily basis changes</h2>
    <p class="hint">30-day rolling stdev of daily basis changes, scaled to a one-year horizon (&times;&radic;252). Orange line = entry.</p>
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
  warn:css('--warn'),bad:css('--bad'),good:css('--good'),entry:css('--entry')};
Chart.defaults.color = C.mut;
Chart.defaults.font.family = "-apple-system,Segoe UI,Roboto,sans-serif";
Chart.defaults.borderColor = C.line;

const D = DATA.daily;
const labels = D.map(r => r.date);
const s = DATA.summary;
const ENTRY = DATA.trade_entry || null;
const entryIdx = ENTRY && ENTRY.in_window ? labels.indexOf(ENTRY.date) : -1;
const POL = DATA.policy_pricing || null;

function fmtVsBank(bp) {
  if (bp == null || Number.isNaN(bp)) return '—';
  return (bp >= 0 ? '+' : '') + bp.toFixed(1) + ' bp';
}
function vsBankCls(bp) {
  if (bp == null) return '';
  if (bp >= 0.5) return 'amber';
  if (bp <= -0.5) return 'green';
  return 'blue';
}

document.getElementById('asof').textContent =
  `Barchart EOD through ${s.end} (pulled ${DATA.generated_utc}). ` +
  `Dec26 ${s.dec26_rate.toFixed(3)}%, Dec27 ${s.dec27_rate.toFixed(3)}%, Brent $${s.brent.toFixed(2)}.`;
document.getElementById('rangePill').textContent = `${s.n_days} sessions · ${s.start} → ${s.end}`;
document.getElementById('winLbl').textContent = s.n_days;

if (ENTRY && ENTRY.in_window) {
  const pnl = ENTRY.pnl_slope_bp != null ? ` · P&L ${f1(ENTRY.pnl_slope_bp)} bp since entry` : '';
  document.getElementById('entryPill').textContent =
    `Entry ${ENTRY.short_label} · ${ENTRY.position} · slope ${f1(ENTRY.slope_bp)} bp${pnl}`;
  const el = document.getElementById('entrySlopeLbl');
  if (el) el.textContent = `${f1(ENTRY.slope_bp)} bp`;
} else if (ENTRY) {
  document.getElementById('entryPill').textContent =
    `Entry ${ENTRY.short_label} (outside ${s.n_days}d window)`;
} else {
  document.getElementById('entryPill').style.display = 'none';
}

if (POL) {
  document.getElementById('policyPill').textContent =
    `Bank Rate ${POL.bank_rate_pct.toFixed(2)}% · as of ${POL.bank_rate_as_of}`;
  document.getElementById('policySummary').innerHTML =
    `<b>Today’s futures</b> price average SONIA over the Dec-26 / Dec-27 contract windows. ` +
    `Versus <b>${POL.bank_rate_pct}%</b> policy: Dec-26 <b>${fmtVsBank(POL.dec26.vs_bank_bp)}</b>, ` +
    `Dec-27 <b>${fmtVsBank(POL.dec27.vs_bank_bp)}</b> ` +
    `(back-end <b>${fmtVsBank(POL.incremental_dec27_over_dec26_bp)}</b> vs Dec-26). ` +
    (POL.change_since_entry
      ? `Since your entry: Dec-26 pricing ${fmtVsBank(POL.change_since_entry.dec26_vs_bank_bp)} · Dec-27 ${fmtVsBank(POL.change_since_entry.dec27_vs_bank_bp)}.`
      : '');

  const pk = [
    ['Bank Rate (policy)', POL.bank_rate_pct.toFixed(2) + '%', `BoE · ${POL.bank_rate_as_of}`, 'blue'],
    ['Spot SONIA', POL.spot_sonia_pct.toFixed(3) + '%', fmtVsBank(POL.spot_vs_bank_bp) + ' vs policy', vsBankCls(POL.spot_vs_bank_bp)],
    ['Dec-26 implied', POL.dec26.implied_rate_pct.toFixed(3) + '%', fmtVsBank(POL.dec26.vs_bank_bp), vsBankCls(POL.dec26.vs_bank_bp)],
    ['Dec-27 implied', POL.dec27.implied_rate_pct.toFixed(3) + '%', fmtVsBank(POL.dec27.vs_bank_bp), vsBankCls(POL.dec27.vs_bank_bp)],
  ];
  document.getElementById('policyKpiGrid').innerHTML = pk.map(([t, v, sub, cls]) =>
    `<div class="card policy"><h2>${t}</h2><div class="stat sm ${cls}">${v}</div><div class="statlbl">${sub}</div></div>`
  ).join('');

  const pathRows = [
    ['Bank Rate (now)', POL.bank_rate_pct, 0, 'Policy anchor'],
    ['Spot SONIA (fixing)', POL.spot_sonia_pct, POL.spot_vs_bank_bp, POL.spot_vs_bank_bp >= 0 ? 'Cash above policy' : 'Cash below policy'],
    ['Dec-26 future (JUZ26)', POL.dec26.implied_rate_pct, POL.dec26.vs_bank_bp, POL.dec26.summary],
    ['Dec-27 future (JUZ27)', POL.dec27.implied_rate_pct, POL.dec27.vs_bank_bp, POL.dec27.summary],
  ];
  const ptbody = document.querySelector('#policyPathTbl tbody');
  ptbody.innerHTML = pathRows.map(([name, rate, bp, txt]) =>
    `<tr><td>${name}</td><td class="num">${rate.toFixed(3)}%</td>` +
    `<td class="num">${fmtVsBank(bp)}</td><td>${txt}</td></tr>`
  ).join('');
}

document.getElementById('kDec26').textContent = fRate(s.dec26_rate);
document.getElementById('kDec26Sub').textContent =
  `JUZ26 · px ${D.at(-1).dec26_px.toFixed(3)} · ${fmtVsBank(s.dec26_vs_bank_bp)} vs 3.75% policy`;
document.getElementById('kDec27').textContent = fRate(s.dec27_rate);
document.getElementById('kDec27Sub').textContent =
  `JUZ27 · px ${D.at(-1).dec27_px.toFixed(3)} · ${fmtVsBank(s.dec27_vs_bank_bp)} vs 3.75% policy`;

const kSlope = document.getElementById('kSlope');
kSlope.textContent = f1(s.slope_bp) + ' bp';
kSlope.className = 'stat ' + (s.slope_bp >= 0 ? 'green' : 'red');
document.getElementById('kSlopeSub').textContent =
  `Dec27 ${fmtVsBank(s.dec27_vs_bank_bp)} vs policy · Dec26 ${fmtVsBank(s.dec26_vs_bank_bp)} · 50d μ ${f1(s.slope_mean_50d)}`;

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
    title: (items) => {
      const i = items[0].dataIndex;
      return labels[i] + (i === entryIdx ? ' · YOUR ENTRY' : '');
    },
    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y == null ? '—' : ctx.parsed.y.toFixed(digits) + suffix}`
  }
});

const ptR = (base) => labels.map((_, i) => (i === entryIdx ? 4 : base));
const ptBorder = (base, fill) => labels.map((_, i) => (i === entryIdx ? C.entry : fill));
const ptBg = (base) => labels.map((_, i) => (i === entryIdx ? C.entry : base));
const ptHover = (base) => labels.map((_, i) => (i === entryIdx ? 5 : base));

const tradeEntryLinePlugin = {
  id: 'tradeEntryLine',
  afterDatasetsDraw(chart) {
    if (entryIdx < 0) return;
    const {ctx, chartArea: a, scales} = chart;
    const x = scales.x.getPixelForValue(entryIdx);
    ctx.save();
    ctx.strokeStyle = 'rgba(255,140,66,.85)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(x, a.top);
    ctx.lineTo(x, a.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    if (chart.canvas.id === 'slopeChart') {
      ctx.fillStyle = C.entry;
      ctx.font = '10px sans-serif';
      ctx.fillText('Entry', x + 4, a.top + 12);
    }
    ctx.restore();
  }
};

function renderPolicyChart() {
  if (!POL) return;
  new Chart(document.getElementById('policyChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Dec-26 vs Bank Rate (bp)',
          data: D.map(r => r.dec26_vs_bank_bp),
          borderColor: C.acc2,
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.15,
        },
        {
          label: 'Dec-27 vs Bank Rate (bp)',
          data: D.map(r => r.dec27_vs_bank_bp),
          borderColor: C.warn,
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.15,
        },
        {
          label: 'Zero (in line with policy)',
          data: labels.map(() => 0),
          borderColor: 'rgba(147,161,181,.5)',
          borderDash: [4, 4],
          borderWidth: 1,
          pointRadius: 0,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed.y;
              const lbl = ctx.dataset.label;
              if (lbl.startsWith('Zero')) return 'Bank Rate level (0 bp)';
              return `${lbl.split(' (')[0]}: ${fmtVsBank(v)}`;
            },
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 10, autoSkip: true }, grid: { display: false } },
        y: {
          title: { display: true, text: 'bp vs Bank Rate 3.75%' },
          grid: { color: C.line },
        },
      },
    },
    plugins: [tradeEntryLinePlugin],
  });
}

function regimeTagClass(key) {
  if (key.startsWith('bear_steep')) return 'tag-bear-steep';
  if (key.startsWith('bull_steep')) return 'tag-bull-steep';
  if (key.startsWith('bear_flat')) return 'tag-bear-flat';
  if (key.startsWith('bull_flat')) return 'tag-bull-flat';
  return 'tag-mixed';
}

function renderTradeStats() {
  const T = ENTRY && ENTRY.stats;
  if (!T) return;
  document.getElementById('tradeSectionTitle').style.display = '';
  const grid = document.getElementById('tradeStatsGrid');
  grid.style.display = '';
  document.getElementById('tradeDetailGrid').style.display = '';

  const fGbp = (x) => (x >= 0 ? '+' : '') + '£' + Math.abs(x).toFixed(0);
  const cards = [
    ['P&L (1 pair)', fGbp(T.pnl_gbp_per_pair), `${f1(T.pnl_slope_bp)} bp on slope`, T.pnl_gbp_per_pair >= 0 ? 'green' : 'red'],
    ['Return on margin', f1(T.return_margin_pct) + '%', `~£${T.margin_assumed_gbp.toLocaleString()} assumed`, T.return_margin_pct >= 0 ? 'green' : 'red'],
    ['Sharpe (ann.)', T.sharpe_ann == null ? '—' : f2(T.sharpe_ann), `rf ${T.risk_free_pct}% · ${T.session_days} sessions`, 'amber'],
    ['Vol (ann.)', T.vol_ann_margin_pct == null ? '—' : f1(T.vol_ann_margin_pct) + '%', 'On margin returns', 'blue'],
    ['CAGR (margin)', T.cagr_margin_pct == null ? '—' : f1(T.cagr_margin_pct) + '%', `${T.calendar_days} calendar days`, 'amber'],
    ['Max drawdown', fGbp(T.max_drawdown_gbp), 'Intra-trade path', 'red'],
  ];
  grid.innerHTML = cards.map(([t, v, sub, cls]) =>
    `<div class="card trade"><h2>${t}</h2><p class="hint">${ENTRY.position}</p>` +
    `<div class="stat sm ${cls}">${v}</div><div class="statlbl">${sub}</div></div>`
  ).join('');

  const L26 = T.legs.dec26;
  const L27 = T.legs.dec27;
  const legCard = document.getElementById('legBreakdownCard');
  legCard.style.display = '';
  const legBody = document.querySelector('#legTbl tbody');
  legBody.innerHTML = '';
  [L26, L27].forEach(L => {
    const rc = L.rate_chg_bp >= 0 ? 'pos' : 'neg';
    const pc = L.spread_pnl_bp >= 0 ? 'pos' : 'neg';
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td><b>${L.label}</b> (${L.contract})</td><td>${L.side}</td>` +
      `<td class="num">${L.entry_rate_pct.toFixed(3)}%</td>` +
      `<td class="num">${L.exit_rate_pct.toFixed(3)}%</td>` +
      `<td class="num ${rc}">${f1(L.rate_chg_bp)} bp</td>` +
      `<td class="num">${L.entry_px.toFixed(3)}</td>` +
      `<td class="num">${L.exit_px.toFixed(3)}</td>` +
      `<td class="num ${rc}">${(L.px_chg >= 0 ? '+' : '') + L.px_chg.toFixed(3)} (${f1(L.price_return_pct)}%)</td>` +
      `<td class="num ${pc}">${f1(L.spread_pnl_bp)} bp · ${fGbp(L.spread_pnl_gbp)}</td>`;
    legBody.appendChild(tr);
  });
  const rec = T.slope_reconciliation;
  document.getElementById('legTblFoot').innerHTML =
    `<tr><td colspan="4"><b>Net spread (Dec27 − Dec26 rate)</b></td>` +
    `<td class="num">${f1(rec.entry_slope_bp)} → ${f1(rec.exit_slope_bp)} bp</td>` +
    `<td colspan="3"></td>` +
    `<td class="num green"><b>${f1(T.pnl_slope_bp)} bp · ${fGbp(T.pnl_gbp_per_pair)}</b></td></tr>` +
    `<tr><td colspan="9" class="note" style="border:none;padding-top:6px">` +
    `Rate Δ: Dec27 ${f1(L27.rate_chg_bp)} − Dec26 ${f1(L26.rate_chg_bp)} = ${f1(rec.dec27_minus_dec26_bp)} bp on slope. ` +
    `Long Dec26 wins when its rate falls (futures px rises); short Dec27 wins when Dec27 rate rises (px falls).</td></tr>`;

  new Chart(document.getElementById('legRatesChart'), {
    type: 'bar',
    data: {
      labels: ['Dec-26 (long)', 'Dec-27 (short)'],
      datasets: [
        {
          label: 'Entry rate (%)',
          data: [L26.entry_rate_pct, L27.entry_rate_pct],
          backgroundColor: 'rgba(147,161,181,.5)',
        },
        {
          label: 'Exit rate (%)',
          data: [L26.exit_rate_pct, L27.exit_rate_pct],
          backgroundColor: [C.acc2, C.warn],
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        y: { title: { display: true, text: 'implied rate (%)' }, grid: { color: C.line } },
        x: { grid: { display: false } },
      },
    },
  });

  const path = T.trade_path || [];
  new Chart(document.getElementById('tradePathChart'), {
    type: 'line',
    data: {
      labels: path.map(p => p.date),
      datasets: [
        {
          label: 'Dec-26 rate (%)',
          data: path.map(p => p.dec26_rate),
          borderColor: C.acc2,
          borderWidth: 2,
          pointRadius: path.map(p => p.date === T.entry_date ? 4 : 1),
          tension: 0.15,
        },
        {
          label: 'Dec-27 rate (%)',
          data: path.map(p => p.dec27_rate),
          borderColor: C.warn,
          borderWidth: 2,
          pointRadius: path.map(p => p.date === T.entry_date ? 4 : 1),
          tension: 0.15,
        },
        {
          label: 'Cum P&L (£)',
          data: path.map(p => p.cum_pnl_gbp),
          borderColor: C.entry,
          borderWidth: 2,
          pointRadius: 1,
          yAxisID: 'y1',
          tension: 0.15,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top', labels: { boxWidth: 12 } } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, autoSkip: true }, grid: { display: false } },
        y: { title: { display: true, text: 'rate (%)' }, grid: { color: C.line } },
        y1: {
          position: 'right',
          title: { display: true, text: 'cum P&L £' },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });

  const om = T.overall_move;
  const dom = T.dominant_regime;
  document.getElementById('driverSummary').innerHTML =
    `<b>Overall move (${T.entry_date} → ${T.exit_date}):</b> ` +
    `<span class="tag ${regimeTagClass(om.regime)}">${om.label}</span> — ` +
    `Dec26 ${f1(om.dec26_bp)} bp, Dec27 ${f1(om.dec27_bp)} bp → slope ${f1(om.slope_bp)} bp. ` +
    (dom ? `<b>Largest daily contributor:</b> ${dom.label} (${fGbp(dom.pnl_gbp)}, ${dom.days} session${dom.days>1?'s':''}). ` : '') +
    `Steepening days ${f1(T.pnl_from_steepening_bp)} bp · flattening ${f1(T.pnl_from_flattening_bp)} bp.`;

  const tbody = document.querySelector('#regimeTbl tbody');
  tbody.innerHTML = '';
  (T.regime_attribution || []).forEach(r => {
    const tr = document.createElement('tr');
    const cls = r.pnl_gbp >= 0 ? 'pos' : 'neg';
    tr.innerHTML =
      `<td><span class="tag ${regimeTagClass(r.regime)}">${r.label}</span></td>` +
      `<td class="num">${r.days}</td>` +
      `<td class="num ${cls}">${f1(r.pnl_slope_bp)}</td>` +
      `<td class="num ${cls}">${fGbp(r.pnl_gbp)}</td>`;
    tbody.appendChild(tr);
  });

  document.getElementById('tradeRiskNote').textContent =
    `Sharpe uses 3.5% rf on margin returns (${T.session_days} sessions). Gross return ${T.return_gross_pct}% on £1m notional.`;

  const REGIME_COLORS = {
    bear_steepening: '#ff6b6b', bull_steepening: '#39d98a',
    bear_flattening: '#ffb84a', bull_flattening: '#4aa8ff',
    mixed_steepening: '#93a1b5', mixed_flattening: '#93a1b5', unchanged: '#56657a',
  };
  const attrs = T.regime_attribution || [];
  new Chart(document.getElementById('regimeChart'), {
    type: 'bar',
    data: {
      labels: attrs.map(a => a.label),
      datasets: [{
        label: 'P&L (£)',
        data: attrs.map(a => a.pnl_gbp),
        backgroundColor: attrs.map(a => REGIME_COLORS[a.regime] || '#93a1b5'),
        borderWidth: 0
      }]
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: C.line }, title: { display: true, text: '£ per pair' } },
        y: { grid: { display: false } }
      }
    }
  });
}
renderTradeStats();

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

renderPolicyChart();

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
        pointRadius: ptR(2),
        pointBackgroundColor: ptBg(C.acc2),
        pointBorderColor: ptBorder(C.acc2, C.acc2),
        pointHoverRadius: ptHover(5),
        tension: 0.15
      },
      {
        label: 'Dec-27 rate (%)',
        data: D.map(r => r.dec27_rate),
        borderColor: C.warn,
        borderWidth: 2,
        pointRadius: ptR(2),
        pointBackgroundColor: ptBg(C.warn),
        pointBorderColor: ptBorder(C.warn, C.warn),
        pointHoverRadius: ptHover(5),
        tension: 0.15
      },
      ...(POL ? [{
        label: 'Bank Rate 3.75%',
        data: labels.map(() => POL.bank_rate_pct),
        borderColor: 'rgba(147,161,181,.65)',
        borderDash: [6, 4],
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0,
      }] : []),
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
  },
  plugins: [tradeEntryLinePlugin]
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
      pointRadius: ptR(2),
      pointBackgroundColor: ptBg(C.acc2),
      pointBorderColor: ptBorder(C.acc2, C.acc2),
      pointHoverRadius: ptHover(5),
      tension: 0.15,
      fill: true
    }]
  },
  options: lineOpts('bp', undefined, undefined, tipOpts(2, ' bp')),
  plugins: [tradeEntryLinePlugin, {id: 'zero', afterDraw: (ch) => {
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
      pointRadius: ptR(2),
      pointBackgroundColor: ptBg(C.warn),
      pointBorderColor: ptBorder(C.warn, C.warn),
      pointHoverRadius: ptHover(5),
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
          title: (items) => {
            const i = items[0].dataIndex;
            return labels[i] + (i === entryIdx ? ' · YOUR ENTRY' : '');
          },
          label: (ctx) => `30d corr: ${ctx.parsed.y == null ? '—' : ctx.parsed.y.toFixed(3)}`
        }
      }
    }
  },
  plugins: [tradeEntryLinePlugin, {id: 'bands', afterDraw: (ch) => {
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
      pointRadius: ptR(2),
      pointBackgroundColor: ptBg(C.acc),
      pointBorderColor: ptBorder(C.acc, C.acc),
      pointHoverRadius: ptHover(5),
      tension: 0.15,
      fill: {target: 'origin', above: 'rgba(57,217,138,.08)', below: 'rgba(255,107,107,.10)'}
    }]
  },
  options: lineOpts('bp', undefined, undefined, tipOpts(2, ' bp')),
  plugins: [tradeEntryLinePlugin]
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
      pointRadius: ptR(2),
      pointBackgroundColor: ptBg(C.good),
      pointBorderColor: ptBorder(C.good, C.good),
      pointHoverRadius: ptHover(5),
      tension: 0.15,
      spanGaps: true
    }]
  },
  options: lineOpts('bp (ann.)', 0, undefined, tipOpts(2, ' bp')),
  plugins: [tradeEntryLinePlugin]
});

document.getElementById('foot').innerHTML =
  `<b>Definitions.</b> ${DATA.definitions.slope_bp} ` +
  (DATA.definitions.vs_bank_bp ? `${DATA.definitions.vs_bank_bp} ` : '') +
  `${DATA.definitions.basis_bp} ` +
  `${DATA.definitions.roll_corr_30} ` +
  `${DATA.definitions.basis_vol_ann} ` +
  (ENTRY && ENTRY.in_window
    ? `<b>Trade entry.</b> ${ENTRY.short_label}: ${ENTRY.position} at slope ${ENTRY.slope_bp} bp` +
      (ENTRY.pnl_slope_bp != null ? `; mark-to-market ${ENTRY.pnl_slope_bp >= 0 ? '+' : ''}${ENTRY.pnl_slope_bp} bp on slope.` : '.')
    : '') +
  ` <b>Sources.</b> ${DATA.sources.futures}; ${DATA.sources.sonia}; ${DATA.sources.brent}. ` +
  `<b>Not investment advice.</b>`;
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JSON)
with open("sonia_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Wrote sonia_dashboard.html", len(html), "bytes")
