"""Fake mdata.load_prices for consumers built before PL-01: serves the mdata.Prices sample, nothing else."""

from __future__ import annotations

import json
from pathlib import Path

from mdata.types import Prices

SAMPLE = Path(__file__).resolve().parent.parent / "mdata.Prices" / "sample.json"


def load_prices(path: object = None, tickers: object = None) -> Prices:
    data = json.loads(SAMPLE.read_text())
    names = tuple(tickers) if tickers else tuple(data["tickers"])
    return Prices(
        dates=tuple(data["dates"]),
        tickers=names,
        closes={t: tuple(data["closes"][t]) for t in names},
    )
