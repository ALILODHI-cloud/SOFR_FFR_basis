# Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock

*ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD), 2 Mar – 29 Jun 2026.*

Each phase has two things happening at once: a **level move** (rates up or down) and a **curve move** (steepening or flattening). The question in each window is: should you have matched the level **outright**, or expressed both the level and the curve through the **aligned spread**? And on the days that hurt the outright — front-end down-days in a bear phase, front-end up-days in a bull phase — did the phase's curve type still show up, insulating you?

---

## Setup

| Item | Detail |
|---|---|
| **Contracts** | J8Z26 (Dec-26), J8Z27 (Dec-27) |
| **Spread** | \(S_t = r_{\text{Dec27}} - r_{\text{Dec26}}\) (bp) |
| **Sample** | 2 Mar → 29 Jun 2026 |

**Hawk / dov** — trimmed μ̃ ± 1.5σ̃ of daily ΔDec26 (10% trimmed each tail):

| | |
|---|---:|
| **Hawk day** | ΔDec26 **> +9.3 bp** (front-end up; hurts a bull outright) |
| **Dov day** | ΔDec26 **< −7.8 bp** (front-end down; hurts a bear outright) |

**Risk-adjusted return** per structure within a phase:

\[\text{RA} = \frac{\bar{r}_{\text{daily}} \times 252}{\sigma_{\text{daily}} \times \sqrt{252}}\]

| Level move | Outright | Aligned curve |
|---|---|---|
| **Bear** (rates net higher) | Short Dec-26 | Flattener or steepener per phase shape |
| **Bull** (rates net lower) | Long Dec-26 | Flattener or steepener per phase shape |

---

## Four phases at a glance

| Phase | Window | Level | Curve | Outright vs |
|---|---|---|---|---|
| **I** | 2 Mar – 20 Mar | **Bear** | Bear flattening | Short Dec-26 vs **flattener** |
| **II** | 23 Mar – 17 Apr | **Bull** | Bull steepening | Long Dec-26 vs **steepener** |
| **III** | 20 Apr – 15 May | **Bear** | Bear steepening | Short Dec-26 vs **steepener** |
| **IV** | 18 May – 29 Jun | **Bull** | Bull flattening | Long Dec-26 vs **flattener** |

![Dec27−Dec26 four phases on ICE 3M SONIA](../charts/dec27_dec26_four_phases_3m.png)

---

## Phase I — Bear level, bear flattening

**Net:** Dec-26 **+128 bp**, Dec-27 **+89 bp**. Spread +9.5 → **−30 bp**.

**Question:** Short Dec-26 outright, or flattener (L Dec26 / S Dec27)?

| | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Short Dec-26 | 242 | **+9.5** |
| Flattener | 108 | +6.6 |

Outright wins on risk-adjusted terms over the full phase. But the flattener runs at less than half the vol.

### On days that hurt the outright (dov days — Dec-26 down big)

Bear outright is short Dec-26. A large front-end **down** move is the adverse session — rates fall, short loses.

| | n | Share of phase |
|---|---:|---:|
| Dov days | 2 | 14% |

| | Value |
|---|---:|
| Bear-flattening on dov days | **0%** |
| Modal curve type | Bull steepening 100% |
| Short Dec-26 avg | **−12.5 bp** |
| Flattener avg | **−2.8 bp** |

No flattening on dov days — the curve does not bail you out with the aligned shape. But the flattener still loses **far less** than the outright short on those sessions. The hedge here is vol reduction, not curve-type alignment on dov tails.

### On days that favour the outright (hawk days — Dec-26 up big)

| | n | Share |
|---|---:|---:|
| Hawk days | 9 | **60%** |

| | Value |
|---|---:|
| Bear-flattening on hawk days | **67%** |
| Short Dec-26 avg | **+18.7 bp** |
| Flattener avg | **+4.4 bp** |

Two-thirds of hawk days bear-flatten — the phase's curve type on the sessions that define it. Outright captures more of the move; flattener participates with the belly as offset.

**Verdict:** Outright short wins on RA. Flattener only makes sense if you wanted lower vol through a crisis that was 60% hawk-day bear-flattening.

---

## Phase II — Bull level, bull steepening

**Net:** Dec-26 **−45.5 bp**, Dec-27 **−36 bp**. Spread −24.5 → −15 bp.

**Question:** Long Dec-26 outright, or steepener (L Dec27 / S Dec26)?

| | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Long Dec-26 | 178 | **+5.0** |
| Steepener | 44 | +4.8 |

Near-parity on RA; steepener at **¼ the vol**.

### On days that hurt the outright (hawk days — Dec-26 up big)

Bull outright is long Dec-26. A large front-end **up** move is adverse.

| | n | Share of phase |
|---|---:|---:|
| Hawk days | 2 | 11% |

| | Value |
|---|---:|
| Any steepening on hawk days | **50%** |
| Modal | Bear steepening / bear flattening |
| Long Dec-26 avg | **−12.5 bp** |
| Steepener avg | **−0.5 bp** |

On one hawk day the curve **still steepens** — bear steepening, a different kind — and the steepener earns **+0.5 bp** while outright loses −11.5 bp. On the other hawk day it bear-flattens: steepener −1.5 bp vs outright −13.5 bp. Even when the front-end spikes against your bull view, half of hawk days still steepen. That is the hedge for being bull via the curve.

### On days that favour the outright (dov days — Dec-26 down big)

| | n | Share |
|---|---:|---:|
| Dov days | 5 | **28%** |

