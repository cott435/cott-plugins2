import json

from risk.report import write_report
from risk.types import Drawdown, TickerSummary


def test_writes_one_row_per_ticker(tmp_path):
    s = [TickerSummary("B", 0.1, 0.2, 0.5, None), TickerSummary("A", 0.2, 0.1, 2.0, 0.1)]
    d = [Drawdown("A", -0.1, "2024-01-02"), Drawdown("B", 0.0, "2024-01-02")]
    rep = write_report(s, d, tmp_path / "r.json")
    on_disk = json.loads((tmp_path / "r.json").read_text())["tickers"]
    assert [r["ticker"] for r in on_disk] == ["A", "B"] == [r["ticker"] for r in rep.rows]
    assert on_disk[0]["max_drawdown"] == -0.1
