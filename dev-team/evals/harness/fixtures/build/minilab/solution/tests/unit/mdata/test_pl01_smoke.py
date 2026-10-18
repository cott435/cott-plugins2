"""PL-01 smoke: a synthetic CSV end to end."""

from mdata import Prices, load_prices


def test_pl01_runs_end_to_end(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(
        "date,ticker,close\n"
        + "".join(f"2024-01-0{d},{t},{10 + d}\n" for d in range(2, 7) for t in "AB")
    )
    p = load_prices(f)
    assert isinstance(p, Prices)
    assert len(p.dates) == 5
    assert p.tickers == ("A", "B")
