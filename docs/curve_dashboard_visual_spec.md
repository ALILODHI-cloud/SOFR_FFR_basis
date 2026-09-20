# STIR curve dashboard — visual / UX spec (replicate exactly)

This file is the implementation brief for another agent. It describes the **live curve dashboards** Ali already has: frozen green latest strip, amber historical overlay, date slider, play, pin cards, calendar-slope banner, central-bank meeting panel, contract table, and daily-Δ heatmap.

**Canonical source to clone:** `build_euribor_3m_dashboard.py` (latest copy of the shared template). Same UX lives in:

| Dashboard | Builder | HTML | Policy field | Meeting object |
|---|---|---|---|---|
| 1M SONIA | `build_sonia_1m_dashboard.py` | `sonia_1m_dashboard.html` | `bank_rate_pct` | `mpc_meeting_pricing` |
| 3M SONIA | `build_sonia_3m_dashboard.py` | `sonia_3m_dashboard.html` | `bank_rate_pct` | `mpc_meeting_pricing` |
| 1M €STR | `build_estr_1m_dashboard.py` | `estr_1m_dashboard.html` | `deposit_facility_pct` | `ecb_meeting_pricing` |
| 3M €STR | `build_estr_3m_dashboard.py` | `estr_3m_dashboard.html` | `deposit_facility_pct` | `ecb_meeting_pricing` |
| 3M Euribor | `build_euribor_3m_dashboard.py` | `euribor_3m_dashboard.html` | `deposit_facility_pct` | `ecb_meeting_pricing` |
| 3M SOFR | `build_sofr_3m_dashboard.py` | `sofr_3m_dashboard.html` | `fed_funds_pct` | `fomc_meeting_pricing` |
| 30d Fed Funds | `build_ff_30d_dashboard.py` | `ff_30d_dashboard.html` | `fed_funds_pct` | `fomc_meeting_pricing` |
| ASX 30d IB | `build_asx_ib_30d_dashboard.py` | `asx_ib_30d_dashboard.html` | `cash_rate_pct` | `rba_meeting_pricing` |

**Do not treat these as the same product:**

- `sonia_dashboard.html` — Dec27−Dec26 **slope/basis monitor**. No full-strip time-travel slider.
- `estr_sonia_1m_dashboard.html` — two-curve **bp-vs-policy** comparison.
- `portal.html` — card index only.

If the task is “the curve with the slider and pins,” replicate the family in the table, not the slope monitor.

---

## 1. What the user sees (one sentence)

A dark single-page app that **always draws the latest EOD curve in green and never moves it**, then lets you **scrub an amber copy of the same strip through every historical session** with a range slider, pin any contracts, and read meeting-implied hike/hold/cut probabilities underneath.

That sentence is the product. If green moves with the slider, the replica is wrong.

---

## 2. Design tokens (copy exactly)

CSS variables on `:root`:

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0b0f17` | Page background |
| `--card` | `#131a26` | Header, cards, tooltip fill |
| `--line` | `#243043` | Borders, gridlines |
| `--ink` | `#e8eef7` | Primary text |
| `--mut` | `#93a1b5` | Hints, axis ticks, legend, muted table text |
| `--acc` | `#39d98a` | Frozen curve, live pill, “rate down”, next-meeting row tint, active layout toggle |
| `--hist` | `#ffb84a` | Historical / slider curve, slider accent, slope banner border, Δ-slope column header |
| `--policy` | `#4aa8ff` | Policy-rate dashed line, meeting cumulative line |
| `--pin` | `#c084fc` | Default pin border / first pin color |
| chip fill | `#1b2536` | Pills, pin cards, meeting stats, sticky table header |

**Pin color cycle** (assigned in order, wrap with modulo):

`#c084fc`, `#f472b6`, `#22d3ee`, `#fb923c`, `#a3e635`, `#facc15`

**Meeting / Δ colors:**

