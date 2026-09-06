"""Guarded writes for curve snapshot JSON.

Barchart chain discovery scrapes the futures-prices page, so a bot challenge
returns a page body with only the front contract instead of the full strip.
The fetch still "succeeds", and writing that payload replaces a healthy
snapshot with a single contract, which leaves the dashboards with nothing to
plot. Reject a regressed payload instead, so the caller exits non-zero and the
workflow rebuilds from the last committed snapshot.
"""
from __future__ import annotations

import json
from pathlib import Path

# A strip may legitimately shrink as contracts roll off or a far-dated tail
# stops quoting; anything past this much of the previous count is a failure.
MIN_RETAINED_FRACTION = 0.6


class DegradedCurveError(RuntimeError):
    """Raised when a payload holds too few contracts to be a usable curve."""


def _contract_count(payload: dict) -> int:
    declared = payload.get("n_contracts")
    if isinstance(declared, int):
        return declared
    contracts = payload.get("contracts")
    return len(contracts) if isinstance(contracts, list) else 0


def previous_contract_count(path: Path) -> int:
    """Contract count of the snapshot already on disk, 0 if unreadable."""
    try:
        with path.open(encoding="utf-8") as f:
            return _contract_count(json.load(f))
    except (OSError, ValueError):
        return 0


def write_snapshot(payload: dict, path: Path, min_contracts: int) -> None:
    """Write payload to path unless its curve is degraded."""
    count = _contract_count(payload)

    if count < min_contracts:
        raise DegradedCurveError(
            f"{path.name}: fetched {count} contracts, need at least "
            f"{min_contracts}; keeping previous snapshot"
        )

    previous = previous_contract_count(path)
    floor = int(previous * MIN_RETAINED_FRACTION)
    if previous and count < floor:
        raise DegradedCurveError(
            f"{path.name}: fetched {count} contracts vs {previous} in the "
            f"previous snapshot (floor {floor}); keeping previous snapshot"
        )

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {path} ({count} contracts)")
