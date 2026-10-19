"""System: PL-03 on the real PL-02 on the real PL-01, no fakes."""

import json

from risk import risk_report


def test_report_end_to_end_on_a_csv(tmp_path):
    f = tmp_path / "p.csv"
    closes = {"A": [100, 101, 99, 102, 104, 103, 101], "B": [50, 49, 50, 51, 52, 50, 49]}
    f.write_text(
        "date,ticker,close\n"
        + "".join(
            f"2024-01-{d + 2:02d},{t},{c}\n" for t, cs in closes.items() for d, c in enumerate(cs)
        )
    )
    rep = risk_report(f, tmp_path / "r.json", window=3)
    rows = json.loads((tmp_path / "r.json").read_text())["tickers"]
    assert [r["ticker"] for r in rows] == ["A", "B"] == [r["ticker"] for r in rep.rows]
    assert all(r["max_drawdown"] <= 0 and r["ann_vol"] > 0 and "peak_date" in r for r in rows)
