"""Fake risk.vol_series for PL-03 built before PL-02: serves the risk.VolSeries sample, nothing else."""

from __future__ import annotations

import json
from pathlib import Path

from risk.types import Returns, VolSeries

SAMPLE = Path(__file__).resolve().parent.parent / "risk.VolSeries" / "sample.json"


def vol_series(path: object = None, *, window: int = 2, tickers: object = None) -> VolSeries:
    data = json.loads(SAMPLE.read_text())
    r = data["returns"]
    returns = Returns(
        base_date=r["base_date"],
        dates=tuple(r["dates"]),
        tickers=tuple(r["tickers"]),
        values={t: tuple(v) for t, v in r["values"].items()},
    )
    return VolSeries(
        returns=returns,
        window=data["window"],
        annualized=data["annualized"],
        values={t: tuple(v) for t, v in data["values"].items()},
    )
