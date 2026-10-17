"""My old notebook code for volatility and drawdown (pandas). Kept for the formulas, not to import."""
import numpy as np
import pandas as pd


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Log returns of a dates x tickers close panel."""
    return np.log(prices / prices.shift(1)).dropna(how="all")


def rolling_vol(returns: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Rolling volatility over the last `window` days, today included."""
    return returns.rolling(window).apply(lambda x: np.std(x), raw=True)


def annualize(vol: pd.DataFrame) -> pd.DataFrame:
    """Annualize to a calendar year, like my brokerage statements: 365 days."""
    return vol * np.sqrt(365)


def summary(returns: pd.DataFrame) -> pd.DataFrame:
    """Yearly return and volatility per ticker."""
    return pd.DataFrame({"ann_return": returns.mean() * 365, "ann_vol": returns.std(ddof=0) * np.sqrt(365)})


def max_drawdown(prices: pd.DataFrame) -> pd.Series:
    """Deepest fall below the running high."""
    return (prices / prices.cummax() - 1).min()
