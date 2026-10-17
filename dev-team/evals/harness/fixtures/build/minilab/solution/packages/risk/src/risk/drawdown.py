"""PL-03 step 3: maximum drawdown with its peak and trough dates."""

from __future__ import annotations

import math

from .types import Drawdown, Returns


def max_drawdown(returns: Returns) -> tuple[Drawdown, ...]:
    """The deepest fall of each ticker's wealth (1 at `base_date`) below its running peak; the first if tied."""
    out = []
    for t in returns.tickers:
        wealth, peak, peak_date = 1.0, 1.0, returns.base_date
        worst, worst_peak, trough = 0.0, returns.base_date, returns.base_date
        for d, r in zip(returns.dates, returns.values[t]):
            wealth *= math.exp(r)
            if wealth > peak:
                peak, peak_date = wealth, d
            depth = wealth / peak - 1.0
            if depth < worst:
                worst, worst_peak, trough = depth, peak_date, d
        out.append(Drawdown(ticker=t, depth=worst, peak_date=worst_peak, trough_date=trough))
    return tuple(out)
