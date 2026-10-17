# M1: Risk report — Plan

**Milestone:** M1 · **Status:** Approved · **Base:** — · **Last updated:** 2026-10-17 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** `risk.risk_report` writes the report for a prices CSV; TC-01–TC-08 pass.
**Covers:** DATA-01–DATA-04, RISK-01–RISK-05, REP-01, QR-01 · **Deferred:** none

## Phase 0: Spine

### M1-T01: Freeze the mdata.load_prices contract
**Package:** mdata · **Step:** contract · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** mdata.load_prices, mdata.Prices
**Acceptance:**
- [ ] `mdata.Prices` as a frozen dataclass in `mdata/types.py`; the `tests/contracts/mdata.Prices/` sample builds it
- [ ] `risk`'s tests can load a fake `load_prices` from `tests/contracts/mdata.load_prices/` that serves the sample and nothing else
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate --pkg mdata`
**Depends on:** — · **Files likely:** packages/mdata/src/mdata/types.py, tests/contracts/mdata.load_prices/fake.py

### M1-T02: PL-01 spine on a synthetic CSV
**Package:** mdata · **Step:** PL-01 · **Covers:** DATA-01 · **Size:** M · **Mode:** solo
**Read:** PL-01, mdata.load_prices, mdata.read_csv, mdata.validate_rows, mdata.align_calendar, DATA-01
**Acceptance:**
- [ ] `pytest tests/unit/mdata/test_pl01_smoke.py` runs PL-01 end to end on a synthetic CSV, every step at its spine version; the output builds `mdata.Prices`
- [ ] PL-01 pre-build sections replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/mdata/test_pl01_smoke.py` · `scripts/check.sh gate --pkg mdata`
**Depends on:** M1-T01 · **Parallel:** G1 · **Files likely:** packages/mdata/src/mdata/__init__.py, packages/mdata/src/mdata/io.py, packages/mdata/src/mdata/validate.py, packages/mdata/src/mdata/calendar.py, packages/mdata/src/mdata/pipeline.py

### M1-T03: PL-02 spine against the load_prices fake
**Package:** risk · **Step:** PL-02 · **Covers:** — · **Size:** M · **Mode:** solo
**Read:** PL-02, mdata.load_prices, risk.vol_series, risk.log_returns, risk.rolling_vol, risk.annualize
**Acceptance:**
- [ ] `pytest tests/unit/risk/test_pl02_smoke.py` runs PL-02 end to end on the `mdata.load_prices` fake, every step at its spine version
- [ ] PL-02 pre-build sections replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/risk/test_pl02_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T01 · **Parallel:** G1 · **Files likely:** packages/risk/src/risk/types.py, packages/risk/src/risk/returns.py, packages/risk/src/risk/vol.py, packages/risk/src/risk/annualize.py, packages/risk/src/risk/vol_pipeline.py

