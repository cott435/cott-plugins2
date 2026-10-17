# quant — Contract

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-15 · **Architecture:** [../../architecture.md](../../architecture.md)

## data

### data.load_prices: Point-in-time prices
`def load_prices(universe: Universe, start: date, end: date) -> Prices`
- **Invariants:** T×N; a name appears only between its listing and delisting dates
- **Errors:** `KeyError` for an unknown ticker; `ValueError` if start > end
- **Used by:** PL-01, PL-02

## stats

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** PL-02, PL-03

### stats.clean_eigen: Random-matrix cleaning
`def clean_eigen(cov: Cov, *, n_obs: int) -> Cov`
- **Invariants:** same shape; no eigenvalue above the Marchenko–Pastur edge is changed
- **Errors:** `ValueError` if n_obs < N
- **Used by:** PL-02

## portfolio

### portfolio.min_variance: Minimum-variance weights
`def min_variance(cov: Cov) -> Weights`
- **Invariants:** weights sum to 1; long only
- **Errors:** `ValueError` if cov is not positive definite
- **Used by:** PL-03
