"""Unit tests for quantcheck.data."""

import numpy as np
import pytest

from quantcheck.data import prepare_returns
from quantcheck.data.prices import load_prices, log_returns


@pytest.mark.unit
def test_load_prices_is_date_by_ticker():
    records = [
        {"date": "2026-01-06", "ticker": "BBB", "close": 2.0},
        {"date": "2026-01-05", "ticker": "AAA", "close": 1.0},
    ]
    prices = load_prices(records)
    assert list(prices.columns) == ["AAA", "BBB"]
    assert prices.index.is_monotonic_increasing


@pytest.mark.unit
def test_log_returns_drops_first_row():
    prices = load_prices(
        [
            {"date": "2026-01-05", "ticker": "AAA", "close": 100.0},
            {"date": "2026-01-06", "ticker": "AAA", "close": 110.0},
        ]
    )
    returns = log_returns(prices)
    assert len(returns) == 1
    assert returns.iloc[0, 0] == pytest.approx(np.log(1.1))


@pytest.mark.unit
def test_prepare_returns_rejects_zero_price():
    with pytest.raises(ValueError, match="positive"):
        prepare_returns([{"date": "2026-01-05", "ticker": "AAA", "close": 0.0}])
