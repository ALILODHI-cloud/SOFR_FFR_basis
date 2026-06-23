#!/usr/bin/env python3
"""Build Supra portal + multi-trade live tracker pages."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "trades_index.json"

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
@media(min-width:800px){.grid.stats{grid-template-columns:repeat(4,1fr)}.grid.two{grid-template-columns:1fr 1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.card h2{font-size:14px;margin:0 0 8px;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.stat{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums}
.stat.good{color:var(--good)}.stat.bad{color:var(--bad)}.stat.neu{color:var(--ink)}
.statlbl{font-size:11px;color:var(--mut);margin-top:4px}
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th,.tbl td{padding:8px;border-bottom:1px solid var(--line);text-align:left}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums}
.chartbox{height:280px;position:relative}
.pill{display:inline-block;font-size:11px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin:4px 6px 0 0}
.pill.warn{border-color:var(--warn);color:var(--warn)}
.foot{color:var(--mut);font-size:11px;margin-top:16px;line-height:1.6}
</style>
</head>
<body>
<div class="wrap">
<div class="nav"><a href="portal.html">← Portal</a> · <a href="trade_tracker.html">All trades</a> · <a id="noteLink" href="#">Market note</a></div>
<header>
  <div class="eyebrow">Supra Fund Management · live trade</div>
  <h1 id="title"></h1>
  <div class="sub" id="subtitle"></div>
  <div id="pills"></div>
</header>
<div class="grid stats" id="stats"></div>
<div class="card"><h2>Cumulative P&amp;L (£)</h2><div class="chartbox"><canvas id="pnlChart"></canvas></div></div>
<div class="grid two">
  <div class="card"><h2 id="slopeTitle">Slope (bp)</h2><div class="chartbox"><canvas id="slopeChart"></canvas></div></div>
  <div class="card"><h2>Implied rates (%)</h2><div class="chartbox"><canvas id="rateChart"></canvas></div></div>
</div>
<div class="card">
  <h2>Regime attribution (since entry)</h2>
  <table class="tbl" id="regimeTbl"><thead><tr><th>Regime</th><th>Days</th><th>Δslope</th><th>P&amp;L £</th></tr></thead><tbody></tbody></table>
</div>
<div class="card">
  <h2>Daily path</h2>
  <div style="overflow:auto;max-height:320px">
    <table class="tbl" id="pathTbl"><thead><tr>
      <th>Date</th><th id="thShort"></th><th id="thLong"></th><th>Slope</th><th>Δ day</th><th>Cum £</th>
    </tr></thead><tbody></tbody></table>
  </div>
</div>
<p class="foot" id="foot"></p>
</div>
<script>
const D = __DATA_JSON__;
const GBP = D.trade.gbp_per_bp || 12.5;
function fmtBp(v){ return (v>=0?'+':'')+Number(v).toFixed(1)+' bp'; }
function fmtGbp(v){ return (v>=0?'+':'')+'£'+Math.abs(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function cls(v){ return v>0.5?'good':v<-0.5?'bad':'neu'; }

document.getElementById('title').textContent = D.trade.label;
document.getElementById('subtitle').textContent =
  D.trade.position + ' · Entry ' + D.entry.label + ' · Mark ' + D.mark.date;
document.getElementById('noteLink').href = D.market_note_url;
document.getElementById('slopeTitle').textContent = D.trade.spread_label + ' slope (bp)';
document.getElementById('thLong').textContent = D.leg_labels.quoted_long + ' %';
document.getElementById('thShort').textContent = D.leg_labels.quoted_short + ' %';

const pills = document.getElementById('pills');
pills.innerHTML = '<span class="pill">' + D.trade.direction + '</span>'
  + '<span class="pill">Bank ' + D.bank_rate_pct + '%</span>'
  + (D.trade.entry_locked ? '<span class="pill">Entry locked (EOD)</span>' : '<span class="pill warn">Entry provisional — awaiting EOD settle</span>')
  + '<span class="pill">Updated ' + D.generated_utc + '</span>';

const pnl = D.pnl;
document.getElementById('stats').innerHTML = [
  ['P&amp;L', fmtGbp(pnl.gbp), cls(pnl.gbp)],
  ['Δ spread', fmtBp(pnl.slope_bp), cls(pnl.slope_bp)],
  ['Entry slope', fmtBp(D.entry.slope_bp), 'neu'],
  ['Mark slope', fmtBp(D.mark.slope_bp), cls(pnl.slope_bp)],
].map(([l,v,c])=>'<div class="card"><div class="statlbl">'+l+'</div><div class="stat '+c+'">'+v+'</div></div>').join('');

const path = D.trade_path || [];
const labels = path.map(r=>r.date);
const cum = path.map(r=>r.cum_pnl_gbp);
const slopes = path.map(r=>r.slope_bp);

new Chart(document.getElementById('pnlChart'), {
  type:'line',
  data:{labels,datasets:[{label:'Cum P&L £',data:cum,borderColor:'#39d98a',backgroundColor:'rgba(57,217,138,.08)',fill:true,tension:.2}]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
});
new Chart(document.getElementById('slopeChart'), {
  type:'line',
  data:{labels,datasets:[
    {label:'Slope bp',data:slopes,borderColor:'#ffb84a',pointRadius:3},
    {label:'Entry',data:labels.map(()=>D.entry.slope_bp),borderColor:'#4aa8ff',borderDash:[5,4],pointRadius:0}
  ]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#93a1b5'}}},scales:{x:{ticks:{color:'#93a1b5'}},y:{ticks:{color:'#93a1b5'}}}}
});
new Chart(document.getElementById('rateChart'), {
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
const pt = document.querySelector('#pathTbl tbody');
[...path].reverse().forEach(r=>{
  pt.innerHTML += '<tr><td>'+r.date+'</td><td class="num">'+r.quoted_short_rate.toFixed(3)+'</td><td class="num">'+r.quoted_long_rate.toFixed(3)+'</td><td class="num">'+r.slope_bp.toFixed(1)+'</td><td class="num">'+(r.daily_pnl_gbp!=null?fmtGbp(r.daily_pnl_gbp):'—')+'</td><td class="num">'+fmtGbp(r.cum_pnl_gbp)+'</td></tr>';
});
document.getElementById('foot').textContent =
  D.trade.position + ' · £'+GBP+'/bp per leg-pair · Barchart EOD. Not investment advice.';
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
.pill.warn{border-color:var(--warn);color:var(--warn)}
.foot{color:var(--mut);font-size:11px;margin-top:20px}
</style>
</head>
<body>
<div class="wrap">
<div class="nav"><a href="portal.html">← Portal</a></div>
<header>
  <div class="eyebrow">Supra Fund Management</div>
  <h1>Live trade tracker</h1>
  <div class="sub">SONIA calendar spreads · Barchart EOD · auto-refresh weekdays</div>
</header>
<div class="grid" id="tradeGrid"></div>
<p class="foot" id="foot"></p>
</div>
<script>
const INDEX = __INDEX_JSON__;
function fmtBp(v){ return (v>=0?'+':'')+Number(v).toFixed(1)+' bp'; }
function fmtGbp(v){ return (v>=0?'+':'')+'£'+Math.abs(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function cls(v){ return v>0.5?'good':v<-0.5?'bad':''; }
const grid = document.getElementById('tradeGrid');
INDEX.trades.forEach(t=>{
  const lock = t.entry_locked ? '' : '<span class="pill warn">Entry provisional</span>';
  grid.innerHTML += '<a class="card" href="'+t.detail_page+'">'
    + '<h2>'+t.label+'</h2>'
    + '<p>'+t.position+'</p>'
    + '<span class="pill">'+t.direction+'</span>'+lock
    + '<div class="row"><span>'+t.spread_label+' entry</span><span>'+fmtBp(t.entry_slope_bp)+'</span></div>'
    + '<div class="row"><span>Mark slope</span><span>'+fmtBp(t.mark_slope_bp)+'</span></div>'
    + '<div class="row"><span>P&amp;L</span><span class="'+cls(t.pnl_gbp)+'">'+fmtGbp(t.pnl_gbp)+'</span></div>'
    + '</a>';
});
document.getElementById('foot').textContent = 'Updated '+INDEX.generated_utc+' · Not investment advice.';
</script>
</body>
</html>
"""