### M1-T04: PL-03 spine on PL-02
**Package:** risk · **Step:** PL-03 · **Covers:** REP-01 · **Size:** M · **Mode:** solo
**Read:** PL-03, risk.risk_report, risk.summary_stats, risk.max_drawdown, risk.write_report, REP-01
**Acceptance:**
- [ ] `pytest tests/unit/risk/test_pl03_smoke.py` runs PL-03 end to end on PL-02 as built, every step at its spine version, and writes the JSON report
- [ ] PL-03 pre-build sections replaced by a `dt layout` pointer
**Verify:** `pytest tests/unit/risk/test_pl03_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T03 · **Files likely:** packages/risk/src/risk/summary.py, packages/risk/src/risk/drawdown.py, packages/risk/src/risk/report.py, packages/risk/src/risk/report_pipeline.py

### M1-T05: PL-02 on the real PL-01
**Package:** risk · **Step:** PL-02 · **Covers:** — · **Size:** S · **Mode:** solo
**Reason:** system spine: swaps the load_prices fake for the real PL-01
**Read:** PL-01, PL-02, PL-03, mdata.load_prices, risk.risk_report
**Acceptance:**
- [ ] `risk.risk_report` runs PL-03 → PL-02 → PL-01 on a CSV with the real `load_prices`; the fake is used only by smoke and contract tests
- [ ] The real `load_prices` output still builds the `tests/contracts/mdata.Prices/` sample's type
**Verify:** `pytest tests/unit/risk/test_pl02_smoke.py` · `pytest tests/unit/risk/test_pl03_smoke.py` · `pytest tests/system` · `scripts/check.sh gate --pkg mdata`
**Depends on:** M1-T02, M1-T04 · **Files likely:** packages/risk/src/risk/__init__.py, tests/system/test_e2e.py

### Checkpoint after M1-T05
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 1: Thicken

### M1-T06: Drop unusable rows, resolve duplicates
**Package:** mdata · **Step:** PL-01.validate_rows · **Covers:** DATA-02 · **Size:** S · **Mode:** split
**Read:** PL-01, TC-01, DATA-02, mdata.validate_rows
**Acceptance:**
- [ ] TC-01 passes
- [ ] A requested ticker with no usable row is a `KeyError` naming it
- [ ] PL-01 smoke test still passes
**Verify:** `pytest tests/intent/mdata tests/unit/mdata -k validate` · `pytest tests/unit/mdata/test_pl01_smoke.py` · `scripts/check.sh gate --pkg mdata`
**Depends on:** M1-T02 · **Parallel:** G2 · **Files likely:** packages/mdata/src/mdata/validate.py, tests/unit/mdata/test_validate.py

### M1-T07: Forward fill with a gap limit
**Package:** mdata · **Step:** PL-01.align_calendar · **Covers:** DATA-03, DATA-04 · **Size:** S · **Mode:** split
**Read:** PL-01, TC-02, TC-03, DATA-03, DATA-04, mdata.align_calendar
**Acceptance:**
- [ ] TC-02 and TC-03 pass
- [ ] PL-01 smoke test still passes
**Verify:** `pytest tests/intent/mdata tests/unit/mdata -k calendar` · `pytest tests/unit/mdata/test_pl01_smoke.py` · `scripts/check.sh gate --pkg mdata`
**Depends on:** M1-T02 · **Parallel:** G2 · **Files likely:** packages/mdata/src/mdata/calendar.py, tests/unit/mdata/test_calendar.py

### M1-T08: Log returns
**Package:** risk · **Step:** PL-02.log_returns · **Covers:** RISK-01 · **Size:** S · **Mode:** split
**Read:** PL-02, TC-04, RISK-01, risk.log_returns
**Acceptance:**
- [ ] TC-04 passes within 1e-12
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/risk tests/unit/risk -k returns` · `pytest tests/unit/risk/test_pl02_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T03 · **Parallel:** G2 · **Files likely:** packages/risk/src/risk/returns.py, tests/unit/risk/test_returns.py

### M1-T09: Rolling volatility from earlier returns
**Package:** risk · **Step:** PL-02.rolling_vol · **Covers:** RISK-02 · **Size:** S · **Mode:** split
**Read:** PL-02, TC-05, RISK-02, risk.rolling_vol, RF-01
**Acceptance:**
- [ ] TC-05 passes within 1e-12
- [ ] A window below 2 is a `ValueError`
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/risk tests/unit/risk -k vol` · `pytest tests/unit/risk/test_pl02_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T03 · **Parallel:** G2 · **Files likely:** packages/risk/src/risk/vol.py, tests/unit/risk/test_vol.py

### Checkpoint after M1-T09
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases of the finished tasks pass
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T10: Annualize over trading days
**Package:** risk · **Step:** PL-02.annualize · **Covers:** RISK-03 · **Size:** S · **Mode:** split
**Read:** PL-02, TC-06, RISK-03, risk.annualize, RF-01
**Acceptance:**
- [ ] TC-06 passes within 1e-12
- [ ] Annualizing an annualized series is a `ValueError`
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/risk tests/unit/risk -k annualize` · `pytest tests/unit/risk/test_pl02_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T03 · **Parallel:** G3 · **Files likely:** packages/risk/src/risk/annualize.py, tests/unit/risk/test_annualize.py

### M1-T11: Annualized summary with Sharpe
**Package:** risk · **Step:** PL-03.summary_stats · **Covers:** RISK-04 · **Size:** S · **Mode:** split
**Read:** PL-03, TC-07, RISK-04, risk.summary_stats, RF-01
**Acceptance:**
- [ ] TC-07 passes within 1e-9
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/risk tests/unit/risk -k summary` · `pytest tests/unit/risk/test_pl03_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T04 · **Parallel:** G3 · **Files likely:** packages/risk/src/risk/summary.py, tests/unit/risk/test_summary.py

### M1-T12: Drawdown with its dates
**Package:** risk · **Step:** PL-03.max_drawdown · **Covers:** RISK-05 · **Size:** S · **Mode:** split
**Read:** PL-03, TC-08, RISK-05, risk.max_drawdown, RF-01
**Acceptance:**
- [ ] TC-08 passes: depth within 1e-12, both dates exact
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/risk tests/unit/risk -k drawdown` · `pytest tests/unit/risk/test_pl03_smoke.py` · `scripts/check.sh gate --pkg risk`
**Depends on:** M1-T04 · **Parallel:** G3 · **Files likely:** packages/risk/src/risk/drawdown.py, tests/unit/risk/test_drawdown.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| The PL-02 spine is built on the load_prices fake | drift from the real PL-01 | M1-T05 swaps the fake for the real provider before thickening |

## Open questions

## Replan notes
