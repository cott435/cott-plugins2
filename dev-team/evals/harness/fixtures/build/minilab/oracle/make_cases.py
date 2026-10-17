#!/usr/bin/env python3
"""Write minilab's golden cases (TC-01..TC-08) and hidden holdout cases (H-01..H-06): inputs and expected.json.

The expected values come from closed forms or from the definitions in docs/spec.md, computed here with
code of its own (no import from solution/, no `statistics`): a sample standard deviation is
sqrt(sum((x - mean)^2) / (n - 1)) with math.fsum, annualizing multiplies by sqrt(252) and 252, the
rolling window ends the day before. So a wrong belief shared by the solution and this script would need
the same mistake written twice in different code.

Usage:
  make_cases.py           rewrite every case
  make_cases.py --check   exit 1 if any case on disk differs from what this script computes
"""
from __future__ import annotations

import csv
import io
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
MINILAB = HERE.parent
TC_ROOT = MINILAB / "project" / "tests" / "fixtures"
HOLDOUT = MINILAB / "holdout" / "cases"
PPY = 252  # trading days per year (spec RISK-03)
TOL = 1e-12

DAYS = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09",
        "2024-01-10", "2024-01-11", "2024-01-12", "2024-01-16", "2024-01-17", "2024-01-18"]


def sd1(xs):
    """Sample standard deviation, n - 1 in the denominator (spec RISK-02)."""
    m = math.fsum(xs) / len(xs)
    return math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def trailing_vol(r, window):
    """Spec RISK-02: the value for date i uses r[i-window] .. r[i-1], never r[i]; None before that."""
    return [None if i < window else sd1(r[i - window:i]) for i in range(len(r))]


def logret(closes):
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]


def drawdown(base, dates, closes):
    """Spec RISK-05 on prices directly: wealth = close / first close; deepest close / running max - 1."""
    best, best_date = closes[0], base
    worst, peak_at, trough_at = 0.0, base, base
    for d, c in zip(dates, closes[1:]):
        if c > best:
            best, best_date = c, d
        dd = c / best - 1.0
        if dd < worst:
            worst, peak_at, trough_at = dd, best_date, d
    return worst, peak_at, trough_at


def summary(r, vol_values):
    m = math.fsum(r) / len(r)
    ann_r, ann_v = m * PPY, sd1(r) * math.sqrt(PPY)
    last = next((v for v in reversed(vol_values) if v is not None), None)
    return {"ann_return": ann_r, "ann_vol": ann_v, "sharpe": ann_r / ann_v if ann_v > 0 else 0.0, "last_vol": last}


# ---- golden cases -----------------------------------------------------------------------------------

def tc01():
    """DATA-02: drop blank and non-positive closes; the later duplicate wins; sort by (date, ticker)."""
    rows = [["2024-01-03", "B", 20.0], ["2024-01-02", "A", 10.0], ["2024-01-02", "B", 0.0],
            ["2024-01-03", "A", 10.5], ["2024-01-03", "A", 10.6], ["2024-01-04", "A", None],
            ["2024-01-04", "B", -1.0], ["2024-01-04", "B", 21.0], ["2024-01-02", "C", 5.0]]
    expected = [["2024-01-02", "A", 10.0], ["2024-01-02", "C", 5.0], ["2024-01-03", "A", 10.6],
                ["2024-01-03", "B", 20.0], ["2024-01-04", "B", 21.0]]
    return {"rows": rows, "tickers": None}, {"rows": expected}


def tc02():
    """DATA-03: the calendar starts on the first date every ticker has a close; gaps take the last close."""
    d = DAYS[:5]
    rows = [[x, "A", 10.0 + i] for i, x in enumerate(d)]
    rows += [[d[0], "B", 20.0], [d[1], "B", 21.0], [d[4], "B", 22.0]]          # B misses d2, d3
    rows += [[x, "C", 5.0] for x in d[1:]]                                       # C starts at d1
    rows.sort(key=lambda r: (r[0], r[1]))
    expected = {"dates": d[1:], "tickers": ["A", "B", "C"],
                "closes": {"A": [11.0, 12.0, 13.0, 14.0], "B": [21.0, 21.0, 21.0, 22.0], "C": [5.0] * 4}}
    return {"rows": rows, "max_gap": 5}, expected


def tc03():
    """DATA-04: six missing dates in a row is a GapError naming the ticker."""
    d = DAYS[:9]
    rows = [[x, "A", 10.0] for x in d] + [[d[0], "B", 20.0], [d[7], "B", 20.5], [d[8], "B", 21.0]]
    rows.sort(key=lambda r: (r[0], r[1]))
    return {"rows": rows, "max_gap": 5}, {"raises": "GapError", "match": "B"}


