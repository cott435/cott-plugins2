"""mdata's frozen samples build their types; the load_prices fake serves the Prices sample."""

from __future__ import annotations

from mdata.types import Prices, RawRow


def test_raw_rows_sample(contract_sample):
    rows = [RawRow(*r) for r in contract_sample("mdata.RawRow")["rows"]]
    assert {r.ticker for r in rows} == {"A", "B"}


def test_prices_sample_is_aligned(contract_sample):
    p = Prices(**contract_sample("mdata.Prices"))
    assert all(len(p.closes[t]) == len(p.dates) for t in p.tickers)


def test_load_prices_fake_serves_the_sample(contract_fake, contract_sample):
    p = contract_fake("mdata.load_prices").load_prices("any.csv")
    assert p.dates == tuple(contract_sample("mdata.Prices")["dates"])
