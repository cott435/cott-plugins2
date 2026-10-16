# quant — Tests

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-16 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m quant.data load --smoke` | read_raw, apply_universe | TC-01 | — |
| PL-02 | `python -m quant.stats cov-report --smoke` | cov, rmt, pca | TC-02, TC-03 | — |

### TC-01: Delisted name drops out
**Pipeline:** PL-01 · **Covers:** DATA-02 · **Kind:** user example · **Fixture:** tests/fixtures/quant/TC-01/
**Source:** user file `delisted_2018.csv` (given 2026-10-15)
**Expected:** ticker XYZ present through 2018-06-29, absent after · **Tolerance:** exact, dates are discrete

### TC-02: MP edge on pure noise
**Pipeline:** PL-02 · **Covers:** STAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/quant/TC-02/
**Source:** generator `noise(T=250, N=50, seed=7)`; Marchenko–Pastur closed form λ+ = σ²(1+√(N/T))²
**Expected:** every cleaned eigenvalue ≤ λ+ · **Tolerance:** 5% of λ+, for finite-sample edge fluctuation

### TC-03: Planted factor is found
**Pipeline:** PL-02 · **Covers:** STAT-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/quant/TC-03/
**Source:** generator `one_factor(T=500, N=20, beta=1.0, seed=3)`
**Expected:** first factor explains ≥ 40% of variance · **Tolerance:** property, no tolerance

## Open questions

## Retired
