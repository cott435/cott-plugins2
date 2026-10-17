"""The grader's own run of the visible golden cases TC-01..TC-08 against a built project.

Reads the pristine cases from this fixture (never the run's copy, which a builder could have edited) and
calls each step through its owner module, the paths both plans freeze. grade_build.py runs it with the
built project's packages/*/src on sys.path and no project conftest.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib

import pytest

CASES = pathlib.Path(__file__).resolve().parents[1] / "project" / "tests" / "fixtures"


def case(pkg, tc):
    d = CASES / pkg / tc
    return json.loads((d / "input.json").read_text()), json.loads((d / "expected.json").read_text())


def tuples(m):
    return {k: tuple(v) for k, v in m.items()}


def returns(d):
    from risk.types import Returns
    return Returns(base_date=d["base_date"], dates=tuple(d["dates"]), tickers=tuple(d["tickers"]),
                   values=tuples(d["values"]))


def vol(d):
    from risk.types import VolSeries
    return VolSeries(returns=returns(d["returns"]), window=d["window"], annualized=d["annualized"],
                     values=tuples(d["values"]))


def same_series(got, want, tol):
    assert [g is None for g in got] == [w is None for w in want]
    assert [g for g in got if g is not None] == pytest.approx([w for w in want if w is not None], abs=tol)


def test_tc01():
    from mdata.types import RawRow
    from mdata.validate import validate_rows
    inp, exp = case("mdata", "TC-01")
    got = validate_rows([RawRow(*r) for r in inp["rows"]], inp["tickers"])
    assert [[r.date, r.ticker, r.close] for r in got] == exp["rows"]


def test_tc02():
    from mdata.calendar import align_calendar
    from mdata.types import RawRow
    inp, exp = case("mdata", "TC-02")
    p = align_calendar([RawRow(*r) for r in inp["rows"]], max_gap=inp["max_gap"])
    assert (list(p.dates), list(p.tickers)) == (exp["dates"], exp["tickers"])
    assert {t: list(c) for t, c in p.closes.items()} == exp["closes"]


def test_tc03():
    from mdata.calendar import align_calendar
    from mdata.types import GapError, RawRow
    inp, exp = case("mdata", "TC-03")
    with pytest.raises(GapError, match=exp["match"]):
        align_calendar([RawRow(*r) for r in inp["rows"]], max_gap=inp["max_gap"])


def test_tc04():
    from mdata.types import Prices
    from risk.returns import log_returns
    inp, exp = case("risk", "TC-04")
    p = inp["prices"]
    r = log_returns(Prices(dates=tuple(p["dates"]), tickers=tuple(p["tickers"]), closes=tuples(p["closes"])))
    assert (r.base_date, list(r.dates)) == (exp["base_date"], exp["dates"])
    for t in exp["tickers"]:
        assert list(r.values[t]) == pytest.approx(exp["values"][t], abs=exp["tol"])


def test_tc05():
    from risk.vol import rolling_vol
    inp, exp = case("risk", "TC-05")
    v = rolling_vol(returns(inp["returns"]), inp["window"])
    for t, want in exp["values"].items():
        same_series(list(v.values[t]), want, exp["tol"])


def test_tc06():
    from risk.annualize import annualize
    inp, exp = case("risk", "TC-06")
    v = annualize(vol(inp["vol"]))
    assert v.annualized is True
    for t, want in exp["values"].items():
        same_series(list(v.values[t]), want, exp["tol"])


def test_tc07():
    from risk.summary import summary_stats
    inp, exp = case("risk", "TC-07")
    got = {s.ticker: s for s in summary_stats(vol(inp["vol"]))}
    for want in exp["summary"]:
        for field in ("ann_return", "ann_vol", "sharpe", "last_vol"):
            assert getattr(got[want["ticker"]], field) == pytest.approx(want[field], abs=exp["tol"]), field


def test_tc08():
    from risk.drawdown import max_drawdown
    inp, exp = case("risk", "TC-08")
    got = {d.ticker: dataclasses.asdict(d) for d in max_drawdown(returns(inp["returns"]))}
    for want in exp["drawdowns"]:
        d = got[want["ticker"]]
        assert d["depth"] == pytest.approx(want["depth"], abs=exp["tol"])
        assert (d.get("peak_date"), d.get("trough_date")) == (want["peak_date"], want["trough_date"])
