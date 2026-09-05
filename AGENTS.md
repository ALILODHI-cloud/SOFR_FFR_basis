# AGENTS.md

## Cursor Cloud specific instructions

This repo is a small Python data pipeline that produces a single-file static dashboard
(`index.html`) for the FFR−SOFR basis "July trade" analysis. There is no package manager
manifest (no `requirements.txt`); the update script installs deps directly.

### Services / pipeline
- `analyze.py` — pulls daily EFFR & SOFR from the NY Fed reference-rate API (live network
  request), computes monthly stats, and writes `basis_data.json`. Requires `numpy`,
  `pandas`, `requests`. It hits `https://markets.newyorkfed.org/api/rates/...`, so it needs
  outbound internet; if the network is blocked it will raise on `raise_for_status()`. The
  committed `basis_data.json` is a usable snapshot, so you can skip `analyze.py` and still
  build the dashboard.
- `build_app.py` — pure stdlib; reads `basis_data.json` and writes `index.html`. Run this
  after `analyze.py` to refresh the dashboard.
- `index.html` — static dashboard (Chart.js loaded from CDN). Serve it over HTTP rather than
  `file://` so the CDN script and the "Try live refresh" button (which fetches the NY Fed API
  directly from the browser) work. Serve with `python3 -m http.server 8000` from the repo
  root, then open `http://localhost:8000/index.html`.

### Reproduce / run
```bash
python3 analyze.py      # refresh basis_data.json (needs internet)
python3 build_app.py    # rebuild index.html
python3 -m http.server 8000   # serve, then open http://localhost:8000/index.html
```

### Notes / gotchas
- Running `analyze.py` and `build_app.py` overwrites the tracked `basis_data.json` and
  `index.html` with current-date data. Those diffs are expected and usually should not be
  committed unless you intend to update the snapshot.
- `dump_pages.py` and `extract_pdf.py` are auxiliary one-off tools that use `PyMuPDF` (`fitz`)
  on hardcoded Windows paths to restricted Barclays PDFs that are NOT in the repo. They cannot
  run in this environment and are not part of the core pipeline; ignore them for setup.
- There is no lint config or automated test suite in this repo.