def tc04():
    """RISK-01: closes 100 * 1.01^t and 50 * 0.98^t have every log return ln(1.01) and ln(0.98)."""
    d = DAYS[:6]
    closes = {"X": [100 * 1.01 ** t for t in range(6)], "Y": [50 * 0.98 ** t for t in range(6)]}
    prices = {"dates": d, "tickers": ["X", "Y"], "closes": closes}
    expected = {"base_date": d[0], "dates": d[1:], "tickers": ["X", "Y"],
                "values": {"X": [math.log(1.01)] * 5, "Y": [math.log(0.98)] * 5}, "tol": TOL}
    return {"prices": prices}, expected


def returns_obj(dates, values):
    return {"base_date": DAYS[0], "dates": dates, "tickers": sorted(values), "values": values}


def tc05():
    """RISK-02: window 4, sample stdev of the four returns before each date."""
    x = [0.01, -0.01, 0.02, -0.02, 0.0, 0.03, -0.03, 0.05]
    y = [0.01] * 8
    rets = returns_obj(DAYS[1:9], {"X": x, "Y": y})
    expected = {"window": 4, "annualized": False,
                "values": {"X": trailing_vol(x, 4), "Y": trailing_vol(y, 4)}, "tol": TOL}
    return {"returns": rets, "window": 4}, expected


def tc06():
    """RISK-03: annualized = daily * sqrt(252)."""
    daily = {"X": [None, None, 0.01, 0.02, 0.015], "Y": [None, None, 0.0, 0.03, 0.005]}
    rets = returns_obj(DAYS[1:6], {"X": [0.0] * 5, "Y": [0.0] * 5})
    vol = {"returns": rets, "window": 2, "annualized": False, "values": daily}
    expected = {"annualized": True, "values": {t: [None if v is None else v * math.sqrt(PPY) for v in s]
                                               for t, s in daily.items()}, "tol": TOL}
    return {"vol": vol}, expected


def tc07():
    """RISK-04: mean * 252, sample stdev * sqrt(252), their ratio (0 when the vol is 0), the last vol."""
    x = [0.01, 0.02, -0.01, 0.005, 0.0, -0.015]
    y = [0.002] * 6
    rets = returns_obj(DAYS[1:7], {"X": x, "Y": y})
    vol_values = {"X": [None, None, 0.2, 0.25, 0.18, None], "Y": [None, None, 0.0, 0.0, 0.0, 0.0]}
    vol = {"returns": rets, "window": 2, "annualized": True, "values": vol_values}
    expected = {"summary": [dict(ticker=t, **summary(r, vol_values[t])) for t, r in (("X", x), ("Y", y))],
                "tol": 1e-9}
    return {"vol": vol}, expected


def tc08():
    """RISK-05: closes 100,110,99,88,95,120 fall 20% from the 110 peak to the 88 trough; a rising series has
    no drawdown (peak and trough at the base date); a first-day fall peaks at the base date."""
    paths = {"X": [100.0, 110.0, 99.0, 88.0, 95.0, 120.0], "Y": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
             "Z": [100.0, 90.0, 95.0, 99.0, 98.0, 101.0]}
    d = DAYS[:6]
    rets = {"base_date": d[0], "dates": d[1:], "tickers": sorted(paths),
            "values": {t: logret(c) for t, c in paths.items()}}
    exp = []
    for t in sorted(paths):
        depth, peak, trough = drawdown(d[0], d[1:], paths[t])
        exp.append({"ticker": t, "depth": depth, "peak_date": peak, "trough_date": trough})
    return {"returns": rets}, {"drawdowns": exp, "tol": 1e-12}


TCS = {"mdata": {"TC-01": tc01, "TC-02": tc02, "TC-03": tc03},
       "risk": {"TC-04": tc04, "TC-05": tc05, "TC-06": tc06, "TC-07": tc07, "TC-08": tc08}}


# ---- holdout: CSV in, public API out -------------------------------------------------------------------

def to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["date", "ticker", "close"])
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def series_rows(ticker, dates, closes):
    return [[d, ticker, c] for d, c in zip(dates, closes) if c is not None]


def report_rows(dates, paths, window):
    """What risk_report must write, from closes already on one calendar (no gaps beyond filled ones)."""
    out = []
    for t in sorted(paths):
        r = logret(paths[t])
        vol = [None if v is None else v * math.sqrt(PPY) for v in trailing_vol(r, window)]
        depth, peak, trough = drawdown(dates[0], dates[1:], paths[t])
        out.append(dict(ticker=t, **summary(r, vol), max_drawdown=depth, peak_date=peak, trough_date=trough))
    return out


def h01():
    """End to end: two tickers, B misses one date (filled with its last close), window 3."""
    d = DAYS[:10]
    a = [100.0, 101.0, 99.5, 102.0, 104.0, 103.0, 101.0, 105.0, 106.5, 104.0]
    b = [50.0, 49.0, 49.5, None, 51.0, 52.5, 50.0, 49.0, 50.5, 51.5]
    rows = series_rows("A", d, a) + series_rows("B", d, b)
    b_filled = [49.5 if c is None else c for c in b]
    return ({"csv": to_csv(rows), "call": "risk_report", "window": 3},
            {"rows": report_rows(d, {"A": a, "B": b_filled}, 3), "tol": 1e-9})


