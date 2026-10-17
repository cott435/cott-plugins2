"""risk's frozen samples build their types; the vol_series fake serves the VolSeries sample."""

from __future__ import annotations

import dataclasses

from risk.types import Drawdown, Report, Returns, TickerSummary, VolSeries


def test_returns_sample_follows_prices(contract_sample):
    r = Returns(**contract_sample("risk.Returns"))
    assert all(len(r.values[t]) == len(r.dates) for t in r.tickers)
    assert r.base_date < r.dates[0]


def test_summary_drawdown_and_report_samples(contract_sample):
    names = {f.name for f in dataclasses.fields(Drawdown)}
    sample = contract_sample("risk.Drawdown")
    assert set(sample) == names
    assert Drawdown(**sample).depth <= 0
    assert TickerSummary(**contract_sample("risk.TickerSummary")).ann_vol > 0
    assert Report(**contract_sample("risk.Report")).rows


def test_vol_series_fake_serves_the_sample(contract_fake):
    v = contract_fake("risk.vol_series").vol_series("any.csv")
    assert isinstance(v, VolSeries)
    assert all(len(v.values[t]) == len(v.returns.dates) for t in v.returns.tickers)
