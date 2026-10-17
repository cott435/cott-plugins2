"""M1 drawdown thicken · TC-08 (RISK-05)."""

import pytest
from risk.drawdown import max_drawdown
from risk.types import Returns


@pytest.mark.intent
def test_tc08_depth_with_peak_and_trough_dates(golden):
    inp, exp = golden("risk", "TC-08")
    r = inp["returns"]
    got = {d.ticker: d for d in max_drawdown(Returns(base_date=r["base_date"], dates=tuple(r["dates"]),
                                                     tickers=tuple(r["tickers"]),
                                                     values={t: tuple(v) for t, v in r["values"].items()}))}
    for want in exp["drawdowns"]:
        d = got[want["ticker"]]
        assert d.depth == pytest.approx(want["depth"], abs=exp["tol"])
        assert (d.peak_date, d.trough_date) == (want["peak_date"], want["trough_date"])
