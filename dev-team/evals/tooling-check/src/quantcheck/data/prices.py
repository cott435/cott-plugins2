"""Turn raw price records into a table of daily log returns."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

TRADING_DAYS = 252
PRICE_COLUMNS = ["date", "ticker", "close"]


def load_prices(records: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    """Build a date-by-ticker table of closing prices."""
    frame = pd.DataFrame.from_records(list(records), columns=PRICE_COLUMNS)
    frame["date"] = pd.to_datetime(frame["date"])
    wide = frame.pivot_table(index="date", columns="ticker", values="close", aggfunc="last")
    return wide.sort_index()


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns. The first date has no return and is dropped."""
    values = prices.to_numpy(dtype=float)
    if (values <= 0).any():
        raise ValueError("prices must be positive")
    logs = pd.DataFrame(np.log(values), index=prices.index, columns=prices.columns)
    return logs.diff().dropna(how="all")


def prepare_returns(records: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    """Pipeline: records -> price table -> log returns."""
    prices = load_prices(records)
    return log_returns(prices)
