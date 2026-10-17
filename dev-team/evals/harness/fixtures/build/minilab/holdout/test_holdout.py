"""Hidden golden cases H-01..H-06, run after the build against the public API only:
mdata.load_prices, risk.vol_series, risk.risk_report. Never shown to an agent.
"""
from __future__ import annotations

import json
import pathlib

import pytest

CASES = pathlib.Path(__file__).resolve().parent / "cases"


def case(h):
    d = CASES / h
    return d, json.loads((d / "params.json").read_text()), json.loads((d / "expected.json").read_text())


def same_series(got, want, tol):
    assert [g is None for g in got] == [w is None for w in want]
    assert [g for g in got if g is not None] == pytest.approx([w for w in want if w is not None], abs=tol)


def check_report(h, tmp_path):
    from risk import risk_report
    d, params, exp = case(h)
    risk_report(d / "prices.csv", tmp_path / "report.json", window=params["window"])
    rows = json.loads((tmp_path / "report.json").read_text())["tickers"]
    assert [r["ticker"] for r in rows] == [r["ticker"] for r in exp["rows"]]
    for got, want in zip(rows, exp["rows"]):
        for k, v in want.items():
            if isinstance(v, float):
                assert got.get(k) == pytest.approx(v, abs=exp["tol"]), k
            else:
                assert got.get(k) == v, k


def check_vol(h):
    from risk import vol_series
    d, params, exp = case(h)
    v = vol_series(d / "prices.csv", window=params["window"])
    for t, want in exp["values"].items():
        same_series(list(v.values[t]), want, exp["tol"])


def test_h01_report_end_to_end(tmp_path):
    check_report("H-01", tmp_path)


def test_h02_no_look_ahead():
    check_vol("H-02")


def test_h03_sample_stdev():
    check_vol("H-03")


def test_h04_trading_day_year(tmp_path):
    check_report("H-04", tmp_path)


def test_h05_load_prices_cleaning():
    from mdata import load_prices
    d, _, exp = case("H-05")
    for key in ("filtered", "all"):
        want = exp[key]
        p = load_prices(d / "prices.csv", want["tickers"] if key == "filtered" else None)
        assert (list(p.tickers), list(p.dates)) == (want["tickers"], want["dates"])
        assert {t: list(c) for t, c in p.closes.items()} == want["closes"]
    with pytest.raises(KeyError):
        load_prices(d / "prices.csv", exp["unknown"]["tickers"])


def test_h06_gap_limit():
    from mdata import GapError, load_prices
    d, _, exp = case("H-06")
    p = load_prices(d / "prices.csv")
    assert list(p.dates) == exp["five"]["dates"]
    assert {t: list(c) for t, c in p.closes.items()} == exp["five"]["closes"]
    with pytest.raises(GapError, match=exp["six"]["match"]):
        load_prices(d / "prices_six.csv")
