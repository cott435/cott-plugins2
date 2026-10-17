"""PL-02 step 3: rolling volatility from earlier returns only."""

from __future__ import annotations

import statistics

from .types import Returns, VolSeries


def rolling_vol(returns: Returns, window: int) -> VolSeries:
    """Sample standard deviation (n - 1) of the `window` returns before each date, never the date itself."""
    if window < 2:
        raise ValueError("window must be at least 2")
    values = {}
    for t in returns.tickers:
        r = returns.values[t]
        values[t] = tuple(None if i < window else statistics.stdev(r[i - window : i]) for i in range(len(r)))
    return VolSeries(returns=returns, window=window, annualized=False, values=values)
