from mdata.types import RawRow
from mdata.validate import validate_rows


def test_output_is_sorted_by_date_then_ticker():
    rows = [RawRow("2024-01-03", "A", 1.0), RawRow("2024-01-02", "B", 2.0), RawRow("2024-01-02", "A", 3.0)]
    got = validate_rows(rows)
    assert [(r.date, r.ticker) for r in got] == [("2024-01-02", "A"), ("2024-01-02", "B"), ("2024-01-03", "A")]


def test_rows_without_a_close_are_dropped():
    assert validate_rows([RawRow("2024-01-02", "A", None)]) == []
