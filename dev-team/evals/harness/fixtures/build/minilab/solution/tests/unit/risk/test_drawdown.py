from risk.drawdown import max_drawdown
from risk.types import Returns


def test_depth_is_never_positive(contract_sample):
    s = contract_sample("risk.Returns")
    r = Returns(base_date=s["base_date"], dates=tuple(s["dates"]), tickers=tuple(s["tickers"]),
                values={t: tuple(v) for t, v in s["values"].items()})
    got = max_drawdown(r)
    assert [d.ticker for d in got] == ["A", "B"]
    assert all(d.depth <= 0 for d in got)
