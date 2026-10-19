"""PL-02 step 2: daily log returns."""

from __future__ import annotations

import itertools
import math

from mdata.types import Prices

from .types import Returns


def log_returns(prices: Prices) -> Returns:
    """ln(close_t / close_{t-1}) per ticker; needs at least two dates."""
    if len(prices.dates) < 2:
        raise ValueError("log returns need at least two dates")
    values = {}
    for t in prices.tickers:
        c = prices.closes[t]
        values[t] = tuple(math.log(b / a) for a, b in itertools.pairwise(c))
    return Returns(
        base_date=prices.dates[0], dates=prices.dates[1:], tickers=prices.tickers, values=values
    )
