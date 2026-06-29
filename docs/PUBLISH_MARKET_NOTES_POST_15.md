# Agent handoff: publish Market-Notes `post_15`

**Target repo:** https://github.com/ALILODHI-cloud/Market-Notes  
**Branch:** `main` (direct push, or PR if you prefer)  
**Status:** Content approved by author. Not yet on GitHub (404 on `post_15/`).

---

## Task

Publish the approved market note **“Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock”** as **`post_15`**, following the same layout as `post_13`, `post_14`, etc.

Do **not** modify analysis code — that already lives in [SOFR_FFR_basis](https://github.com/ALILODHI-cloud/SOFR_FFR_basis) (merged PR #21).

---

## Files to create

```
Market-Notes/
├── README.md                          # edit — add post_15 as first “Latest Post”
└── post_15/
    ├── body.md                        # create — full text in Appendix below
    └── figures/
        └── dec27_dec26_four_phases_3m.png   # copy from SOFR repo
```

---

## Step-by-step

### 1. Clone Market-Notes

```bash
git clone https://github.com/ALILODHI-cloud/Market-Notes.git
cd Market-Notes
```

### 2. Create directories

```bash
mkdir -p post_15/figures
```

### 3. Copy the chart from SOFR_FFR_basis `main`

```bash
curl -L -o post_15/figures/dec27_dec26_four_phases_3m.png \
  https://raw.githubusercontent.com/ALILODHI-cloud/SOFR_FFR_basis/main/charts/dec27_dec26_four_phases_3m.png
```

### 4. Create `post_15/body.md`

Copy the **entire contents** of the [Appendix](#appendix-post_15bodymd) below into `post_15/body.md`.

Image path in `body.md` must be:

```markdown
![Dec27−Dec26 four phases on ICE 3M SONIA](figures/dec27_dec26_four_phases_3m.png)
```

### 5. Update `README.md`

Under `## Latest Posts:`, **insert as the first bullet** (above post_14):

```markdown
- [**Dec27−Dec26 SONIA: four curve regimes since the Iran shock (2026-06-29)**](post_15/body.md)
```

### 6. Commit and push

```bash
git add post_15 README.md
git commit -m "Add post_15: Dec27-Dec26 SONIA four curve regimes since Iran shock"
git push origin main
```

### 7. Verify

- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_15/body.md  
- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_15/figures/dec27_dec26_four_phases_3m.png  

---

## One-line prompt for the other agent

> Publish `post_15` to https://github.com/ALILODHI-cloud/Market-Notes per `PUBLISH_MARKET_NOTES_POST_15.md` in SOFR_FFR_basis `docs/`: create `post_15/body.md` and chart (from SOFR main), update README, push to main.

---

## Appendix: `post_15/body.md`

Copy everything in the fenced block below **verbatim** into `post_15/body.md`:

```markdown
# Dec27−Dec26 on ICE 3M SONIA: four curve regimes since the Iran shock

*Follow-up to [Dec26/Dec27 SONIA curve steepener (2026-06-08)](../post_13/body.md). ICE 3M SONIA futures **J8Z26 / J8Z27** (Barchart EOD), 2 Mar – 29 Jun 2026.*

After the Iran shock, the Dec27−Dec26 belly did not behave as a single trade. It ran through four separable regimes — each with its own level move (rates up or down over the window) and its own curve move (steepening or flattening). In every regime the same question arises: should you have expressed the view **outright** on Dec-26, or through the **spread** aligned with the curve shape?

The answer is not in the average session. It is in the **contrary days** — roughly thirty percent of every phase — when the front end moves against the prevailing level trend, and above all in the **worst outright days**, when the level bet hurts most. On those days, did the curve still do what the phase required? And did that translate into a better return per unit of tail risk?

---

## Method

We use ICE 3M compounded SONIA futures J8Z26 (Dec-26) and J8Z27 (Dec-27). The spread is Dec27 minus Dec26 in basis points. The sample runs from 2 March 2026, the first post-weekend session after the shock, through 29 June.

A **contrary day** is any session where the daily change in the Dec-26 implied rate opposes the phase's level direction — no size threshold. In a bear phase (rates net higher over the window), contrary means Dec-26 fell that day. In a bull phase (rates net lower), contrary means Dec-26 rose. An **aligned day** is the reverse.

The **correct curve move** depends on the phase shape: flattening (bear, bull, or mixed) in flat phases; steepening in steep phases. The outright benchmark matches the level: short Dec-26 in bear phases, long Dec-26 in bull phases. The curve alternative is the aligned spread — flattener (long Dec-26 / short Dec-27) in flattening phases, steepener (long Dec-27 / short Dec-26) in steepening phases.

We compare three things. First, the share of contrary days on which the curve moved correctly. Second, **return divided by the absolute value of maximum drawdown** over the phase — total return per unit of tail risk. Third, the **top worst outright days** in each phase: what the curve did on the sessions that hurt the level bet most, and whether that movement was the right one.

---

## Four phases

| Phase | Window | Level | Curve | Question |
|-------|--------|-------|-------|----------|
| **I** | 2 Mar – 20 Mar | Bear | Bear flattening | Short Dec-26 vs flattener |
| **II** | 23 Mar – 17 Apr | Bull | Bull steepening | Long Dec-26 vs steepener |
| **III** | 20 Apr – 15 May | Bear | Bear steepening | Short Dec-26 vs steepener |
| **IV** | 18 May – 29 Jun | Bull | Bull flattening | Long Dec-26 vs flattener |

![Dec27−Dec26 four phases on ICE 3M SONIA](figures/dec27_dec26_four_phases_3m.png)

*Top: Dec27−Dec26 spread (bp). Bottom: Dec-26 and Dec-27 implied rates (%); green dotted = Bank Rate 3.75%.*

---

## Phase I — Bear level, bear flattening

Over fourteen sessions both legs sold off violently and the front ran harder. Dec-26 rose 128 bp, Dec-27 rose 89 bp, and the spread collapsed from +9.5 bp to −30 bp — a deep inversion. The level move was bear; the curve move was bear flattening.

The outright expression is short Dec-26. The curve expression is the flattener. Short Dec-26 returned +128 bp over the phase with a maximum drawdown of −15.5 bp, giving a return-to-max-drawdown ratio of 8.3. The flattener returned +39.5 bp with max drawdown −6.5 bp and a ratio of 6.1. The outright max drawdown was 2.4 times larger.

Four of fourteen days (29%) were contrary — the front end fell, hurting the short. On half of those the curve still flattened. The other half bull-steepened.

There were only four losing outright sessions in the entire phase. They are the ones that matter:

| Date | Outright | Flattener | ΔDec26 | Curve type |
|------|----------|-----------|--------|------------|
| 10 Mar | −15.5 | −3.5 | −15.5 | Bull steepening |
| 4 Mar | −9.5 | −2.0 | −9.5 | Bull steepening |
| 16 Mar | −4.0 | +3.0 | −4.0 | Bull flattening |
| 17 Mar | −3.5 | +2.5 | −3.5 | Bull flattening |

The two largest hits — 4 and 10 March, together −25 bp on the short — were bull-steepening days. Wrong curve for a flattener; the spread still lost only −5.5 bp combined, cutting the outright damage by roughly three quarters. The two smaller losses came on bull-flattening days: outright −7.5 bp, flattener +5.5 bp. When the curve moved correctly on a bad outright day, it flipped positive.

Outright wins on return per unit of tail risk in this phase. The flattener's case is limited damage on the worst sessions, not superior total return.

---

## Phase II — Bull level, bull steepening

Over eighteen sessions both legs rallied. Dec-26 fell 45.5 bp, Dec-27 fell 36 bp, and the spread recovered from −24.5 bp to −15 bp. Bull level, bull steepening curve.

Long Dec-26 returned +64 bp; max drawdown −17.5 bp; ratio 3.7. The steepener returned +15 bp; max drawdown −4.5 bp; ratio 3.3. The outright drawdown was 3.9 times larger — the widest gap in the sample — yet return per unit of tail risk is nearly identical.

Six of eighteen days (33%) were contrary: Dec-26 rose, hurting the long. Only two of those six steepened. Most contrary days bear-flattened.

The five worst outright sessions:

| Date | Outright | Steepener | ΔDec26 | Curve type |
|------|----------|-----------|--------|------------|
| 7 Apr | −13.5 | −1.5 | +13.5 | Bear flattening |
| 26 Mar | −11.5 | +0.5 | +11.5 | Bear steepening |
| 13 Apr | −7.5 | −2.5 | +7.5 | Bear flattening |
| 9 Apr | −5.5 | +2.0 | +5.5 | Bear steepening |
| 4 Apr | −4.0 | −3.0 | +4.0 | Bear flattening |

Two of the five worst days steepened — 26 March and 9 April. On those two the outright lost −17 bp while the steepener earned +2.5 bp. On the three that bear-flattened, outright lost −25 bp and the steepener lost −7 bp. The steepener earns when the curve cooperates on a spike; even when it does not, the loss is a fraction of the outright hit.

This is the phase where the curve nearly matches outright on return per unit of tail risk (3.3 vs 3.7) at less than a quarter of the drawdown. The insurance is real even though only a third of contrary days steepen.

---

## Phase III — Bear level, bear steepening

Nineteen sessions. Dec-26 rose 39.5 bp, Dec-27 rose 53 bp, spread moved from −13.5 bp to flat. Bear level, bear steepening — the belly repricing hawkishly relative to the front.

Short Dec-26: +46 bp total, −21.5 bp max drawdown, ratio 2.1. Steepener: +15 bp total, −7.3 bp max drawdown, ratio 2.1. Identical return per unit of tail risk, but the outright drawdown was three times deeper.

Six of nineteen days (32%) were contrary. Half steepened.

The five worst outright sessions:

| Date | Outright | Steepener | ΔDec26 | Curve type |
|------|----------|-----------|--------|------------|
| 6 May | −15.5 | +1.5 | −15.5 | Bull steepening |
| 30 Apr | −9.5 | +0.5 | −9.5 | Bull steepening |
| 14 May | −5.5 | −1.0 | −5.5 | Bull flattening |
| 13 May | −5.0 | +3.0 | −5.0 | Bull steepening |
| 1 May | −2.0 | −0.7 | −2.0 | Bull flattening |

Three of the five worst days steepened. On those three the outright lost −30 bp. The steepener earned +5 bp. On the two that flattened, outright lost −7.5 bp and the steepener lost −1.7 bp.

This is the standout. The curve does not just cushion the worst sessions — on the three largest outright hits it is profitable. Return per unit of tail risk matches the outright at one-third of the drawdown. Phase III is where the steepener pays for itself on the days that matter.

---

## Phase IV — Bull level, bull flattening

Thirty sessions. Dec-26 fell 42 bp, Dec-27 fell 49 bp, spread moved from +3.0 bp to −3.5 bp. Bull level, but the belly outperformed on the way down — bull flattening.

Long Dec-26: +46 bp, −18.0 bp max drawdown, ratio 2.6. Flattener: +3.5 bp, −8.5 bp max drawdown, ratio 0.4. Outright dominates on every measure except raw tail size.

Nine of thirty days (30%) were contrary. Only a third flattened.

The five worst outright sessions:

| Date | Outright | Flattener | ΔDec26 | Curve type |
|------|----------|-----------|--------|------------|
| 1 Jun | −15.5 | +1.5 | +15.5 | Bear flattening |
| 19 Jun | −5.0 | −6.5 | +5.0 | Bear steepening |
| 3 Jun | −4.5 | −1.0 | +4.5 | Bear steepening |
| 8 Jun | −3.5 | −1.5 | +3.5 | Bear steepening |
| 10 Jun | −3.0 | +0.5 | +3.0 | Bear flattening |

The single worst day — 1 June, outright −15.5 bp — was a bear-flattening session and the flattener earned +1.5 bp. That is the hedge working perfectly on the tail event. But the next three worst days all bear-steepened; both structures lost, and the flattener lost more on 19 June (−6.5 bp vs −5.0 bp outright).

Two of five worst days had the right curve; three did not. On the two correct days, outright lost −18.5 bp and the flattener earned +2 bp. On the three wrong days, outright lost −13 bp and the flattener lost −9 bp. Tail risk is halved, but return per unit of drawdown collapses to 0.4 against 2.6 for outright. The flattener is not a substitute for being long in this phase.

---

## Synthesis

| Phase | Level + curve | Contrary days | Correct curve on contrary | Return / \|max DD\| outright | Return / \|max DD\| curve | Max DD ratio |
|-------|---------------|---------------|---------------------------|-------------------------------|---------------------------|--------------|
| **I** | Bear + bear flat | 29% | 50% | **8.3** | 6.1 | 2.4× |
| **II** | Bull + bull steep | 33% | 33% | **3.7** | 3.3 | 3.9× |
| **III** | Bear + bear steep | 32% | 50% | 2.1 | **2.1** | 3.0× |
| **IV** | Bull + bull flat | 30% | 33% | **2.6** | 0.4 | 2.1× |

Every phase is roughly thirty percent contrary days. The proportion of those days on which the curve moves correctly is necessary but not sufficient — what matters is whether the **worst outright sessions** fall on correctly-moving curve days.

When they do, the spread can earn while the outright bleeds (Phase III: −30 bp outright, +5 bp steepener on the three worst steepening days). When they do not, the spread still often softens the blow (Phase I: −25 bp outright, −5.5 bp flattener on the two largest bull-steepening hits) but cannot match total return.

Return per unit of maximum drawdown is the honest scorecard. Outright captures more total return in every phase. The curve is rational only where worst-day curve behaviour and contrary-day alignment combine to hold that ratio up while materially reducing drawdown — Phase II (3.3 vs 3.7 at one-quarter of the tail) and Phase III (2.1 vs 2.1 at one-third). Elsewhere, outright wins.

The belly was four different environments. The right question in each was not "bull or bear" alone, but whether the curve shape on the bad days justified being curved rather than outright.

## Ali Lodhi
```
