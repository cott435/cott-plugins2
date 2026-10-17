# risk — Pipelines

**Package:** risk · **Status:** Approved · **Last updated:** 2026-10-17 · **Contract:** [contract.md](contract.md)

## PL-02: Volatility
**Entry:** `packages/risk/src/risk/vol_pipeline.py::vol_series` · **Trigger:** called from Python (`risk.vol_series`)
**Covers:** RISK-01–RISK-03

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_prices` | mdata | path → Prices | PL-01 as built | DATA-01 |
| 2 | `log_returns` | risk.returns | Prices → Returns | simple returns | RISK-01 |
| 3 | `rolling_vol` | risk.vol | Returns → VolSeries | expanding stdev of earlier returns | RISK-02 |
| 4 | `annualize` | risk.annualize | VolSeries → VolSeries | daily values pass through | RISK-03 |

### Entry sketch (pre-build — removed by spine task)
```python
def vol_series(path, *, window=20, tickers=None) -> VolSeries:
    prices = load_prices(path, tickers)
    returns = log_returns(prices)
    vol = rolling_vol(returns, window)
    return annualize(vol)
```

## PL-03: Risk report
**Entry:** `packages/risk/src/risk/report_pipeline.py::risk_report` · **Trigger:** called from Python (`risk.risk_report`)
**Covers:** RISK-04, RISK-05, REP-01, QR-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `vol_series` | risk | path → VolSeries | PL-02 as built | RISK-02 |
| 2 | `summary_stats` | risk.summary | VolSeries → TickerSummary | daily mean and stdev | RISK-04 |
| 3 | `max_drawdown` | risk.drawdown | Returns → Drawdown | depth only | RISK-05 |
| 4 | `write_report` | risk.report | TickerSummary, Drawdown → Report | JSON rows | REP-01 |

### Entry sketch (pre-build — removed by spine task)
```python
def risk_report(path, out_path, *, window=20, tickers=None) -> Report:
    vol = vol_series(path, window=window, tickers=tickers)
    summary = summary_stats(vol)
    drawdowns = max_drawdown(vol.returns)
    return write_report(summary, drawdowns, out_path)
```

## Planned layout (pre-build — removed by spine task)
```
packages/risk/src/risk/
  __init__.py   contract exports only
  types.py      Returns, VolSeries, TickerSummary, Drawdown, Report
  returns.py  vol.py  annualize.py  vol_pipeline.py
  summary.py  drawdown.py  report.py  report_pipeline.py
tests/intent/risk/  tests/unit/risk/
```

## Open questions
- Should `rolling_vol` take the window from a config object? (assumed: parameter)
