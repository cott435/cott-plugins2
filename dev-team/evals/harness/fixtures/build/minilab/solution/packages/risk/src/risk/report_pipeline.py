"""PL-03 Risk report: the entry function."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .drawdown import max_drawdown
from .report import write_report
from .summary import summary_stats
from .types import Report
from .vol_pipeline import vol_series


def risk_report(path: str | Path, out_path: str | Path, *, window: int = 20,
                tickers: Sequence[str] | None = None) -> Report:
    """Per-ticker return, volatility, Sharpe and drawdown of a prices CSV, written to `out_path`."""
    vol = vol_series(path, window=window, tickers=tickers)
    summary = summary_stats(vol)
    drawdowns = max_drawdown(vol.returns)
    return write_report(summary, drawdowns, out_path)
