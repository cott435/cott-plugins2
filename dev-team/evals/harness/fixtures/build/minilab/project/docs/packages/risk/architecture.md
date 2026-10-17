# risk — Architecture

**Package:** risk · **Status:** Approved · **Last updated:** 2026-10-17 · **Root:** [../../architecture.md](../../architecture.md)

## Overview
Log returns, rolling and annualized volatility (PL-02), and a report with whole-period statistics and drawdowns (PL-03).

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `returns` | Log returns | RISK-01 | `mdata` |
| `vol` | Rolling volatility, annualizing | RISK-02, RISK-03 | — |
| `report` | Summary, drawdown, JSON report | RISK-04, RISK-05, REP-01 | — |

## Interfaces
See [contract.md](contract.md).

## Project layout
```
packages/risk/src/risk/
  __init__.py  types.py  returns.py  vol.py  annualize.py  vol_pipeline.py
  summary.py  drawdown.py  report.py  report_pipeline.py
```
