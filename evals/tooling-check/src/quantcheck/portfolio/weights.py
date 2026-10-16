"""Inverse-volatility portfolio weights."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from quantcheck.data import prepare_returns
from quantcheck.stats import summarize_returns


def inverse_vol_weights(vol: pd.Series[float]) -> pd.Series[float]:
    """Weights proportional to 1 / volatility, summing to one."""
    if vol.empty or (vol <= 0).any():
        raise ValueError("volatilities must be positive")
    inverse = 1.0 / vol
    return inverse / inverse.sum()


def build_portfolio(records: Iterable[Mapping[str, object]]) -> dict[str, float]:
    """Pipeline: price records -> returns -> volatility -> weights."""
    returns = prepare_returns(records)
    summary = summarize_returns(returns)
    weights = inverse_vol_weights(summary["vol"])
    return {str(ticker): round(float(weight), 6) for ticker, weight in weights.items()}
