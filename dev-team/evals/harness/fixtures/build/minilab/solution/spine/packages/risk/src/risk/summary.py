"""PL-03 step 2 (spine): daily mean and volatility."""

from __future__ import annotations

import statistics

from .annualize import PERIODS_PER_YEAR
from .types import TickerSummary, VolSeries


def summary_stats(vol: VolSeries, periods_per_year: int = PERIODS_PER_YEAR) -> tuple[TickerSummary, ...]:
    """Per ticker: daily mean and sample stdev, not annualized yet, and their ratio."""
    out = []
    for t in vol.returns.tickers:
        r = vol.returns.values[t]
        mean, sd = statistics.fmean(r), statistics.stdev(r)
        out.append(TickerSummary(ticker=t, ann_return=mean, ann_vol=sd, sharpe=mean / sd if sd > 0 else 0.0,
                                 last_vol=None))
    return tuple(out)
