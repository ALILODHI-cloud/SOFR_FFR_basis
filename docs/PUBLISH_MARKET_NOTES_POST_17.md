# Agent handoff: publish Market-Notes `post_17`

**Target repo:** https://github.com/ALILODHI-cloud/Market-Notes
**Branch:** `main` (direct push, or PR if you prefer)
**Post:** *Closing the Dec-26 UK−EUR policy-pricing trade at the first sub-4 bp print*

Closes the Dec26 UK−EUR flattener (short JUZ26 / long IJZ26) at the first end-of-day print where relative implied policy change through Dec-26 sat at or below +4 bp: **30 July 2026**, relative 0.0 bp, +4.5 bp, **+$112.50**.

---

## Files to create

```
Market-Notes/
├── README.md                       # edit — add post_17 as first "Latest Post"
└── post_17/
    ├── body.md                     # copy from SOFR_FFR_basis docs/dec26-uk-eur-policy-pricing-close.md
    └── figures/
        └── dec26_uk_eur_relative_policy_close.png
```

## Steps

```bash
git clone https://github.com/ALILODHI-cloud/Market-Notes.git
cd Market-Notes
mkdir -p post_17/figures

# body text — verbatim, no edits needed
curl -L -o post_17/body.md \
  https://raw.githubusercontent.com/ALILODHI-cloud/SOFR_FFR_basis/main/docs/dec26-uk-eur-policy-pricing-close.md

# figure
curl -L -o post_17/figures/dec26_uk_eur_relative_policy_close.png \
  https://raw.githubusercontent.com/ALILODHI-cloud/SOFR_FFR_basis/main/charts/dec26_uk_eur_relative_policy_close.png
```

The image reference in `body.md` is already relative and correct:

```markdown
![Dec-26 UK−EUR relative policy pricing, entry to close](figures/dec26_uk_eur_relative_policy_close.png)
```

Under `## Latest Posts:` in `README.md`, insert as the **first** bullet:

```markdown
- [**Closing the Dec-26 UK−EUR policy-pricing trade at the first sub-4 bp print (2026-07-30)**](post_17/body.md)
```

```bash
git add post_17 README.md
git commit -m "Add post_17: closing the Dec26 UK-EUR policy-pricing trade at the first sub-4bp print"
git push origin main
```

## Verify

- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_17/body.md
- https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_17/figures/dec26_uk_eur_relative_policy_close.png

---

## Numbers the post asserts (all from `closed_trades/dec26_uk_eur_flattener_trade_data.json`)

| Item | Value |
|---|---|
| Close rule | first EOD relative ≤ +4 bp |
| Entry | 28 Jul 2026, relative +4.5 bp, UK−EUR 154.5 bp |
| Exit | 30 Jul 2026, relative 0.0 bp, UK−EUR 150.0 bp |
| P&L | +4.5 bp, +$112.50 at $25/bp |
| Sessions held | 2 |
| Max adverse mark | −$37.50 (29 Jul) |
| Forgone to 4 Sep mark | 13.5 bp / $337.50 if held |
| Cumulative realised, two rolls | $325.00 |

External facts cited: BoE MPC 6–3 hold at 3.75% announced 30 Jul 2026 (Greene, Mann, Pill dissenting for +25 bp); Bailey press-conference quote; 2y gilt −12.3 bp to 4.34%; LSEG 2026 priced tightening 38 bp → 29 bp; 27 Aug LSEG ~24 bp priced for ECB 10 Sep vs <4 bp for BoE 17 Sep.

## One-line prompt for the other agent

> Publish `post_17` to https://github.com/ALILODHI-cloud/Market-Notes per `PUBLISH_MARKET_NOTES_POST_17.md` in SOFR_FFR_basis `docs/`: create `post_17/body.md` from `docs/dec26-uk-eur-policy-pricing-close.md`, copy the figure from `charts/`, update README, push to main.
