"""M1 calendar thicken · TC-02 (DATA-03), TC-03 (DATA-04)."""

import pytest

from mdata.calendar import align_calendar
from mdata.types import GapError, RawRow


@pytest.mark.intent
def test_tc02_starts_when_every_ticker_trades_and_fills_gaps(golden):
    inp, exp = golden("mdata", "TC-02")
    p = align_calendar([RawRow(*r) for r in inp["rows"]], max_gap=inp["max_gap"])
    assert list(p.dates) == exp["dates"]
    assert list(p.tickers) == exp["tickers"]
    assert {t: list(c) for t, c in p.closes.items()} == exp["closes"]


@pytest.mark.intent
def test_tc03_six_missing_dates_is_a_gap_error(golden):
    inp, exp = golden("mdata", "TC-03")
    with pytest.raises(GapError, match=exp["match"]):
        align_calendar([RawRow(*r) for r in inp["rows"]], max_gap=inp["max_gap"])
