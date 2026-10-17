"""M1 annualize thicken · TC-06 (RISK-03)."""

import pytest
from risk.annualize import annualize
from risk.types import Returns, VolSeries


def vol(d):
    r = d["returns"]
    rets = Returns(base_date=r["base_date"], dates=tuple(r["dates"]), tickers=tuple(r["tickers"]),
                   values={t: tuple(v) for t, v in r["values"].items()})
    return VolSeries(returns=rets, window=d["window"], annualized=d["annualized"],
                     values={t: tuple(v) for t, v in d["values"].items()})


@pytest.mark.intent
def test_tc06_daily_vol_scales_by_root_252(golden):
    inp, exp = golden("risk", "TC-06")
    got = annualize(vol(inp["vol"]))
    assert got.annualized is exp["annualized"]
    for t, want in exp["values"].items():
        assert [g is None for g in got.values[t]] == [w is None for w in want]
        assert [g for g in got.values[t] if g is not None] == pytest.approx(
            [w for w in want if w is not None], abs=exp["tol"])


@pytest.mark.intent
def test_annualizing_twice_is_rejected(golden):
    inp, _ = golden("risk", "TC-06")
    with pytest.raises(ValueError, match="annualized"):
        annualize(annualize(vol(inp["vol"])))
