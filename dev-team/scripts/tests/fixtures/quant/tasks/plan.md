# M1: Data + stats — Plan

**Milestone:** M1 · **Status:** In progress · **Base:** 3f2c1ab · **Last updated:** 2026-10-16 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass.
**Covers:** DATA-01, DATA-02, STAT-01–STAT-04, QR-01, QR-02 · **Deferred:** none
**Skills:** data-science (stats steps)

## Phase 0: Interface

### M1-T01: Freeze the M1 interfaces
**Package:** quant · **Step:** contract · **Kind:** interface · **Size:** M · **Mode:** solo
**Read:** PL-01, PL-02, data.RawPrices, data.Prices, stats.Returns, stats.Cov, stats.Factors, stats.CovReport, data.load_prices
**Acceptance:**
- [x] Boundary types in `data/types.py` and `stats/types.py`, one sample each under `tests/contracts/`
- [x] Every M1 step signature in its owner module, body `raise NotImplementedError("<task>")`
- [x] `data.load_prices` fake backed by fixtures; `__init__` exports
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/quant/__init__.py, src/quant/data/__init__.py, src/quant/data/types.py, src/quant/data/raw.py, src/quant/data/universe.py, src/quant/stats/__init__.py, src/quant/stats/types.py, src/quant/stats/cov.py, src/quant/stats/rmt.py, src/quant/stats/pca.py, src/quant/stats/report.py, tests/contracts/**

## Phase 1: Step spines

### M1-T02: read_raw spine on a synthetic CSV
**Package:** quant · **Step:** PL-01.read_raw · **Kind:** spine · **Covers:** DATA-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, data.RawPrices, DATA-01
**Acceptance:**
- [ ] `read_raw` returns a schema-valid data.RawPrices from a synthetic CSV; signature unchanged
**Verify:** `pytest tests/unit/quant -k read_raw` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/data/raw.py, tests/unit/quant/test_raw.py

### M1-T03: apply_universe spine (static universe)
**Package:** quant · **Step:** PL-01.apply_universe · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-01, data.RawPrices, data.Prices
**Acceptance:**
- [ ] `apply_universe` turns the data.RawPrices sample into a schema-valid data.Prices; no delistings yet
**Verify:** `pytest tests/unit/quant -k universe` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/data/universe.py, tests/unit/quant/test_universe.py

### M1-T04: estimate_cov spine (sample covariance)
**Package:** quant · **Step:** PL-02.estimate_cov · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Returns, stats.Cov, stats.estimate_cov
**Acceptance:**
- [ ] `estimate_cov` returns the sample covariance of the stats.Returns sample as a valid stats.Cov
**Verify:** `pytest tests/unit/quant -k estimate_cov` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/cov.py, tests/unit/quant/test_cov.py

### M1-T05: clean_eigen spine (no cleaning)
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] `clean_eigen` returns its input on the stats.Cov sample; signature unchanged
**Verify:** `pytest tests/unit/quant -k clean_eigen` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py

### M1-T06: pca spine (full eigendecomposition)
**Package:** quant · **Step:** PL-02.pca · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.Factors
**Acceptance:**
- [ ] `pca` turns the stats.Cov sample into a valid stats.Factors, largest first
**Verify:** `pytest tests/unit/quant -k pca` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/pca.py, tests/unit/quant/test_pca.py

### M1-T07: write_report spine (print table)
**Package:** quant · **Step:** PL-02.write_report · **Kind:** spine · **Covers:** STAT-04 · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Factors, stats.CovReport, STAT-04
**Acceptance:**
- [ ] `write_report` prints the stats.Factors sample as a table and returns a valid stats.CovReport
**Verify:** `pytest tests/unit/quant -k report` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/report.py, tests/unit/quant/test_report.py

## Phase 2: Wiring

### M1-T08: Wire PL-01
**Package:** quant · **Step:** PL-01 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-01, data.load_prices
**Acceptance:**
- [ ] `python -m quant.data load --smoke` runs end to end on a synthetic CSV
- [ ] PL-01 entry sketch replaced by a `dt layout` pointer
**Verify:** `python -m quant.data load --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02, M1-T03 · **Writes:** src/quant/data/pipeline.py, src/quant/data/__main__.py

### M1-T09: Wire PL-02 on the load_prices fake
**Package:** quant · **Step:** PL-02 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-02, data.load_prices, stats.CovReport
**Acceptance:**
- [ ] `python -m quant.stats cov-report --smoke` runs end to end on the data.load_prices fake
- [ ] Pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07 · **Writes:** src/quant/stats/pipeline.py, src/quant/stats/__main__.py

## Phase 2: Thicken

### M1-T10: Delisting-aware universe
**Package:** quant · **Step:** PL-01.apply_universe · **Kind:** thicken · **Covers:** DATA-02 · **Size:** S · **Mode:** split
**Skills:** —
**Read:** PL-01, TC-01, DATA-02, data.Prices
**Acceptance:**
- [ ] TC-01 passes
- [ ] The static universe stays selectable
**Verify:** `pytest tests/intent/quant tests/unit/quant -k universe` · `scripts/check.sh gate`
**Depends on:** M1-T03 · **Writes:** src/quant/data/universe.py, tests/unit/quant/test_universe.py

### M1-T11: Marchenko–Pastur cleaning
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** thicken · **Covers:** STAT-03 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] TC-02 passes within tolerance; the no-cleaning baseline stays selectable
**Verify:** `pytest tests/intent/quant tests/unit/quant -k rmt` · `scripts/check.sh gate`
**Depends on:** M1-T05 · **Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py

### M1-T12: Shrinkage covariance
**Package:** quant · **Step:** PL-02.estimate_cov · **Kind:** thicken · **Covers:** STAT-02, QR-02 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, STAT-02, QR-02, stats.Returns, stats.estimate_cov
**Acceptance:**
- [ ] Shrinkage estimate is positive definite on TC-02's input; sample covariance stays selectable
**Verify:** `pytest tests/intent/quant tests/unit/quant -k cov` · `scripts/check.sh gate`
**Depends on:** M1-T04 · **Writes:** src/quant/stats/cov.py, tests/unit/quant/test_cov.py

### M1-T13: Planted-factor PCA check
**Package:** quant · **Step:** PL-02.pca · **Kind:** thicken · **Covers:** STAT-01, QR-01 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-03, STAT-01, QR-01, stats.Factors, RF-01:pca_factors
**Acceptance:**
- [ ] TC-03 passes with a fixed seed
**Verify:** `pytest tests/intent/quant -k pca` · `scripts/check.sh gate`
**Depends on:** M1-T06 · **Writes:** src/quant/stats/pca.py, tests/intent/quant/test_pca.py

### Checkpoint after M1-T13
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] Every stub names an open task (`scripts/check.sh gate`)
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 3: System

### M1-T14: PL-02 on the real PL-01
**Package:** quant · **Step:** PL-02 · **Kind:** system · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, TC-01, TC-02, TC-03, data.load_prices
**Acceptance:**
- [ ] PL-02 calls the real `load_prices`; the fake is used only by contract tests
- [ ] Both smoke commands pass; TC-01–TC-03 pass
**Verify:** `python -m quant.data load --smoke` · `python -m quant.stats cov-report --smoke` · `pytest tests/intent/quant` · `scripts/check.sh gate`
**Depends on:** M1-T08, M1-T09, M1-T10, M1-T11, M1-T12, M1-T13 · **Writes:** src/quant/stats/pipeline.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass; no `NotImplementedError` stub is left
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T03 apply_universe spine | M1-T02 read_raw spine | data | data.RawPrices sample (M1-T01) |
| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.Cov sample (M1-T01) |
| M1-T06 pca spine | M1-T05 clean_eigen spine | data | stats.Cov sample (M1-T01) |
| M1-T07 write_report spine | M1-T06 pca spine | data | stats.Factors sample (M1-T01) |
| M1-T08 wire PL-01 | M1-T02 read_raw spine | code | none: the smoke test runs the real read_raw |
| M1-T08 wire PL-01 | M1-T03 apply_universe spine | code | none: the smoke test runs the real apply_universe |
| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | data.load_prices fake (M1-T01) |
| M1-T09 wire PL-02 | M1-T04 estimate_cov spine | code | none: the smoke test runs the real estimate_cov |
| M1-T09 wire PL-02 | M1-T05 clean_eigen spine | code | none: the smoke test runs the real clean_eigen |
| M1-T09 wire PL-02 | M1-T06 pca spine | code | none: the smoke test runs the real pca |
| M1-T09 wire PL-02 | M1-T07 write_report spine | code | none: the smoke test runs the real write_report |
| M1-T10 delisting universe | M1-T03 apply_universe spine | code | none: thickens the same module |
| M1-T11 MP cleaning | M1-T05 clean_eigen spine | code | none: thickens the same module |
| M1-T11 MP cleaning | M1-T12 shrinkage | data | stats.Cov sample (M1-T01): cleaning takes any Cov |
| M1-T12 shrinkage | M1-T04 estimate_cov spine | code | none: thickens the same module |
| M1-T13 PCA check | M1-T06 pca spine | code | none: thickens the same module |
| M1-T14 system | M1-T08 wire PL-01 | code | none: swaps the fake for the real PL-01 |
| M1-T14 system | M1-T09 wire PL-02 | file | none: rewires stats/pipeline.py, which M1-T09 writes |
| M1-T14 system | M1-T10 delisting universe | order | none: the golden cases run on the finished steps |
| M1-T14 system | M1-T11 MP cleaning | order | none: the golden cases run on the finished steps |
| M1-T14 system | M1-T12 shrinkage | order | none: the golden cases run on the finished steps |
| M1-T14 system | M1-T13 PCA check | order | none: the golden cases run on the finished steps |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Free delisting data incomplete | survivorship bias | TC-01 pins a known delisting |

## Open questions

## Replan notes
