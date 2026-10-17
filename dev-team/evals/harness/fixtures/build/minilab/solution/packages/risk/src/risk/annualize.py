"""PL-02 step 4: scale daily volatility to a year of trading days."""

from __future__ import annotations

import dataclasses
import math

from .types import VolSeries

PERIODS_PER_YEAR = 252  # trading days, not calendar days


def annualize(vol: VolSeries, periods_per_year: int = PERIODS_PER_YEAR) -> VolSeries:
    """Daily volatility times sqrt(periods_per_year); annualizing twice is a ValueError."""
    if vol.annualized:
        raise ValueError("already annualized")
    k = math.sqrt(periods_per_year)
    values = {t: tuple(None if v is None else v * k for v in s) for t, s in vol.values.items()}
    return dataclasses.replace(vol, annualized=True, values=values)
