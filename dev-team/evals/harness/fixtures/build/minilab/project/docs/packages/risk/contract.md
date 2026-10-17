# risk — Contract

**Package:** risk · **Status:** Approved · **Last updated:** 2026-10-17 · **Architecture:** [architecture.md](architecture.md)

## Types

### risk.Returns: Daily log returns
**Kind:** type · **Sample:** `tests/contracts/risk.Returns/sample.json`
`@dataclass(frozen=True) class Returns: base_date: str; dates: tuple[str, ...]; tickers: tuple[str, ...]; values: Mapping[str, tuple[float, ...]]`
- **Invariants:** `dates` are the prices' dates after the first, which is `base_date`; one value per date and ticker
- **Used by:** PL-02, PL-03

### risk.VolSeries: Rolling volatility
**Kind:** type · **Sample:** `tests/contracts/risk.VolSeries/sample.json`
`@dataclass(frozen=True) class VolSeries: returns: Returns; window: int; annualized: bool; values: Mapping[str, tuple[float | None, ...]]`
- **Invariants:** aligned to `returns.dates`; None until `window` earlier returns exist
- **Used by:** PL-02, PL-03

### risk.TickerSummary: Whole-period statistics
**Kind:** type · **Sample:** `tests/contracts/risk.TickerSummary/sample.json`
`@dataclass(frozen=True) class TickerSummary: ticker: str; ann_return: float; ann_vol: float; sharpe: float; last_vol: float | None`
- **Used by:** PL-03

### risk.Drawdown: Worst fall from a peak
**Kind:** type · **Sample:** `tests/contracts/risk.Drawdown/sample.json`
`@dataclass(frozen=True) class Drawdown: ticker: str; depth: float; peak_date: str`
- **Invariants:** `depth` ≤ 0
- **Used by:** PL-03

### risk.Report: The written report
**Kind:** type · **Sample:** `tests/contracts/risk.Report/sample.json`
`@dataclass(frozen=True) class Report: path: str; rows: tuple[Mapping[str, object], ...]`
- **Invariants:** one row per ticker, sorted; the same rows as the file
- **Used by:** PL-03

## Functions

### risk.vol_series: Annualized rolling volatility of a CSV
`def vol_series(path: str | Path, *, window: int = 20, tickers: Sequence[str] | None = None) -> VolSeries`
- **Invariants:** RISK-01–RISK-03 hold; `annualized` is True
- **Errors:** as `mdata.load_prices`; `ValueError` if `window` < 2
- **Fixtures:** tests/contracts/risk.vol_series/ · **Cases:** two tickers, window 2
- **Used by:** PL-02, PL-03

### risk.risk_report: The JSON risk report
`def risk_report(path: str | Path, out_path: str | Path, *, window: int = 20, tickers: Sequence[str] | None = None) -> Report`
- **Invariants:** REP-01, QR-01
- **Used by:** PL-03

### risk.log_returns: Log returns
`def log_returns(prices: Prices) -> Returns`
- **Errors:** `ValueError` with fewer than two dates
- **Used by:** PL-02

### risk.rolling_vol: Rolling volatility
`def rolling_vol(returns: Returns, window: int) -> VolSeries`
- **Errors:** `ValueError` if `window` < 2
- **Used by:** PL-02

### risk.annualize: Annualized volatility
`def annualize(vol: VolSeries, periods_per_year: int = 252) -> VolSeries`
- **Errors:** `ValueError` if `vol` is already annualized
- **Used by:** PL-02

### risk.summary_stats: Whole-period summary
`def summary_stats(vol: VolSeries, periods_per_year: int = 252) -> tuple[TickerSummary, ...]`
- **Errors:** `ValueError` with fewer than two returns
- **Used by:** PL-03

### risk.max_drawdown: Maximum drawdown
`def max_drawdown(returns: Returns) -> tuple[Drawdown, ...]`
- **Used by:** PL-03

### risk.write_report: Write the report
`def write_report(summary: Sequence[TickerSummary], drawdowns: Sequence[Drawdown], out_path: str | Path) -> Report`
- **Errors:** `ValueError` if summary and drawdowns cover different tickers
- **Used by:** PL-03
