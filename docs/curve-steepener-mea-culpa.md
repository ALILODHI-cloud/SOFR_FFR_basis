# Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock

*ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD), 2 Mar – 29 Jun 2026.*

After the Iran shock the Dec27−Dec26 belly did not move in one direction. It cycled through **four separable regimes** — each with a distinct overall curve shape, a different hawk/dov/neutral day mix, and a different answer to a simple question: **was it better to ride the outright rate trend, or to express the view through the curve?**

---

## Setup

| Item | Detail |
|---|---|
| **Contracts** | J8Z26 (Dec-26), J8Z27 (Dec-27) |
| **Spread** | \(S_t = r_{\text{Dec27}} - r_{\text{Dec26}}\) (bp) |
| **Sample** | 2 Mar 2026 (first post-weekend session) → 29 Jun 2026 |

**Overall phase type** — net leg moves from phase open to close (`classify_curve_move` on cumulative ΔDec26, ΔDec27, Δspread; ε = 0.5 bp).

**Daily curve type** — same taxonomy session-by-session (ε = 0.25 bp on spread).

**Hawk / dov / neutral** — based on daily ΔDec26. Sort all daily changes from 2 Mar, drop the top and bottom **10%**, compute trimmed mean \(\tilde\mu\) and trimmed stdev \(\tilde\sigma\) on the remainder (66 of 82 sessions), then:

| | |
|---|---:|
| \(\tilde\mu\) | +0.73 bp |
| \(\tilde\sigma\) | 5.69 bp |
| **Hawk** | ΔDec26 **> +9.3 bp** |
| **Dov** | ΔDec26 **< −7.8 bp** |
| **Neutral** | between |

**Risk-adjusted return** — for each structure within a phase, \(\text{RA} = \dfrac{\bar{r}_{\text{daily}} \times 252}{\sigma_{\text{daily}} \times \sqrt{252}}\) (bp; no risk-free subtracted).

The **outright benchmark** matches the rate trend in each phase:

| Phase type | Outright benchmark | Daily return (bp) |
|---|---|---|
| **Bear** (rates rising) | **Short Dec-26** | \(+\Delta r_{\text{Dec26}}\) |
| **Bull** (rates falling) | **Long Dec-26** | \(-\Delta r_{\text{Dec26}}\) |

Curve structures compared against that benchmark:

| Structure | Daily return (bp) |
|---|---|
| Steepener (L Dec27 / S Dec26) | \(\Delta r_{\text{Dec27}} - \Delta r_{\text{Dec26}}\) |
| Flattener (L Dec26 / S Dec27) | \(\Delta r_{\text{Dec26}} - \Delta r_{\text{Dec27}}\) |

---

## Four phases

| Phase | Window | Anchor | Spread (bp) | **Overall type** |
|---|---|---|---:|---|
| **I** | 2 Mar – 20 Mar | Trough **−30** on **20 Mar** | +9.5 → −30.0 | **Bear flattening** |
| **II** | 23 Mar – 17 Apr | Local rate low both legs (**17 Apr**) | −24.5 → −15.0 | **Bull steepening** |
| **III** | 20 Apr – 15 May | Rate highs **12–15 May** | −13.5 → 0.0 | **Bear steepening** |
| **IV** | 18 May – 29 Jun | Post-peak unwind | +3.0 → −3.5 | **Bull flattening** |

![Dec27−Dec26 four phases on ICE 3M SONIA](../charts/dec27_dec26_four_phases_3m.png)

*Top: Dec27−Dec26 spread (bp). Bottom: Dec-26 and Dec-27 implied rates (%); green dotted = Bank Rate 3.75%.*

---

## Phase I — Bear flattening / inversion (2 Mar – 20 Mar)

**Level story.** Both legs sell off violently; the front runs harder. Spread collapses from +9.5 bp to **−30 bp** — deep inversion. Net: Dec-26 **+128 bp**, Dec-27 **+89 bp**.

**Hawk / dov mix** — crisis repricing dominated by large front-end up-moves.

| | n | Share |
|---|---:|---:|
| Hawk | 9 | **60%** |
| Neutral | 4 | 27% |
| Dov | 2 | 13% |

| On… | Modal curve type |
|-----|-----------------|
| Hawk days (n=9) | Bear flattening **67%** |
| Dov days (n=2) | Bull steepening **100%** |
| All days | Bear flattening **53%** |

**Outright vs curve.** Bear phase → benchmark is **short Dec-26**.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Short Dec-26** | 242 | **+9.5** |
| Flattener | 108 | +6.6 |
| Steepener | 108 | −6.6 |

Short Dec-26 outright is the clear winner — you are riding the hawk shock directly. The flattener delivers positive RA (+6.6) at less than half the vol, but still trails the outright trend trade. The steepener is on the wrong side of both the level move and the hawk-day mix (60% hawk, modal bear-flat).

---

## Phase II — Bull steepening (23 Mar – 17 Apr)

**Level story.** Both legs rally off the lows; spread recovers from −24.5 to −15 bp. Net: Dec-26 **−45.5 bp**, Dec-27 **−36 bp**.

**Hawk / dov mix** — dovish days dominate; hawks are rare.

