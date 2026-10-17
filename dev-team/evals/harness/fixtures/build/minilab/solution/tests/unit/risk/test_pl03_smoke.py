"""PL-03 smoke on the risk.vol_series fake."""

import json

import risk.report_pipeline


def test_pl03_runs_end_to_end_on_the_fake(monkeypatch, contract_fake, tmp_path):
    monkeypatch.setattr(risk.report_pipeline, "vol_series", contract_fake("risk.vol_series").vol_series)
    rep = risk.report_pipeline.risk_report("unused.csv", tmp_path / "r.json", window=2)
    assert [r["ticker"] for r in json.loads((tmp_path / "r.json").read_text())["tickers"]] == ["A", "B"]
    assert len(rep.rows) == 2
