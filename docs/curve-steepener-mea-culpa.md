# Dec27−Dec26 on ICE 3M SONIA: four regimes since the Iran shock

*Follow-up to [UK SONIA Dec27−Dec26: Front-Loaded Hike Pricing and the Calendar Steepener](uk-sonia-front-loaded-hike-pricing.md). ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD) through 29 Jun 2026.*

The Dec27−Dec26 calendar spread did not move in one direction after the Iran shock. It ran through **four separable regimes** — each with a distinct **overall** curve type (net leg moves), and a different split between **hawk**, **dov**, and **neutral** days. This note pins phase boundaries to extrema in the data, defines hawk/dov with an explicit threshold, and maps where a long Dec27 / short Dec26 steepener won or lost.

---

## Data & definitions

| Item | Detail |
|---|---|
| **Contracts** | J8Z26 (Dec-26), J8Z27 (Dec-27) — ICE **3M compounded SONIA** |
| **Spread** | \(S_t = r_{\text{Dec27}} - r_{\text{Dec26}}\) (bp) |
| **Sample** | 2 Mar 2026 (first post-weekend session) → 29 Jun 2026 |
| **Overall phase type** | `classify_curve_move(ΣΔDec26, ΣΔDec27, ΣΔspread)` on start→end totals (ε = 0.5 bp) |
| **Daily curve regime** | Same taxonomy on each session's ΔDec26, ΔDec27, Δspread (ε = 0.25 bp on spread) |

### Hawk / dov / neutral days

Sort all **daily** \(\Delta r_{\text{Dec26}}\) (bp) from 2 Mar onward, drop the **top and bottom 10%** of observations, then compute **trimmed mean** \(\tilde\mu\) and **trimmed stdev** \(\tilde\sigma\) on the remainder (66 of 82 sessions):

| Stat | Value |
|---|---:|
| **\(\tilde\mu\)** | **+0.73 bp** |
| **\(\tilde\sigma\)** | **5.69 bp** |
| **k** | **1.5** |

| Label | Rule |
|---|---|
| **Hawk day** | \(\Delta r_{\text{Dec26}} > \tilde\mu + k\tilde\sigma\) → **> +9.3 bp** |
| **Dov day** | \(\Delta r_{\text{Dec26}} < \tilde\mu - k\tilde\sigma\) → **< −7.8 bp** |
| **Neutral day** | \(\tilde\mu - k\tilde\sigma \le \Delta r_{\text{Dec26}} \le \tilde\mu + k\tilde\sigma\) |

Trimming removes the Iran-shock outliers before estimating dispersion, so 1.5σ lands near **±8–9 bp** rather than the **±15 bp** you'd get from the raw sample σ (~10 bp).

---

## Four phases (data-pinned boundaries)

Boundaries follow the structure you outlined; dates are the **nearest EOD sessions** to the cited turning points.

| Phase | Window | Anchor | Spread (bp) | **Overall type** | Steepener P&L |
|---|---|---|---|---:|---:|
| **I** Bear flat / inversion | **2 Mar – 20 Mar** | Spread trough **−30 bp** on **20 Mar** (last low before 24 Mar) | +9.5 → **−30.0** (−39.5) | **Bear flattening** | **−43.0** |
| **II** Bull steepening | **23 Mar – 17 Apr** | **Local implied-rate low** both legs (**17 Apr**) | −24.5 → −15.0 (+9.5) | **Bull steepening** | +15.0 |
| **III** Bear steepening | **20 Apr – 15 May** | **Local implied-rate high** (Dec-26 **12 May**, Dec-27 **15 May**) | −13.5 → **0.0** (+13.5) | **Bear steepening** | +15.0 |
| **IV** Bull flattening | **18 May – 29 Jun** | First session after peak cluster; dovish unwind | +3.0 → −3.5 (−6.5) | **Bull flattening** | −3.5 |

*Note on Phase III end:* joint rate highs sit **12–15 May**, not 26 May — by 26 May both legs had already fallen ~25 bp from peak. Phase IV starts **18 May** (next session after the 15 May high).

![Dec27−Dec26 four phases on ICE 3M SONIA](../charts/dec27_dec26_four_phases_3m.png)

*Top: Dec27−Dec26 spread (bp). Bottom: Dec-26 and Dec-27 implied rates (%); green dotted = Bank Rate 3.75%. Rebuild: `python3 build_dec27_dec26_four_phases_3m.py`.*

