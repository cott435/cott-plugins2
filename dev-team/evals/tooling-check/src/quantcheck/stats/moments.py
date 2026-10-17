"""Annualised mean, volatility and Sharpe ratio per ticker."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantcheck.data import TRADING_DAYS


def annualised_volatility(returns: pd.DataFrame) -> pd.Series[float]:
    """Sample standard deviation of daily returns, scaled to a year."""
    return returns.std(ddof=1) * float(np.sqrt(TRADING_DAYS))


def summarize_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Pipeline: returns -> annualised mean, volatility and Sharpe ratio."""
    mean = returns.mean() * TRADING_DAYS
    vol = annualised_volatility(returns)
    sharpe = mean / vol.replace(0.0, np.nan)
    return pd.DataFrame({"mean": mean, "vol": vol, "sharpe": sharpe})
