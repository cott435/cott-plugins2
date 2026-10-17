from mdata.calendar import align_calendar
from mdata.types import RawRow


def test_every_ticker_has_one_close_per_date():
    rows = [RawRow(d, t, 1.0) for d in ("2024-01-02", "2024-01-03") for t in ("A", "B")]
    p = align_calendar(rows)
    assert p.dates == ("2024-01-02", "2024-01-03")
    assert p.tickers == ("A", "B")
    assert all(len(p.closes[t]) == 2 for t in p.tickers)
