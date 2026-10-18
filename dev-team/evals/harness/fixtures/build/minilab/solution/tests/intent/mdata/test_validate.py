"""M1 validate thicken · TC-01 (DATA-02)."""

import pytest

from mdata.types import RawRow
from mdata.validate import validate_rows


@pytest.mark.intent
def test_tc01_drops_unusable_rows_keeps_last_duplicate_and_sorts(golden):
    inp, exp = golden("mdata", "TC-01")
    rows = [RawRow(*r) for r in inp["rows"]]
    got = validate_rows(rows, inp["tickers"])
    assert [[r.date, r.ticker, r.close] for r in got] == exp["rows"]


@pytest.mark.intent
def test_unknown_ticker_is_a_key_error(golden):
    inp, _ = golden("mdata", "TC-01")
    with pytest.raises(KeyError, match="ZZZ"):
        validate_rows([RawRow(*r) for r in inp["rows"]], ["A", "ZZZ"])
