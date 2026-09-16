"""30-day Fed Funds monthly strip helpers and FOMC mapping."""
from __future__ import annotations

from datetime import date

from analyze_ff_30d import (
    _meeting_probs_25bp,
    _ref_contract_key,
    compute_fomc_meeting_pricing,
    symbol_to_meta,
)


def test_zq_symbol_to_meta():
    oct26 = symbol_to_meta("ZQV26")
    assert oct26["key"] == "2026-10"
    assert oct26["label"] == "Oct-26"
    assert oct26["sort_key"] == (2026, 10)
    assert symbol_to_meta("ZQZ27")["key"] == "2027-12"
    assert symbol_to_meta("SQZ26") is None


def test_fomc_maps_to_next_calendar_month():
    assert _ref_contract_key(date(2026, 9, 17)) == "2026-10"
    assert _ref_contract_key(date(2026, 11, 5)) == "2026-12"
    assert _ref_contract_key(date(2026, 12, 10)) == "2027-01"


def test_hike_probability_is_fedwatch_25bp():
    p = _meeting_probs_25bp(3.5)
    assert p["hike_pct"] == 14.0
    assert p["cut_pct"] == 0.0
    assert p["hold_pct"] == 86.0


def test_fomc_pricing_marks_next_meeting_and_uses_fed_midpoint():
    contracts = [
        {
            "key": "2026-10",
            "label": "Oct-26",
            "symbol": "ZQV26",
            "latest_date": "2026-09-15",
            "implied_rate_pct": 3.660,
        },
        {
            "key": "2026-12",
            "label": "Dec-26",
            "symbol": "ZQZ26",
            "latest_date": "2026-09-15",
            "implied_rate_pct": 3.875,
        },
        {
            "key": "2027-01",
            "label": "Jan-27",
            "symbol": "ZQF27",
            "latest_date": "2026-09-15",
            "implied_rate_pct": 4.000,
        },
    ]
    out = compute_fomc_meeting_pricing(contracts, 3.625, "2026-09-14")
    sep = next(m for m in out["meetings"] if m["meeting_label"] == "Sep FOMC")
    assert sep["ref_contract_key"] == "2026-10"
    assert sep["ref_symbol"] == "ZQV26"
    assert sep["cumulative_vs_fed_bp"] == 3.5
    assert sep["incremental_bp"] == 3.5
    assert sep["hike_pct"] == 14.0

    nov = next(m for m in out["meetings"] if m["meeting_label"] == "Nov FOMC")
    assert nov["ref_contract_key"] == "2026-12"
    assert nov["incremental_bp"] == 21.5

    statuses = [m["status"] for m in out["meetings"]]
    assert statuses.count("next") <= 1
    if out["next_meeting"]:
        assert out["next_meeting"]["status"] == "next"
        assert out["next_meeting"]["meeting_date"] > "2026-09-15"