| Meaning | Color |
|---|---|
| Cut / rate down (easing) | `#39d98a` / `rgba(57,217,138,0.75)` on bars |
| Hold / flat | `#64748b` / `rgba(100,116,139,0.75)` |
| Hike / rate up | `#f87171` / `rgba(248,113,113,0.75)` |
| Strong hike (≥ +8 bp session) | `#fca5a5` + bold |
| Strong cut (≤ −8 bp session) | `#6ee7a8` + bold |
| Next meeting row | `background: rgba(57,217,138,0.06)` |
| Past meeting row | `color: var(--mut)` |
| Slider-date highlight in Δ table | `rgba(255,184,74,0.08)` on cells; sticky date cell `#1a2233` |

**Typography**

- Font: `system-ui, sans-serif` (not a webfont).
- Page max width: `1200px`, centered, padding `16px 16px 48px`.
- `h1`: `clamp(20px, 4vw, 28px)`, margin `4px 0`.
- Card `h2`: `15px`.
- Hints: `12px`, `--mut`, line-height `1.45`.
- Numbers: `font-variant-numeric: tabular-nums`.
- Implied rates: **three decimals** + `%` (`3.015%`).
- Basis points: sign always shown except exact-zero formatter in the Δ table (`+51.5 bp`, `−3.0 bp`, em dash `—` for null).

**Shape**

- Header radius `16px`, card radius `14px`, pin/stat radius `10px`, pills radius `20px`, buttons radius `8px`.
- Header / cards: `1px solid var(--line)`, background `--card`.
- No drop shadows except the sticky Δ-table header (`box-shadow: 0 1px 0 var(--line)`).

**Libraries**

- Chart.js `4.4.1` UMD from jsDelivr.
- `chartjs-plugin-annotation` `3.1.0`.
- No React, no Vue, no build step. One self-contained HTML file with **embedded JSON**.

---

## 3. Page chrome (top to bottom)

### 3.1 Header card

1. Optional back-nav line, 13px, `#93a1b5`, no underline:
   - `← Markets portal` → `portal.html`
   - Sibling curve link when it exists (Euribor also links `3M €STR`).
2. Title pattern: `{tenor} {name} curve · frozen reference + time travel`
   Examples: `3M Euribor curve · frozen reference + time travel`, `1M SONIA curve · frozen reference + time travel`.
3. `#asof` subtitle: `Data {generated_utc}` and, if live status exists, ` · refresh {last_refresh_utc}`.
4. Legend pills in one row:
   - Frozen: class `pill frozen`, text `■ Frozen = latest curve`, green border/text.
   - Historical: inline style amber border/text, `■ Amber = historical (slider)`.
   - Policy: `#policyPill`, class `pill policy`. Copy is curve-specific:
     - SONIA: `BoE {bank_rate}%` (or similar).
     - €STR / Euribor: `ECB dep {deposit}%`.
     - SOFR / FF: Fed-funds midpoint.
     - ASX: cash rate.
   - Live: `#livePill`, class `pill live`, text `● Live`, **hidden by default**. Show only in live mode (see §10).
5. Layout toggle, right-aligned under the pills (`viewbar`):
   - Tiny uppercase label `Layout`.
   - Two-button segmented control: `Desktop` | `Phone`.
   - Active button: green fill `#39d98a`, text `#0b0f17`, bold.
   - Inactive: transparent, `--mut` text.

### 3.2 Card: Curve comparison

- `h2`: `Curve comparison`
- Long hint (class `hint long`, hidden on phone):

  > Opens on the **latest** curve (frozen green). Scrub the slider to morph the amber line through history — green stays fixed. **Click** any point to pin a detail card (cards persist). Pin exactly two legs to see calendar slope at top. Toggle “level line” per pin only when you want a dotted horizontal.

- Short hint (`#hintShort`, hidden on desktop):

  > Green = latest · amber = slider date · tap curve to pin · two pins = slope

