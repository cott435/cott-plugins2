# mdata — Tests

**Package:** mdata · **Status:** Approved · **Last updated:** 2026-10-17 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `pytest tests/unit/mdata/test_pl01_smoke.py` | read_csv, validate_rows, align_calendar | TC-01, TC-02, TC-03 | — |

### TC-01: Unusable rows and duplicates
**Pipeline:** PL-01 · **Covers:** DATA-02 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/mdata/TC-01/
**Source:** nine hand-made rows: a blank, a zero and a negative close, one repeated (date, ticker)
**Expected:** five rows, the later duplicate kept, sorted by date then ticker · **Tolerance:** exact

### TC-02: One calendar with filled gaps
**Pipeline:** PL-01 · **Covers:** DATA-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/mdata/TC-02/
**Source:** three tickers; C starts a day late, B misses two dates
**Expected:** four dates from C's first; B's gaps take its previous close · **Tolerance:** exact

### TC-03: A six-date gap
**Pipeline:** PL-01 · **Covers:** DATA-04 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/mdata/TC-03/
**Source:** B missing six dates in a row
**Expected:** `GapError` naming B · **Tolerance:** exact

## Open questions

## Retired
