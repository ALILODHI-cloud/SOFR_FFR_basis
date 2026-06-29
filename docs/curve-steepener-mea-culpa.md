# Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock

*ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD), 2 Mar – 29 Jun 2026.*

Each phase combines a **level move** (rates up or down over the window) and a **curve move** (steepening or flattening). The question: should you have ridden the level **outright**, or expressed both legs through the **aligned spread**? The test is what happens on **contrary days** — sessions where the front end moves against the phase's level direction, regardless of size — and whether the curve shape you needed still appeared on those days. **Max loss** over the sample matters more than average return for that comparison.

---

## Setup

| Item | Detail |
|---|---|
| **Contracts** | J8Z26 (Dec-26), J8Z27 (Dec-27) |
| **Spread** | \(S_t = r_{\text{Dec27}} - r_{\text{Dec26}}\) (bp) |
| **Sample** | 2 Mar → 29 Jun 2026 |

**Contrary day** — any session where ΔDec26 opposes the phase level move (no size threshold):

| Phase level | Contrary day | Aligned day |
|---|---|---|
| **Bear** (rates net higher) | ΔDec26 **< 0** (front-end down) | ΔDec26 **> 0** |
| **Bull** (rates net lower) | ΔDec26 **> 0** (front-end up) | ΔDec26 **< 0** |

**Correct curve move** — daily steepening or flattening matching the phase shape:

| Phase curve | Correct on any day |
|---|---|
| Flattening (I, IV) | Bear, bull, or mixed **flattening** |
| Steepening (II, III) | Bear, bull, or mixed **steepening** |

**Structures compared:**

| Level | Outright | Aligned curve |
|---|---|---|
| Bear | Short Dec-26 | Flattener (I) or steepener (III) |
| Bull | Long Dec-26 | Steepener (II) or flattener (IV) |

**Risk metrics:** RA gap (outright minus curve) and **max loss** — worst single session and maximum drawdown over the phase.

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

**Net:** Dec-26 **+128 bp**, Dec-27 **+89 bp**. Spread +9.5 → **−30 bp**.

### Contrary days (front-end down — hurts a short)

| | |
|---|---:|
| Contrary days | **4 of 14 (29%)** |
| Correct curve move (flattening) on contrary days | **50%** |
| Modal on contrary days | Bull steep / bull flat |

On contrary days the outright short loses (avg **−8.1 bp**/session). The flattener is flat (avg **0.0 bp**). Half of contrary sessions still flatten — the curve type you wanted survives even when the front end rallies against the bear trend.

### Aligned-level days (front-end up — favours short)

| | |
|---|---:|
| Aligned days | 10 of 14 (71%) |
| Correct curve move on aligned days | **70%** |

### Outright vs flattener — full phase

| Metric | Short Dec-26 | Flattener |
|---|---:|---:|
| RA | **+9.5** | +6.6 |
| RA gap | **+2.9** | — |
| Worst single day | −15.5 bp | **−3.5 bp** |
| Max drawdown | −15.5 bp | **−6.5 bp** |

Outright wins on RA. But on contrary days — 29% of the sample — the flattener avoids the front-end hit and half those sessions still flatten. Max single-day loss is **4× smaller** on the curve.

---

## Phase II — Bull level, bull steepening

**Net:** Dec-26 **−45.5 bp**, Dec-27 **−36 bp**. Spread −24.5 → −15 bp.

### Contrary days (front-end up — hurts a long)

| | |
|---|---:|
| Contrary days | **6 of 18 (33%)** |
| Correct curve move (steepening) on contrary days | **33%** |
| Modal on contrary days | Bear flattening 67% |

Only one-third of contrary days steepen — mostly they bear-flatten. Yet the steepener still absorbs the shock: avg **−1.1 bp** vs outright **−7.4 bp** on contrary sessions.

### Aligned-level days (front-end down)

| | |
|---|---:|
| Aligned days | 11 of 18 (61%) |
| Correct curve move on aligned days | **73%** |

### Outright vs steepener — full phase

| Metric | Long Dec-26 | Steepener |
|---|---:|---:|
| RA | **+5.0** | +4.8 |
| RA gap | **+0.3** | — |
| Worst single day | −13.5 bp | **−3.0 bp** |
| Max drawdown | −17.5 bp | **−4.5 bp** |

RA essentially tied. Max drawdown on outright is **−17.5 bp** vs **−4.5 bp** on the steepener — the curve caps tail risk on the 33% of days the front end moves against you, even when only a third of those still steepen.

