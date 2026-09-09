"""SFI calendar / fly arithmetic and 1M evolution strip coverage."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analyze_sfi_structures import horizon_moves, structures_from_rates
from analyze_sonia_1m import rebuild_evolution_from_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _wide():
    idx = pd.to_datetime(["2026-06-08", "2026-08-07", "2026-09-08"])
    return pd.DataFrame(
        {
            "J8Z26": [3.995, 3.915, 4.120],
            "J8M27": [4.225, 4.100, 4.470],
            "J8Z27": [4.000, 4.090, 4.500],
            "J8Z28": [4.045, 4.130, 4.460],
        },
        index=idx,
    )


def test_structures_match_rate_definitions():
    s = structures_from_rates(_wide()).iloc[-1]
    assert abs(s["z6_z7"] - 38.0) < 1e-9
    assert abs(s["z6_m7"] - 35.0) < 1e-9
    assert abs(s["m7_z7"] - 3.0) < 1e-9
    assert abs(s["z7_z8"] - (-4.0)) < 1e-9
    assert abs(s["fly"] - 42.0) < 1e-9


def test_horizon_sharpest_is_largest_abs_change():
    struct = structures_from_rates(_wide())
    rows = horizon_moves(struct, months=(1, 3))
    assert [r["horizon"] for r in rows] == ["1m", "3m"]
    for r in rows:
        chg = r["changes_bp"]
        expected = max(chg, key=lambda k: abs(chg[k]))
        assert r["sharpest_id"] == expected
        assert r["sharpest_bp"] == chg[expected]


def test_sonia_1m_evolution_includes_listed_2028_tail():
    payload = json.loads((ROOT / "sonia_1m_data.json").read_text(encoding="utf-8"))
    keys = [c["key"] for c in payload["contracts"]]
    assert keys[-1] >= "2028-08"
    evo = rebuild_evolution_from_snapshot(payload)["curve_evolution"]
    assert evo["contract_keys"][-1] >= "2028-08"
    last = evo["history"][-1]
    last_keys = [p["key"] for p in last["points"]]
    assert "2028-08" in last_keys
    assert last["points"][-1]["key"] == keys[-1]
