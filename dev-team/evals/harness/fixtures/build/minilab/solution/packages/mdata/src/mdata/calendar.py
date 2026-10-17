"""PL-01 step 3: put every ticker on one calendar."""

from __future__ import annotations

from collections.abc import Sequence

from .types import GapError, Prices, RawRow

MAX_GAP = 5


def align_calendar(rows: Sequence[RawRow], *, max_gap: int = MAX_GAP) -> Prices:
    """Prices on the dates any ticker trades, from the first date every ticker has a close.

    A ticker missing on a date takes its previous close; more than `max_gap` missing dates in a row is a
    GapError. `rows` are validated rows (positive closes, one per date and ticker).
    """
    if not rows:
        raise ValueError("no rows")
    by_ticker: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.close is None:
            raise ValueError(f"{r.ticker} {r.date}: no close; validate the rows first")
        by_ticker.setdefault(r.ticker, {})[r.date] = r.close
    first_seen = {t: min(d) for t, d in by_ticker.items()}
    start = max(first_seen.values())
    dates = tuple(sorted({r.date for r in rows if r.date >= start}))
    closes = {}
    for ticker, quotes in sorted(by_ticker.items()):
        series, last, run = [], 0.0, 0
        for d in dates:
            if d in quotes:
                last, run = quotes[d], 0
            else:
                run += 1
                if run > max_gap:
                    raise GapError(f"{ticker}: more than {max_gap} missing dates in a row at {d}")
            series.append(last)
        closes[ticker] = tuple(series)
    return Prices(dates=dates, tickers=tuple(sorted(by_ticker)), closes=closes)