---

## Phase I — Bear flattening / inversion (2 Mar – 20 Mar)

**Net:** Dec-26 **+128 bp**, Dec-27 **+88.5 bp** → spread **−39.5 bp**. Both legs sell off violently; front runs → **bear flattening** into deep inversion.

| | n | Share of phase |
|---|---:|---|
| Hawk days | 9 | **60%** |
| Neutral | 4 | 27% |
| Dov | 2 | 13% |

**On hawk days (n=9):** Bear flattening **67%**, Bear steepening 22%.

**On dov days (n=2):** Bull steepening **100%**.

**On neutral days (n=4):** Bear flattening **50%**, Bull flattening 50%.

**Steepener:** **−43 bp** — the crisis expression loses outright. Paying the front / flattening would have been the crisis trade.

---

## Phase II — Bull steepening (23 Mar – 17 Apr)

**Net:** Both legs **rally** (Dec-26 −45.5 bp, Dec-27 −36 bp); spread **widens** from −24.5 to −15 bp → **bull steepening** (less inverted).

| | n | Share |
|---|---:|---|
| Hawk | 2 | 11% |
| Neutral | 11 | 61% |
| Dov | 5 | **28%** |

**On dov days (n=5):** Bull steepening **80%** — when Dec-26 has a large *down* move, the belly catches bid.

**On hawk days (n=2):** Split 50% bear steep / 50% bear flat (n too small).

**On neutral days (n=11):** Bull steepening **27%**, Bear flattening 27%.

**Steepener:** **+15 bp** — recovery from inversion as both rates fall, back faster.

---

## Phase III — Bear steepening (20 Apr – 15 May)

**Net:** Dec-26 **+39.5 bp**, Dec-27 **+53 bp** → spread **+13.5 bp** to **flat** → **bear steepening**.

| | n | Share |
|---|---:|---|
| Hawk | 2 | 11% |
| Neutral | 15 | **79%** |
| Dov | 2 | 11% |

**On hawk days (n=2):** Bear flattening **100%**.

**On dov days (n=2):** Bull steepening **100%**.

**On neutral days (n=15):** Bear steepening **40%**, Bear flattening 27%.

**Steepener:** **+15 bp** — the regime your original thesis needed. Belly underperforms on hawk tails; on average both legs rise with Dec-27 leading.

---

## Phase IV — Bull flattening (18 May – 29 Jun)

**Net:** Dec-26 **−42 bp**, Dec-27 **−48.5 bp** → spread **−6.5 bp** → **bull flattening**.

| | n | Share |
|---|---:|---|
| Hawk | 1 | 3% |
| Neutral | 27 | **90%** |
| Dov | 2 | 7% |

**On hawk days (n=1):** Bear flattening **100%**.

**On dov days (n=2):** Bull flattening **50%**, Unchanged 50%.

**On neutral days (n=27):** Bull flattening **33%** (modal); Unchanged 19%.

Modal **daily** type: Bull flattening **33%** — most sessions are neutral on the hawk/dov filter, but **persistent** belly compression on the level.

**Steepener:** **−3.5 bp**. The **5 Jun** calendar steepener entry sat in this phase (belly already uninverted on 1M; 3M spread near flat). Modal path = dovish **bull flattening**, not migration.

---

## What this means for the trade

1. **Four regimes, four overall types** — bear flat → bull steep → bear steep → bull flat. No single calendar spread wins all four without timing the switches.

2. **The steepener only carries Phases II–III** (+30 bp combined); Phase I (**−43 bp**) dominates the crisis window.

3. **Hawk/dov via \(\tilde\mu \pm 1.5\tilde\sigma\)** (trimmed σ ≈ 5.7 bp) recovers a usable tail-day split — hawk days cluster in Phase I (60%), dov days in Phase II (28%) — while Phase IV stays mostly neutral (90%) yet still bull-flattens on the level.

4. **Original thesis anatomy** (front-loaded hikes) was a Phase I–III story; **post-entry P&L** was a Phase IV story.

---

## Reproduce

```bash
python3 build_dec27_dec26_four_phases_3m.py
# → charts/dec27_dec26_four_phases_3m.png
# → data/dec27_dec26_four_phases_3m.json
```

---

*Internal research note. Not investment advice. ICE 3M SONIA EOD via Barchart; Bank Rate 3.75%.*