| | n | Share |
|---|---:|---:|
| Hawk | 2 | 11% |
| Neutral | 11 | 61% |
| Dov | 5 | **28%** |

| On… | Modal curve type |
|-----|-----------------|
| Dov days (n=5) | Bull steepening **80%** |
| Hawk days (n=2) | 50/50 bear steep / bear flat |
| All days | Bull steepening **39%** |

**Outright vs curve.** Bull phase → benchmark is **long Dec-26**.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Long Dec-26** | 178 | **+5.0** |
| Steepener | 44 | +4.8 |
| Flattener | 44 | −4.8 |

Long Dec-26 outright marginally beats the steepener on RA (+5.0 vs +4.8), but at **four times the vol** (178 vs 44 bp ann.). The steepener sacrifices a sliver of return for insulation — on the occasional hawk day the short front leg offsets the spike, and dov tails modal bull-steep (80%). This is the phase where curve expression is closest to outright parity.

---

## Phase III — Bear steepening (20 Apr – 15 May)

**Level story.** Both legs rise again; the belly leads. Spread moves from −13.5 bp to **flat**. Net: Dec-26 **+39.5 bp**, Dec-27 **+53 bp**.

**Hawk / dov mix** — mostly neutral sessions; tails are symmetric.

| | n | Share |
|---|---:|---:|
| Hawk | 2 | 11% |
| Neutral | 15 | **79%** |
| Dov | 2 | 11% |

| On… | Modal curve type |
|-----|-----------------|
| Hawk days (n=2) | Bear flattening **100%** |
| Dov days (n=2) | Bull steepening **100%** |
| Neutral days (n=15) | Bear steepening **40%** |
| All days | Bear steep / bear flat **32%** each |

**Outright vs curve.** Bear phase → benchmark is **short Dec-26**.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Short Dec-26** | 116 | **+5.2** |
| Steepener | 43 | +4.6 |
| Flattener | 43 | −4.6 |

Short Dec-26 outright still wins on RA, but the steepener is close (+4.6 vs +5.2) at **less than half the vol**. Neutral days modal bear-steepening (40%) — the belly is repricing hawkishly relative to the front, and the steepener captures that. Hawk days bear-flatten, but only two of them. Here the curve structure is a **vol-efficient substitute** for the outright short, not a superior expression.

---

## Phase IV — Bull flattening (18 May – 29 Jun)

**Level story.** Post-peak unwind. Both legs fall; belly compresses. Net: Dec-26 **−42 bp**, Dec-27 **−49 bp**.

**Hawk / dov mix** — almost entirely neutral; no structural tail days.

| | n | Share |
|---|---:|---:|
| Hawk | 1 | 3% |
| Neutral | 27 | **90%** |
| Dov | 2 | 7% |

| On… | Modal curve type |
|-----|-----------------|
| Neutral days (n=27) | Bull flattening **33%** |
| Dov days (n=2) | Bull flattening 50% / Unchanged 50% |
| All days | Bull flattening **33%** |

**Outright vs curve.** Bull phase → benchmark is **long Dec-26**.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Long Dec-26** | 81 | **+4.8** |
| Flattener | 35 | +0.9 |
| Steepener | 35 | −0.9 |

Long Dec-26 outright dominates. The steepener's RA turns negative despite the bull backdrop — neutral days modal bull-flattening (33%), so the belly outperforms on the way down and the steepener fights the trend. Curve structures here are a drag relative to riding the outright long.

---

## Synthesis

| Phase | Rate trend | Outright benchmark | **RA** | Best curve | **RA** | Curve vs outright |
|---|---|---:|---:|---|---:|---|
| **I** Bear flat | Rates up | Short Dec-26 | **+9.5** | Flattener | +6.6 | Outright wins; flattener partial insulation |
| **II** Bull steep | Rates down | Long Dec-26 | **+5.0** | Steepener | +4.8 | Near-parity at ¼ vol |
| **III** Bear steep | Rates up | Short Dec-26 | **+5.2** | Steepener | +4.6 | Outright wins; steepener close at ⅓ vol |
| **IV** Bull flat | Rates down | Long Dec-26 | **+4.8** | Flattener | +0.9 | Outright dominates |

Three patterns link the proportion analysis to the risk-adjusted ranking:

1. **Bear phases (I, III)** — hawk/neutral days modal bear-flattening or bear-steepening. **Short Dec-26 outright** is the trend trade and scores highest RA. Curve structures only make sense as lower-vol alternatives (flattener in I, steepener in III).

2. **Bull steepening (II)** — dov days modal bull-steepening (80%). Long Dec-26 outright marginally best, but the steepener is essentially tied on RA at a fraction of the vol — curve as **insurance** against hawk tails.

3. **Bull flattening (IV)** — neutral days modal bull-flattening (33%). Long Dec-26 outright wins cleanly; curve structures subtract value because the belly outperforms on the way down.

The outright trend trade — short in bear phases, long in bull phases — wins on risk-adjusted terms in every period. The curve only competes when the phase shape offers insulation without fighting the level move.

---

*Rebuild chart and stats: `python3 build_dec27_dec26_four_phases_3m.py`. Internal research note; not investment advice.*
