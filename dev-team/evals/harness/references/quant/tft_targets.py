"""Forward targets for return and volatility forecasting.

Builds the label columns a sequence model is trained on: forward log returns and forward realised
volatility over one or more horizons, per ticker, from a long table of daily closes. Rows whose horizon
runs past the end of a ticker's history get NaN targets and are dropped by ``drop_incomplete``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def log_returns(prices: pd.DataFrame, price_col: str = "adj_close") -> pd.Series:
    """Daily log return per ticker. ``prices`` is long: one row per (ticker, date), sorted or not."""
    p = prices.sort_values(["ticker", "date"])
    lr = np.log(p[price_col]).groupby(p["ticker"]).diff()
    return lr.rename("log_ret")


def forward_return(prices: pd.DataFrame, horizon: int, price_col: str = "adj_close") -> pd.Series:
    """Sum of the next ``horizon`` daily log returns, aligned to the row it is predicted from.

    The value on date t uses closes t .. t+horizon, so it is only known after t+horizon.
    """
    p = prices.sort_values(["ticker", "date"])
    lp = np.log(p[price_col])
    fwd = lp.groupby(p["ticker"]).shift(-horizon) - lp
    return fwd.rename(f"fwd_ret_{horizon}d")


def forward_volatility(prices: pd.DataFrame, horizon: int, annualise: bool = True,
                       price_col: str = "adj_close") -> pd.Series:
    """Realised volatility of daily log returns over (t, t+horizon], aligned to date t."""
    p = prices.sort_values(["ticker", "date"]).copy()
    p["log_ret"] = log_returns(p, price_col)
    sq = p["log_ret"] ** 2
    # Sum of squared returns over the next `horizon` days: shift the trailing sum back by `horizon`.
    trailing = sq.groupby(p["ticker"]).transform(lambda s: s.rolling(horizon, min_periods=horizon).sum())
    fwd_sum = trailing.groupby(p["ticker"]).shift(-horizon)
    vol = np.sqrt(fwd_sum / horizon)
    if annualise:
        vol = vol * np.sqrt(TRADING_DAYS)
    return vol.rename(f"fwd_vol_{horizon}d")


def make_targets(prices: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 21),
                 price_col: str = "adj_close") -> pd.DataFrame:
    """All target columns for the given horizons, keyed by (ticker, date).

    Returns a frame with ``ticker``, ``date`` and, per horizon h, ``fwd_ret_{h}d`` and ``fwd_vol_{h}d``.
    """
    p = prices.sort_values(["ticker", "date"]).reset_index(drop=True)
    out = p[["ticker", "date"]].copy()
    for h in horizons:
        out[f"fwd_ret_{h}d"] = forward_return(p, h, price_col).to_numpy()
        out[f"fwd_vol_{h}d"] = forward_volatility(p, h, price_col=price_col).to_numpy()
    return out


def demean_cross_section(targets: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Subtract each date's cross-sectional mean from the given target columns (a crude market adjustment)."""
    t = targets.copy()
    t[cols] = t[cols] - t.groupby("date")[cols].transform("mean")
    return t


def drop_incomplete(targets: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where any target is NaN (the last ``max(horizons)`` days of each ticker)."""
    cols = [c for c in targets.columns if c.startswith(("fwd_ret_", "fwd_vol_"))]
    return targets.dropna(subset=cols).reset_index(drop=True)


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2022-01-03", periods=300)
    rows = []
    for tk in ["AAA", "BBB", "CCC"]:
        px = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(dates))))
        rows.append(pd.DataFrame({"ticker": tk, "date": dates, "adj_close": px}))
    prices = pd.concat(rows, ignore_index=True)
    tg = drop_incomplete(make_targets(prices))
    print(tg.describe().round(4))
