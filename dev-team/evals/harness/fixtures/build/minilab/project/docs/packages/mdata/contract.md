# mdata — Contract

**Package:** mdata · **Status:** Approved · **Last updated:** 2026-10-17 · **Architecture:** [architecture.md](architecture.md)

## Types

### mdata.RawRow: One CSV row
**Kind:** type · **Sample:** `tests/contracts/mdata.RawRow/sample.json`
`@dataclass(frozen=True) class RawRow: date: str; ticker: str; close: float | None`
- **Invariants:** `date` is ISO `yyyy-mm-dd`; `close` is None for a blank cell
- **Used by:** PL-01

### mdata.Prices: Aligned daily closes
**Kind:** type · **Sample:** `tests/contracts/mdata.Prices/sample.json`
`@dataclass(frozen=True) class Prices: dates: tuple[str, ...]; tickers: tuple[str, ...]; closes: Mapping[str, tuple[float, ...]]`
- **Invariants:** dates ascending; tickers sorted; every ticker has one positive close per date
- **Used by:** PL-01, PL-02

### mdata.GapError: Gap too long to fill
**Kind:** type
`class GapError(ValueError)`
- **Used by:** PL-01

## Functions

### mdata.load_prices: Prices from a CSV
`def load_prices(path: str | Path, tickers: Sequence[str] | None = None) -> Prices`
- **Invariants:** DATA-01–DATA-04 hold for the result
- **Errors:** `KeyError` for a requested ticker with no usable row; `GapError` for a gap over 5 dates; `ValueError` for a malformed file
- **Boundary:** risk · **Fixtures:** tests/contracts/mdata.load_prices/ · **Cases:** two tickers over six dates
- **Used by:** risk; PL-01, PL-02

### mdata.read_csv: Read the rows
`def read_csv(path: str | Path) -> list[RawRow]`
- **Errors:** `ValueError` for a missing column or a malformed date
- **Used by:** PL-01

### mdata.validate_rows: Usable rows, sorted
`def validate_rows(rows: Sequence[RawRow], tickers: Sequence[str] | None = None) -> list[RawRow]`
- **Invariants:** positive closes only; one row per (date, ticker), the later one in file order; sorted by (date, ticker)
- **Errors:** `KeyError` for a requested ticker with no usable row
- **Used by:** PL-01

### mdata.align_calendar: One calendar
`def align_calendar(rows: Sequence[RawRow], *, max_gap: int = 5) -> Prices`
- **Invariants:** starts on the first date every ticker has a close; gaps take the previous close
- **Errors:** `GapError` naming the ticker when more than `max_gap` dates in a row are missing
- **Used by:** PL-01
