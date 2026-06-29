# UK SONIA Dec27−Dec26: Front-Loaded Hike Pricing and the Calendar Steepener

At trade inception (Friday 5 June 2026 EOD), cumulative hiking priced through Dec-2027 sat at **+46 bp** versus the BoE Bank Rate of **3.75%** — but **92%** of that total was already embedded in Dec-2026, with only **+3.5 bp** in the Dec27−Dec26 calendar increment (Figure 1). That is an unusually front-loaded curve: almost the entire hiking path sits in the front contract, and the calendar belly is barely priced for any further restriction beyond Dec-2026.

*Figure 1. Cumulative through Dec-27 — stacked share bars at entry vs mark. At entry (5 Jun 2026): +46.0 bp total priced above 3.75% Bank Rate; +42.5 bp (92%) in Dec-26, +3.5 bp (8%) in Dec27−Dec26 increment. Dashboard section: “Cumulative through Dec-27”. Source: `sonia_dashboard.html` / `sonia_dashboard_data.json`.*

<!-- Alt_text: Stacked bar chart comparing hike pricing at trade entry vs latest. Entry bar almost entirely blue (Dec-26 portion); thin orange sliver (Dec27-Dec26 increment). Now bar shows smaller total with a larger orange share. -->

---

ICE 1M SONIA futures are quoted as 100 minus the implied average SONIA rate over each contract window. When the market prices a hawkish BoE path, front-end contracts — here Dec-2026 — tend to absorb the bulk of the repricing before the back end moves. The implied rate on JUZ26 rises (the future falls), and the Dec27−Dec26 spread compresses unless Dec-2027 is repricing in lockstep.

So the causal chain, as conventionally told, runs as follows: the Middle East conflict pushes up energy prices → headline CPI re-accelerates → the BoE must hike (or reverse previously priced cuts) → Dec-2026 implied rates rise further → the Dec27−Dec26 slope compresses or inverts. A natural expression is to **sell the front leg** of a Dec-26 / Dec-27 calendar spread — or, in swap space, to **pay fixed** at the Dec-2026 point.

But in fact one step is missing. That conclusion only follows if: **(i)** the BoE's required policy response is genuinely hawkish relative to what is already priced; and **(ii)** that response must fall disproportionately on the front end of the curve (Dec-2026), rather than being absorbed by a repricing of the back end alone. Absent **(i)**, the entire hiking narrative is moot — the curve is fairly priced and there is nothing to pay. Absent **(ii)**, even a modest tightening requirement would widen the Dec27−Dec26 increment rather than crush it, and the correct trade is the opposite of belly-paying: **long Dec-26 / short Dec-27**, i.e. a bull steepener.

---

The April 2026 Monetary Policy Report makes **(i)** contestable. The MPC conditioned three scenarios on the market-implied Bank Rate path (15 UK working days to 22 April 2026):

| Scenario | Energy shock | Second-round effects | CPI end-2026 (market curve) | Policy implication |
|---|---|---|---|---|
| **A** | Futures curves; relatively short-lived | **None** — slack limits pass-through | **3.6%** | Tightening largely via **reversing ~40 bp of cuts** priced in February; market curve already **~55 bp higher** |
| **B** | Same peak, more persistent | **Modest** (Bernanke-Blanchard calibration) | **3.7%** | Same; **~55 bp** market repricing **within range** of rule-implied tightening for B |
| **C** | Prolonged ($130/bbl oil, 211 p/therm gas) | **Material** — expectations embed | **>6%** peak (start 2027) | Bank Rate must rise **materially above** market path; staff model: **~5.25% by 2027 Q1** |

Governor Bailey (press conference, 30 April 2026): *"For Scenarios A and B, the illustrative interest rate responses would largely be accommodated by reversing out [the] assumed cuts without further increases in rates… this would not be the case for Scenario C."* And: *"It is not the case that we're giving some sort of slightly clandestine message that interest rates are going to go up… it's an active hold."*

At entry, Dec-2026 priced **+42.5 bp** above 3.75%. That is a front-end hiking path closer to **Scenario C** than to **A/B** — despite incoming data pointing the other way (Figure 2).

*Figure 2. Forward pricing vs Bank Rate — 50-session time series. Dec-26 and Dec-27 implied rates (bp above 3.75%) with zero line; orange dashed vertical at Fri 5 Jun entry. Both series elevated at entry (~+42 bp / +46 bp), Dec-26 tracking above policy by a wide margin. Dashboard section: “Forward pricing vs Bank Rate”.*

