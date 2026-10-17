"""Every frozen sample builds its type, and every fake serves a valid payload."""

from __future__ import annotations

import dataclasses

from mdata.types import Prices, RawRow
from risk.types import Drawdown, Report, Returns, TickerSummary, VolSeries


def test_raw_rows_sample(contract_sample):
    rows = [RawRow(*r) for r in contract_sample("mdata.RawRow")["rows"]]
    assert {r.ticker for r in rows} == {"A", "B"}


def test_prices_sample_is_aligned(contract_sample):
    p = Prices(**contract_sample("mdata.Prices"))
    assert all(len(p.closes[t]) == len(p.dates) for t in p.tickers)


def test_returns_sample_follows_prices(contract_sample):
    r = Returns(**contract_sample("risk.Returns"))
    assert all(len(r.values[t]) == len(r.dates) for t in r.tickers)
    assert r.base_date < r.dates[0]


def test_summary_and_drawdown_samples(contract_sample):
    names = {f.name for f in dataclasses.fields(Drawdown)}
    sample = contract_sample("risk.Drawdown")
    assert Drawdown(**{k: v for k, v in sample.items() if k in names}).depth <= 0
    assert TickerSummary(**contract_sample("risk.TickerSummary")).ann_vol > 0
    assert Report(**contract_sample("risk.Report")).rows


def test_load_prices_fake_serves_the_sample(contract_fake, contract_sample):
    p = contract_fake("mdata.load_prices").load_prices("any.csv")
    assert p.dates == tuple(contract_sample("mdata.Prices")["dates"])


def test_vol_series_fake_serves_the_sample(contract_fake):
    v = contract_fake("risk.vol_series").vol_series("any.csv")
    assert isinstance(v, VolSeries)
    assert all(len(v.values[t]) == len(v.returns.dates) for t in v.returns.tickers)
