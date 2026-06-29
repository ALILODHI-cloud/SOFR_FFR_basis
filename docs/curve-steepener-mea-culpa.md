# Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock

*ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD), 2 Mar – 29 Jun 2026.*

Each phase has a **level move** and a **curve move**. Should you have ridden the level outright, or through the aligned spread? The answer turns on **contrary days** — sessions where the front end moves against the phase trend — and especially on the **worst outright days**: did the curve still do the right thing when it mattered?

---

## Setup

| Item | Detail |
|---|---|
| **Contracts** | J8Z26 (Dec-26), J8Z27 (Dec-27) |
| **Spread** | \(S_t = r_{\text{Dec27}} - r_{\text{Dec26}}\) (bp) |
| **Sample** | 2 Mar → 29 Jun 2026 |

**Contrary day** — ΔDec26 opposes the phase level (any size):

| Phase level | Contrary | Aligned |
|---|---|---|
| **Bear** | ΔDec26 **< 0** | ΔDec26 **> 0** |
| **Bull** | ΔDec26 **> 0** | ΔDec26 **< 0** |

**Correct curve move** — flattening in flat phases (I, IV); steepening in steep phases (II, III).

| Level | Outright | Aligned curve |
|---|---|---|
| Bear | Short Dec-26 | Flattener (I) / steepener (III) |
| Bull | Long Dec-26 | Steepener (II) / flattener (IV) |

**Metrics:**

| Metric | Definition |
|---|---|
| **Contrary-day alignment** | % of contrary days where the curve moved correctly |
| **Return / \|max DD\|** | Total phase return ÷ absolute max drawdown — return per unit of tail risk |
| **Max DD ratio** | \|max DD outright\| ÷ \|max DD curve\| |
| **Worst outright days** | Largest daily losses on the outright; curve type and P&L on each |

---

## Four phases

| Phase | Window | Level | Curve | Outright vs |
|---|---|---|---|---|
| **I** | 2 Mar – 20 Mar | Bear | Bear flattening | Short Dec-26 vs **flattener** |
| **II** | 23 Mar – 17 Apr | Bull | Bull steepening | Long Dec-26 vs **steepener** |
| **III** | 20 Apr – 15 May | Bear | Bear steepening | Short Dec-26 vs **steepener** |
| **IV** | 18 May – 29 Jun | Bull | Bull flattening | Long Dec-26 vs **flattener** |

![Dec27−Dec26 four phases on ICE 3M SONIA](../charts/dec27_dec26_four_phases_3m.png)

---

## Phase I — Bear level, bear flattening

**Net:** Dec-26 **+128 bp**, Dec-27 **+89 bp**. Spread → **−30 bp**.

| | Outright (short) | Flattener |
|---|---:|---:|
| Total return | +128 bp | +39.5 bp |
| Max drawdown | −15.5 bp | **−6.5 bp** |
| **Return / \|max DD\|** | **8.3** | 6.1 |
| Max DD ratio | **2.4×** | — |

**Contrary days:** 4 of 14 (**29%**) — front-end down, hurts the short. Correct curve (flattening) on contrary days: **50%**.

### Worst outright days (all 4 losing sessions)

| Date | Outright | Curve | ΔDec26 | Curve type | Correct? |
|---|---:|---:|---:|---|---|
| 10 Mar | **−15.5** | −3.5 | −15.5 | Bull steepening | no |
| 4 Mar | **−9.5** | −2.0 | −9.5 | Bull steepening | no |
| 16 Mar | −4.0 | **+3.0** | −4.0 | Bull flattening | **yes** |
| 17 Mar | −3.5 | **+2.5** | −3.5 | Bull flattening | **yes** |

The two biggest outright hits (Mar 4, Mar 10) were bull-steepening — wrong curve for a flattener. Combined: outright **−25 bp**, curve **−5.5 bp**. The smaller two losses had flattening: outright −7.5 bp, curve **+5.5 bp**. When the curve moved correctly on bad outright days, it flipped positive. When it didn't, it still cut the loss by ~75%.

---

## Phase II — Bull level, bull steepening

**Net:** Dec-26 **−45.5 bp**, Dec-27 **−36 bp**. Spread −24.5 → −15 bp.

| | Outright (long) | Steepener |
|---|---:|---:|
| Total return | +64 bp | +15 bp |
| Max drawdown | −17.5 bp | **−4.5 bp** |
| **Return / \|max DD\|** | **3.7** | 3.3 |
| Max DD ratio | **3.9×** | — |

**Contrary days:** 6 of 18 (**33%**) — front-end up, hurts the long. Correct curve (steepening) on contrary days: **33%**.

### Worst 5 outright days

| Date | Outright | Curve | ΔDec26 | Curve type | Correct? |
|---|---:|---:|---:|---|---|
| 7 Apr | **−13.5** | −1.5 | +13.5 | Bear flattening | no |
| 26 Mar | **−11.5** | **+0.5** | +11.5 | Bear steepening | **yes** |
| 13 Apr | −7.5 | −2.5 | +7.5 | Bear flattening | no |
| 9 Apr | −5.5 | **+2.0** | +5.5 | Bear steepening | **yes** |
| 4 Apr | −4.0 | −3.0 | +4.0 | Bear flattening | no |

**2 of 5** worst days steepened. On those two: outright **−17 bp**, curve **+2.5 bp**. On the three that bear-flattened: outright **−25 bp**, curve **−7 bp**. The steepener earns on the worst day when the curve cooperates (bear steepening on a hawk spike); even when it doesn't, max DD is **3.9× smaller**. Return/max-DD nearly tied (3.7 vs 3.3) despite a quarter of the tail risk.

