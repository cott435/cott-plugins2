# Minilab — References

**Status:** Approved · **Last updated:** 2026-10-17

### RF-01: Volatility notebook
**File:** `references/vol_notebook.py` · **Hash:** 1e1d95d0 · **Kind:** code · **Milestones:** M1
- **Purpose:** the user's pandas notebook for returns, rolling volatility, annualizing, a summary and drawdown
- **Key parts:** `daily_returns`, `rolling_vol(returns, window)`, `annualize`, `summary`, `max_drawdown`
- **In → Out:** dates × tickers closes → returns, rolling vol, a summary frame, drawdown per ticker
- **Use for:** PL-02 `rolling_vol` and `annualize`, PL-03 `summary_stats` and `max_drawdown` design
- **Caveats:** pandas and numpy, which the project doesn't use (AD-01): reimplement, don't copy
