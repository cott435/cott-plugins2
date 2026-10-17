"""PL-01 step 1: read a prices CSV."""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

from .types import RawRow

COLUMNS = ("date", "ticker", "close")


def read_csv(path: str | Path) -> list[RawRow]:
    """Rows of a `date,ticker,close` CSV in file order; a blank close is None."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(missing)}")
        rows = []
        for line in reader:
            date = line["date"].strip()
            datetime.date.fromisoformat(date)  # ValueError on a malformed date
            cell = (line["close"] or "").strip()
            rows.append(RawRow(date=date, ticker=line["ticker"].strip(), close=float(cell) if cell else None))
    return rows