| | Value |
|---|---:|
| Bull-steepening on dov days | **80%** |
| Long Dec-26 avg | **+17.6 bp** |
| Steepener avg | **+3.8 bp** |

Dov tails are aligned — bull steepening dominates. Both structures earn; outright captures more.

**Verdict:** If you can take the vol, outright long marginally wins. If you want bull exposure with hawk-day insulation, the steepener is essentially tied on RA at a fraction of the risk.

---

## Phase III — Bear level, bear steepening

**Net:** Dec-26 **+39.5 bp**, Dec-27 **+53 bp**. Spread −13.5 → **0 bp**.

**Question:** Short Dec-26 outright, or steepener (L Dec27 / S Dec26)?

| | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Short Dec-26 | 116 | **+5.2** |
| Steepener | 43 | +4.6 |

Outright short wins on RA, but closely — and at nearly 3× the vol.

### On days that hurt the outright (dov days — Dec-26 down big)

| | n | Share of phase |
|---|---:|---:|
| Dov days | 2 | 11% |

| | Value |
|---|---:|
| Any steepening on dov days | **100%** |
| Modal | Bull steepening 100% |
| Short Dec-26 avg | **−12.5 bp** |
| Steepener avg | **+1.0 bp** |

This is the cleanest adverse-day hedge in the sample. Front-end rallies against your bear view, but the curve **still steepens** every time — and the steepener earns while the outright short loses. Being bear via the steepener insulates you on dov tails even though the steepening is bull-steep rather than bear-steep.

### On days that favour the outright (hawk days — Dec-26 up big)

| | n | Share |
|---|---:|---:|
| Hawk days | 2 | 11% |

| | Value |
|---|---:|
| Any steepening on hawk days | **0%** |
| Modal | Bear flattening 100% |
| Short Dec-26 avg | **+12.3 bp** |
| Steepener avg | **−2.8 bp** |

Hawk days flip the other way — bear-flattening, steepener loses, outright wins. Rare (11%), but the outright captures hawk tails better.

### On neutral days (79% of phase)

Bear-steepening modal **40%** — the phase's curve type on the grind, without a Dec-26 tail event.

**Verdict:** Outright short wins on RA narrowly. The steepener's case is dov-day insulation (100% steepening, +1.0 vs −12.5 bp) and the neutral-day bear-steep grind — not hawk tails.

---

## Phase IV — Bull level, bull flattening

**Net:** Dec-26 **−42 bp**, Dec-27 **−49 bp**. Spread +3.0 → −3.5 bp.

**Question:** Long Dec-26 outright, or flattener (L Dec26 / S Dec27)?

| | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Long Dec-26 | 81 | **+4.8** |
| Flattener | 35 | +0.9 |

Outright dominates on RA. Not close.

### On days that hurt the outright (hawk days — Dec-26 up big)

| | n | Share of phase |
|---|---:|---:|
| Hawk days | 1 | 3% |

| | Value |
|---|---:|
| Flattening on hawk days | **100%** |
| Modal | Bear flattening 100% |
| Long Dec-26 avg | **−15.5 bp** |
| Flattener avg | **+1.5 bp** |

One hawk day, but instructive: front-end spikes and the curve **flattens** (bear-flattening — belly does not participate). Outright crushed; flattener earns. On hawk sessions the aligned curve type fires even when the level move does not.

### On neutral days (90% of phase)

| | Value |
|---|---:|
| Bull-flattening on neutral days | **33%** (modal) |
| Long Dec-26 avg | **+1.4 bp** |
| Flattener avg | **≈ 0 bp** |

The phase is a slow bull-flattening grind on neutral sessions. Outright captures it; flattener treads water.

**Verdict:** Outright long wins clearly on RA. The flattener only pays on the rare hawk spike — correct curve type, but too few sessions to compete with outright over the phase.

---

## Synthesis

| Phase | Level + curve | RA winner | Adverse-day curve alignment | Hedge case for curve? |
|---|---|---|---|---|
| **I** Bear + bear flat | Short **9.5** vs flat 6.6 | Outright | 0% flat on dov days | Vol only — flattener loses less on dov tails |
| **II** Bull + bull steep | Long **5.0** vs steep 4.8 | Outright (marginal) | **50%** steepen on hawk days | **Yes** — steepener −0.5 vs outright −12.5 on hawks |
| **III** Bear + bear steep | Short **5.2** vs steep 4.6 | Outright (narrow) | **100%** steepen on dov days | **Yes** — steepener +1.0 vs outright −12.5 on dovs |
| **IV** Bull + bull flat | Long **4.8** vs flat 0.9 | Outright | **100%** flat on hawk days | Theoretically yes, but one session — outright dominates |

The logic in each phase:

1. Identify **level** (bear → short Dec-26; bull → long Dec-26) and **curve** (flat or steep).
2. Ask whether the **aligned spread** beats outright on RA over the window.
3. On **adverse outright days** (dov in bear, hawk in bull), check whether the phase's curve type still appears — that is the insurance argument.
4. Where RA and adverse-day alignment agree, the curve expression earns its keep. Where outright wins on RA and adverse days lack alignment (Phase I dovs, Phase IV neutrals), there is no reason to be curved.

Outright wins on risk-adjusted terms in **every** phase. The curve only rationalises itself when adverse-day proportions show the aligned curve move still firing — and even then, usually at the cost of full-phase return.

---

*Rebuild: `python3 build_dec27_dec26_four_phases_3m.py`. Internal research note; not investment advice.*