- `#slopeBanner` — hidden until exactly two pins (see §6).
- Flex row `.chart-wrap`:
  - `.chartbox` flex 1, height **480px**, contains `<canvas id="mainChart">`.
  - `#pinTray` width **240px**, max-height 480px, overflow-y auto.
  - Empty tray placeholder (CSS `::before`): `Click curve points to pin contracts here. Pins stay on screen while you scrub time.`
- Slider row (see §5).
- `#evoHint` under the slider: evolution note + session count + date range.

### 3.3 Card: Meeting pricing

Title examples:

- `BoE MPC meeting pricing (from 1M SONIA strip)`
- `ECB Governing Council meeting pricing (from 3M Euribor strip)`
- `FOMC meeting pricing (from 30-day Fed Funds strip)`

Contents, in order:

1. `#…Note` — the pricing caveat from JSON (`note`). Must say this is approximate futures mapping, not official WIRP/OIS, 25 bp steps.
2. Summary chips (flex wrap, gap 10px):
   - Policy rate, two decimals + `%`.
   - `Total easing priced` → actually `total_easing_priced_bp` (last meeting’s cumulative vs policy). Format with `fmtBp`.
   - Next meeting: label, big incremental bp, then `cut% cut · hold% hold · hike% hike`.
3. Meeting chart, height **220px** (`#ecbChart` / `#mpcChart` / `#fomcChart`).
4. Meeting table (sticky-scroll `.tblwrap` max-height 320px). Columns:

   `Meeting | Ref {tenor} | Implied % | Cum vs {policy} | Δ at meeting | Cut | Hold | Hike | Probs`

   Meeting cell: `MM-DD · {label}` from `meeting_date.slice(5)`.
   Ref cell: `{ref_contract_label}` + muted symbol.
   Last column: 8px stacked bar (`prob-cut` / `prob-hold` / `prob-hike`) widths = those percents.

### 3.4 Card: All contracts (latest)

Columns: `Delivery | Symbol | Implied % | vs {policy} | As of`

Sort by `delivery_ym`. Latest snapshot only — this table does **not** follow the slider.

### 3.5 Card: Daily changes (bp) · all contracts

Hint explains color meaning and that the highlighted row is the slider date.

Wide table in `.chg-wrap` (max-height 520px, border, radius 10px). See §7.

### 3.6 Footer

`#foot` — source, quote convention (`price = 100 − implied rate`), EOD-only Barchart rule. Keep muted 12px.

---

## 4. Main chart — exact behavior

Chart.js `type: 'line'`. `responsive: true`, `maintainAspectRatio: false`.

**Animation is off.** Use:

```js
const NO_ANIM = { duration: 0, easing: 'linear' };
```

and `animation: NO_ANIM` plus `transitions.active` / `transitions.resize` also `NO_ANIM`. Slider updates call `mainChart.update('none')`.

### 4.1 Three datasets, this order

| # | Label | Color | Width | Points | Order |
|---|---|---|---|---|---|
| 0 | `Frozen · latest` | `#39d98a` | 3 | yes | 1 |
| 1 | `Historical · {YYYY-MM-DD}` | `#ffb84a` | 2 | yes | 2 |
| 2 | `{Policy name} {rate}%` | `#4aa8ff` dashed `[6,4]` | 1.5 | **no** (`pointRadius: 0`) | 3 |

- Tension `0.28` on the two curves.
- `spanGaps: true` — later-listed contracts with no print on an old date leave a hole; the amber line skips them. Do not interpolate a fake rate.
- Point border `#0b0f17`, width 2.
- Default point radius **5**; pinned radius **9**.
- Hit radius = radius + **14** (large tap target).
- Unpinned point fill = dataset color. Pinned point fill = that pin’s color on **both** green and amber.

X labels are contract **labels** (`Dec-26`, `Mar-27`, …), not dates. X index `i` maps to `keys[i]` (`YYYY-MM`).

Y axis:

