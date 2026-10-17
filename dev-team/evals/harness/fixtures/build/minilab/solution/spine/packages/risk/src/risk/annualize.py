"""PL-02 step 4 (spine): daily values pass through."""

from __future__ import annotations

from .types import VolSeries

PERIODS_PER_YEAR = 252


def annualize(vol: VolSeries, periods_per_year: int = PERIODS_PER_YEAR) -> VolSeries:
    """Returns `vol` unchanged (still daily) until annualizing is built."""
    return vol
