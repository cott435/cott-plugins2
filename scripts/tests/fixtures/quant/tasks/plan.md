# M1: Data + stats — Plan

**Milestone:** M1 · **Status:** In progress · **Base:** 3f2c1ab · **Last updated:** 2026-10-16 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass.
**Covers:** DATA-01, DATA-02, STAT-01–STAT-04, QR-01, QR-02 · **Deferred:** none
**Skills:** data-science (stats steps)

## Phase 0: Spine

### M1-T01: PL-01 spine on synthetic prices
**Package:** quant · **Step:** PL-01 · **Covers:** DATA-01 · **Size:** S · **Mode:** solo
**Read:** PL-01, data.load_prices, DATA-01
**Acceptance:**
- [x] `python -m quant.data load --smoke` runs end to end on a synthetic CSV
- [x] PL-01 entry sketch replaced by a `dt layout` pointer
**Verify:** `python -m quant.data load --smoke` · `scripts/check.sh gate`
**Depends on:** — · **Files likely:** src/quant/data/pipeline.py, src/quant/data/steps.py

### M1-T02: PL-02 spine with sample covariance
**Package:** quant · **Step:** PL-02 · **Covers:** STAT-04 · **Size:** M · **Mode:** solo
**Read:** PL-02, stats.estimate_cov, STAT-04
**Acceptance:**
- [ ] `python -m quant.stats cov-report --smoke` runs end to end on synthetic returns
- [ ] Pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Files likely:** src/quant/stats/pipeline.py, src/quant/stats/cov.py, src/quant/stats/pca.py, src/quant/stats/report.py

## Phase 1: Thicken

### M1-T03: Delisting-aware universe
**Package:** quant · **Step:** PL-01.apply_universe · **Covers:** DATA-02 · **Size:** S · **Mode:** split
**Skills:** —
**Read:** PL-01, TC-01, DATA-02, data.load_prices
**Acceptance:**
- [ ] TC-01 passes
- [ ] PL-01 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k universe` · `python -m quant.data load --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Parallel:** G1 · **Files likely:** src/quant/data/steps.py, tests/unit/quant/test_universe.py

### M1-T04: Marchenko–Pastur cleaning
**Package:** quant · **Step:** PL-02.clean_eigen · **Covers:** STAT-03 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, stats.clean_eigen
**Acceptance:**
- [ ] TC-02 passes within tolerance; the no-cleaning baseline stays selectable
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k rmt` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02 · **Parallel:** G1 · **Files likely:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py

### Checkpoint after M1-T04
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M1-T05: Shrinkage covariance
**Package:** quant · **Step:** PL-02.estimate_cov · **Covers:** STAT-02, QR-02 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, STAT-02, QR-02, stats.estimate_cov
**Acceptance:**
- [ ] Shrinkage estimate is positive definite on TC-02's input; sample covariance stays selectable
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k cov` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04 · **Files likely:** src/quant/stats/cov.py, tests/unit/quant/test_cov.py

### M1-T06: Planted-factor PCA check
**Package:** quant · **Step:** PL-02.pca · **Covers:** STAT-01, QR-01 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-03, STAT-01, QR-01
**Acceptance:**
- [ ] TC-03 passes with a fixed seed
**Verify:** `pytest tests/intent/quant -k pca` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02 · **Files likely:** src/quant/stats/pca.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Free delisting data incomplete | survivorship bias | TC-01 pins a known delisting |

## Open questions

## Replan notes