- Title `Implied rate (%)`.
- Ticks `v.toFixed(2) + '%'`.
- Domain = min/max of **all frozen points + all historical points + policy rate**, then pad `max(0.08, (hi-lo)*0.12)`.
- Do not auto-rescale on every slider tick; compute once from the full history so the green line does not jump.

Legend at **bottom**, muted labels, `usePointStyle: true`.

Interaction: `{ mode: 'nearest', intersect: false, axis: 'x' }`.

### 4.2 Click-to-pin

`onClick`:

1. Use clicked elements; if empty, `getElementsAtEventForMode(..., 'nearest', { intersect: false })`.
2. Ignore dataset index 2 (policy line).
3. `addPin(keys[el.index])`.
4. If that key is already pinned, **do nothing** (no unpin-on-second-click). Unpin only via the card’s Remove button.

Tooltip:

- Dark `#131a26` with `#243043` border.
- After title: futures **symbol** (`IMZ26`, `JUZ26`, …).
- Lines: dataset label + rate to 3dp; on amber also `Δ vs frozen` and `vs {policy}`; on green `vs {policy}`; last line always `Click to pin`.

### 4.3 Pin annotations (annotation plugin)

For each pin, a **label** sitting on the **frozen** point (`y = frozen implied`, `x = index`):

- `yAdjust: -14`
- Background `rgba(19,26,38,0.92)`
- Border / text = pin color
- Content: `{label} {rate.toFixed(3)}%` e.g. `Dec-26 3.015%`

Optional **level line** (off by default): horizontal dashed `[5,5]` at the **frozen** rate, width 1.5, end label `{label} level`. Only if that pin’s checkbox is on.

---

## 5. Slider, Latest, Play

DOM order on desktop: `[ ▶ Play ] [ Latest ] [======range======] [YYYY-MM-DD]`

- Range `#dateSlider` `min=0`, `max = history.length - 1`, `accent-color: var(--hist)` (amber thumb).
- `#sliderDate` tabular, min-width 100px.

**Initial state:** `evoIdx = history.length - 1` (latest session). Amber sits **on top of green**. User must see that on first paint.

`oninput` and `onchange` both set `evoIdx` and call `applySlider(true)`.

**Latest** sets `evoIdx` to last index.

**Play:**

- If already playing: clear interval, button text back to `▶ Play`.
- Else: jump `evoIdx` to **0** (oldest), button `⏸ Pause`, `setInterval` every **120 ms**, increment until last session, then stop and restore `▶ Play`.
- Play must update the slider thumb, the date label, amber data, pin cards, slope banner, and the highlighted Δ-table row.

`applySlider` also rewrites dataset 1’s label to `Historical · {date}`.

`#evoHint` example:

> Full listed 3M Euribor strip (24 contracts through 2032-09). Later deliveries have shorter history; the amber line skips missing points. · 64 sessions · 2026-06-22 → 2026-09-17

---

## 6. Pin tray and slope banner

Each pin card (`.pin-card.pinned`), border = pin color:

```
{label}                 e.g. Dec-26
{symbol}                e.g. IMZ26
Frozen (latest)         3.015%
Historical              2.590%
vs deposit 2.5%         −8.5 bp     ← policy label/rate is curve-specific
Δ vs frozen             −42.5 bp
{slider date}
☐ Show level line
[ Remove ]
```

- Historical / vs-policy / Δ use the **slider session**, not frozen.
- `Δ vs frozen` = `(hist - frozen) * 100` bp.
- Checkbox default **unchecked**.
- Remove splices that pin, then refresh tray, banner, chart.

**Slope banner** (`#slopeBanner`) shows **only when `pins.length === 2`**.

- Sort the two pins by `key` (`YYYY-MM`) so front = earlier delivery, back = later.
- `histSlope = (hBack - hFront) * 100`
- `frozenSlope = (fBack - fFront) * 100`
- `delta = histSlope - frozenSlope`
- Copy:

  **`{back.label} − {front.label}`** on **`{date}`**: **`{histSlope}`** (amber curve) · frozen was `{frozenSlope}` · Δ `{delta}`

