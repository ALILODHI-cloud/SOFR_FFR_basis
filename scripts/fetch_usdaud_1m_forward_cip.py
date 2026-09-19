#!/usr/bin/env python3
"""Build daily USDAUD 1M forward from spot + covered interest parity.

Sources (all free, daily):
  - RBA F11.1 A$1=USD  -> inverted to USDAUD (AUD per USD), 2023+
  - FRED DEXUSAL       -> inverted to USDAUD, 1971+ (fills pre-2023)
  - RBA F1 FIRMMBAB30D -> AUD 1M bank bill yield (%), 2011+
  - FRED DGS1MO        -> USD 1M Treasury yield (%), 2001+

Forward (AUD per USD) = Spot × (1 + r_AUD×T) / (1 + r_USD×T), T = 30/360.

Note: this is CIP-implied, not dealer OTC forward points. For actual 1M
forward points history use Barchart Premier, Bloomberg, or Refinitiv.
"""

from __future__ import annotations

import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "usdaud_1m_forward_daily_cip.csv"

RBA_SPOT = "https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv"
RBA_AUD1M = "https://api.db.nomics.world/v22/series/RBA/F1/FIRMMBAB30D?format=csv&observations=1"
FRED_USD1M = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1MO"
FRED_SPOT = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSAL"


def fetch(url: str) -> str:
    proc = subprocess.run(
        ["curl", "-sL", "--max-time", "90", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def parse_rba_spot(text: str) -> dict[str, float]:
    rows = list(csv.reader(io.StringIO(text)))
    col = 1
    for row in rows:
        if row and row[0] == "Title":
            try:
                col = row.index("A$1=USD")
            except ValueError:
                col = 1
            break
    out: dict[str, float] = {}
    for row in rows:
        if not row or not row[0].strip():
            continue
        try:
            d = datetime.strptime(row[0].strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
            v = float(row[col])
            if v > 0:
                out[d] = 1.0 / v
        except (ValueError, IndexError):
            continue
    return out


def parse_fred(text: str) -> dict[str, float]:
    rows = list(csv.reader(io.StringIO(text)))
    out: dict[str, float] = {}
    for row in rows[1:]:
        if len(row) < 2 or row[1] in ("", "."):
            continue
        try:
            out[row[0]] = float(row[1])
        except ValueError:
            continue
    return out


def parse_dbnomics(text: str) -> dict[str, float]:
    rows = list(csv.reader(io.StringIO(text)))
    hdr = rows[0]
    dc = hdr.index("period") if "period" in hdr else hdr.index("period_start_date")
    vc = 1
    out: dict[str, float] = {}
    for row in rows[1:]:
        if len(row) <= max(dc, vc):
            continue
        try:
            out[row[dc][:10]] = float(row[vc])
        except ValueError:
            continue
    return out


def merge_spot(rba: dict[str, float], fred_audusd: dict[str, float]) -> dict[str, float]:
    """USDAUD = AUD per USD. RBA preferred; FRED DEXUSAL is AUDUSD so invert."""
    out = {d: 1.0 / v for d, v in fred_audusd.items() if v > 0}
    out.update(rba)
    return out


def main() -> None:
    print("Fetching RBA spot (2023+)...")
    rba_spot = parse_rba_spot(fetch(RBA_SPOT))
    print(f"  {len(rba_spot)} days")

    print("Fetching FRED DEXUSAL spot (1971+)...")
    fred_spot = parse_fred(fetch(FRED_SPOT))
    spot = merge_spot(rba_spot, fred_spot)
    print(f"  merged {len(spot)} days")

    print("Fetching AUD 1M (RBA)...")
    aud = parse_dbnomics(fetch(RBA_AUD1M))
    print(f"  {len(aud)} days")

    print("Fetching USD 1M (FRED)...")
    usd = parse_fred(fetch(FRED_USD1M))
    print(f"  {len(usd)} days")

    dates = sorted(set(spot) & set(aud) & set(usd))
    T = 30.0 / 360.0
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "date", "usdaud_spot", "aud_1m_pct", "usd_1m_pct",
            "usdaud_1m_forward_cip", "forward_points_pips",
            "spot_source", "method",
        ])
        for d in dates:
            s, ra, ru = spot[d], aud[d], usd[d]
            fwd = s * (1.0 + ra / 100.0 * T) / (1.0 + ru / 100.0 * T)
            pts = (fwd - s) * 10000.0
            src = "RBA" if d in rba_spot else "FRED_DEXUSAL"
            w.writerow([
                d, f"{s:.6f}", f"{ra:.4f}", f"{ru:.4f}",
                f"{fwd:.6f}", f"{pts:.2f}", src, "CIP_30d",
            ])

    print(f"Wrote {len(dates)} rows -> {OUT}")
    if dates:
        d = dates[-1]
        s, ra, ru = spot[d], aud[d], usd[d]
        fwd = s * (1.0 + ra / 100.0 * T) / (1.0 + ru / 100.0 * T)
        pts = (fwd - s) * 10000.0
        print(f"Latest {d}: spot={s:.5f} fwd={fwd:.5f} pts={pts:.1f} pips")


if __name__ == "__main__":
    main()
