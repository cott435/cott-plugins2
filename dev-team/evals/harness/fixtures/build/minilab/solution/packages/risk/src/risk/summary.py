"""PL-03 step 2: whole-period return, volatility and Sharpe ratio."""

from __future__ import annotations

import math
import statistics

from .annualize import PERIODS_PER_YEAR
from .types import TickerSummary, VolSeries


def summary_stats(
    vol: VolSeries, periods_per_year: int = PERIODS_PER_YEAR
) -> tuple[TickerSummary, ...]:
    """Per ticker: mean return x periods, sample stdev (n - 1) x sqrt(periods), their ratio, the last vol."""
    out = []
    for t in vol.returns.tickers:
        r = vol.returns.values[t]
        if len(r) < 2:
            raise ValueError(f"{t}: summary needs at least two returns")
        ann_return = statistics.fmean(r) * periods_per_year
        ann_vol = statistics.stdev(r) * math.sqrt(periods_per_year)
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0
        last_vol = next((v for v in reversed(vol.values[t]) if v is not None), None)
        out.append(
            TickerSummary(
                ticker=t, ann_return=ann_return, ann_vol=ann_vol, sharpe=sharpe, last_vol=last_vol
            )
        )
    return tuple(out)
