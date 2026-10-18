"""A contract-first pipeline in one file: the shape build-planning cuts a milestone into.

Daily stock bars from several sources -> cleaners -> validators -> an idempotent sink, rejects
quarantined with a reason. Each section names the plan task that builds it:

    Kind: interface  the contracts (record, protocols), the fake, the conformance cases: frozen first
    Kind: spine      the orchestration over the protocols, run end to end on the fake
    Kind: wiring     a registry and config pick the real parts; the spine never changes
    Kind: thicken    retries, rate limits: wrappers over the same protocol

Two rules the eval runs showed matter most (evals/results-iteration-b1/contract-first-gaps.html):
- A contract test checks shape and behaviour, never a temporary state ("still a stub").
- The fake and every real source pass the same conformance cases, so a fake can't drift.

Run it: `python3 contract_first_pipeline.py` (stdlib only; `pytest` and `mypy --strict` also work).
"""
from __future__ import annotations

import csv
import io
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, TypedDict, runtime_checkable

# ---- Kind: interface (M1-T01) -------------------------------------------------------------------
# The canonical record states its meaning, not only its fields: one source's "close" must mean
# the same as another's.

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Bar:
    """One trading day for one symbol. Prices are split-adjusted, in `currency`; `day` is the
    exchange's session date (not UTC)."""

    symbol: str
    day: date
    close: float
    volume: int
    source: str
    currency: str = "USD"


@dataclass(frozen=True)
class Reject:
    bar: Bar
    reason: str


@runtime_checkable
class Source(Protocol):
    """Raises KeyError naming the symbol when the source has no data for it. Returns only the
    requested symbols, days in [start, end], in any order."""

    name: str

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]: ...


class Cleaner(Protocol):
    """Fixes or reshapes; never judges."""

    def __call__(self, bars: list[Bar]) -> list[Bar]: ...


class Validator(Protocol):
    """Judges only: returns the reason a bar is bad, or None. Never drops silently."""

    def __call__(self, bar: Bar) -> str | None: ...


class Sink(Protocol):
    """Keyed on (symbol, day, source): writing the same bar twice leaves one row."""

    def write(self, bars: list[Bar]) -> int: ...


class FakeSource:
    """The fake ships with the contract, so every later task can run before a real source exists."""

    def __init__(self, name: str, bars: Iterable[Bar]):
        self.name, self._bars = name, list(bars)

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]:
        known = {b.symbol for b in self._bars}
        for s in symbols:
            if s not in known:
                raise KeyError(s)
        return [b for b in self._bars if b.symbol in symbols and start <= b.day <= end]


def conformance_cases(source: Source, symbols: list[str], start: date, end: date) -> None:
    """The contract's cases. They run against the fake now and every real source later, so a fake
    can't promise behaviour the real code lacks (minilab's fake narrowed tickers; the real code
    didn't). Shape and behaviour only: nothing here asserts that code is unfinished."""
    bars = source.fetch(symbols, start, end)
    assert all(isinstance(b, Bar) for b in bars)
    assert {b.symbol for b in bars} <= set(symbols), "returns only the requested symbols"
    assert all(start <= b.day <= end for b in bars), "returns only days in range"
    assert all(b.source == source.name for b in bars)
    try:
        source.fetch(["NO-SUCH-SYMBOL"], start, end)
    except KeyError as e:
        assert "NO-SUCH-SYMBOL" in str(e)
    else:
        raise AssertionError("an unknown symbol raises KeyError")


# ---- Kind: spine (M1-T02) ----------------------------------------------------------------------
# Knows only the protocols. Adding a source, cleaner or validator never edits this function.


@dataclass
class RunReport:
    written: int = 0
    rejects: list[Reject] = field(default_factory=list)
    failed_sources: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


def run(sources: list[Source], cleaners: list[Cleaner], validators: list[Validator], sink: Sink,
        symbols: list[str], start: date, end: date, max_reject_share: float = 0.2) -> RunReport:
    report = RunReport()
    bars: list[Bar] = []
    for src in sources:                       # one failing source doesn't stop the others
        try:
            got = src.fetch(symbols, start, end)
        except Exception as e:                # noqa: BLE001 - recorded, never swallowed silently
            report.failed_sources[src.name] = f"{type(e).__name__}: {e}"
            continue
        report.counts[f"fetched:{src.name}"] = len(got)
        bars += got
    for clean in cleaners:
        bars = clean(bars)
    report.counts["cleaned"] = len(bars)
    good: list[Bar] = []
    for bar in bars:
        reason = next((r for v in validators if (r := v(bar)) is not None), None)
        if reason is None:
            good.append(bar)
        else:
            report.rejects.append(Reject(bar, reason))   # quarantined with its reason
    if bars and len(report.rejects) / len(bars) > max_reject_share:
        raise RuntimeError(f"{len(report.rejects)} of {len(bars)} bars rejected: failing the batch")
    report.written = sink.write(good)
    return report


# ---- Kind: thicken (later tasks, one per piece) -------------------------------------------------
# Real behaviour behind the same protocols. The spine above is untouched.


def dedupe(bars: list[Bar]) -> list[Bar]:
    """Last write wins per (symbol, day, source)."""
    return list({(b.symbol, b.day, b.source): b for b in bars}.values())


def by_day(bars: list[Bar]) -> list[Bar]:
    return sorted(bars, key=lambda b: (b.symbol, b.day, b.source))


