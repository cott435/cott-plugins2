"""M1 rolling vol thicken · TC-05 (RISK-02)."""

import pytest

from risk.types import Returns
from risk.vol import rolling_vol


def returns(d):
    return Returns(
        base_date=d["base_date"],
        dates=tuple(d["dates"]),
        tickers=tuple(d["tickers"]),
        values={t: tuple(v) for t, v in d["values"].items()},
    )


@pytest.mark.intent
def test_tc05_sample_stdev_of_the_window_before_each_date(golden):
    inp, exp = golden("risk", "TC-05")
    v = rolling_vol(returns(inp["returns"]), inp["window"])
    assert v.window == exp["window"]
    assert v.annualized is exp["annualized"]
    for t, want in exp["values"].items():
        got = list(v.values[t])
        assert [g is None for g in got] == [w is None for w in want]
        assert [g for g in got if g is not None] == pytest.approx(
            [w for w in want if w is not None], abs=exp["tol"]
        )


@pytest.mark.intent
def test_window_below_two_is_rejected(golden):
    inp, _ = golden("risk", "TC-05")
    with pytest.raises(ValueError, match="window"):
        rolling_vol(returns(inp["returns"]), 1)
