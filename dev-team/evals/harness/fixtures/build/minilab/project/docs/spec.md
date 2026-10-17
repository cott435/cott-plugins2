# Minilab — Spec

**Status:** Approved · **Last updated:** 2026-10-17 · **Brief:** [brief.md](brief.md)

## Features

### Prices (`DATA`)
**Serves:** Goal 1

**Requirements**
- **DATA-01** A `date,ticker,close` CSV is read row by row.
  - Given a CSV, when it is read, then each row comes back in file order, and a blank close is missing, not zero.
- **DATA-02** Unusable rows are dropped and duplicates resolved.
  - Given rows with blank, zero or negative closes and a repeated (date, ticker), when validated, then those rows are gone, the later of the duplicates wins, and rows are sorted by date, then ticker.
  - Given a requested ticker with no usable row, when validated, then a `KeyError` names it.
- **DATA-03** Every ticker sits on one calendar.
  - Given tickers that start on different dates and miss some dates, when aligned, then the calendar is the dates any ticker trades from the first date on which every ticker has a close, and a missing date takes that ticker's previous close.
- **DATA-04** A long gap is an error, not a fill.
  - Given a ticker missing more than 5 calendar dates in a row, when aligned, then a `GapError` names the ticker.

### Risk (`RISK`)
**Serves:** Goal 2

**Requirements**
- **RISK-01** Daily returns are log returns.
  - Given closes, when returns are computed, then r_t = ln(close_t / close_t−1), dated t.
- **RISK-02** Rolling volatility uses only earlier returns.
  - Given a window of w, when the volatility for date t is computed, then it is the sample standard deviation (n − 1) of the w returns before t, never t's own return, and there is no value until w earlier returns exist.
- **RISK-03** Volatility is annualized over trading days.
  - Given a daily volatility σ, when annualized, then the value is σ·√252.
- **RISK-04** Each ticker gets a whole-period summary.
  - Given returns, when summarized, then the annualized return is 252 × the mean, the annualized volatility is √252 × the sample standard deviation, the Sharpe ratio is their quotient (0 when the volatility is 0; no risk-free rate), and the last rolling volatility is reported.
- **RISK-05** Maximum drawdown comes with its dates.
  - Given closes, when the drawdown is computed, then wealth starts at 1 on the first date, and the result is the deepest fall below the running peak (trough / peak − 1, at most 0) with the date of that peak and the date of the trough; the first if tied. With no fall, both dates are the first date.

### Report (`REP`)
**Serves:** Goal 3

**Requirements**
- **REP-01** The risk report is a JSON file.
  - Given a prices CSV, when the report runs, then `{"tickers": [...]}` is written with one row per ticker, sorted, holding the RISK-04 fields and RISK-05's drawdown (as `max_drawdown`) and both dates.

### Quality
- **QR-01** A run is deterministic.
  - Given the same CSV and window, when the report runs twice, then the files are identical.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-17 | Initial spec | brief.md | DATA-01–DATA-04, RISK-01–RISK-05, REP-01, QR-01 |