- Banner: `#1b2536` fill, amber border, 10px radius, strong text amber. Hidden (`display:none`) otherwise.

This is how the user reads Dec27−Dec26 (or Jun27−Dec26) **through time** without leaving the strip chart.

---

## 7. Daily Δ table (the heatmap)

Built from `DATA.timeseries.rows`, not from `curve_evolution`.

For each session `i ≥ 1`:

- `Δ bp = round((cur[k] - prev[k]) * 1000) / 10`  → one decimal, already in bp.
- Skip a cell if either side is null (`—`).
- After the last contract column, **Δ slope** = change in `(rate[2027-12] - rate[2026-12]) * 100`. Hard-coded Dec26/Dec27 keys in the current builders. If you add a new curve that has those two quarters, keep it. If not, omit or generalize to the two pinned keys — but the existing dashboards use Z26/Z27.

Row order: **newest first** (`rows.reverse()`).

Header row: sticky top (`#1b2536`). First column `Date` is sticky left. Date cell `title="vs {prevDate}"`.

**Color bins** (`chgCellClass`):

| |Δ| | class | color |
|---|---|---|
| null / \|Δ\| < 0.5 | `chg-flat` | `--mut` |
| +0.5 to +7.9 | `chg-up` | `#f87171` |
| ≥ +8.0 | `chg-up-strong` | `#fca5a5` bold |
| −0.5 to −7.9 | `chg-dn` | `--acc` green |
| ≤ −8.0 | `chg-dn-strong` | `#6ee7a8` bold |

`fmtChgBp`: null → `—`; `|bp| < 0.05` → `0.0` (no plus); else `+1.5` / `-2.0`.

**Highlight:** if `row.date === slider date`, class `row-hi`. Scrubbing the slider must move this highlight. That is how the table and the chart stay coupled.

Color convention (do not invert): **green = rate down / cuts priced; red = rate up / hikes priced.** This is a rates dashboard, not an equity dashboard.

---

## 8. Meeting panel chart

Mixed chart: upcoming meetings only (`status !== 'past'`).

- Line dataset: cumulative vs policy (bp), `#4aa8ff`, pointRadius 4.
- Bar dataset: incremental bp at that meeting. Bar color by sign: green if `<0`, red if `>0`, slate if `0`.
- X labels: `MM-DD` (`meeting_date.slice(5)`).
- Y ticks: signed (`+40`, `-10`).
- Height 220px desktop, 180px phone.

Probabilities (data layer, already in JSON):

```
cut  = clamp(-incremental_bp / 25, 0, 1)
hike = clamp( incremental_bp / 25, 0, 1)
hold = 1 - cut - hike
```

25 bp steps. Not a proper binomial FedWatch model. Keep the disclaimer.

Meeting `status`:

- `past` if meeting date ≤ `max(today, latest EOD on the strip)`
- first non-past = `next`
- rest = `upcoming`

**1M / 30d mapping:** meeting → **next calendar month** contract.  
**3M / quarterly mapping:** meeting → **next quarter** (`H` Mar, `M` Jun, `U` Sep, `Z` Dec).

---

## 9. Phone / desktop layout

Two triggers, both must exist:

1. CSS `@media (max-width: 720px)` — automatic.
2. `body.view-phone` — forced by the Layout toggle.

Phone changes:

- Chart column stack; chart height `min(52vw, 340px)`, min-height 260px.
- Pin tray becomes a **horizontal** scroller; each card `min-width: 168px`.
- Long hint hidden; short hint shown.
- Slider wraps: both buttons on row 1, range full-width row 2 (`order:3`), date centered row 3.
- Buttons grow (`flex:1`, padding `10px 8px`).
- Meeting stats two-up (`calc(50% - 6px)`).
- Bottom safe-area padding: `calc(48px + env(safe-area-inset-bottom))`.
- After toggle, `requestAnimationFrame` → `mainChart.resize()` and meeting-chart resize.

