import pytest
from mdata.io import read_csv


def test_reads_rows_in_file_order_with_blank_as_none(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("date,ticker,close\n2024-01-03,B,2.5\n2024-01-02,A,\n")
    rows = read_csv(f)
    assert [(r.date, r.ticker, r.close) for r in rows] == [("2024-01-03", "B", 2.5), ("2024-01-02", "A", None)]


def test_missing_column_is_rejected(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("date,close\n2024-01-02,1\n")
    with pytest.raises(ValueError, match="ticker"):
        read_csv(f)
