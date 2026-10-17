"""PL-03 step 4: write the risk report as JSON."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from pathlib import Path

from .types import Drawdown, Report, TickerSummary


def write_report(summary: Sequence[TickerSummary], drawdowns: Sequence[Drawdown], out_path: str | Path) -> Report:
    """One row per ticker, its summary then its drawdown (depth as max_drawdown), written as {"tickers": [...]}."""
    dd = {d.ticker: d for d in drawdowns}
    if set(dd) != {s.ticker for s in summary}:
        raise ValueError("summary and drawdowns cover different tickers")
    rows = []
    for s in sorted(summary, key=lambda s: s.ticker):
        row = dataclasses.asdict(s)
        fall = dataclasses.asdict(dd[s.ticker])
        del fall["ticker"]
        row["max_drawdown"] = fall.pop("depth")
        row.update(fall)
        rows.append(row)
    path = Path(out_path)
    path.write_text(json.dumps({"tickers": rows}, indent=1) + "\n", encoding="utf-8")
    return Report(path=str(path), rows=tuple(rows))
