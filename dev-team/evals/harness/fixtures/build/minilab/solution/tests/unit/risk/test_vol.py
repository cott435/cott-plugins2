from risk.types import Returns
from risk.vol import rolling_vol


def test_vol_is_aligned_to_returns(contract_sample):
    s = contract_sample("risk.Returns")
    r = Returns(
        base_date=s["base_date"],
        dates=tuple(s["dates"]),
        tickers=tuple(s["tickers"]),
        values={t: tuple(v) for t, v in s["values"].items()},
    )
    v = rolling_vol(r, 2)
    assert v.window == 2
    assert not v.annualized
    assert all(len(v.values[t]) == len(r.dates) for t in r.tickers)
    assert v.values["A"][0] is None
