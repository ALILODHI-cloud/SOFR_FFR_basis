"""Deterministic futures-strip symbols, for when chain scraping degrades.

Chain discovery reads the Barchart futures-prices page to learn which
contracts exist. That page is the piece that gets bot-challenged, while
per-symbol price-history pages keep serving, so a challenged scrape leaves the
strip nearly empty even though the data is still reachable. Synthesizing the
expected symbols keeps a refresh going: contracts that do not exist simply
miss during the batch fetch and get skipped.
"""
from __future__ import annotations

from datetime import date

# Barchart/CME month codes.
MONTH_LETTER = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z",
}
QUARTERLY_MONTHS = (3, 6, 9, 12)


def strip_symbols(
    prefix: str,
    count: int,
    quarterly: bool = False,
    start: date | None = None,
    back: int = 1,
) -> list[str]:
    """`count` contract symbols from `back` periods before `start`'s month.

    The lookback keeps a just-expired front contract in the list; its history
    still belongs on the curve until it drops off the chain.
    """
    ref = start or date.today()
    year, month = ref.year, ref.month

    if quarterly:
        # Step back to the quarterly month at or before the reference month so
        # the front contract matches the listed strip.
        month = max((m for m in QUARTERLY_MONTHS if m <= month), default=None)
        if month is None:
            year, month = year - 1, 12

    step = 3 if quarterly else 1
    month -= step * back
    while month < 1:
        month += 12
        year -= 1

    symbols: list[str] = []
    while len(symbols) < count:
        symbols.append(f"{prefix}{MONTH_LETTER[month]}{str(year)[2:]}")
        month += 3 if quarterly else 1
        while month > 12:
            month -= 12
            year += 1
    return symbols
