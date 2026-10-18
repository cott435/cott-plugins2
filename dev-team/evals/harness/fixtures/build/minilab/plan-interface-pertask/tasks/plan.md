# M1: Risk report — Plan

**Milestone:** M1 · **Status:** Approved · **Base:** — · **Last updated:** 2026-10-17 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** `risk.risk_report` writes the report for a prices CSV; TC-01–TC-08 pass.
**Covers:** DATA-01–DATA-04, RISK-01–RISK-05, REP-01, QR-01 · **Deferred:** none

## Phase 0: Interface

### M1-T01: Freeze the M1 interfaces
**Package:** mdata · **Step:** contract · **Kind:** interface · **Size:** M · **Mode:** solo
**Read:** PL-01, PL-02, PL-03, mdata.RawRow, mdata.Prices, mdata.GapError, risk.Returns, risk.VolSeries, risk.TickerSummary, risk.Drawdown, risk.Report, mdata.load_prices, risk.vol_series
**Acceptance:**
- [ ] Boundary types in `mdata/types.py` and `risk/types.py`, one sample each under `tests/contracts/<pkg>.<Type>/`
- [ ] Every M1 step and entry signature in its owner module, body `raise NotImplementedError("<task>")` naming the task that replaces it
- [ ] `mdata.load_prices` and `risk.vol_series` fakes backed by the samples; `__init__` exports
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** packages/mdata/src/mdata/__init__.py, packages/mdata/src/mdata/types.py, packages/mdata/src/mdata/io.py, packages/mdata/src/mdata/validate.py, packages/mdata/src/mdata/calendar.py, packages/mdata/src/mdata/pipeline.py, packages/risk/src/risk/__init__.py, packages/risk/src/risk/types.py, packages/risk/src/risk/returns.py, packages/risk/src/risk/vol.py, packages/risk/src/risk/annualize.py, packages/risk/src/risk/summary.py, packages/risk/src/risk/drawdown.py, packages/risk/src/risk/report.py, packages/risk/src/risk/vol_pipeline.py, packages/risk/src/risk/report_pipeline.py, tests/contracts/**

### Checkpoint after M1-T01 (barrier)
- [ ] The interface code is the contract: types, signatures, stubs, samples, fakes and exports match contract.md, no more and no less
- [ ] Every split task's tester can write its tests from what is frozen
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 1: Step spines

### M1-T02: read_csv spine (read every row)
**Package:** mdata · **Step:** PL-01.read_csv · **Kind:** spine · **Covers:** DATA-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, mdata.read_csv, mdata.RawRow, DATA-01
**Acceptance:**
- [ ] `read_csv` returns valid output on a synthetic input (its spine version: read every row); signature unchanged
**Verify:** `pytest tests/unit/mdata/test_io.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/mdata/src/mdata/io.py, tests/unit/mdata/test_io.py

### Checkpoint after M1-T02
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T03: validate_rows spine (keep rows with a close, sorted)
**Package:** mdata · **Step:** PL-01.validate_rows · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-01, mdata.validate_rows, mdata.RawRow
**Acceptance:**
- [ ] `validate_rows` turns the mdata.RawRow sample into a valid output (its spine version: keep rows with a close, sorted); signature unchanged
**Verify:** `pytest tests/unit/mdata/test_validate.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/mdata/src/mdata/validate.py, tests/unit/mdata/test_validate.py

### Checkpoint after M1-T03
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T04: align_calendar spine (dates every ticker has, no fill)
**Package:** mdata · **Step:** PL-01.align_calendar · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-01, mdata.align_calendar, mdata.RawRow, mdata.Prices
**Acceptance:**
- [ ] `align_calendar` turns the mdata.RawRow sample into a valid output (its spine version: dates every ticker has, no fill); signature unchanged
**Verify:** `pytest tests/unit/mdata/test_calendar.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/mdata/src/mdata/calendar.py, tests/unit/mdata/test_calendar.py

### Checkpoint after M1-T04
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T05: log_returns spine (simple returns)
**Package:** risk · **Step:** PL-02.log_returns · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, risk.log_returns, mdata.Prices, risk.Returns
**Acceptance:**
- [ ] `log_returns` turns the mdata.Prices sample into a valid output (its spine version: simple returns); signature unchanged
**Verify:** `pytest tests/unit/risk/test_returns.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/returns.py, tests/unit/risk/test_returns.py

### Checkpoint after M1-T05
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T06: rolling_vol spine (expanding stdev of earlier returns)
**Package:** risk · **Step:** PL-02.rolling_vol · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, risk.rolling_vol, risk.Returns, risk.VolSeries
**Acceptance:**
- [ ] `rolling_vol` turns the risk.Returns sample into a valid output (its spine version: expanding stdev of earlier returns); signature unchanged
**Verify:** `pytest tests/unit/risk/test_vol.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/vol.py, tests/unit/risk/test_vol.py

### Checkpoint after M1-T06
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T07: annualize spine (daily values pass through)
**Package:** risk · **Step:** PL-02.annualize · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, risk.annualize, risk.VolSeries
**Acceptance:**
- [ ] `annualize` turns the risk.VolSeries sample into a valid output (its spine version: daily values pass through); signature unchanged
**Verify:** `pytest tests/unit/risk/test_annualize.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/annualize.py, tests/unit/risk/test_annualize.py

### Checkpoint after M1-T07
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T08: summary_stats spine (daily mean, stdev)
**Package:** risk · **Step:** PL-03.summary_stats · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-03, risk.summary_stats, risk.VolSeries, risk.TickerSummary
**Acceptance:**
- [ ] `summary_stats` turns the risk.VolSeries sample into a valid output (its spine version: daily mean, stdev); signature unchanged
**Verify:** `pytest tests/unit/risk/test_summary.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/summary.py, tests/unit/risk/test_summary.py

### Checkpoint after M1-T08
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T09: max_drawdown spine (depth only)
**Package:** risk · **Step:** PL-03.max_drawdown · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-03, risk.max_drawdown, risk.Returns, risk.Drawdown
**Acceptance:**
- [ ] `max_drawdown` turns the risk.Returns sample into a valid output (its spine version: depth only); signature unchanged
**Verify:** `pytest tests/unit/risk/test_drawdown.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/drawdown.py, tests/unit/risk/test_drawdown.py

### Checkpoint after M1-T09
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T10: write_report spine (JSON rows)
**Package:** risk · **Step:** PL-03.write_report · **Kind:** spine · **Covers:** REP-01 · **Size:** XS · **Mode:** solo
**Read:** PL-03, risk.write_report, risk.TickerSummary, risk.Drawdown, risk.Report, REP-01
**Acceptance:**
- [ ] `write_report` turns the risk.TickerSummary sample into a valid output (its spine version: JSON rows); signature unchanged
**Verify:** `pytest tests/unit/risk/test_report.py` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** packages/risk/src/risk/report.py, tests/unit/risk/test_report.py

### Checkpoint after M1-T10
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 2: Wiring

### M1-T11: Wire PL-01
**Package:** mdata · **Step:** PL-01 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-01, mdata.read_csv, mdata.validate_rows, mdata.align_calendar
**Acceptance:**
- [ ] `pytest tests/unit/mdata/test_pl01_smoke.py` runs PL-01 end to end
- [ ] PL-01 entry sketch replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/mdata/test_pl01_smoke.py` · `scripts/check.sh gate`
**Depends on:** M1-T02, M1-T03, M1-T04 · **Writes:** packages/mdata/src/mdata/pipeline.py, tests/unit/mdata/test_pl01_smoke.py

### Checkpoint after M1-T11
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T12: Wire PL-02 on the mdata.load_prices fake
**Package:** risk · **Step:** PL-02 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-02, risk.log_returns, risk.rolling_vol, risk.annualize, mdata.load_prices
**Acceptance:**
- [ ] `pytest tests/unit/risk/test_pl02_smoke.py` runs PL-02 end to end on the mdata.load_prices fake
- [ ] PL-02 entry sketch replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/risk/test_pl02_smoke.py` · `scripts/check.sh gate`
**Depends on:** M1-T05, M1-T06, M1-T07 · **Writes:** packages/risk/src/risk/vol_pipeline.py, tests/unit/risk/test_pl02_smoke.py

### Checkpoint after M1-T12
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T13: Wire PL-03 on the risk.vol_series fake
**Package:** risk · **Step:** PL-03 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-03, risk.summary_stats, risk.max_drawdown, risk.write_report, risk.vol_series
**Acceptance:**
- [ ] `pytest tests/unit/risk/test_pl03_smoke.py` runs PL-03 end to end on the risk.vol_series fake
- [ ] PL-03 entry sketch replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/risk/test_pl03_smoke.py` · `scripts/check.sh gate`
**Depends on:** M1-T08, M1-T09, M1-T10 · **Writes:** packages/risk/src/risk/report_pipeline.py, tests/unit/risk/test_pl03_smoke.py

### Checkpoint after M1-T13
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 2: Thicken

### M1-T14: Drop unusable rows, resolve duplicates
**Package:** mdata · **Step:** PL-01.validate_rows · **Kind:** thicken · **Covers:** DATA-02 · **Size:** S · **Mode:** split
**Read:** PL-01, mdata.validate_rows, mdata.RawRow, TC-01, DATA-02
**Acceptance:**
- [ ] TC-01 passes
- [ ] A requested ticker with no usable row is a `KeyError` naming it
**Verify:** `pytest tests/intent/mdata/test_validate.py tests/unit/mdata/test_validate.py` · `scripts/check.sh gate`
**Depends on:** M1-T03 · **Writes:** packages/mdata/src/mdata/validate.py, tests/intent/mdata/test_validate.py, tests/unit/mdata/test_validate.py

### Checkpoint after M1-T14
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T15: Forward fill with a gap limit
**Package:** mdata · **Step:** PL-01.align_calendar · **Kind:** thicken · **Covers:** DATA-03, DATA-04 · **Size:** S · **Mode:** split
**Read:** PL-01, mdata.align_calendar, mdata.RawRow, mdata.Prices, TC-02, TC-03, DATA-03, DATA-04
**Acceptance:**
- [ ] TC-02 and TC-03 pass
**Verify:** `pytest tests/intent/mdata/test_calendar.py tests/unit/mdata/test_calendar.py` · `scripts/check.sh gate`
**Depends on:** M1-T04 · **Writes:** packages/mdata/src/mdata/calendar.py, tests/intent/mdata/test_calendar.py, tests/unit/mdata/test_calendar.py

### Checkpoint after M1-T15
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T16: Log returns
**Package:** risk · **Step:** PL-02.log_returns · **Kind:** thicken · **Covers:** RISK-01 · **Size:** S · **Mode:** split
**Read:** PL-02, risk.log_returns, mdata.Prices, risk.Returns, TC-04, RISK-01
**Acceptance:**
- [ ] TC-04 passes within 1e-12
**Verify:** `pytest tests/intent/risk/test_returns.py tests/unit/risk/test_returns.py` · `scripts/check.sh gate`
**Depends on:** M1-T05 · **Writes:** packages/risk/src/risk/returns.py, tests/intent/risk/test_returns.py, tests/unit/risk/test_returns.py

### Checkpoint after M1-T16
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T17: Rolling volatility from earlier returns
**Package:** risk · **Step:** PL-02.rolling_vol · **Kind:** thicken · **Covers:** RISK-02 · **Size:** S · **Mode:** split
**Read:** PL-02, risk.rolling_vol, risk.Returns, risk.VolSeries, TC-05, RISK-02, RF-01
**Acceptance:**
- [ ] TC-05 passes within 1e-12
- [ ] A window below 2 is a `ValueError`
**Verify:** `pytest tests/intent/risk/test_vol.py tests/unit/risk/test_vol.py` · `scripts/check.sh gate`
**Depends on:** M1-T06 · **Writes:** packages/risk/src/risk/vol.py, tests/intent/risk/test_vol.py, tests/unit/risk/test_vol.py

### Checkpoint after M1-T17
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T18: Annualize over trading days
**Package:** risk · **Step:** PL-02.annualize · **Kind:** thicken · **Covers:** RISK-03 · **Size:** S · **Mode:** split
**Read:** PL-02, risk.annualize, risk.VolSeries, TC-06, RISK-03, RF-01
**Acceptance:**
- [ ] TC-06 passes within 1e-12
- [ ] Annualizing an annualized series is a `ValueError`
**Verify:** `pytest tests/intent/risk/test_annualize.py tests/unit/risk/test_annualize.py` · `scripts/check.sh gate`
**Depends on:** M1-T07 · **Writes:** packages/risk/src/risk/annualize.py, tests/intent/risk/test_annualize.py, tests/unit/risk/test_annualize.py

### Checkpoint after M1-T18
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T19: Annualized summary with Sharpe
**Package:** risk · **Step:** PL-03.summary_stats · **Kind:** thicken · **Covers:** RISK-04 · **Size:** S · **Mode:** split
**Read:** PL-03, risk.summary_stats, risk.VolSeries, risk.TickerSummary, TC-07, RISK-04, RF-01
**Acceptance:**
- [ ] TC-07 passes within 1e-9
**Verify:** `pytest tests/intent/risk/test_summary.py tests/unit/risk/test_summary.py` · `scripts/check.sh gate`
**Depends on:** M1-T08 · **Writes:** packages/risk/src/risk/summary.py, tests/intent/risk/test_summary.py, tests/unit/risk/test_summary.py

### Checkpoint after M1-T19
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T20: Drawdown with its dates
**Package:** risk · **Step:** PL-03.max_drawdown · **Kind:** thicken · **Covers:** RISK-05 · **Size:** S · **Mode:** split
**Read:** PL-03, risk.max_drawdown, risk.Returns, risk.Drawdown, TC-08, RISK-05, RF-01
**Acceptance:**
- [ ] TC-08 passes: depth within 1e-12, both dates exact
**Verify:** `pytest tests/intent/risk/test_drawdown.py tests/unit/risk/test_drawdown.py` · `scripts/check.sh gate`
**Depends on:** M1-T09 · **Writes:** packages/risk/src/risk/drawdown.py, tests/intent/risk/test_drawdown.py, tests/unit/risk/test_drawdown.py

### Checkpoint after M1-T20
- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 3: System

### M1-T21: Risk report on the real pipelines
**Package:** mdata · **Step:** PL-03 · **Kind:** system · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, PL-03, TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, mdata.load_prices, risk.vol_series, risk.risk_report
**Acceptance:**
- [ ] `risk.risk_report` runs PL-03 → PL-02 → PL-01 on a CSV with no fakes; the fakes are used only by smoke and contract tests
- [ ] All smoke tests and TC-01–TC-08 pass
**Verify:** `pytest tests/unit/mdata/test_pl01_smoke.py` · `pytest tests/unit/risk/test_pl02_smoke.py` · `pytest tests/unit/risk/test_pl03_smoke.py` · `pytest tests` · `scripts/check.sh full --exit`
**Depends on:** M1-T11, M1-T12, M1-T13, M1-T14, M1-T15, M1-T16, M1-T17, M1-T18, M1-T19, M1-T20 · **Writes:** packages/risk/src/risk/report_pipeline.py, tests/system/test_e2e.py, tests/unit/risk/test_risk_report.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass; no `NotImplementedError` stub is left (`scripts/check.sh full --exit`)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T03 validate_rows spine | M1-T02 read_csv spine | data | mdata.RawRow sample (M1-T01) |
| M1-T04 align_calendar spine | M1-T03 validate_rows spine | data | mdata.RawRow sample (M1-T01) |
| M1-T05 log_returns spine | M1-T04 align_calendar spine | data | mdata.Prices sample (M1-T01) |
| M1-T06 rolling_vol spine | M1-T05 log_returns spine | data | risk.Returns sample (M1-T01) |
| M1-T07 annualize spine | M1-T06 rolling_vol spine | data | risk.VolSeries sample (M1-T01) |
| M1-T08 summary_stats spine | M1-T07 annualize spine | data | risk.VolSeries sample (M1-T01) |
| M1-T09 max_drawdown spine | M1-T05 log_returns spine | data | risk.Returns sample (M1-T01) |
| M1-T10 write_report spine | M1-T08 summary_stats spine | data | risk.TickerSummary sample (M1-T01) |
| M1-T10 write_report spine | M1-T09 max_drawdown spine | data | risk.Drawdown sample (M1-T01) |
| M1-T11 wire PL-01 | M1-T02 read_csv spine | code | none: the smoke test runs the real read_csv |
| M1-T11 wire PL-01 | M1-T03 validate_rows spine | code | none: the smoke test runs the real validate_rows |
| M1-T11 wire PL-01 | M1-T04 align_calendar spine | code | none: the smoke test runs the real align_calendar |
| M1-T12 wire PL-02 | M1-T11 wire PL-01 | call | mdata.load_prices fake (M1-T01) |
| M1-T12 wire PL-02 | M1-T05 log_returns spine | code | none: the smoke test runs the real log_returns |
| M1-T12 wire PL-02 | M1-T06 rolling_vol spine | code | none: the smoke test runs the real rolling_vol |
| M1-T12 wire PL-02 | M1-T07 annualize spine | code | none: the smoke test runs the real annualize |
| M1-T13 wire PL-03 | M1-T12 wire PL-02 | call | risk.vol_series fake (M1-T01) |
| M1-T13 wire PL-03 | M1-T08 summary_stats spine | code | none: the smoke test runs the real summary_stats |
| M1-T13 wire PL-03 | M1-T09 max_drawdown spine | code | none: the smoke test runs the real max_drawdown |
| M1-T13 wire PL-03 | M1-T10 write_report spine | code | none: the smoke test runs the real write_report |
| M1-T14 drop unusable rows, resolve duplicates | M1-T03 validate_rows spine | code | none: thickens the same module |
| M1-T15 forward fill with a gap limit | M1-T04 align_calendar spine | code | none: thickens the same module |
| M1-T16 log returns | M1-T05 log_returns spine | code | none: thickens the same module |
| M1-T17 rolling volatility from earlier returns | M1-T06 rolling_vol spine | code | none: thickens the same module |
| M1-T18 annualize over trading days | M1-T07 annualize spine | code | none: thickens the same module |
| M1-T19 annualized summary with sharpe | M1-T08 summary_stats spine | code | none: thickens the same module |
| M1-T20 drawdown with its dates | M1-T09 max_drawdown spine | code | none: thickens the same module |
| M1-T21 system | M1-T11 wire PL-01 | code | none: runs the real pipeline end to end, no fakes |
| M1-T21 system | M1-T12 wire PL-02 | code | none: runs the real pipeline end to end, no fakes |
| M1-T21 system | M1-T13 wire PL-03 | code | none: runs the real pipeline end to end, no fakes |
| M1-T21 system | M1-T14 drop unusable rows, resolve duplicates | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T15 forward fill with a gap limit | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T16 log returns | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T17 rolling volatility from earlier returns | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T18 annualize over trading days | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T19 annualized summary with sharpe | order | none: the golden cases run on the finished steps |
| M1-T21 system | M1-T20 drawdown with its dates | order | none: the golden cases run on the finished steps |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| A frozen type misses a field a later step needs | a contract change mid-milestone | testers start on the interface and escalate as `contract-change` |

## Open questions

## Replan notes