def positive_close(bar: Bar) -> str | None:
    return None if bar.close > 0 else f"close {bar.close} is not positive"


def no_negative_volume(bar: Bar) -> str | None:
    return None if bar.volume >= 0 else f"volume {bar.volume} is negative"


class CsvSource:
    """A real source: parses `symbol,day,close,volume` text (in production, an HTTP response)."""

    def __init__(self, name: str, text: str):
        self.name, self._text = name, text

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]:
        rows = [Bar(r["symbol"], date.fromisoformat(r["day"]), float(r["close"]), int(r["volume"]), self.name)
                for r in csv.DictReader(io.StringIO(self._text))]
        missing = set(symbols) - {b.symbol for b in rows}
        if missing:
            raise KeyError(", ".join(sorted(missing)))
        return [b for b in rows if b.symbol in symbols and start <= b.day <= end]


class Retrying:
    """A wrapper with the same shape as Source: thickening without touching the spine."""

    def __init__(self, inner: Source, tries: int = 3, wait: float = 0.0):
        self.inner, self.tries, self.wait, self.name = inner, tries, wait, inner.name

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]:
        for attempt in range(1, self.tries + 1):
            try:
                return self.inner.fetch(symbols, start, end)
            except (ConnectionError, TimeoutError):
                if attempt == self.tries:
                    raise
                time.sleep(self.wait)
        raise AssertionError("unreachable")


class MemorySink:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, date, str], Bar] = {}

    def write(self, bars: list[Bar]) -> int:
        for b in bars:
            self.rows[(b.symbol, b.day, b.source)] = b
        return len(bars)


# ---- Kind: wiring (one task per pipeline) --------------------------------------------------------
# Config names the parts; a registry builds them. A new source is one class plus one config line.

STOOQ_CSV = "symbol,day,close,volume\nAAPL,2026-10-12,231.5,5100\nAAPL,2026-10-13,233.0,4800\nMSFT,2026-10-12,412.1,3900\n"

SOURCES: dict[str, Callable[[], Source]] = {
    "stooq": lambda: Retrying(CsvSource("stooq", STOOQ_CSV)),
}
CLEANERS: dict[str, Cleaner] = {"dedupe": dedupe, "by_day": by_day}
VALIDATORS: dict[str, Validator] = {"positive_close": positive_close, "no_negative_volume": no_negative_volume}

class Config(TypedDict):
    sources: list[str]
    cleaners: list[str]
    validators: list[str]
    symbols: list[str]
    start: str
    end: str


CONFIG: Config = {"sources": ["stooq"], "cleaners": ["dedupe", "by_day"],
          "validators": ["positive_close", "no_negative_volume"], "symbols": ["AAPL", "MSFT"],
          "start": "2026-10-12", "end": "2026-10-13"}


def build_and_run(config: Config, sink: Sink) -> RunReport:
    sources = [SOURCES[name]() for name in config["sources"]]
    for s in sources:                         # a cheap start-up check: names only, not behaviour
        assert isinstance(s, Source), f"{s!r} doesn't look like a Source"
    return run(sources, [CLEANERS[c] for c in config["cleaners"]],
               [VALIDATORS[v] for v in config["validators"]], sink, config["symbols"],
               date.fromisoformat(config["start"]), date.fromisoformat(config["end"]))


# ---- Tests: what each task's gate runs -----------------------------------------------------------

D1, D2 = date(2026, 10, 12), date(2026, 10, 13)
FAKE_BARS = [Bar("AAPL", D1, 231.5, 5100, "fake"), Bar("AAPL", D2, 233.0, 4800, "fake"),
             Bar("MSFT", D1, 412.1, 3900, "fake")]


def test_conformance_fake() -> None:          # interface task
    conformance_cases(FakeSource("fake", FAKE_BARS), ["AAPL"], D1, D2)


def test_conformance_real() -> None:          # the real source's task: the same cases
    conformance_cases(CsvSource("stooq", STOOQ_CSV), ["AAPL"], D1, D2)


def test_spine_end_to_end_on_the_fake() -> None:   # spine task: runs and output shape, no values
    sink = MemorySink()
    report = run([FakeSource("fake", FAKE_BARS)], [], [], sink, ["AAPL", "MSFT"], D1, D2)
    assert report.written == len(sink.rows) and not report.rejects


def test_a_failing_source_is_isolated() -> None:
    class Down:
        name = "down"

        def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]:
            raise ConnectionError("timeout")

    report = run([Down(), FakeSource("fake", FAKE_BARS)], [], [], MemorySink(), ["AAPL"], D1, D2)
    assert "down" in report.failed_sources and report.written == 2


def test_rejects_are_quarantined_with_a_reason() -> None:
    bad = Bar("AAPL", D2, -1.0, 10, "fake")
    report = run([FakeSource("fake", FAKE_BARS + [bad])], [], [positive_close], MemorySink(), ["AAPL"], D1, D2,
                 max_reject_share=0.5)
    assert report.rejects == [Reject(bad, "close -1.0 is not positive")]


def test_rerun_is_idempotent() -> None:       # wiring task
    sink = MemorySink()
    build_and_run(CONFIG, sink)
    first = dict(sink.rows)
    build_and_run(CONFIG, sink)
    assert sink.rows == first


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"pass  {name}")
    print(build_and_run(CONFIG, MemorySink()))