def trade_cards_html(trades: list[dict]) -> str:
    cards = []
    for t in trades:
        pnl_cls = "good" if t["pnl_gbp"] > 0.5 else "bad" if t["pnl_gbp"] < -0.5 else ""
        sign = "+" if t["pnl_gbp"] >= 0 else ""
        cards.append(
            f"""  <a class="card featured" href="{t['detail_page']}">
    <h2>{t['label']} · live P&amp;L</h2>
    <p>{t['position']}</p>
    <span class="pill live">● {t['direction']}</span>
    <span style="display:block;margin-top:10px;font-size:13px">P&amp;L <span class="{pnl_cls}">{sign}£{abs(t['pnl_gbp']):,.0f}</span> · mark {t['mark_slope_bp']:+.1f} bp</span>
  </a>"""
        )
    return "\n".join(cards)


def portal_html(trades: list[dict]) -> str:
  trade_section = trade_cards_html(trades)
  return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0b0f17"/>
<title>Supra · Markets Portal</title>
<style>
:root{{--bg:#0b0f17;--card:#131a26;--line:#243043;--ink:#e8eef7;--mut:#93a1b5;--acc:#39d98a;--warn:#ffb84a;--bad:#ff6b6b;--good:#39d98a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif}}
.wrap{{max-width:960px;margin:0 auto;padding:20px 16px 64px}}
header{{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--card);margin-bottom:20px}}
.eyebrow{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}}
h1{{margin:8px 0 6px;font-size:clamp(22px,4vw,30px)}}
.sub{{color:var(--mut);font-size:14px;line-height:1.5}}
.grid{{display:grid;gap:14px}}
@media(min-width:700px){{.grid.cols-2{{grid-template-columns:1fr 1fr}}}}
.card{{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;text-decoration:none;color:inherit;transition:border-color .15s}}
.card:hover{{border-color:var(--acc)}}
.card h2{{margin:0 0 6px;font-size:16px}}
.card p{{margin:0;color:var(--mut);font-size:13px;line-height:1.45}}
.card.featured{{border-color:rgba(57,217,138,.35);background:linear-gradient(165deg,var(--card),rgba(57,217,138,.05))}}
.pill{{display:inline-block;font-size:11px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);color:var(--mut);margin-top:10px}}
.pill.live{{border-color:var(--acc);color:var(--acc)}}
.good{{color:var(--good)}}.bad{{color:var(--bad)}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Supra Fund Management</div>
  <h1>Markets portal</h1>
  <div class="sub">Live dashboards &amp; trade trackers · Barchart EOD · auto-refresh weekdays</div>
</header>
<div class="grid cols-2">
  <a class="card featured" href="trade_tracker.html">
    <h2>All live trades</h2>
    <p>Jul27−Dec26 steepener &amp; Jul27−Dec27 flattener · daily P&amp;L &amp; regime attribution.</p>
    <span class="pill live">● Trade tracker</span>
  </a>
{trade_section}
  <a class="card" href="sonia_1m_dashboard.html">
    <h2>1M SONIA curve live</h2>
    <p>Full JU* strip, MPC pricing, daily Δ table, phone layout.</p>
  </a>
  <a class="card" href="sonia_dashboard.html">
    <h2>Dec27−Dec26 SONIA monitor</h2>
    <p>Slope, basis, Brent correlation, prior steepener entry.</p>
  </a>
  <a class="card" href="stir_curves_dashboard.html">
    <h2>STIR curves (SOFR / SONIA / €STR)</h2>
    <p>3M quarterly chains, 88+ contracts.</p>
  </a>
  <a class="card" href="index.html">
    <h2>FFR−SOFR basis</h2>
    <p>US money markets · July trade monitor.</p>
  </a>
</div>
</div>
</body>
</html>
"""


def main() -> None:
    with INDEX_FILE.open(encoding="utf-8") as f:
        index = json.load(f)

    outputs: list[tuple[str, str]] = []

    hub = HUB_HTML.replace("__INDEX_JSON__", json.dumps(index))
    outputs.append(("trade_tracker.html", hub))

    portal = portal_html(index["trades"])
    outputs.append(("portal.html", portal))

    for t in index["trades"]:
        data_path = ROOT / t["data_file"]
        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)
        page = (
            DETAIL_HTML.replace("__PAGE_TITLE__", f"{data['trade']['label']} · live tracker")
            .replace("__DATA_JSON__", json.dumps(data))
        )
        outputs.append((t["detail_page"], page))

    for name, html in outputs:
        for prefix in ("", "docs/"):
            out = ROOT / prefix / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            print(f"Wrote {out}")


if __name__ == "__main__":
    main()
