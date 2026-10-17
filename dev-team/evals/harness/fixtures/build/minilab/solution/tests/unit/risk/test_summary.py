from risk.summary import summary_stats


def test_one_summary_per_ticker(contract_fake):
    v = contract_fake("risk.vol_series").vol_series()
    got = summary_stats(v)
    assert [s.ticker for s in got] == list(v.returns.tickers)
    assert all(s.ann_vol >= 0 for s in got)
