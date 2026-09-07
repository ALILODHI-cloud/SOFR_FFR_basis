# Agent handoff: publish Market-Notes `post_18`

**Target repo:** https://github.com/ALILODHI-cloud/Market-Notes
**Branch:** `main` (direct push, or PR if you prefer)
**Post:** *Trade Update: Closing our BoE−ECB Dec-26 flattener for +9.0bps*
**Post date:** 4 August 2026 — the session the target printed.

Closes `post_17` (*Long BoE vs ECB Dec-26 @ +4.5bps*) at the **first EOD print that hit the published −4.5 bp target**: 4 August 2026, +9.0 bp, **+$225.00** at $25/bp.

`post_17` is the entry note for this trade, so the close is `post_18`. Do not overwrite `post_17`.

---

## Files to create

```
Market-Notes/
├── README.md                       # edit — add post_18 as first "Latest Post"
└── post_18/
    ├── body.md                     # copy from SOFR_FFR_basis docs/dec26-uk-eur-policy-pricing-close.md
    └── figures/
        └── dec26_uk_eur_relative_policy_close.png
```

## Steps

```bash
git clone https://github.com/ALILODHI-cloud/Market-Notes.git
cd Market-Notes
mkdir -p post_18/figures

# body text — verbatim, no edits needed
curl -L -o post_18/body.md \
  https://raw.githubusercontent.com/ALILODHI-cloud/SOFR_FFR_basis/main/docs/dec26-uk-eur-policy-pricing-close.md

# figure
curl -L -o post_18/figures/dec26_uk_eur_relative_policy_close.png \
  https://raw.githubusercontent.com/ALILODHI-cloud/SOFR_FFR_basis/main/charts/dec26_uk_eur_relative_policy_close.png
```

The image reference in `body.md` is already relative and correct:

```markdown
![Dec-26 relative policy pricing, entry to target](figures/dec26_uk_eur_relative_policy_close.png)
```

Under `## Latest Posts:` in `README.md`, insert as the **first** bullet:

```markdown
- [**Trade Update: Closing our BoE−ECB Dec-26 flattener for +9.0bps (2026-08-04)**](post_18/body.md)
```

```bash
git add post_18 README.md
git commit -m "Add post_18: closing the BoE-ECB Dec-26 flattener for +9.0bps"
git push origin main
```

## Verify

- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_18/body.md
- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_18/figures/dec26_uk_eur_relative_policy_close.png

---

## Numbers the post asserts (all from `closed_trades/dec26_uk_eur_flattener_trade_data.json`)

| Item | Value |
|---|---|
| Entry | 28 Jul 2026, relative +4.5 bp, UK−EUR 154.5 bp |
| Exit | 4 Aug 2026, relative −4.5 bp, UK−EUR 145.5 bp |
| Close reason | published −4.5 bp target hit |
| P&L | +9.0 bp, +$225.00 at $25/bp |
| Sessions held | 5 |
| Worst mark | −$37.50 on 29 Jul, at +6.0 bp relative |
| Stop | +8.5 bp, never threatened |
| UK leg | SONIA Dec-26 4.040% → 3.935%, +29.0 → +18.5 bp vs Bank Rate, −10.5 bp |
| EUR leg | €STR Dec-26 2.495% → 2.480%, +24.5 → +23.0 bp vs deposit, −1.5 bp |
| Curve move | bull flattening; 3 of 5 sessions bull flattening for −9.5 bp |
| Cumulative realised, two rolls | +$437.50 |

Session classifications come from `classify_curve_move` in `analyze_sonia.py`, applied to the daily leg changes.

External facts cited: BoE MPC 6–3 hold at 3.75% announced 30 Jul 2026 (Greene, Mann, Pill dissenting for +25 bp) against a 7–2 Reuters consensus; Bailey press-conference quote; 2y gilt −12.3 bp to 4.34%; LSEG 2026 priced tightening 38 bp → 29 bp; ECB hiked in June 2026 then held on 23 Jul with the deposit rate at 2.25%; UK and euro-area final manufacturing PMIs revised lower on 3 Aug with the UK correction larger; TD Securities fading the post-MPC sterling rally on 4 Aug.

## One-line prompt for the other agent

> Publish `post_18` to https://github.com/ALILODHI-cloud/Market-Notes per `PUBLISH_MARKET_NOTES_POST_18.md` in SOFR_FFR_basis `docs/`: create `post_18/body.md` from `docs/dec26-uk-eur-policy-pricing-close.md`, copy the figure from `charts/`, update README, push to main. Do not touch `post_17`, which is the entry note.
