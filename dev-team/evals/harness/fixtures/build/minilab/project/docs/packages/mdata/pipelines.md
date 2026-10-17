# mdata — Pipelines

**Package:** mdata · **Status:** Approved · **Last updated:** 2026-10-17 · **Contract:** [contract.md](contract.md)

## PL-01: Load prices
**Entry:** `packages/mdata/src/mdata/pipeline.py::load_prices` · **Trigger:** called from Python (`mdata.load_prices`)
**Covers:** DATA-01–DATA-04, QR-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `read_csv` | mdata.io | path → RawRow | read every row | DATA-01 |
| 2 | `validate_rows` | mdata.validate | RawRow → RawRow | keep rows with a close, sorted | DATA-02 |
| 3 | `align_calendar` | mdata.calendar | RawRow → Prices | dates every ticker has, no fill | DATA-03, DATA-04 |

### Entry sketch (pre-build — removed by spine task)
```python
def load_prices(path, tickers=None) -> Prices:
    rows = read_csv(path)
    rows = validate_rows(rows, tickers)
    return align_calendar(rows)
```

## Planned layout (pre-build — removed by spine task)
```
packages/mdata/src/mdata/
  __init__.py   contract exports only
  types.py      RawRow, Prices, GapError
  io.py  validate.py  calendar.py  pipeline.py
tests/intent/mdata/  tests/unit/mdata/
```