<!-- Alt_text: Line chart, 50 days. Two lines (Dec-26 blue, Dec-27 amber) both positive vs 0 bp policy line. Orange vertical entry marker on 2026-06-05. Dec-26 line higher than Dec-27 throughout; gap is calendar slope. -->

---

Macro releases available at inception undercut **Scenario C** and support **A/B**:

- **Labour market overview, UK: May 2026** (ONS, 19 May): unemployment **5.0%** (Jan–Mar), up from **4.9%** (Dec–Feb); vacancies and payrolls softening. Key Policy Judgement 1 (April MPR): *"Continued weakness in demand and the labour market is likely to lessen the strength of second-round effects."*
- **Consumer price inflation, UK: April 2026** (ONS, 20 May): CPI **2.8% y/y** (from **3.3%**); CPIH services **3.4%** (from **4.3%**).
- **Citi/YouGov inflation expectations** (27 Apr): one-year-ahead **5.0%** (from **5.4%** in March; March spike described as *"anomalous"*); Citi: *"little basis yet"* for a hawkish read.
- **S&P Global UK Services PMI** (final, 3 Jun): **49.3** in May (from **52.7** in Apr) — first contraction since Apr 2025; new orders down three months running.
- **Retail sales, Great Britain: April 2026** (ONS, 22 May): volumes **−1.3% m/m** (consensus **−0.6%**); ex-fuel **−0.4%**.

The question then stands: with the BoE holding at **3.75%** (8–1 at April MPC; Megan Greene the sole dissenter for +25 bp) and financial conditions already **~55 bp tighter** than February, can we expect another wave of front-end hike pricing — and thus further selling of Dec-2026 versus Dec-2027 — as the energy shock works through?

Well, we need just check whether **(i)** and **(ii)** obtain. Though not quite just that. Though true the macro data favour **A/B**, we need also know the **extant pricing** in SONIA futures: maybe the front end is *already* too hawkish — perhaps because markets front-ran a Scenario C that the BoE explicitly rejects, or because the **~55 bp** of market tightening since February was loaded into Dec-2026 rather than distributed across the curve — in which case we should expect not paying but **unwinding**: Dec-26 implied rates fall faster than Dec-27, and the Dec27−Dec26 slope **widens**.

So in reality one must know:

1. **Cumulative hike priced through Dec-2027** — and its split between Dec-26 and the Dec27−Dec26 increment (is the belly already cheap?);
2. **Which BoE scenario the curve embeds** — A/B (reverse priced cuts, active hold) vs C (material second-round effects, Bank Rate toward ~5.25%);
3. **Whether incoming data confirm or refute second-round pass-through** — labour slack, services CPI, inflation expectations, activity PMIs.

It is only after furnishing answers to these questions that one may propose doing some **steepening** of their own — long Dec-26 / short Dec-27 on the UK SONIA curve.

---

## Trade expression (5 Jun 2026 EOD)

| Leg | Contract | Side | Entry implied | vs Bank Rate |
|---|---|---|---:|---:|
| Front | JUZ26 (Dec-2026) | **Long** | 4.175% | +42.5 bp |
| Back | JUZ27 (Dec-2027) | **Short** | 4.210% | +46.0 bp |
| **Calendar slope** | Dec27 − Dec26 | — | **+3.5 bp** | — |

**Thesis:** Front-loaded hike pricing (+42.5 bp in Dec-26, only +3.5 bp in the increment) is inconsistent with BoE Scenarios A/B and disinflationary macro. Expect Dec-26 to reprice lower relative to Dec-27 → slope widens.

**P&L sensitivity:** ~£12.50 per bp per 1:1 pair (£500k face per leg).

**Primary risks:** Scenario C materialises (prolonged energy disruption, second-round effects embed); BoE hikes (+25 bp dissent becomes majority); bear flattening (both legs sell off, back faster).

**Dashboard:** rebuild with `python3 analyze_sonia.py && python3 build_sonia_dashboard.py` — see [`sonia_dashboard.html`](../sonia_dashboard.html).

---

*Follow-up: [Mea culpa — two curve regimes and the modal path since entry](curve-steepener-mea-culpa.md).*

*Internal research note. Not investment advice. SONIA data: Barchart ICE EOD; policy anchor: BoE Bank Rate 3.75% (held since Dec 2025).*
