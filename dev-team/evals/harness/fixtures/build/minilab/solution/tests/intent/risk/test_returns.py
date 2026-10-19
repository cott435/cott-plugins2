"""M1 log returns thicken · TC-04 (RISK-01)."""

import pytest

from mdata.types import Prices
from risk.returns import log_returns


@pytest.mark.intent
def test_tc04_geometric_closes_have_constant_log_returns(golden):
    inp, exp = golden("risk", "TC-04")
    p = inp["prices"]
    r = log_returns(
        Prices(
            dates=tuple(p["dates"]),
            tickers=tuple(p["tickers"]),
            closes={t: tuple(c) for t, c in p["closes"].items()},
        )
    )
    assert r.base_date == exp["base_date"]
    assert list(r.dates) == exp["dates"]
    for t in exp["tickers"]:
        assert list(r.values[t]) == pytest.approx(exp["values"][t], abs=exp["tol"])
