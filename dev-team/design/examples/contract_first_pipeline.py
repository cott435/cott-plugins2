"""A contract-first pipeline in one file, labelled with the milestone shape build-planning plans.

PL-01 `ingest`: fetch daily bars -> clean -> validate -> write, rejects quarantined with a reason.
Each section names the task that builds it (build-planning's phase0.md):

    M1-T01  interface (solo, first)   record, protocols, step signatures, the provider fake, __main__
    M1-T02  spine  sources.StooqSource.fetch     each spine writes its owner module only
    M1-T03  spine  clean.dedupe, clean.by_day    steps sharing one module share one spine task
    M1-T04  spine  validate.*
    M1-T05  spine  sink.MemorySink.write
    M1-T06  wiring PL-01                         the entry function and its smoke test, on the fake
    M1-T07  thicken sources fetch: retries       after its step's spine, never needed by the wiring
    M1-T08  system (solo, last)                  swaps the fake for the real provider; golden case

The real file layout puts each part in its owner module; here they share one file, in task order.
Two rules the eval runs showed matter most (evals/results-iteration-b1/contract-first-gaps.html):
- A contract test checks shape and behaviour, never a temporary state ("still a stub").
- The fake and the real provider pass the same conformance cases, so the fake can't drift.

Run it: `python3 contract_first_pipeline.py` (stdlib only; `pytest` and `mypy --strict` also work).
"""
from __future__ import annotations

import csv
import io
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol, TypedDict

# ---- M1-T01 interface ---------------------------------------------------------------------------
# Freezes every boundary between tasks: the record, the step signatures, the provider fake.
# At this task each step body below was `raise NotImplementedError("<the task that replaces it>")`;
# the gate's stub rule (CR-02) allows that only while that task is open. No test checks a body.

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Bar:
    """One trading day for one symbol. Prices are split-adjusted, in `currency`; `day` is the
    exchange's session date (not UTC). The record states its meaning, not only its fields."""

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


class Transport(Protocol):
    """The provider boundary: the market-data service is outside the package, so this call gets
    the milestone's one fake. Raises KeyError naming the symbol when the provider has none."""

    def get_csv(self, symbol: str) -> str: ...


class Source(Protocol):
    """Returns only the requested symbols, days in [start, end]; KeyError names a missing symbol."""

    name: str

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]: ...


class Cleaner(Protocol):
    """Fixes or reshapes; never judges."""

    def __call__(self, bars: list[Bar]) -> list[Bar]: ...


class Validator(Protocol):
    """Judges only: the reason a bar is bad, or None. Never drops silently."""

    def __call__(self, bar: Bar) -> str | None: ...


class Sink(Protocol):
    """Keyed on (symbol, day, source): writing the same bar twice leaves one row."""

    def write(self, bars: list[Bar]) -> int: ...


class Config(TypedDict):
    sources: list[str]
    cleaners: list[str]
    validators: list[str]
    symbols: list[str]
    start: str
    end: str


@dataclass
class RunReport:
    written: int = 0
    rejects: list[Reject] = field(default_factory=list)
    failed_sources: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


# tests/contracts/sources.Transport/: the fixtures the fake serves (recorded provider responses).
FIXTURES = {
    "AAPL": "day,close,volume\n2026-10-12,231.5,5100\n2026-10-13,233.0,4800\n",
    "MSFT": "day,close,volume\n2026-10-12,412.1,3900\n",
}


class FakeTransport:
    """Serves the fixtures. The wiring's smoke test runs on it; the system task swaps it out."""

    def __init__(self, fixtures: dict[str, str] = FIXTURES):
        self.fixtures = fixtures

    def get_csv(self, symbol: str) -> str:
        if symbol not in self.fixtures:
            raise KeyError(symbol)
        return self.fixtures[symbol]


def transport_conformance(t: Transport) -> None:
    """The contract's cases. They run on the fake now and on the real provider at the system task,
    so the fake can't promise what the provider doesn't do. Shape and behaviour only."""
    text = t.get_csv("AAPL")
    assert next(csv.reader(io.StringIO(text))) == ["day", "close", "volume"]
    try:
        t.get_csv("NO-SUCH-SYMBOL")
    except KeyError as e:
        assert "NO-SUCH-SYMBOL" in str(e)
    else:
        raise AssertionError("an unknown symbol raises KeyError")


