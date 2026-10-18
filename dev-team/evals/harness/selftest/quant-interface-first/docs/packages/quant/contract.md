# quant — Contract

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-15 · **Architecture:** [../../architecture.md](../../architecture.md)

## data

### data.Universe: type
`class Universe: tickers: tuple[str, ...]; listed: dict[str, tuple[date, date | None]]`
- **Invariants:** every ticker has a listing date; delisting after listing
- **Sample:** tests/contracts/data.Universe/sample.json

### data.RawPrices: type
`class RawPrices: rows: list[tuple[date, str, float]]`
- **Invariants:** one row per (date, ticker); prices > 0
- **Sample:** tests/contracts/data.RawPrices/sample.json

### data.Prices: type
`class Prices: frame: DataFrame  # dates × tickers; def returns(self) -> Returns`
- **Invariants:** T×N; a name has values only between its listing and delisting dates
- **Sample:** tests/contracts/data.Prices/sample.json

### data.load_prices: Point-in-time prices
`def load_prices(universe: Universe, start: date, end: date) -> Prices`
- **Invariants:** T×N; a name appears only between its listing and delisting dates
- **Errors:** `KeyError` for an unknown ticker; `ValueError` if start > end
- **Boundary:** stats · **Fixtures:** tests/contracts/data.load_prices/ · **Cases:** a 2×2 panel
- **Used by:** PL-01, PL-02

## stats

### stats.Returns: type
`class Returns: frame: DataFrame  # dates × tickers, simple returns`
- **Invariants:** T×N; no NaN inside a name's listed window
- **Sample:** tests/contracts/stats.Returns/sample.json

### stats.Cov: type
`class Cov: matrix: ndarray; tickers: tuple[str, ...]; n_obs: int`
- **Invariants:** N×N; symmetric; positive semi-definite
- **Sample:** tests/contracts/stats.Cov/sample.json

### stats.Factors: type
`class Factors: eigenvalues: ndarray; loadings: ndarray; explained: ndarray`
- **Invariants:** eigenvalues descending; explained sums to 1
- **Sample:** tests/contracts/stats.Factors/sample.json

### stats.CovReport: type
`class CovReport: factors: Factors; table: str`
- **Invariants:** one table row per factor
- **Sample:** tests/contracts/stats.CovReport/sample.json

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** PL-02, PL-03

### stats.clean_eigen: Random-matrix cleaning
`def clean_eigen(cov: Cov) -> Cov`
- **Invariants:** same shape; no eigenvalue above the Marchenko–Pastur edge is changed
- **Errors:** `ValueError` if cov.n_obs < N
- **Used by:** PL-02

## portfolio

### portfolio.Weights: type
`class Weights: values: ndarray; tickers: tuple[str, ...]`
- **Invariants:** sums to 1; long only

### portfolio.Comparison: type
`class Comparison: realized_variance: dict[str, float]`
- **Invariants:** one entry per compared portfolio

### portfolio.min_variance: Minimum-variance weights
`def min_variance(cov: Cov) -> Weights`
- **Invariants:** weights sum to 1; long only
- **Errors:** `ValueError` if cov is not positive definite
- **Used by:** PL-03
