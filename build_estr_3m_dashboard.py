"""Build interactive 3M €STR curve dashboard with ECB schedule."""
from __future__ import annotations

import json
from pathlib import Path

from analyze_estr_1m import ECB_GOVERNING_COUNCIL
from analyze_estr_3m import compute_ecb_meeting_pricing_3m

ROOT = Path(__file__).resolve().parent
with (ROOT / "estr_3m_data.json").open(encoding="utf-8") as f:
    data = json.load(f)

# Ensure QoQ bp_change exists on snapshot contracts
contracts = data["contracts"]
for i, c in enumerate(contracts):
    if "bp_change" not in c:
        if i == 0:
            c["bp_change"] = None
        else:
            c["bp_change"] = round(
                (c["implied_rate_pct"] - contracts[i - 1]["implied_rate_pct"]) * 100, 1
            )

deposit = float(data["deposit_facility_pct"])
as_of = data.get("deposit_facility_as_of") or contracts[0].get("latest_date")

if "ecb_meeting_pricing" not in data:
    data["ecb_meeting_pricing"] = compute_ecb_meeting_pricing_3m(
        contracts, deposit, as_of
    )

data.setdefault("ecb_calendar", ECB_GOVERNING_COUNCIL)
data.setdefault(
    "ecb_calendar_source",
    "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
)

