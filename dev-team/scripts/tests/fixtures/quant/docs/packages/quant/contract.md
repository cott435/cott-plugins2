# quant — Contract

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-15 · **Architecture:** [../../architecture.md](../../architecture.md)

## data

### data.RawPrices: Raw price rows
**Kind:** type · **Sample:** `tests/contracts/data.RawPrices/sample.json`
`@dataclass(frozen=True) class RawPrices: rows: pd.DataFrame  # date, ticker, close`
- **Invariants:** one row per (date, ticker); dates sorted; no universe applied yet
- **Used by:** PL-01

### data.Prices: Point-in-time price panel
**Kind:** type · **Sample:** `tests/contracts/data.Prices/sample.json`
`@dataclass(frozen=True) class Prices: close: pd.DataFrame  # T×N, index dates, columns tickers`
- **Invariants:** a name has values only between its listing and delisting dates; `.returns() -> Returns`
- **Used by:** PL-01, PL-02

### data.load_prices: Point-in-time prices
`def load_prices(universe: Universe, start: date, end: date) -> Prices`
- **Invariants:** T×N; a name appears only between its listing and delisting dates
- **Errors:** `KeyError` for an unknown ticker; `ValueError` if start > end
- **Used by:** PL-01, PL-02

## stats

### stats.Returns: Daily returns
**Kind:** type · **Sample:** `tests/contracts/stats.Returns/sample.json`
`@dataclass(frozen=True) class Returns: values: np.ndarray; tickers: tuple[str, ...]  # T×N`
- **Invariants:** no NaN; T ≥ 2
- **Used by:** PL-02, PL-03

### stats.Cov: Covariance matrix
**Kind:** type · **Sample:** `tests/contracts/stats.Cov/sample.json`
`@dataclass(frozen=True) class Cov: values: np.ndarray; tickers: tuple[str, ...]; n_obs: int  # N×N`
- **Invariants:** symmetric; positive semi-definite; `tickers` in column order
- **Used by:** PL-02, PL-03

### stats.Factors: Principal factors
**Kind:** type · **Sample:** `tests/contracts/stats.Factors/sample.json`
`@dataclass(frozen=True) class Factors: loadings: np.ndarray; explained: np.ndarray  # N×K, K`
- **Invariants:** `explained` sorted descending, sums to ≤ 1
- **Used by:** PL-02

### stats.CovReport: Covariance report
**Kind:** type · **Sample:** `tests/contracts/stats.CovReport/sample.json`
`@dataclass(frozen=True) class CovReport: table: str; factors: Factors`
- **Invariants:** `table` lists every factor in `factors`
- **Used by:** PL-02

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

### portfolio.Weights: Portfolio weights
**Kind:** type · **Sample:** `tests/contracts/portfolio.Weights/sample.json`
`@dataclass(frozen=True) class Weights: values: np.ndarray; tickers: tuple[str, ...]`
- **Used by:** PL-03

### portfolio.Comparison: Out-of-sample comparison
**Kind:** type · **Sample:** `tests/contracts/portfolio.Comparison/sample.json`
`@dataclass(frozen=True) class Comparison: realized_var: dict[str, float]`
- **Used by:** PL-03

### portfolio.min_variance: Minimum-variance weights
`def min_variance(cov: Cov) -> Weights`
- **Invariants:** weights sum to 1; long only
- **Errors:** `ValueError` if cov is not positive definite
- **Used by:** PL-03
