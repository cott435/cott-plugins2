# mini — Tests

**Package:** mini · **Status:** Approved · **Last updated:** 2026-10-17 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m mini summarize --smoke` | summarize | TC-01 | — |

### TC-01: Mean of four numbers
**Pipeline:** PL-01 · **Covers:** SUM-02 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/mini/TC-01/
**Source:** arithmetic by hand: (1 + 2 + 3 + 4) ÷ 4
**Expected:** count 4, total 10, mean 2.5 · **Tolerance:** exact

## Open questions

## Retired
