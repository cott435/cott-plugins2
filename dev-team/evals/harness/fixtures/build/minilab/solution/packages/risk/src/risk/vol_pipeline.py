"""PL-02 Volatility: the entry function."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import mdata

from .annualize import annualize
from .returns import log_returns
from .types import VolSeries
from .vol import rolling_vol


def vol_series(
    path: str | Path, *, window: int = 20, tickers: Sequence[str] | None = None
) -> VolSeries:
    """Annualized rolling volatility of every ticker in a prices CSV."""
    prices = mdata.load_prices(path, tickers)
    returns = log_returns(prices)
    vol = rolling_vol(returns, window)
    return annualize(vol)