---

## Phase III — Bear level, bear steepening

**Net:** Dec-26 **+39.5 bp**, Dec-27 **+53 bp**. Spread → **flat**.

| | Outright (short) | Steepener |
|---|---:|---:|
| Total return | +46 bp | +15 bp |
| Max drawdown | −21.5 bp | **−7.3 bp** |
| **Return / \|max DD\|** | 2.1 | **2.1** |
| Max DD ratio | **3.0×** | — |

**Contrary days:** 6 of 19 (**32%**). Correct curve (steepening) on contrary days: **50%**.

### Worst 5 outright days

| Date | Outright | Curve | ΔDec26 | Curve type | Correct? |
|---|---:|---:|---:|---|---|
| 6 May | **−15.5** | **+1.5** | −15.5 | Bull steepening | **yes** |
| 30 Apr | **−9.5** | **+0.5** | −9.5 | Bull steepening | **yes** |
| 14 May | −5.5 | −1.0 | −5.5 | Bull flattening | no |
| 13 May | −5.0 | **+3.0** | −5.0 | Bull steepening | **yes** |
| 1 May | −2.0 | −0.7 | −2.0 | Bull flattening | no |

**3 of 5** worst days steepened. On those three: outright **−30 bp**, curve **+5 bp** — the steepener *earns* on the biggest outright hits. On the two that flattened: outright −7.5 bp, curve −1.7 bp. Return/max-DD is **identical** (2.1 vs 2.1) at one-third the drawdown. This is the phase where the curve pays for itself on the days that matter.

---

## Phase IV — Bull level, bull flattening

**Net:** Dec-26 **−42 bp**, Dec-27 **−49 bp**. Spread +3.0 → −3.5 bp.

| | Outright (long) | Flattener |
|---|---:|---:|
| Total return | +46 bp | +3.5 bp |
| Max drawdown | −18.0 bp | **−8.5 bp** |
| **Return / \|max DD\|** | **2.6** | 0.4 |
| Max DD ratio | **2.1×** | — |

**Contrary days:** 9 of 30 (**30%**). Correct curve (flattening) on contrary days: **33%**.

### Worst 5 outright days

| Date | Outright | Curve | ΔDec26 | Curve type | Correct? |
|---|---:|---:|---:|---|---|
| 1 Jun | **−15.5** | **+1.5** | +15.5 | Bear flattening | **yes** |
| 19 Jun | −5.0 | −6.5 | +5.0 | Bear steepening | no |
| 3 Jun | −4.5 | −1.0 | +4.5 | Bear steepening | no |
| 8 Jun | −3.5 | −1.5 | +3.5 | Bear steepening | no |
| 10 Jun | −3.0 | **+0.5** | +3.0 | Bear flattening | **yes** |

**2 of 5** worst days flattened. The single biggest hit (1 Jun): outright **−15.5 bp**, flattener **+1.5 bp** — bear-flattening on a hawk spike. But the next three all bear-steepen and both legs lose. Return/max-DD heavily favours outright (2.6 vs 0.4). Tail risk is halved but return is not worth the trade.

---

## Synthesis

| Phase | Contrary | Correct curve on contrary | Return/\|max DD\| outright | Return/\|max DD\| curve | Max DD ratio | Worst-5 correct |
|---|---:|---:|---:|---:|---:|---:|
| **I** Bear flat | 29% | 50% | **8.3** | 6.1 | 2.4× | 2/4 |
| **II** Bull steep | 33% | 33% | **3.7** | 3.3 | 3.9× | 2/5 |
| **III** Bear steep | 32% | 50% | 2.1 | **2.1** | 3.0× | **3/5** |
| **IV** Bull flat | 30% | 33% | **2.6** | 0.4 | 2.1× | 2/5 |

~**30% contrary days** in every phase. The weighted question: on the **worst outright sessions**, did the curve move correctly — and what did it earn?

| Phase | Worst days with correct curve | Outright loss | Curve P&L |
|---|---|---:|---:|
| **I** | 2 smaller hits | −7.5 bp | **+5.5 bp** |
| **I** | 2 biggest hits (wrong curve) | −25 bp | −5.5 bp |
| **II** | 2 hits (steepened) | −17 bp | **+2.5 bp** |
| **II** | 3 hits (flattened) | −25 bp | −7 bp |
| **III** | 3 hits (steepened) | −30 bp | **+5 bp** |
| **III** | 2 hits (flattened) | −7.5 bp | −1.7 bp |
| **IV** | 2 hits (flattened) | −18.5 bp | **+2 bp** |
| **IV** | 3 hits (steepened) | −13 bp | −9 bp |

The curve earns its keep when the worst outright days coincide with the right curve type — Phase III being the standout (3/5 worst days steepen, curve **+5 bp** while outright loses 30 bp on those sessions). Return/max-DD can be **identical** (III: 2.1 vs 2.1) at a fraction of the drawdown. Where worst days mostly get the wrong curve type (IV: 3/5 bear-steepen), return/max-DD collapses for the spread (0.4 vs 2.6) and outright wins clearly.

Outright captures more total return in every phase. The curve is rational when contrary-day alignment and worst-day curve behaviour combine to cap max DD without destroying return per unit of tail risk.

---

*Rebuild: `python3 build_dec27_dec26_four_phases_3m.py`. Internal research note; not investment advice.*
