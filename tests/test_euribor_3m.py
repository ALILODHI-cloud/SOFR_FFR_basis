"""3M Euribor quarterly strip helpers and ECB mapping."""
from __future__ import annotations

from datetime import date

from analyze_euribor_3m import compute_ecb_meeting_pricing_3m, meta
from analyze_estr_3m import _ref_contract_key


def test_im_symbol_to_meta():
    dec26 = meta("IMZ26")
    assert dec26["key"] == "2026-12"
    assert dec26["label"] == "Dec-26"
    assert meta("IMU27")["key"] == "2027-09"
    assert meta("IJZ26") is None
    assert meta("EBZ26") is None


def test_ecb_maps_to_next_quarter():
    assert _ref_contract_key(date(2026, 10, 29)) == "2026-12"
    assert _ref_contract_key(date(2026, 12, 17)) == "2027-03"


def test_ecb_pricing_uses_deposit_and_next_quarter():
    contracts = [
        {
            "key": "2026-12",
            "label": "Dec-26",
            "symbol": "IMZ26",
            "latest_date": "2026-09-17",
            "implied_rate_pct": 3.000,
        },
        {
            "key": "2027-03",
            "label": "Mar-27",
            "symbol": "IMH27",
            "latest_date": "2026-09-17",
            "implied_rate_pct": 3.300,
        },
        {
            "key": "2027-06",
            "label": "Jun-27",
            "symbol": "IMM27",
            "latest_date": "2026-09-17",
            "implied_rate_pct": 3.430,
        },
    ]
    out = compute_ecb_meeting_pricing_3m(contracts, 2.50, "2026-09-10")
    oct_mtg = next(m for m in out["meetings"] if m["meeting_label"] == "Oct ECB")
    assert oct_mtg["ref_contract_key"] == "2026-12"
    assert oct_mtg["ref_symbol"] == "IMZ26"
    assert oct_mtg["cumulative_vs_deposit_bp"] == 50.0
    assert oct_mtg["status"] == "next"
    assert out["next_meeting"]["meeting_label"] == "Oct ECB"
