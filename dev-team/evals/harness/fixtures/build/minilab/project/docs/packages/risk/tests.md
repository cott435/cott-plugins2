# risk — Tests

**Package:** risk · **Status:** Approved · **Last updated:** 2026-10-17 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-02 | `pytest tests/unit/risk/test_pl02_smoke.py` | log_returns, rolling_vol, annualize | TC-04, TC-05, TC-06 | — |
| PL-03 | `pytest tests/unit/risk/test_pl03_smoke.py` | summary_stats, max_drawdown, write_report | TC-07, TC-08 | — |

### TC-04: Geometric closes
**Pipeline:** PL-02 · **Covers:** RISK-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/risk/TC-04/
**Source:** closes 100·1.01^t and 50·0.98^t; closed form r = ln(1.01), ln(0.98)
**Expected:** every return equals the closed form · **Tolerance:** 1e-12 absolute

### TC-05: Rolling volatility from earlier returns
**Pipeline:** PL-02 · **Covers:** RISK-02 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/risk/TC-05/
**Source:** eight hand-made returns, window 4; sample standard deviation of the four returns before each date
**Expected:** no value for the first four dates, then the listed values · **Tolerance:** 1e-12 absolute

### TC-06: Annualizing
**Pipeline:** PL-02 · **Covers:** RISK-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/risk/TC-06/
**Source:** daily volatilities with gaps; closed form σ·√252
**Expected:** each value scaled, gaps kept · **Tolerance:** 1e-12 absolute

### TC-07: Whole-period summary
**Pipeline:** PL-03 · **Covers:** RISK-04 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/risk/TC-07/
**Source:** six returns for X, a constant series for Y (zero volatility)
**Expected:** 252·mean, √252·sample stdev, their ratio (0 for Y), the last rolling value · **Tolerance:** 1e-9 absolute

### TC-08: Drawdown with dates
**Pipeline:** PL-03 · **Covers:** RISK-05 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/risk/TC-08/
**Source:** closes 100, 110, 99, 88, 95, 120 (X), a rising series (Y), a first-day fall (Z)
**Expected:** X −20% from the second date to the fourth; Y 0 at the first date; Z peaks at the first date · **Tolerance:** 1e-12 absolute on depth, dates exact

## Open questions

## Retired
