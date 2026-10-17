"""PL-02 smoke on the mdata.load_prices fake."""

import risk.vol_pipeline
from risk.types import VolSeries


def test_pl02_runs_end_to_end_on_the_fake(monkeypatch, contract_fake):
    monkeypatch.setattr(risk.vol_pipeline, "load_prices", contract_fake("mdata.load_prices").load_prices)
    v = risk.vol_pipeline.vol_series("unused.csv", window=2)
    assert isinstance(v, VolSeries)
    assert v.window == 2
