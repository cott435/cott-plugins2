# M1: Data + stats — Plan

**Milestone:** M1 · **Status:** Approved · **Base:** 3f2c1ab · **Last updated:** 2026-10-16 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass.
**Covers:** DATA-01, DATA-02, STAT-01–STAT-04, QR-01, QR-02 · **Deferred:** none
**Skills:** data-science (stats steps)

## Phase 0: Interface

### M1-T01: Freeze M1's step boundaries
**Package:** quant · **Step:** contract · **Kind:** interface · **Size:** M · **Mode:** solo
**Read:** PL-01, PL-02, data.Universe, data.RawPrices, data.Prices, stats.Returns, stats.Cov, stats.Factors, stats.CovReport, data.load_prices, stats.estimate_cov, stats.clean_eigen
**Acceptance:**
- [ ] Every type above is a dataclass in its owner's `types.py`, with one sample under `tests/contracts/<component>.<Type>/`
- [ ] Every step signature exists in its owner module with body `raise NotImplementedError("<spine task>")`
- [ ] The data.load_prices fake replays `tests/contracts/data.load_prices/` for PL-02
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/quant/data/**, src/quant/stats/**, tests/contracts/**

## Phase 1: Step spines

### M1-T02: read_raw spine
**Package:** quant · **Step:** PL-01.read_raw · **Kind:** spine · **Covers:** DATA-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, data.Universe, data.RawPrices
**Acceptance:**
- [ ] `read_raw` returns a schema-valid RawPrices on the Universe sample
**Verify:** `pytest tests/unit/quant -k read` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/data/read.py, tests/unit/quant/test_read.py

### M1-T03: apply_universe spine
**Package:** quant · **Step:** PL-01.apply_universe · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-01, data.RawPrices, data.Universe, data.Prices
**Acceptance:**
- [ ] `apply_universe` returns a schema-valid Prices on the RawPrices sample (static universe)
**Verify:** `pytest tests/unit/quant -k universe` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/data/universe.py, tests/unit/quant/test_universe.py

### M1-T04: estimate_cov spine
**Package:** quant · **Step:** PL-02.estimate_cov · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Returns, stats.Cov, stats.estimate_cov
**Acceptance:**
- [ ] Sample covariance of the Returns sample is a schema-valid Cov
**Verify:** `pytest tests/unit/quant -k cov` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/cov.py, tests/unit/quant/test_cov.py

### M1-T05: clean_eigen spine (no cleaning)
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] `clean_eigen` returns its input on the stats.Cov sample; signature unchanged
**Verify:** `pytest tests/unit/quant -k rmt` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py

### M1-T06: pca spine
**Package:** quant · **Step:** PL-02.pca · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.Factors
**Acceptance:**
- [ ] Full eigendecomposition of the Cov sample is a schema-valid Factors
**Verify:** `pytest tests/unit/quant -k pca` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/pca.py, tests/unit/quant/test_pca.py

### M1-T07: write_report spine
**Package:** quant · **Step:** PL-02.write_report · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Factors, stats.CovReport
**Acceptance:**
- [ ] The Factors sample prints as a CovReport table
**Verify:** `pytest tests/unit/quant -k report` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/report.py, tests/unit/quant/test_report.py

## Phase 2: Wiring and thicken

### M1-T08: Wire PL-01
**Package:** quant · **Step:** PL-01 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-01, data.load_prices, data.Prices
**Acceptance:**
- [ ] `python -m quant.data load --smoke` runs end to end on a synthetic CSV
- [ ] PL-01 entry sketch replaced by a `dt layout` pointer
**Verify:** `python -m quant.data load --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02, M1-T03 · **Writes:** src/quant/data/pipeline.py, tests/unit/quant/test_pl01_smoke.py

### M1-T09: Wire PL-02 on the load_prices fake
**Package:** quant · **Step:** PL-02 · **Kind:** wiring · **Size:** S · **Mode:** solo
**Read:** PL-02, data.load_prices, stats.CovReport
**Acceptance:**
- [ ] `python -m quant.stats cov-report --smoke` runs end to end on the data.load_prices fake
**Verify:** `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07 · **Writes:** src/quant/stats/pipeline.py, tests/unit/quant/test_pl02_smoke.py

### M1-T10: Delisting-aware universe
**Package:** quant · **Step:** PL-01.apply_universe · **Kind:** thicken · **Covers:** DATA-02 · **Size:** S · **Mode:** split
**Read:** PL-01, TC-01, DATA-02, data.Universe, data.Prices
**Acceptance:**
- [ ] TC-01 passes
- [ ] PL-01 smoke test still passes
**Verify:** `pytest tests/intent/quant -k universe` · `python -m quant.data load --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T03 · **Writes:** src/quant/data/universe.py, tests/intent/quant/test_universe.py, tests/unit/quant/test_universe.py

### M1-T11: Marchenko–Pastur cleaning
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** thicken · **Covers:** STAT-03 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] TC-02 passes within tolerance; the no-cleaning baseline stays selectable
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/quant -k rmt` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T05 · **Writes:** src/quant/stats/rmt.py, tests/intent/quant/test_rmt.py, tests/unit/quant/test_rmt.py

### M1-T12: Shrinkage covariance
**Package:** quant · **Step:** PL-02.estimate_cov · **Kind:** thicken · **Covers:** STAT-02, QR-02 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, STAT-02, QR-02, stats.Returns, stats.estimate_cov
**Acceptance:**
- [ ] Shrinkage estimate is positive definite on TC-02's input; sample covariance stays selectable
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/quant -k cov` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04 · **Writes:** src/quant/stats/cov.py, tests/intent/quant/test_cov.py, tests/unit/quant/test_cov.py

### M1-T13: Planted-factor PCA check
**Package:** quant · **Step:** PL-02.pca · **Kind:** thicken · **Covers:** STAT-01, QR-01 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-03, STAT-01, QR-01, RF-01:pca_factors, stats.Factors
**Acceptance:**
- [ ] TC-03 passes with a fixed seed
**Verify:** `pytest tests/intent/quant -k pca` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T06 · **Writes:** src/quant/stats/pca.py, tests/intent/quant/test_pca.py, tests/unit/quant/test_pca.py

### Checkpoint after M1-T13
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Phase 3: System

### M1-T14: PL-02 on the real PL-01
**Package:** quant · **Step:** PL-02 · **Kind:** system · **Covers:** STAT-04 · **Size:** S · **Mode:** split
**Read:** PL-01, PL-02, data.load_prices
**Acceptance:**
- [ ] PL-02 calls the real `load_prices`; both smoke commands pass; TC-01–TC-03 pass
**Verify:** `python -m quant.data load --smoke` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T08, M1-T09, M1-T10, M1-T11, M1-T12, M1-T13 · **Writes:** src/quant/stats/pipeline.py, tests/intent/quant/test_system.py, tests/unit/quant/test_system_smoke.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] No `NotImplementedError` stub left
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T03 apply_universe spine | M1-T02 read_raw spine | data | data.RawPrices sample (M1-T01) |
| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.Cov sample (M1-T01) |
| M1-T06 pca spine | M1-T05 clean_eigen spine | data | stats.Cov sample (M1-T01) |
| M1-T07 write_report spine | M1-T06 pca spine | data | stats.Factors sample (M1-T01) |
| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | data.load_prices fake (M1-T01) |
| M1-T11 MP cleaning | M1-T12 shrinkage | data | stats.Cov sample (M1-T01): cleaning takes any Cov |
| M1-T08 wire PL-01 | M1-T02 read_raw spine | code | none: the smoke test runs the real step code |
| M1-T08 wire PL-01 | M1-T03 apply_universe spine | code | none: the smoke test runs the real step code |
| M1-T09 wire PL-02 | M1-T04 estimate_cov spine | code | none: the smoke test runs the real step code |
| M1-T09 wire PL-02 | M1-T05 clean_eigen spine | code | none: the smoke test runs the real step code |
| M1-T09 wire PL-02 | M1-T06 pca spine | code | none: the smoke test runs the real step code |
| M1-T09 wire PL-02 | M1-T07 write_report spine | code | none: the smoke test runs the real step code |
| M1-T10 universe | M1-T03 apply_universe spine | code | none: thickens the same module |
| M1-T11 MP cleaning | M1-T05 clean_eigen spine | code | none: thickens the same module |
| M1-T12 shrinkage | M1-T04 estimate_cov spine | code | none: thickens the same module |
| M1-T13 PCA check | M1-T06 pca spine | code | none: thickens the same module |
| M1-T14 system | M1-T08 wire PL-01 | code | none: swaps the fake for the real PL-01 end to end |
| M1-T14 system | M1-T09 wire PL-02 | file | none: shared entry module src/quant/stats/pipeline.py |
| M1-T14 system | M1-T10 universe | code | none: the system smoke runs the real step code |
| M1-T14 system | M1-T11 MP cleaning | code | none: the system smoke runs the real step code |
| M1-T14 system | M1-T12 shrinkage | code | none: the system smoke runs the real step code |
| M1-T14 system | M1-T13 PCA check | code | none: the system smoke runs the real step code |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Free delisting data incomplete | survivorship bias | TC-01 pins a known delisting |

## Open questions

## Replan notes