`localStorage` key is **per dashboard** (do not share):

| Page | `VIEW_KEY` |
|---|---|
| 1M SONIA | `sonia1m_layout` |
| 3M SONIA | `sonia3m_layout` |
| 1M €STR | `estr1m_layout` |
| 3M €STR | `estr3m_layout` |
| 3M Euribor | `euribor3m_layout` |
| 3M SOFR | `sofr3m_layout` |
| 30d FF | `ff30d_layout` |
| ASX 30d | `asxib30d_layout` |

Values: `'phone'` | `'desktop'`. If unset, follow `matchMedia('(max-width: 720px)')`. If the user has saved a choice, ignore later media changes.

---

## 10. Live vs GitHub Pages

`isLiveMode()` is true only when hostname is:

- `localhost` or `127.0.0.1`
- `*.devtunnels.ms`
- `*.trycloudflare.com`

Otherwise (including `*.github.io`) **never hit the network**. Use the baked-in `EMBEDDED` JSON.

In live mode:

- `GET /api/data?{Date.now()}` for a fresh snapshot; on any failure, fall back to `EMBEDDED`.
- `GET /api/status` for `last_refresh_utc`.
- Poll every `LIVE_POLL_MS = 60000`.
- Show the green `● Live` pill.

GitHub Pages must work with **zero API**. The HTML file is the data.

---

## 11. Data contract the viz must consume

Embedded as `const EMBEDDED = {…}` then `let DATA = EMBEDDED`.

```json
{
  "generated_utc": "2026-09-18 13:54 UTC",
  "source": "Barchart historical lastPrice (finalized EOD sessions only)",
  "contract": "ICE 3M Euribor (IM*)",
  "quote_convention": "price = 100 − implied rate (%)",
  "deposit_facility_pct": 2.5,
  "n_contracts": 24,
  "contracts": [
    {
      "key": "2026-12",
      "label": "Dec-26",
      "symbol": "IMZ26",
      "delivery_ym": "2026-12",
      "latest_date": "2026-09-17",
      "price": 96.985,
      "implied_rate_pct": 3.015,
      "vs_deposit_bp": 51.5,
      "bp_change": null
    }
  ],
  "timeseries": {
    "columns": ["2026-12", "2027-03", "..."],
    "rows": [{ "date": "2026-09-17", "2026-12": 3.015, "2027-03": 3.315 }],
    "n_sessions": 64,
    "start": "2026-06-22",
    "end": "2026-09-17"
  },
  "curve_evolution": {
    "contract_keys": ["2026-12", "..."],
    "n_sessions": 64,
    "start": "2026-06-22",
    "end": "2026-09-17",
    "note": "Full listed … amber line skips missing points.",
    "history": [
      {
        "date": "2026-09-17",
        "points": [
          {
            "key": "2026-12",
            "label": "Dec-26",
            "symbol": "IMZ26",
            "implied_rate_pct": 3.015,
            "vs_deposit_bp": 51.5
          }
        ]
      }
    ]
  },
  "ecb_meeting_pricing": {
    "note": "Approximate meeting path …",
    "deposit_facility_pct": 2.5,
    "total_easing_priced_bp": 91.0,
    "next_meeting": { "meeting_label": "Oct ECB", "incremental_bp": 0, "cut_pct": 0, "hold_pct": 100, "hike_pct": 0 },
    "meetings": [
      {
        "meeting_date": "2026-10-29",
        "meeting_label": "Oct ECB",
        "status": "next",
        "ref_contract_key": "2026-12",
        "ref_contract_label": "Dec-26",
        "ref_symbol": "IMZ26",
        "implied_rate_pct": 3.015,
        "cumulative_vs_deposit_bp": 51.5,
        "incremental_bp": 0.0,
        "cut_pct": 0,
        "hold_pct": 100,
        "hike_pct": 0
      }
    ]
  }
}
```

