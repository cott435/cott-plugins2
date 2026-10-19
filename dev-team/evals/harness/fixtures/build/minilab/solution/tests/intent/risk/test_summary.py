"""M1 summary thicken · TC-07 (RISK-04)."""

import pytest

from risk.summary import summary_stats
from risk.types import Returns, VolSeries


@pytest.mark.intent
def test_tc07_annualized_return_vol_sharpe_and_last_vol(golden):
    inp, exp = golden("risk", "TC-07")
    d = inp["vol"]
    r = d["returns"]
    rets = Returns(
        base_date=r["base_date"],
        dates=tuple(r["dates"]),
        tickers=tuple(r["tickers"]),
        values={t: tuple(v) for t, v in r["values"].items()},
    )
    v = VolSeries(
        returns=rets,
        window=d["window"],
        annualized=d["annualized"],
        values={t: tuple(x) for t, x in d["values"].items()},
    )
    got = {s.ticker: s for s in summary_stats(v)}
    for want in exp["summary"]:
        s = got[want["ticker"]]
        for field in ("ann_return", "ann_vol", "sharpe", "last_vol"):
            assert getattr(s, field) == pytest.approx(want[field], abs=exp["tol"]), field
