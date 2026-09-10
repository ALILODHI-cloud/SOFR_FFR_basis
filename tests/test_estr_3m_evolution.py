"""3M €STR curve evolution uses the full listed strip."""
from __future__ import annotations

import json
from pathlib import Path

from analyze_estr_3m import rebuild_evolution_from_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_evolution_includes_full_listed_strip():
    payload = json.loads((ROOT / "estr_3m_data.json").read_text(encoding="utf-8"))
    keys = [c["key"] for c in payload["contracts"]]
    assert keys[0] <= "2026-09"
    assert keys[-1] >= "2028-12"
    evo = rebuild_evolution_from_snapshot(payload)["curve_evolution"]
    assert evo["contract_keys"] == keys
    assert evo["n_sessions"] >= 20
    last = evo["history"][-1]
    last_keys = [p["key"] for p in last["points"]]
    assert last_keys[-1] == keys[-1]
    assert "2026-12" in last_keys
    assert "2027-12" in last_keys


def test_dashboard_html_has_time_travel_controls():
    html = (ROOT / "estr_3m_dashboard.html").read_text(encoding="utf-8")
    for needle in (
        "dateSlider",
        "Frozen · latest",
        "Historical",
        "curve_evolution",
        "playBtn",
        "chgTbl",
    ):
        assert needle in html, needle
