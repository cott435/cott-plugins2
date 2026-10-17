"""PL-01 step 3 (spine): the dates every ticker has, no filling."""

from __future__ import annotations

from collections.abc import Sequence

from .types import Prices, RawRow

MAX_GAP = 5


def align_calendar(rows: Sequence[RawRow], *, max_gap: int = MAX_GAP) -> Prices:
    """Prices on the dates on which every ticker has a close; `max_gap` is not used yet."""
    by_ticker: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.close is not None:
            by_ticker.setdefault(r.ticker, {})[r.date] = r.close
    if not by_ticker:
        raise ValueError("no rows")
    common = set.intersection(*(set(q) for q in by_ticker.values()))
    dates = tuple(sorted(common))
    closes = {t: tuple(q[d] for d in dates) for t, q in sorted(by_ticker.items())}
    return Prices(dates=dates, tickers=tuple(sorted(by_ticker)), closes=closes)
