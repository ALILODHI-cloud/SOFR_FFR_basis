"""3M Euribor quarterly strip helpers and ECB mapping."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from analyze_euribor_3m import compute_ecb_meeting_pricing_3m, meta, rebuild_evolution_from_snapshot
from analyze_estr_3m import _ref_contract_key

ROOT = Path(__file__).resolve().parents[1]


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
    if date.today() < date(2026, 10, 30):
        assert oct_mtg["status"] == "next"
        assert out["next_meeting"]["meeting_label"] == "Oct ECB"


def test_snapshot_evolution_uses_im_strip():
    payload = json.loads((ROOT / "euribor_3m_data.json").read_text(encoding="utf-8"))
    keys = [c["key"] for c in payload["contracts"]]
    assert payload["contract"] == "ICE 3M Euribor (IM*)"
    assert keys[0] == "2026-12"
    assert keys[-1] >= "2028-12"
    assert all(c["symbol"].startswith("IM") for c in payload["contracts"])
    evo = rebuild_evolution_from_snapshot(payload)["curve_evolution"]
    assert evo["contract_keys"] == keys
    assert evo["n_sessions"] >= 20
    last_keys = [p["key"] for p in evo["history"][-1]["points"]]
    assert "2026-12" in last_keys
    assert "2027-12" in last_keys


def test_dashboard_html_has_time_travel_and_ecb_panel():
    html = (ROOT / "euribor_3m_dashboard.html").read_text(encoding="utf-8")
    for needle in (
        "3M Euribor",
        "dateSlider",
        "Frozen · latest",
        "Historical",
        "curve_evolution",
        "playBtn",
        "chgTbl",
        "ECB Governing Council",
        "IMZ26",
        "vs deposit",
    ):
        assert needle in html, needle
    assert "1M Euribor" not in html
    assert "vs Bank" not in html
    assert "IJZ26" not in html
    assert "EBZ26" not in html