---

## Phase III — Bear level, bear steepening

**Net:** Dec-26 **+39.5 bp**, Dec-27 **+53 bp**. Spread −13.5 → **0 bp**.

### Contrary days (front-end down — hurts a short)

| | |
|---|---:|
| Contrary days | **6 of 19 (32%)** |
| Correct curve move (steepening) on contrary days | **50%** |
| Modal on contrary days | Bull steep / bull flat |

Half of contrary days still steepen. Outright short avg **−6.5 bp**; steepener avg **+0.4 bp** — the curve earns on the sessions that hurt the outright.

### Aligned-level days (front-end up)

| | |
|---|---:|
| Aligned days | 13 of 19 (68%) |
| Correct curve move on aligned days | 46% |

### Outright vs steepener — full phase

| Metric | Short Dec-26 | Steepener |
|---|---:|---:|
| RA | **+5.2** | +4.6 |
| RA gap | **+0.6** | — |
| Worst single day | −15.5 bp | **−3.0 bp** |
| Max drawdown | −21.5 bp | **−7.3 bp** |

Narrow RA gap. Max drawdown **−21.5 bp** outright vs **−7.3 bp** steepener — the starkest tail-risk gap in the sample. On 32% contrary days, 50% still steepen and the curve is near flat while the short bleeds.

---

## Phase IV — Bull level, bull flattening

**Net:** Dec-26 **−42 bp**, Dec-27 **−49 bp**. Spread +3.0 → −3.5 bp.

### Contrary days (front-end up — hurts a long)

| | |
|---|---:|
| Contrary days | **9 of 30 (30%)** |
| Correct curve move (flattening) on contrary days | **33%** |
| Modal on contrary days | Bear steepening 56% |

Only a third of contrary days flatten — most bear-steepen. But the flattener still loses less (avg **−0.5 bp** vs **−4.2 bp** outright).

### Aligned-level days (front-end down)

| | |
|---|---:|
| Aligned days | 21 of 30 (70%) |
| Correct curve move on aligned days | 48% |

### Outright vs flattener — full phase

| Metric | Long Dec-26 | Flattener |
|---|---:|---:|
| RA | **+4.8** | +0.9 |
| RA gap | **+3.9** | — |
| Worst single day | −15.5 bp | **−6.5 bp** |
| Max drawdown | −18.0 bp | **−8.5 bp** |

Outright wins clearly on RA. Curve only limits tail loss: worst day −6.5 vs −15.5 bp, drawdown −8.5 vs −18.0 bp. With only 33% of contrary days flattening, the insurance case is weaker than Phases II–III.

---

## Synthesis

| Phase | Level + curve | Contrary days | Correct curve on contrary | Max DD outright | Max DD curve | RA gap |
|---|---|---:|---:|---:|---:|---:|
| **I** | Bear + bear flat | 29% | **50%** flat | −15.5 | **−6.5** | +2.9 |
| **II** | Bull + bull steep | 33% | 33% steep | −17.5 | **−4.5** | +0.3 |
| **III** | Bear + bear steep | 32% | **50%** steep | −21.5 | **−7.3** | +0.6 |
| **IV** | Bull + bull flat | 30% | 33% flat | −18.0 | **−8.5** | +3.9 |

Roughly **30% of every phase** is contrary days — front-end moving against the level trend, no size filter. The curve question is: on those days, does the phase's curve shape still appear, and does the spread cap your loss?

1. **Correct curve on contrary days** ranges from 33–50%. It does not need to be a majority to matter — the curve structure can still cut max drawdown by 60–75% (Phases II–III).

2. **RA gap** is small where the curve earns its keep (II: +0.3, III: +0.6) and large where it does not (I: +2.9, IV: +3.9). Max loss is the sharper discriminator.

3. **Phase III** is the sweet spot: 50% of contrary days steepen, steepener earns on contrary sessions, max DD **−7.3 vs −21.5 bp**.

4. **Phase IV** — outright dominates. Contrary days mostly bear-steepen; flattener only softens the tail.

Outright wins RA in every phase. The curve is justified when contrary-day curve alignment is high **and** max drawdown on the spread is materially smaller — not because it beats outright on average, but because it survives the days that oppose the level trend.

---

*Rebuild: `python3 build_dec27_dec26_four_phases_3m.py`. Internal research note; not investment advice.*
