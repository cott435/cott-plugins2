"""mdata's boundary types: what PL-01 hands to the risk package."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RawRow:
    """One line of a prices CSV, as read."""

    date: str  # ISO yyyy-mm-dd
    ticker: str
    close: float | None  # None when the cell is blank


@dataclass(frozen=True)
class Prices:
    """Daily closes on one calendar, every ticker aligned to it."""

    dates: tuple[str, ...]  # ascending ISO dates
    tickers: tuple[str, ...]  # sorted
    closes: Mapping[str, tuple[float, ...]]  # ticker -> one close per date, gaps forward-filled


class GapError(ValueError):
    """A ticker is missing for more consecutive calendar dates than may be filled."""
