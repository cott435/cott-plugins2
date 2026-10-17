"""PL-01 Load prices: the entry function."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .calendar import align_calendar
from .io import read_csv
from .types import Prices
from .validate import validate_rows


def load_prices(path: str | Path, tickers: Sequence[str] | None = None) -> Prices:
    """Daily closes from a prices CSV, cleaned and on one calendar."""
    rows = read_csv(path)
    rows = validate_rows(rows, tickers)
    return align_calendar(rows)
