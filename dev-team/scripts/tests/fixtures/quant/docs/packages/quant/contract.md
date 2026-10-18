# quant — Contract

**Package:** quant · **Status:** Approved · **Last updated:** 2026-10-15 · **Architecture:** [../../architecture.md](../../architecture.md)

## data

### data.RawPrices: type
`@dataclass(frozen=True) class RawPrices: rows: pd.DataFrame  # date, ticker, close`
- **Invariants:** one row per (date, ticker); dates sorted; no universe applied yet
- **Boundary:** data · **Fixtures:** tests/contracts/data.RawPrices/ · **Cases:** two raw rows
- **Used by:** PL-01

### data.Prices: type
`@dataclass(frozen=True) class Prices: close: pd.DataFrame  # T×N, index dates, columns tickers`
- **Invariants:** a name has values only between its listing and delisting dates; `.returns() -> Returns`
- **Boundary:** stats · **Fixtures:** tests/contracts/data.Prices/ · **Cases:** a 2×2 panel
- **Used by:** PL-01, PL-02

### data.load_prices: Point-in-time prices
`def load_prices(universe: tuple[str, ...], start: date, end: date) -> Prices`
- **Invariants:** T×N; a name appears only between its listing and delisting dates
- **Errors:** `KeyError` for an unknown ticker; `ValueError` if start > end
- **Boundary:** stats · **Fixtures:** tests/contracts/data.load_prices/ · **Cases:** a 2×2 panel
- **Used by:** PL-01, PL-02

## stats

### stats.Returns: type
`@dataclass(frozen=True) class Returns: values: np.ndarray; tickers: tuple[str, ...]  # T×N`
- **Invariants:** no NaN; T ≥ 2
- **Boundary:** stats · **Fixtures:** tests/contracts/stats.Returns/ · **Cases:** 3×2 returns
- **Used by:** PL-02, PL-03

### stats.Cov: type
`@dataclass(frozen=True) class Cov: values: np.ndarray; tickers: tuple[str, ...]; n_obs: int  # N×N`
- **Invariants:** symmetric; positive semi-definite; `tickers` in column order
- **Boundary:** stats, portfolio · **Fixtures:** tests/contracts/stats.Cov/ · **Cases:** a 2×2 covariance
- **Used by:** PL-02, PL-03

### stats.Factors: type
`@dataclass(frozen=True) class Factors: loadings: np.ndarray; explained: np.ndarray  # N×K, K`
- **Invariants:** `explained` sorted descending, sums to ≤ 1
- **Boundary:** stats · **Fixtures:** tests/contracts/stats.Factors/ · **Cases:** two factors
- **Used by:** PL-02

### stats.CovReport: type
`@dataclass(frozen=True) class CovReport: table: str; factors: Factors`
- **Invariants:** `table` lists every factor in `factors`
- **Boundary:** stats · **Fixtures:** tests/contracts/stats.CovReport/ · **Cases:** a two-factor report
- **Used by:** PL-02

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: Literal["sample", "shrunk"] = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** PL-02, PL-03

### stats.clean_eigen: Random-matrix cleaning
`def clean_eigen(cov: Cov, *, n_obs: int) -> Cov`
- **Invariants:** same shape; no eigenvalue above the Marchenko–Pastur edge is changed
- **Errors:** `ValueError` if n_obs < N
- **Used by:** PL-02

## portfolio

### portfolio.Weights: type
`@dataclass(frozen=True) class Weights: values: np.ndarray; tickers: tuple[str, ...]`
- **Used by:** PL-03

### portfolio.Comparison: type
`@dataclass(frozen=True) class Comparison: realized_var: dict[str, float]`
- **Used by:** PL-03

### portfolio.min_variance: Minimum-variance weights
`def min_variance(cov: Cov) -> Weights`
- **Invariants:** weights sum to 1; long only
- **Errors:** `ValueError` if cov is not positive definite
- **Used by:** PL-03
