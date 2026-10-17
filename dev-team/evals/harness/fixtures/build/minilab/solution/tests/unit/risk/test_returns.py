from mdata.types import Prices
from risk.returns import log_returns


def test_one_return_per_pair_of_dates(contract_sample):
    p = contract_sample("mdata.Prices")
    r = log_returns(Prices(dates=tuple(p["dates"]), tickers=tuple(p["tickers"]),
                           closes={t: tuple(c) for t, c in p["closes"].items()}))
    assert r.base_date == p["dates"][0]
    assert r.dates == tuple(p["dates"][1:])
    assert all(len(r.values[t]) == len(r.dates) for t in r.tickers)