Policy field names differ by curve (`bank_rate_pct`, `deposit_facility_pct`, `fed_funds_pct`, `cash_rate_pct`) and so do the `vs_*_bp` fields on each contract. Meeting block name differs (`mpc_meeting_pricing`, `ecb_meeting_pricing`, `fomc_meeting_pricing`, `rba_meeting_pricing`). The **shapes** are the same.

`curve_evolution.history` is chronological (oldest first). Slider index 0 = first history date.

EOD rule: drop the in-progress session (today before ~5pm ET, or a thin-volume bar). The last history date is a **finished** session.

Quote: futures price = `100 − implied rate`. The chart plots **rate**, not price.

---

## 12. Small features people miss (checklist)

- [ ] Green line is latest EOD and **does not move** when the slider moves.
- [ ] First paint: slider at the **right** (latest); amber overlaps green.
- [ ] Play starts from the **left** (oldest) at 120 ms/frame, not from the current thumb.
- [ ] Amber **skips** missing points (`spanGaps: true`); do not invent a 2032 rate in 2026-06.
- [ ] Click pin; second click on same point does **not** unpin.
- [ ] Pins survive slider motion and play.
- [ ] Level line off until checked; line uses **frozen** level, not historical.
- [ ] Slope banner only for **exactly two** pins; order by delivery, later minus earlier.
- [ ] Pin point swells to radius 9 and recolors on both curves.
- [ ] Tooltip says `Click to pin` and shows the ticker.
- [ ] Policy line is dashed blue, no points.
- [ ] Y-axis pad includes the policy rate so the dashed line is never clipped.
- [ ] No Chart.js animation on slider or hover.
- [ ] Δ table newest-first; highlighted row = slider date.
- [ ] Green Δ = rates down; red Δ = rates up. Never the equity convention.
- [ ] Strong coloring at ±8 bp.
- [ ] Δ slope column is Dec27−Dec26 spread change, amber header, left border.
- [ ] Next meeting row has a faint green wash; past rows muted.
- [ ] Prob bar is cut/hold/hike in that order, green/slate/red.
- [ ] Live pill hidden on GitHub Pages; embedded JSON is the source of truth.
- [ ] Desktop/Phone toggle persisted per-curve in `localStorage`.
- [ ] Phone: pins scroll sideways; slider stacks under the buttons.
- [ ] Rates to 3 decimals; bp to 1 decimal with sign.
- [ ] Header pills document green vs amber **before** the user touches anything.
- [ ] Contract table is latest-only; do not bind it to the slider.
- [ ] Back link to `portal.html`.
- [ ] Footer states 100 − rate and EOD-only.

---

## 13. Portal card (if you add a new curve)

`portal.html` / `docs/portal.html` / `PORTAL_HTML` in `build_trade_tracker.py` stay in sync.

Card: dark, 14px radius, no underline, title 16px, one-line blurb with **as-of date + the slope or meeting hook**. Example:

`3M Euribor curve · ECB`  
`17 Sep EOD · Z27−Z26 +43.5 · next Oct ECB`

Portal page: same tokens, max-width 960px, 2-column grid from 700px, eyebrow `Supra Fund Management`, section labels uppercase tracked.

---

## 14. How to implement without drifting

1. Copy `build_euribor_3m_dashboard.py` (or the matching builder for the curve).
2. Swap title, policy field names, meeting object name, `VIEW_KEY`, sibling nav link, and JSON filename.
3. Do **not** restyle colors, radii, or chart tensions “to improve” them.
4. Keep the file a single HTML with `__DATA_JSON__` replaced at build time; write both repo-root and `docs/` copies.
5. Smoke-test: load the HTML with no server (Pages mode), scrub to mid-sample, pin Dec-26 and Dec-27, confirm the amber slope banner and the highlighted Δ row, toggle Phone, hit Play, hit Latest.

Reference live files in this repo: `euribor_3m_dashboard.html`, `sonia_1m_dashboard.html`, `ff_30d_dashboard.html`.
