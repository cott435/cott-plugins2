"""risk's boundary types: what each step of PL-02 and PL-03 hands to the next."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Returns:
    """Daily log returns; `dates[i]` is the later date of the pair."""

    base_date: str  # the first price date, before dates[0]
    dates: tuple[str, ...]
    tickers: tuple[str, ...]
    values: Mapping[str, tuple[float, ...]]


@dataclass(frozen=True)
class VolSeries:
    """Rolling volatility per ticker, aligned to `returns.dates`."""

    returns: Returns
    window: int
    annualized: bool
    values: Mapping[str, tuple[float | None, ...]]  # None until `window` earlier returns exist


@dataclass(frozen=True)
class TickerSummary:
    """Whole-period statistics of one ticker."""

    ticker: str
    ann_return: float
    ann_vol: float
    sharpe: float
    last_vol: float | None  # the last rolling value of the VolSeries


@dataclass(frozen=True)
class Drawdown:
    """The worst fall from a running peak of one ticker's wealth path."""

    ticker: str
    depth: float  # <= 0: trough / peak - 1
    peak_date: str
    trough_date: str = ""  # contract-change: RISK-05 needs the trough's date


@dataclass(frozen=True)
class Report:
    """The written risk report."""

    path: str
    rows: tuple[Mapping[str, object], ...]  # one per ticker, sorted by ticker
