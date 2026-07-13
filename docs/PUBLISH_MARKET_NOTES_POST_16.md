# Agent handoff: publish Market-Notes `post_16`

**Target repo:** https://github.com/ALILODHI-cloud/Market-Notes  
**Status:** Written locally in workspace `Market-Notes/` — **push blocked** (cursor bot lacks write access). Author can push from desktop or grant repo access.

---

## One-line push

```bash
cd Market-Notes
git pull origin main
# If post_16 not present, copy from this repo's Market-Notes/ subfolder or from commit on SOFR_FFR_basis
git add post_16 README.md
git commit -m "Add post_16: Mar28-Mar27 SOFR steepener thesis"
git push origin main
```

---

## Files

```
post_16/body.md
post_16/figures/mar28_mar27_sofr_steepener_since_entry.png
README.md   # post_16 added as first Latest Post
```

**Live link after push:** https://github.com/ALILODHI-cloud/Market-Notes/blob/main/post_16/body.md

**Trade tracker:** https://alilodhi-cloud.github.io/SOFR_FFR_basis/trade_mar28_mar27_sofr.html

SOFR_FFR_basis `trades/mar28_mar27_sofr_steepener.json` includes `market_note_url` pointing to this post.
