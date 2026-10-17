"""Unit tests for quantcheck.portfolio, including a property test."""

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from quantcheck.portfolio import inverse_vol_weights


@pytest.mark.unit
@given(st.lists(st.floats(min_value=1e-3, max_value=10.0), min_size=1, max_size=20))
def test_inverse_vol_weights_are_positive_and_sum_to_one(vols):
    weights = inverse_vol_weights(pd.Series(vols))
    assert (weights > 0).all()
    assert weights.sum() == pytest.approx(1.0)


@pytest.mark.unit
def test_inverse_vol_weights_rejects_empty():
    with pytest.raises(ValueError, match="positive"):
        inverse_vol_weights(pd.Series([], dtype=float))
