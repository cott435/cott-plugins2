"""PL-03 step 3 (spine): drawdown depth only."""

from __future__ import annotations

import math

from .types import Drawdown, Returns


def max_drawdown(returns: Returns) -> tuple[Drawdown, ...]:
    """The deepest fall below the running peak; the peak date is not tracked yet (base date)."""
    out = []
    for t in returns.tickers:
        wealth, peak, worst = 1.0, 1.0, 0.0
        for r in returns.values[t]:
            wealth *= math.exp(r)
            peak = max(peak, wealth)
            worst = min(worst, wealth / peak - 1.0)
        out.append(Drawdown(ticker=t, depth=worst, peak_date=returns.base_date))
    return tuple(out)
