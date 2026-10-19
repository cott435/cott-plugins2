"""PL-02 step 2 (spine): simple daily returns."""

from __future__ import annotations

import itertools

from mdata.types import Prices

from .types import Returns


def log_returns(prices: Prices) -> Returns:
    """close_t / close_{t-1} - 1 per ticker (simple returns, the spine baseline)."""
    if len(prices.dates) < 2:
        raise ValueError("returns need at least two dates")
    values = {
        t: tuple(b / a - 1.0 for a, b in itertools.pairwise(c)) for t, c in prices.closes.items()
    }
    return Returns(
        base_date=prices.dates[0], dates=prices.dates[1:], tickers=prices.tickers, values=values
    )
