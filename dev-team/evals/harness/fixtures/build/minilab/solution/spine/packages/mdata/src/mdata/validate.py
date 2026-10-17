"""PL-01 step 2 (spine): keep every row with a close, sorted."""

from __future__ import annotations

from collections.abc import Sequence

from .types import RawRow


def validate_rows(rows: Sequence[RawRow], tickers: Sequence[str] | None = None) -> list[RawRow]:
    """Rows with a close, sorted by (date, ticker); no duplicate or price checks yet."""
    kept = [r for r in rows if r.close is not None and (tickers is None or r.ticker in tickers)]
    return sorted(kept, key=lambda r: (r.date, r.ticker))