# ---- M1-T02 spine: sources.StooqSource.fetch (a library class row is a step) --------------------


class StooqSource:
    """Spine version: parse every row, keep the requested symbols and days. Adding a source is one
    more step like this one (its own spine task) plus one registry line in the wiring."""

    def __init__(self, transport: Transport, name: str = "stooq"):
        self.transport, self.name = transport, name

    def fetch(self, symbols: list[str], start: date, end: date) -> list[Bar]:
        bars = []
        for sym in symbols:
            for r in csv.DictReader(io.StringIO(self.transport.get_csv(sym))):
                d = date.fromisoformat(r["day"])
                if start <= d <= end:
                    bars.append(Bar(sym, d, float(r["close"]), int(r["volume"]), self.name))
        return bars


# ---- M1-T03 spine: clean.dedupe, clean.by_day (one module, one spine task) ----------------------


def dedupe(bars: list[Bar]) -> list[Bar]:
    """Last write wins per (symbol, day, source)."""
    return list({(b.symbol, b.day, b.source): b for b in bars}.values())


def by_day(bars: list[Bar]) -> list[Bar]:
    return sorted(bars, key=lambda b: (b.symbol, b.day, b.source))


# ---- M1-T04 spine: validate.positive_close, validate.no_negative_volume -------------------------


def positive_close(bar: Bar) -> str | None:
    return None if bar.close > 0 else f"close {bar.close} is not positive"


def no_negative_volume(bar: Bar) -> str | None:
    return None if bar.volume >= 0 else f"volume {bar.volume} is negative"


# ---- M1-T05 spine: sink.MemorySink.write ---------------------------------------------------------


class MemorySink:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, date, str], Bar] = {}

    def write(self, bars: list[Bar]) -> int:
        for b in bars:
            self.rows[(b.symbol, b.day, b.source)] = b
        return len(bars)


# ---- M1-T06 wiring PL-01: the entry function in the pipeline's own entry module ----------------
# Depends on the spines only (never a thicken), and calls the provider through whatever Transport
# it is given: the fake in its smoke test. Config names the parts; the registries build them.

SOURCES: dict[str, Callable[[Transport], Source]] = {"stooq": StooqSource}
CLEANERS: dict[str, Cleaner] = {"dedupe": dedupe, "by_day": by_day}
VALIDATORS: dict[str, Validator] = {"positive_close": positive_close, "no_negative_volume": no_negative_volume}


def ingest(config: Config, transport: Transport, sink: Sink, max_reject_share: float = 0.2) -> RunReport:
    report = RunReport()
    start, end = date.fromisoformat(config["start"]), date.fromisoformat(config["end"])
    bars: list[Bar] = []
    for name in config["sources"]:            # one failing source doesn't stop the others
        try:
            got = SOURCES[name](transport).fetch(config["symbols"], start, end)
        except Exception as e:                # noqa: BLE001 - recorded, never swallowed silently
            report.failed_sources[name] = f"{type(e).__name__}: {e}"
            continue
        report.counts[f"fetched:{name}"] = len(got)
        bars += got
    for c in config["cleaners"]:
        bars = CLEANERS[c](bars)
    report.counts["cleaned"] = len(bars)
    good: list[Bar] = []
    for bar in bars:
        reason = next((r for v in config["validators"] if (r := VALIDATORS[v](bar)) is not None), None)
        if reason is None:
            good.append(bar)
        else:
            report.rejects.append(Reject(bar, reason))   # quarantined with its reason
    if bars and len(report.rejects) / len(bars) > max_reject_share:
        raise RuntimeError(f"{len(report.rejects)} of {len(bars)} bars rejected: failing the batch")
    report.written = sink.write(good)
    return report


# ---- M1-T07 thicken: sources fetch retries -------------------------------------------------------
# Real behaviour behind the same protocol, after its step's spine. The entry function is untouched.


