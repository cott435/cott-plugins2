"""PL-01 step 2: drop unusable rows, resolve duplicates, sort."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .types import RawRow


def validate_rows(rows: Sequence[RawRow], tickers: Sequence[str] | None = None) -> list[RawRow]:
    """Usable rows sorted by (date, ticker).

    A row without a positive, finite close is dropped. Of two rows for one (date, ticker) the later one in
    file order wins. With `tickers`, only those are kept, and one that has no usable row is a KeyError.
    """
    latest: dict[tuple[str, str], RawRow] = {}
    for r in rows:
        if r.close is None or not math.isfinite(r.close) or r.close <= 0:
            continue
        latest[(r.date, r.ticker)] = r
    kept = list(latest.values())
    if tickers is not None:
        have = {r.ticker for r in kept}
        unknown = sorted(set(tickers) - have)
        if unknown:
            raise KeyError(f"no usable prices for {', '.join(unknown)}")
        kept = [r for r in kept if r.ticker in set(tickers)]
    return sorted(kept, key=lambda r: (r.date, r.ticker))
