#!/usr/bin/env python3
"""Fetch and parse ICE IRM 2 indicative margins for ICE 1M SONIA (JU*) futures."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_FILE = ROOT / "ice_sonia_margins.json"

# ICE Margin Matrix product-guide id for IFEU 1M SONIA monthly futures (commodity code M).
ICE_SONIA_MARGIN_PRODUCT_ID = 910
ICE_MARGIN_PDF_URL = (
    f"https://www.ice.com/api/productguide/margin-rates/{ICE_SONIA_MARGIN_PRODUCT_ID}/pdf"
)
UA = (
    "Mozilla/5.0 (compatible; SupraSTIR/1.0; +https://github.com/alilodhi-cloud/sofr_ffr_basis)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def fetch_margin_pdf() -> bytes:
    req = urllib.request.Request(ICE_MARGIN_PDF_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise RuntimeError("ICE margin response is not a PDF")
    return data


def parse_margin_pdf(data: bytes) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf required to parse ICE margin PDF") from exc

    text = "\n".join((p.extract_text() or "") for p in PdfReader(BytesIO(data)).pages)
    # business date line e.g. "July 1, 2026"
    as_of = None
    for line in text.splitlines():
        if re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$", line.strip()):
            as_of = line.strip()
            break

    outrights: dict[str, dict] = {}
    for m in re.finditer(
        r"IFEU M MONTH (M\d+) ([A-Z][a-z]{2}-\d{2}) GBP ([\-\d,\.]+) ([\-\d,\.]+)",
        text,
    ):
        expiry = m.group(2)
        outrights[expiry] = {
            "period": m.group(1),
            "expiry": expiry,
            "long_im_gbp": abs(float(m.group(3).replace(",", ""))),
            "short_im_gbp": abs(float(m.group(4).replace(",", ""))),
        }

    if not outrights:
        raise RuntimeError("No ICE 1M SONIA outright margins parsed from PDF")

    spreads: list[dict] = []
    for m in re.finditer(
        r"Calendar Spread IFEU M MONTH (M\d+)\s+(M\d+)\s+"
        r"([A-Z][a-z]{2}-\d{2})\s+([A-Z][a-z]{2}-\d{2})\s+"
        r"GBP 1\s+-1\s+([\-\d,\.]+)\s+([\-\d,\.]+)",
        text,
    ):
        spreads.append({
            "near_period": m.group(1),
            "far_period": m.group(2),
            "near_expiry": m.group(3),
            "far_expiry": m.group(4),
            "long_near_im_gbp": abs(float(m.group(5).replace(",", ""))),
            "short_near_im_gbp": abs(float(m.group(6).replace(",", ""))),
        })

    return {
        "fetched_utc": utc_now(),
        "source": {
            "exchange": "ICE Futures Europe (IFEU)",
            "product": "ICE 1M SONIA Index Futures (JU*)",
            "model": "IRM 2 Margin Matrix (indicative outright / calendar spread)",
            "url": ICE_MARGIN_PDF_URL,
            "product_guide_id": ICE_SONIA_MARGIN_PRODUCT_ID,
            "as_of": as_of,
            "note": (
                "Per-contract indicative initial margin for a 1-lot position from ICE "
                "Clearing Analytics Margin Matrix. Portfolio margin on multi-leg STIR "
                "books is typically lower than the sum of leg IM."
            ),
        },
        "outrights": outrights,
        "calendar_spreads": spreads,
    }


def load_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    with CACHE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_cache(payload: dict) -> None:
    CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def refresh_margins() -> dict:
    data = parse_margin_pdf(fetch_margin_pdf())
    save_cache(data)
    return data


def load_margins(refresh: bool = False) -> dict:
    if refresh:
        try:
            return refresh_margins()
        except Exception:
            cached = load_cache()
            if cached:
                return cached
            raise
    cached = load_cache()
    if cached:
        return cached
    return refresh_margins()


def _leg_margin_gbp(expiry: str, side: str, contracts: int, margins: dict) -> float:
    row = margins["outrights"].get(expiry)
    if not row:
        raise KeyError(f"No ICE margin for expiry {expiry!r}")
    key = "long_im_gbp" if side == "long" else "short_im_gbp"
    return float(row[key]) * contracts


def margin_spread_gbp(
    long_expiry: str,
    short_expiry: str,
    contracts_per_leg: int,
    margins: dict | None = None,
) -> tuple[float, str]:
    """Return (margin_gbp, method) for a 1:1 calendar spread."""
    m = margins or load_margins()
    for spr in m.get("calendar_spreads", []):
        if spr["near_expiry"] == long_expiry and spr["far_expiry"] == short_expiry:
            return spr["long_near_im_gbp"] * contracts_per_leg, "ice_calendar_spread"
        if spr["near_expiry"] == short_expiry and spr["far_expiry"] == long_expiry:
            return spr["short_near_im_gbp"] * contracts_per_leg, "ice_calendar_spread"
    total = _leg_margin_gbp(long_expiry, "long", contracts_per_leg, m) + _leg_margin_gbp(
        short_expiry, "short", contracts_per_leg, m
    )
    return total, "ice_outright_legs"


def margin_outright_long_gbp(
    expiry: str,
    contracts: int,
    margins: dict | None = None,
) -> tuple[float, str]:
    m = margins or load_margins()
    return _leg_margin_gbp(expiry, "long", contracts, m), "ice_outright_long"


def margin_note(margins: dict) -> str:
    src = margins["source"]
    as_of = src.get("as_of") or "latest ICE publish"
    return (
        f"Initial margin from ICE IRM 2 Margin Matrix ({as_of}), per 1-lot indicative IM "
        f"× book contracts/leg. Source: {src['url']}. "
        "Multi-leg book uses sum of leg IM where no listed calendar spread; "
        "actual cleared margin may be lower via portfolio offsets."
    )


def main() -> None:
    payload = refresh_margins()
    print(f"Wrote {CACHE_FILE}")
    for exp in ("Dec-26", "Jun-27", "Dec-27"):
        row = payload["outrights"].get(exp)
        if row:
            print(
                f"  {exp}: long £{row['long_im_gbp']:,.0f} · "
                f"short £{row['short_im_gbp']:,.0f}"
            )


if __name__ == "__main__":
    main()
