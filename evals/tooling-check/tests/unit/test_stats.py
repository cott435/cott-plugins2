"""Unit tests for quantcheck.stats."""

import numpy as np
import pandas as pd
import pytest

from quantcheck.stats import annualised_volatility, summarize_returns


@pytest.mark.unit
def test_annualised_volatility_scales_by_sqrt_252():
    returns = pd.DataFrame({"AAA": [0.01, -0.01, 0.01, -0.01]})
    expected = np.std([0.01, -0.01, 0.01, -0.01], ddof=1) * np.sqrt(252)
    assert annualised_volatility(returns)["AAA"] == pytest.approx(expected)


@pytest.mark.unit
def test_summarize_returns_sharpe_is_nan_for_zero_vol():
    returns = pd.DataFrame({"AAA": [0.0, 0.0, 0.0]})
    summary = summarize_returns(returns)
    assert np.isnan(summary.loc["AAA", "sharpe"])
