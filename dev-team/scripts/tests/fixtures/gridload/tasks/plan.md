# M1: Ingest + seasonality — Plan

**Milestone:** M1 · **Status:** Approved · **Last updated:** 2026-10-17 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** PL-01 and PL-02 run end to end on a synthetic export.
**Covers:** LOAD-01, PROF-02 · **Deferred:** LOAD-02, PROF-01 (their thicken tasks land in M2)

## Phase 0: Interface

### M1-T01: Freeze the M1 interfaces
**Package:** gridload · **Step:** contract · **Kind:** interface · **Size:** M · **Mode:** solo
**Read:** PL-01, PL-02, ingest.RawReadings, ingest.Readings, profile.Profile, profile.Report, ingest.load_readings
**Acceptance:**
- [ ] Boundary types in `ingest/types.py` and `profile/types.py`, one sample per case under `tests/contracts/`
- [ ] Every M1 step and entry signature in its module, body `raise NotImplementedError("<task>")`
- [ ] `__main__.py` routes `ingest` and `seasonality` to their entry stubs; `pipeline.py` re-exports the entries
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/gridload/__init__.py, src/gridload/__main__.py, src/gridload/pipeline.py, src/gridload/ingest/**, src/gridload/profile/**, src/gridload/pipelines/**, tests/contracts/**

## Phase 1: Step spines

### M1-T02: read_export spine on a synthetic export
**Package:** gridload · **Step:** PL-01.read_export · **Kind:** spine · **Covers:** LOAD-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, ingest.RawReadings, LOAD-01
**Acceptance:**
- [ ] `read_export` returns a valid ingest.RawReadings from a synthetic export; signature unchanged
**Verify:** `pytest tests/unit/gridload -k export` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/gridload/ingest/export.py, tests/unit/gridload/test_export.py

### M1-T03: clean_units spine (every meter in kWh)
**Package:** gridload · **Step:** PL-01.clean_units · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-01, ingest.RawReadings, ingest.Readings
**Acceptance:**
- [ ] `clean_units` turns the ingest.RawReadings sample into a valid ingest.Readings
**Verify:** `pytest tests/unit/gridload -k units` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/gridload/ingest/units.py, tests/unit/gridload/test_units.py

### M1-T04: fit_seasonality spine (daily term only)
**Package:** gridload · **Step:** PL-02.fit_seasonality · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, ingest.Readings, profile.Profile, profile.fit_seasonality
**Acceptance:**
- [ ] `fit_seasonality` fits the daily term of the ingest.Readings sample as a valid profile.Profile
**Verify:** `pytest tests/unit/gridload -k seasonality` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/gridload/profile/seasonality.py, tests/unit/gridload/test_seasonality.py

### M1-T05: write_report spine (print table)
**Package:** gridload · **Step:** PL-02.write_report · **Kind:** spine · **Covers:** PROF-02 · **Size:** XS · **Mode:** solo
**Read:** PL-02, profile.Profile, profile.Report, PROF-02
**Acceptance:**
- [ ] `write_report` prints the profile.Profile sample as a table and returns a valid profile.Report
**Verify:** `pytest tests/unit/gridload -k report` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/gridload/profile/report.py, tests/unit/gridload/test_report.py

## Phase 2: Wiring

### M1-T06: Wire PL-01
**Package:** gridload · **Step:** PL-01 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-01, ingest.load_readings
**Acceptance:**
- [ ] `python -m gridload ingest --smoke` runs end to end on a synthetic export
**Verify:** `python -m gridload ingest --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02, M1-T03 · **Writes:** src/gridload/pipelines/pl01_ingest.py, tests/unit/gridload/test_pl01_smoke.py

### M1-T07: Wire PL-02 on the load_readings fake
**Package:** gridload · **Step:** PL-02 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-02, ingest.load_readings, profile.Report
**Acceptance:**
- [ ] `python -m gridload seasonality --smoke` runs end to end on the ingest.load_readings fake
**Verify:** `python -m gridload seasonality --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04, M1-T05 · **Writes:** src/gridload/pipelines/pl02_seasonality.py, tests/unit/gridload/test_pl02_smoke.py

## Phase 3: System

### M1-T08: PL-02 on the real PL-01
**Package:** gridload · **Step:** PL-02 · **Kind:** system · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, ingest.load_readings
**Acceptance:**
- [ ] PL-02 calls the real `load_readings`; the fake is used only by contract tests
**Verify:** `python -m gridload ingest --smoke` · `python -m gridload seasonality --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T06, M1-T07 · **Writes:** src/gridload/pipelines/pl02_seasonality.py, tests/unit/gridload/test_system_smoke.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] No `NotImplementedError` stub is left; `scripts/check.sh full` passes

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T03 clean_units spine | M1-T02 read_export spine | data | ingest.RawReadings sample (M1-T01) |
| M1-T05 write_report spine | M1-T04 fit_seasonality spine | data | profile.Profile sample (M1-T01) |
| M1-T06 wire PL-01 | M1-T02 read_export spine | code | none: the smoke test runs the real read_export |
| M1-T06 wire PL-01 | M1-T03 clean_units spine | code | none: the smoke test runs the real clean_units |
| M1-T07 wire PL-02 | M1-T06 wire PL-01 | call | ingest.load_readings fake (M1-T01) |
| M1-T07 wire PL-02 | M1-T04 fit_seasonality spine | code | none: the smoke test runs the real fit_seasonality |
| M1-T07 wire PL-02 | M1-T05 write_report spine | code | none: the smoke test runs the real write_report |
| M1-T08 system | M1-T06 wire PL-01 | code | none: swaps the fake for the real PL-01 |
| M1-T08 system | M1-T07 wire PL-02 | file | none: PL-02's entry module, which M1-T07 writes |

## Open questions
