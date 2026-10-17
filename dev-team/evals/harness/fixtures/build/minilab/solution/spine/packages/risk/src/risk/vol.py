"""PL-02 step 3 (spine): expanding volatility."""

from __future__ import annotations

import statistics

from .types import Returns, VolSeries


def rolling_vol(returns: Returns, window: int) -> VolSeries:
    """Sample stdev of every return before each date (expanding; `window` only labels the series)."""
    values = {}
    for t in returns.tickers:
        r = returns.values[t]
        values[t] = tuple(None if i < 2 else statistics.stdev(r[:i]) for i in range(len(r)))
    return VolSeries(returns=returns, window=window, annualized=False, values=values)
