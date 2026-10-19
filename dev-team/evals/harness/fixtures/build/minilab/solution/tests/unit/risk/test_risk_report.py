"""risk_report on the real chain: the report it returns is the report it wrote."""

import json

from risk import risk_report


def test_risk_report_returns_what_it_wrote(tmp_path):
    closes = {"A": [100, 101, 99, 102, 104], "B": [50, 49, 50, 51, 52]}
    (tmp_path / "p.csv").write_text(
        "date,ticker,close\n"
        + "".join(
            f"2024-01-{d + 2:02d},{t},{c}\n" for t, cs in closes.items() for d, c in enumerate(cs)
        )
    )
    rep = risk_report(tmp_path / "p.csv", tmp_path / "r.json", window=2)
    assert rep.path == str(tmp_path / "r.json")
    assert json.loads((tmp_path / "r.json").read_text())["tickers"] == [dict(r) for r in rep.rows]