class Retrying:
    def __init__(self, inner: Transport, tries: int = 3, wait: float = 0.0):
        self.inner, self.tries, self.wait = inner, tries, wait

    def get_csv(self, symbol: str) -> str:
        for attempt in range(1, self.tries + 1):
            try:
                return self.inner.get_csv(symbol)
            except (ConnectionError, TimeoutError):
                if attempt == self.tries:
                    raise
                time.sleep(self.wait)
        raise AssertionError("unreachable")


# ---- M1-T08 system: the real provider swapped in; the golden case on the real chain -------------


class DirTransport:
    """The real provider: one `<symbol>.csv` per symbol under `root` (in production, HTTP)."""

    def __init__(self, root: Path):
        self.root = root

    def get_csv(self, symbol: str) -> str:
        path = self.root / f"{symbol}.csv"
        if not path.exists():
            raise KeyError(symbol)
        return path.read_text()


def real_transport(root: Path) -> Transport:
    return Retrying(DirTransport(root))


CONFIG: Config = {"sources": ["stooq"], "cleaners": ["dedupe", "by_day"],
                  "validators": ["positive_close", "no_negative_volume"], "symbols": ["AAPL", "MSFT"],
                  "start": "2026-10-12", "end": "2026-10-13"}


# ---- Tests: what each task's gate runs -----------------------------------------------------------

D1, D2 = date(2026, 10, 12), date(2026, 10, 13)


def provider_dump(root: Path) -> Path:
    """Stands in for the real provider's data in this offline example."""
    for sym, text in FIXTURES.items():
        (root / f"{sym}.csv").write_text(text)
    return root


def test_transport_conformance_fake() -> None:       # M1-T01
    transport_conformance(FakeTransport())


def test_stooq_spine_on_the_fake() -> None:          # M1-T02: the input sample gives a valid output
    bars = StooqSource(FakeTransport()).fetch(["AAPL"], D1, D2)
    assert bars and all(isinstance(b, Bar) and b.symbol == "AAPL" and D1 <= b.day <= D2 for b in bars)


def test_rejects_carry_a_reason() -> None:           # M1-T04
    assert positive_close(Bar("AAPL", D2, -1.0, 10, "stooq")) == "close -1.0 is not positive"
    assert positive_close(Bar("AAPL", D2, 1.0, 1, "stooq")) is None


def test_smoke_pl01() -> None:                       # M1-T06: runs end to end on the fake; shape only
    sink = MemorySink()
    report = ingest(CONFIG, FakeTransport(), sink)
    assert report.written == len(sink.rows) and not report.failed_sources


def test_a_failing_source_is_isolated() -> None:     # M1-T06
    report = ingest({**CONFIG, "symbols": ["AAPL", "NOPE"]}, FakeTransport(), MemorySink())
    assert "stooq" in report.failed_sources and report.written == 0


def test_retries_transient_errors() -> None:         # M1-T07
    class Flaky:
        calls = 0

        def get_csv(self, symbol: str) -> str:
            self.calls += 1
            if self.calls < 3:
                raise ConnectionError("reset")
            return FIXTURES[symbol]

    assert Retrying(Flaky()).get_csv("AAPL") == FIXTURES["AAPL"]


def test_system_real_provider() -> None:             # M1-T08: same cases, real chain, golden case
    with tempfile.TemporaryDirectory() as d:
        real = real_transport(provider_dump(Path(d)))
        transport_conformance(real)
        sink = MemorySink()
        ingest(CONFIG, real, sink)
        ingest(CONFIG, real, sink)                    # a rerun leaves the same rows
        # TC-01: its expected rows come from the fixture, not from this code
        assert sorted((s, day.isoformat(), b.close) for (s, day, _), b in sink.rows.items()) == [
            ("AAPL", "2026-10-12", 231.5), ("AAPL", "2026-10-13", 233.0), ("MSFT", "2026-10-12", 412.1)]


if __name__ == "__main__":                           # __main__ dispatch: the interface task's
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"pass  {name}")
    print(ingest(CONFIG, FakeTransport(), MemorySink()))