DATA_JSON = json.dumps(data)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>3M €STR Curve · ECB schedule</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--hist:#ffb84a;--policy:#4aa8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px 16px 48px}
header{padding:20px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:16px}
h1{margin:4px 0;font-size:clamp(20px,4vw,28px)}
.sub{color:var(--mut);font-size:14px;line-height:1.5}
.pill{display:inline-block;background:#1b2536;border:1px solid var(--line);padding:5px 10px;border-radius:20px;font-size:12px;color:var(--mut);margin:4px 6px 0 0}
.pill.next{border-color:var(--acc);color:var(--acc)}
.pill.policy{border-color:var(--policy);color:var(--policy)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.card h2{font-size:15px;margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:0 0 10px;line-height:1.45}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:#1b2536;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .k{font-size:11px;color:var(--mut)}
.kpi .v{font-size:18px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
.chartbox{position:relative;height:380px}
.tblwrap{overflow:auto;max-height:520px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--mut);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.pos{color:var(--acc)}.neg{color:#f87171}
tr.ecb-next td{background:rgba(57,217,138,.06)}
tr.ecb-past td{color:var(--mut)}
.ecb-chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:#1b2536;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:12px;color:var(--mut)}
.chip.next{border-color:var(--acc);color:var(--acc)}
.foot{color:var(--mut);font-size:12px;margin-top:16px;line-height:1.6}
a{color:var(--policy);text-decoration:none}
.probbar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:#1b2536;min-width:90px}
.probbar span{display:block;height:100%}
.prob-cut{background:#39d98a}
.prob-hold{background:#64748b}
.prob-hike{background:#f87171}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p style="margin:0 0 10px;font-size:13px"><a href="portal.html" style="color:#93a1b5">← Markets portal</a> · <a href="estr_1m_dashboard.html" style="color:#93a1b5">1M €STR</a></p>
  <h1>3M €STR curve · ECB schedule</h1>
  <div class="sub" id="asof"></div>
  <div>
    <span class="pill policy" id="policyPill"></span>
    <span class="pill next" id="nextPill"></span>
  </div>
</header>

<div class="kpis" id="kpis"></div>

<div class="card">
  <h2>Implied rate curve (%)</h2>
  <p class="hint">CME EB* quarterly. Implied = 100 − price. Amber dashed line = deposit facility.</p>
  <div class="chartbox"><canvas id="curve"></canvas></div>
</div>

<div class="card">
  <h2>ECB Governing Council decision dates</h2>
  <p class="hint">Official Day-2 monetary-policy announcements. Source: <a href="https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html" target="_blank" rel="noopener">ECB calendar</a>.</p>
  <div class="ecb-chips" id="ecbChips"></div>
</div>

<div class="card">
  <h2>ECB meeting path (approx. from 3M strip)</h2>
  <p class="hint" id="ecbNote"></p>
  <div class="tblwrap">
    <table>
      <thead><tr>
        <th>Meeting</th><th>Status</th><th>Proxy</th><th class="num">Implied %</th>
        <th class="num">Cum vs dep (bp)</th><th class="num">Δ (bp)</th><th>25bp odds</th>
      </tr></thead>
      <tbody id="ecbRows"></tbody>
    </table>
  </div>
</div>

<div class="card">
  <h2>Full 3M €STR strip</h2>
  <div class="tblwrap">
    <table>
      <thead><tr>
        <th>Contract</th><th>Month</th><th class="num">Price</th><th class="num">Implied %</th>
        <th class="num">Vs deposit (bp)</th><th class="num">QoQ (bp)</th>
      </tr></thead>
      <tbody id="stripRows"></tbody>
    </table>
  </div>
</div>

<p class="foot">Barchart finalized EOD lastPrice only · Not investment advice.</p>
</div>
<script>
const DATA = __DATA_JSON__;
const deposit = DATA.deposit_facility_pct;
const contracts = DATA.contracts;
const pricing = DATA.ecb_meeting_pricing || {};
const calendar = DATA.ecb_calendar || [];
const asOf = contracts[0]?.latest_date || DATA.deposit_facility_as_of || '—';

document.getElementById('asof').textContent =
  `${DATA.n_contracts} contracts · as of ${asOf} · generated ${DATA.generated_utc}`;
document.getElementById('policyPill').textContent = `Deposit facility ${deposit.toFixed(2)}%`;
const next = pricing.next_meeting;
document.getElementById('nextPill').textContent = next
  ? `Next ECB ${next.meeting_date}`
  : 'No upcoming ECB mapped';

const front = contracts[0];
const sep = contracts.find(c => c.label === 'Sep-26');
const peak = contracts.reduce((a,b)=> a.implied_rate_pct >= b.implied_rate_pct ? a : b);
document.getElementById('kpis').innerHTML = [
  ['Front', `${front.label} · ${front.implied_rate_pct.toFixed(3)}%`],
  ['Sep-26', sep ? `${sep.implied_rate_pct.toFixed(3)}%` : '—'],
  ['Strip peak', `${peak.label} · ${peak.implied_rate_pct.toFixed(3)}%`],
  ['Vs deposit (peak)', `${peak.vs_deposit_bp>0?'+':''}${peak.vs_deposit_bp.toFixed(1)} bp`],
].map(([k,v]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');

const labels = contracts.map(c => c.label);
const rates = contracts.map(c => c.implied_rate_pct);
new Chart(document.getElementById('curve'), {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'Implied %',
      data: rates,
      borderColor: '#ffb84a',
      backgroundColor: 'rgba(255,184,74,0.12)',
      fill: true,
      tension: 0.15,
      pointRadius: 3,
      pointBackgroundColor: '#ffb84a',
    },{
      label: 'Deposit',
      data: labels.map(() => deposit),
      borderColor: '#4aa8ff',
      borderDash: [6,4],
      pointRadius: 0,
      fill: false,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#93a1b5' } } },
    scales: {
      x: { ticks: { color: '#93a1b5', maxRotation: 55 }, grid: { color: '#243043' } },
      y: { ticks: { color: '#93a1b5' }, grid: { color: '#243043' }, title: { display: true, text: '%', color: '#93a1b5' } }
    }
  }
});

const nextDate = next?.meeting_date;
document.getElementById('ecbChips').innerHTML = calendar.map(m => {
  const d = m.date || m;
  const label = m.label ? `${d} · ${m.label}` : d;
  const cls = d === nextDate ? 'chip next' : 'chip';
  const tag = d === nextDate ? ' · next' : '';
  return `<span class="${cls}">${label}${tag}</span>`;
}).join('');

document.getElementById('ecbNote').textContent = pricing.note || '';
document.getElementById('ecbRows').innerHTML = (pricing.meetings || []).map(m => {
  const rowCls = m.status === 'next' ? 'ecb-next' : (m.status === 'past' ? 'ecb-past' : '');
  const inc = m.incremental_bp;
  const incCls = inc > 0 ? 'neg' : inc < 0 ? 'pos' : '';
  const cum = m.cumulative_vs_deposit_bp;
  const cumCls = cum > 0 ? 'neg' : cum < 0 ? 'pos' : '';
  return `<tr class="${rowCls}">
    <td>${m.meeting_label}<div style="color:var(--mut);font-size:11px">${m.meeting_date}</div></td>
    <td>${m.status}</td>
    <td>${m.ref_contract_label} <span style="color:var(--mut)">${m.ref_symbol}</span></td>
    <td class="num">${m.implied_rate_pct.toFixed(3)}</td>
    <td class="num ${cumCls}">${cum>0?'+':''}${cum.toFixed(1)}</td>
    <td class="num ${incCls}">${inc>0?'+':''}${inc.toFixed(1)}</td>
    <td><div class="probbar" title="cut ${m.cut_pct}% / hold ${m.hold_pct}% / hike ${m.hike_pct}%">
      <span class="prob-cut" style="width:${m.cut_pct}%"></span>
      <span class="prob-hold" style="width:${m.hold_pct}%"></span>
      <span class="prob-hike" style="width:${m.hike_pct}%"></span>
    </div>
    <div style="font-size:10px;color:var(--mut);margin-top:3px">↓${m.cut_pct} · —${m.hold_pct} · ↑${m.hike_pct}</div></td>
  </tr>`;
}).join('');

document.getElementById('stripRows').innerHTML = contracts.map(c => {
  const vs = c.vs_deposit_bp;
  const vsCls = vs > 0 ? 'neg' : vs < 0 ? 'pos' : '';
  const ch = c.bp_change;
  const chCls = ch == null ? '' : (ch > 0 ? 'neg' : ch < 0 ? 'pos' : '');
  const chTxt = ch == null ? '—' : ((ch>0?'+':'') + ch.toFixed(1));
  return `<tr>
    <td>${c.symbol}</td>
    <td>${c.label}</td>
    <td class="num">${Number(c.price).toFixed(4)}</td>
    <td class="num">${c.implied_rate_pct.toFixed(4)}</td>
    <td class="num ${vsCls}">${vs>0?'+':''}${vs.toFixed(1)}</td>
    <td class="num ${chCls}">${chTxt}</td>
  </tr>`;
}).join('');
</script>
</body>
</html>
"""

html = HTML.replace("__DATA_JSON__", DATA_JSON)
for name in ("estr_3m_dashboard.html", "docs/estr_3m_dashboard.html"):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"Wrote {path}")

# Persist enriched snapshot fields
with (ROOT / "estr_3m_data.json").open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Updated estr_3m_data.json with ECB pricing")
