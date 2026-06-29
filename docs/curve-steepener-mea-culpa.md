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

**Risk-adjusted return** — for each structure within a phase, \(\text{RA} = \dfrac{\bar{r}_{\text{daily}} \times 252}{\sigma_{\text{daily}} \times \sqrt{252}}\) (bp; no risk-free subtracted). Structures compared:

| Structure | Daily return (bp) |
|---|---|
| Long Dec-26 outright | \(-\Delta r_{\text{Dec26}}\) |
| Long Dec-27 outright | \(-\Delta r_{\text{Dec27}}\) |
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

**Outright vs curve.** This is a **bear** phase for rate longs — both outrights lose, with Dec-26 the worse leg (front sells off hardest).

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Long Dec-26 | 242 | **−9.5** |
| Long Dec-27 | 174 | −9.2 |
| Steepener | 108 | −6.6 |
| **Flattener** | 108 | **+6.6** |

The flattener is the only structure with positive risk-adjusted return: it **insulates** against the bear shock by paying the front. The steepener amplifies the wrong leg — hawk days are 60% of the phase and modal bear-flattening — so curve exposure here is worse than even the back outright, not better.

---

## Phase II — Bull steepening (23 Mar – 17 Apr)

**Level story.** Both legs rally off the lows; spread recovers from −24.5 to −15 bp. Net: Dec-26 **−45.5 bp**, Dec-27 **−36 bp** — a **bull** phase for rate longs.

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

**Outright vs curve.** Outright long Dec-26 has the **highest** risk-adjusted return — you want to be in the bull trend directly.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Long Dec-26** | 178 | **+5.0** |
| Long Dec-27 | 148 | +4.6 |
| Steepener | 44 | +4.8 |
| Flattener | 44 | −4.8 |

The steepener's RA is close to outright Dec-26 (+4.8 vs +5.0) but at roughly **one-quarter the annualized vol** (44 vs 178 bp). In a bull steepening phase with frequent dov days (bull-steep modal 80% on dov tails), the curve structure **sacrifices a sliver of return for insulation** — when Dec-26 spikes on the occasional hawk day, the short front leg offsets it. Outright is optimal on a risk-adjusted basis only if you can tolerate the full front-end vol.

---

## Phase III — Bear steepening (20 Apr – 15 May)

**Level story.** Both legs rise again; the belly leads. Spread moves from −13.5 bp to **flat**. Net: Dec-26 **+39.5 bp**, Dec-27 **+53 bp** — another **bear** phase for rate longs, but now the **curve** shape matters.

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

**Outright vs curve.** Outrights lose again — both legs rise, belly more. But the **steepener** is the only structure with positive risk-adjusted return.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| Long Dec-26 | 116 | −5.2 |
| Long Dec-27 | 125 | −6.5 |
| **Steepener** | 43 | **+4.6** |
| Flattener | 43 | −4.6 |

This is the regime where curve expression **dominates** outright: the belly is repricing hawkishly (bear steepening on neutral days, 40% modal), and the steepener captures that relative move at low vol. Hawk days bear-flatten, but there are only two of them — not enough to flip the phase. The proportion analysis and the risk-adjusted ranking tell the same story.

---

## Phase IV — Bull flattening (18 May – 29 Jun)

**Level story.** Post-peak unwind. Both legs fall; belly compresses. Net: Dec-26 **−42 bp**, Dec-27 **−49 bp** — a **bull** phase, but the **curve flattens** rather than steepens.

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

**Outright vs curve.** Outrights win cleanly — you want to be long rates, full stop.

| Structure | Ann. vol (bp) | **RA** |
|---|---:|---:|
| **Long Dec-26** | 81 | **+4.8** |
| Long Dec-27 | 93 | +4.5 |
| Flattener | 35 | +0.9 |
| Steepener | 35 | −0.9 |

The steepener's RA turns **negative** despite the bull backdrop: modal daily path is bull-flattening (33%), so the belly **outperforms** on the way down. The flattener offers modest positive RA at low vol, but outright Dec-26 is clearly superior. Curve structures here are a **drag** relative to riding the outright bull trend — the proportion data shows why (persistent belly outperformance on neutral days, not hawk/dov tails).

---

## Synthesis

| Phase | Rate environment | Best outright | Best curve | Curve vs outright |
|---|---|---|---|---|
| **I** Bear flat | Rates up; front runs | — (both lose) | **Flattener** (+6.6 RA) | Curve **insulates** in bear shock |
| **II** Bull steep | Rates down; spread widens | **Long Dec-26** (+5.0) | Steepener (+4.8, ¼ vol) | Curve **near-parity**, much lower vol |
| **III** Bear steep | Rates up; belly leads | — (both lose) | **Steepener** (+4.6) | Curve **beats** outright |
| **IV** Bull flat | Rates down; belly compresses | **Long Dec-26** (+4.8) | Flattener (+0.9) | Outright **dominates**; steepener negative |

Three patterns link the proportion analysis to the risk-adjusted ranking:

1. **Bear phases (I, III)** — hawk/neutral days modal bear-flattening or bear-steepening. Outrights lose; the curve structure aligned with the phase (flattener in I, steepener in III) is the only way to positive RA.

2. **Bull phases with steepening (II)** — dov days modal bull-steepening (80%). Outright is marginally best on RA, but the steepener offers near-identical return at a fraction of the vol — curve as **insurance** against hawk tails.

3. **Bull phases with flattening (IV)** — neutral days modal bull-flattening (33%), no hawk tail risk. Outright dominates; curve structures subtract value.

The belly was not one trade. It was four different curve environments, and the right expression — outright, steepener, or flattener — depended on which regime you were in.

---

*Rebuild chart and stats: `python3 build_dec27_dec26_four_phases_3m.py`. Internal research note; not investment advice.*
