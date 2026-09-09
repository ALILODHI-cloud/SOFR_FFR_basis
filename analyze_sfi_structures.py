"""
ICE 3M SONIA (SFI / J8*) calendar spreads and the Z6/Z7/Z8 fly.

SFI is the ICE Three Month SONIA Index Future. Barchart root is J8*.

Structures (rate space, bp):
  Z6/Z7  = Dec-27 − Dec-26     (1y calendar)
  Z6/M7  = Jun-27 − Dec-26     (6m calendar)
  M7/Z7  = Dec-27 − Jun-27     (back 6m of 2027)
  Z7/Z8  = Dec-28 − Dec-27     (1y calendar, end-2028 vs end-2027)
  fly    = 2×Dec-27 − Dec-26 − Dec-28   (belly richness)

Writes sfi_structures_data.json for build_sfi_structures_dashboard.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyze_sonia import price_to_rate
from analyze_stir_curves import fetch_barchart_batch

ROOT = Path(__file__).resolve().parent

LEGS = {
    "Z6": {"symbol": "J8Z26", "key": "2026-12", "label": "Dec-26"},
    "M7": {"symbol": "J8M27", "key": "2027-06", "label": "Jun-27"},
    "Z7": {"symbol": "J8Z27", "key": "2027-12", "label": "Dec-27"},
    "Z8": {"symbol": "J8Z28", "key": "2028-12", "label": "Dec-28"},
}

STRUCTURES = [
    {
        "id": "z6_z7",
        "label": "SFI Z6/Z7",
        "formula": "Dec-27 − Dec-26",
        "legs": "long Z7 / short Z6 in rate (steepener)",
    },
    {
        "id": "z6_m7",
        "label": "SFI Z6/M7",
        "formula": "Jun-27 − Dec-26",
        "legs": "long M7 / short Z6 in rate (steepener)",
    },
    {
        "id": "m7_z7",
        "label": "SFI M7/Z7",
        "formula": "Dec-27 − Jun-27",
        "legs": "long Z7 / short M7 in rate (steepener)",
    },
    {
        "id": "z7_z8",
        "label": "SFI Z7/Z8",
        "formula": "Dec-28 − Dec-27",
        "legs": "long Z8 / short Z7 in rate (steepener)",
    },
    {
        "id": "fly",
        "label": "Z6/Z7/Z8 fly",
        "formula": "2×Dec-27 − Dec-26 − Dec-28",
        "legs": "short 2×Z7 / long Z6+Z8 fades belly richness",
    },
]

HORIZONS_MONTHS = (1, 2, 3, 4, 6)


def structures_from_rates(wide: pd.DataFrame) -> pd.DataFrame:
    """wide columns are J8 symbols; returns structure series in bp."""
    z6, m7, z7, z8 = (wide["J8Z26"], wide["J8M27"], wide["J8Z27"], wide["J8Z28"])
    return pd.DataFrame(
        {
            "z6_z7": (z7 - z6) * 100.0,
            "z6_m7": (m7 - z6) * 100.0,
            "m7_z7": (z7 - m7) * 100.0,
            "z7_z8": (z8 - z7) * 100.0,
            "fly": (2.0 * z7 - z6 - z8) * 100.0,
        },
        index=wide.index,
    )


def _nearest_session(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp:
    loc = int(index.searchsorted(target))
    if loc >= len(index):
        return index[-1]
    if loc > 0 and abs((index[loc] - target).days) > abs((index[loc - 1] - target).days):
        return index[loc - 1]
    return index[loc]


def horizon_moves(struct: pd.DataFrame, months: tuple[int, ...] = HORIZONS_MONTHS) -> list[dict]:
    last = struct.index.max()
    rows: list[dict] = []
    for m in months:
        start = last - pd.DateOffset(months=m)
        if start < struct.index.min() - pd.Timedelta(days=5):
            continue
        dt0 = _nearest_session(struct.index, start)
        a, b = struct.loc[dt0], struct.iloc[-1]
        chg = (b - a).to_dict()
        abs_chg = {k: abs(float(v)) for k, v in chg.items()}
        sharpest = max(abs_chg, key=abs_chg.get)
        rows.append(
            {
                "horizon": f"{m}m",
                "horizon_months": m,
                "from_date": str(dt0.date()),
                "to_date": str(last.date()),
                "changes_bp": {k: round(float(v), 1) for k, v in chg.items()},
                "sharpest_id": sharpest,
                "sharpest_bp": round(float(chg[sharpest]), 1),
            }
        )
    return rows


def series_stats(s: pd.Series) -> dict:
    last = float(s.iloc[-1])
    return {
        "last_bp": round(last, 1),
        "min_bp": round(float(s.min()), 1),
        "max_bp": round(float(s.max()), 1),
        "pctile": round(float((s <= last).mean() * 100.0), 1),
        "mean_bp": round(float(s.mean()), 1),
        "stdev_bp": round(float(s.std(ddof=1)), 1) if len(s) > 2 else None,
    }


def fetch_leg_rates() -> pd.DataFrame:
    symbols = [meta["symbol"] for meta in LEGS.values()]
    batch = fetch_barchart_batch(symbols, history_limit=250)
    series = {}
    for sym in symbols:
        df = batch.get(sym)
        if df is None or df.empty:
            raise RuntimeError(f"No EOD history for {sym}")
        series[sym] = price_to_rate(df["price"])
    return pd.DataFrame(series).dropna().sort_index()


def build_payload(wide: pd.DataFrame | None = None) -> dict:
    if wide is None:
        wide = fetch_leg_rates()
    struct = structures_from_rates(wide)
    last = struct.iloc[-1]
    horizons = horizon_moves(struct)
    sharpest_by_h = {h["horizon"]: h["sharpest_id"] for h in horizons}

    # Most frequent sharpest across 1–3m is the near-term signal.
    near = [h["sharpest_id"] for h in horizons if h["horizon_months"] <= 3]
    consensus = max(set(near), key=near.count) if near else horizons[0]["sharpest_id"]

    structures_out = []
    for spec in STRUCTURES:
        sid = spec["id"]
        s = struct[sid]
        structures_out.append(
            {
                **spec,
                **series_stats(s),
                "rows": [
                    {"date": str(dt.date()), "bp": round(float(v), 2)}
                    for dt, v in s.items()
                ],
            }
        )

    legs_out = []
    for code, meta in LEGS.items():
        s = wide[meta["symbol"]]
        legs_out.append(
            {
                "code": code,
                **meta,
                "implied_rate_pct": round(float(s.iloc[-1]), 4),
                "latest_date": str(s.index[-1].date()),
            }
        )

    fly_stats = next(s for s in structures_out if s["id"] == "fly")
    z6z7_stats = next(s for s in structures_out if s["id"] == "z6_z7")
    trade_note = _trade_note(consensus, fly_stats, z6z7_stats, last)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD lastPrice · ICE 3M SONIA (J8* / SFI)",
        "as_of": str(struct.index.max().date()),
        "history_start": str(struct.index.min().date()),
        "n_sessions": int(len(struct)),
        "quote_note": (
            "Spreads are later minus earlier implied 3m SONIA, in bp. "
            "Fly is belly richness: 2×Z7 − Z6 − Z8. Positive fly = Dec-27 rich "
            "vs the Z6–Z8 wing interpolation."
        ),
        "legs": legs_out,
        "latest_bp": {k: round(float(last[k]), 1) for k in last.index},
        "horizons": horizons,
        "sharpest_near_term": consensus,
        "trade_note": trade_note,
        "structures": structures_out,
    }


def _trade_note(consensus: str, fly: dict, z6z7: dict, last: pd.Series) -> dict:
    """Fade the structure that is both near-term sharpest and historically extreme."""
    sell_fly = (
        consensus == "fly"
        and fly["pctile"] >= 90
        and z6z7["pctile"] >= 85
    )
    if sell_fly:
        return {
            "action": "Sell Z6/Z7/Z8 fly",
            "position": "Long J8Z26 + Long J8Z28 / Short 2× J8Z27 (1:-2:1)",
            "entry_bp": round(float(last["fly"]), 1),
            "rationale": (
                "Fly is the sharpest 1–2m move and sits at the top of its 1y range. "
                "Dec-27 is rich vs both Dec-26 and Dec-28; selling the fly fades that "
                "peak without taking a one-way view on the 2026–27 steepener alone."
            ),
            "target_bp": 25.0,
            "stop_bp": 48.0,
        }
    if consensus == "z6_z7" and z6z7["pctile"] >= 90:
        return {
            "action": "Flatten SFI Z6/Z7",
            "position": "Long J8Z26 / Short J8Z27 (short the steepener)",
            "entry_bp": round(float(last["z6_z7"]), 1),
            "rationale": (
                "Z6/Z7 is the sharpest multi-month move and is at the top of its 1y range."
            ),
            "target_bp": 20.0,
            "stop_bp": 46.0,
        }
    return {
        "action": "No fade — structure not extreme",
        "position": None,
        "entry_bp": None,
        "rationale": f"Near-term sharpest is {consensus}, but percentile ranks are not stretched.",
        "target_bp": None,
        "stop_bp": None,
    }


def main() -> None:
    payload = build_payload()
    path = ROOT / "sfi_structures_data.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {path} ({payload['n_sessions']} sessions → {payload['as_of']})")
    print("Latest", payload["latest_bp"])
    for h in payload["horizons"]:
        print(
            f"  {h['horizon']:>3} {h['from_date']}  sharpest {h['sharpest_id']} "
            f"{h['sharpest_bp']:+.1f}  {h['changes_bp']}"
        )


if __name__ == "__main__":
    main()