def h02():
    """No look-ahead: the last date's 50% jump must not be in that date's own volatility."""
    d = DAYS[:7]
    a = [100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 151.5]
    r = logret(a)
    vol = [None if v is None else v * math.sqrt(PPY) for v in trailing_vol(r, 3)]
    return ({"csv": to_csv(series_rows("A", d, a)), "call": "vol_series", "window": 3},
            {"values": {"A": vol}, "tol": 1e-12})


def h03():
    """Sample stdev: with window 2 the value is |r1 - r2| / sqrt(2), not |r1 - r2| / 2."""
    d = DAYS[:5]
    a = [100.0, 102.0, 100.0, 102.0, 100.0]
    r = logret(a)
    closed = [None, None] + [abs(r[i - 2] - r[i - 1]) / math.sqrt(2) * math.sqrt(PPY) for i in range(2, len(r))]
    return ({"csv": to_csv(series_rows("A", d, a)), "call": "vol_series", "window": 2},
            {"values": {"A": closed}, "tol": 1e-12})


def h04():
    """Trading-day year: ann_return = 252 * mean, ann_vol = sqrt(252) * sample stdev."""
    d = DAYS[:8]
    a = [100.0, 100.5, 101.5, 101.0, 102.5, 102.0, 103.0, 104.0]
    return ({"csv": to_csv(series_rows("A", d, a)), "call": "risk_report", "window": 2},
            {"rows": report_rows(d, {"A": a}, 2), "tol": 1e-9})


def h05():
    """load_prices: the later duplicate wins, unusable closes drop, a ticker filter keeps only those names,
    and asking for a ticker with no usable rows is a KeyError."""
    d = DAYS[:3]
    rows = [[d[0], "A", 10.0], [d[0], "B", 5.0], [d[1], "A", 11.0], [d[1], "A", 11.5], [d[1], "B", 0.0],
            [d[2], "A", 12.0], [d[2], "B", 6.0], [d[0], "Q", None], [d[1], "Q", -2.0]]
    expected = {"filtered": {"tickers": ["A"], "dates": d, "closes": {"A": [10.0, 11.5, 12.0]}},
                "all": {"tickers": ["A", "B"], "dates": d, "closes": {"A": [10.0, 11.5, 12.0], "B": [5.0, 5.0, 6.0]}},
                "unknown": {"tickers": ["Q"], "raises": "KeyError"}}
    return {"csv": to_csv(rows), "call": "load_prices"}, expected


def h06():
    """Gaps: five missing dates in a row are filled; six are a GapError."""
    d = DAYS[:9]
    five = [[x, "A", 10.0] for x in d[:8]] + [[d[0], "B", 20.0], [d[6], "B", 21.0], [d[7], "B", 22.0]]
    six = [[x, "A", 10.0] for x in d] + [[d[0], "B", 20.0], [d[7], "B", 21.0], [d[8], "B", 22.0]]
    return ({"csv": to_csv(five), "csv_six": to_csv(six), "call": "load_prices"},
            {"five": {"dates": d[:8], "closes": {"A": [10.0] * 8, "B": [20.0] * 6 + [21.0, 22.0]}},
             "six": {"raises": "GapError", "match": "B"}})


HOLDOUTS = {"H-01": h01, "H-02": h02, "H-03": h03, "H-04": h04, "H-05": h05, "H-06": h06}


def files():
    """Every case file this script owns: {path: text}."""
    out = {}
    for pkg, cases in TCS.items():
        for tc, fn in cases.items():
            inp, exp = fn()
            out[TC_ROOT / pkg / tc / "input.json"] = json.dumps(inp, indent=1) + "\n"
            out[TC_ROOT / pkg / tc / "expected.json"] = json.dumps(exp, indent=1) + "\n"
    for h, fn in HOLDOUTS.items():
        inp, exp = fn()
        for key in [k for k in inp if k.startswith("csv")]:
            out[HOLDOUT / h / f"{key.replace('csv', 'prices')}.csv"] = inp.pop(key)
        out[HOLDOUT / h / "params.json"] = json.dumps(inp, indent=1) + "\n"
        out[HOLDOUT / h / "expected.json"] = json.dumps(exp, indent=1) + "\n"
    return out


def main():
    check = "--check" in sys.argv
    bad = []
    for path, text in files().items():
        if check:
            if not path.exists() or path.read_text() != text:
                bad.append(str(path.relative_to(MINILAB)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if check:
        print("\n".join(f"differs: {b}" for b in bad) or "ok: every case matches the oracle")
        sys.exit(1 if bad else 0)
    print(f"wrote {len(files())} files")


if __name__ == "__main__":
    main()
