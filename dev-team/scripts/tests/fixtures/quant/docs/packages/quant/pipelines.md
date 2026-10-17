# quant — Pipelines

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-16 · **Contract:** [contract.md](contract.md)

## PL-01: Load prices
**Entry:** `src/quant/data/pipeline.py::run_load_prices` · **Trigger:** `python -m quant.data load`
**Covers:** DATA-01, DATA-02, QR-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `read_raw` | data | dates → RawPrices | read a synthetic CSV | DATA-01 |
| 2 | `apply_universe` | data | RawPrices, dates → Prices | static universe, no delistings | DATA-02 |

Layout: `dt layout quant`

## PL-02: Covariance report
**Entry:** `src/quant/stats/pipeline.py::run_cov_report` · **Trigger:** `python -m quant.stats cov-report`
**Covers:** STAT-01–STAT-04, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_prices` | data | universe, dates → Prices | PL-01 as built | DATA-01 |
| 2 | `estimate_cov` | stats | Returns → Cov | sample covariance | STAT-02 |
| 3 | `clean_eigen` | stats | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
| 4 | `pca` | stats | Cov → Factors | full eigendecomposition | STAT-01 |
| 5 | `write_report` | stats | Factors → CovReport | print table | STAT-04 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_cov_report(cfg: CovConfig) -> CovReport:
    prices = load_prices(cfg.universe, cfg.start, cfg.end)
    cov = estimate_cov(prices.returns())
    cov = clean_eigen(cov, n_obs=len(prices))
    factors = pca(cov)
    return write_report(factors, cfg.out)
```

## PL-03: Min-variance backtest
**Entry:** `src/quant/portfolio/pipeline.py::run_backtest` · **Trigger:** `python -m quant.portfolio backtest`
**Covers:** PORT-01, PORT-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `estimate_cov` | stats | Returns → Cov | sample covariance | STAT-02 |
| 2 | `min_variance` | portfolio | Cov → Weights | equal weight | PORT-01 |
| 3 | `compare` | portfolio | Weights, Returns → Comparison | realized variance only | PORT-02 |

## Planned layout (pre-build — removed by spine task)
```
src/quant/
  stats/
    __init__.py   contract exports only
    pipeline.py   PL-02 entry
    cov.py  rmt.py  pca.py  report.py
  portfolio/
    __init__.py  pipeline.py  minvar.py  compare.py
tests/intent/quant/  tests/unit/quant/
```

## Open questions
- Should `clean_eigen` take T from Returns instead of a parameter? (assumed: parameter)

## Retired
- ~~PL-04: Raw eigen dump~~ Retired 2026-10-16: folded into PL-02 (AD-03)
