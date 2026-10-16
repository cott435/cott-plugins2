# Quant Lab — Architecture

**Status:** Approved · **Shape:** Single package · **Last updated:** 2026-10-15 · **Spec:** [spec.md](spec.md)

## Overview
One Python package, `quant`, with three components: `data` loads prices, `stats` estimates structure, `portfolio` builds portfolios from the estimates.

## Tech stack
| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.12 | AD-01 |
| Storage | Parquet files | AD-03 |

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `data` | Load point-in-time prices | DATA-01, DATA-02, QR-01 | — |
| `stats` | Estimate covariance and factors | STAT-01–STAT-04, QR-02 | `data` |
| `portfolio` | Build and compare portfolios | PORT-01, PORT-02 | `stats`, `data` |

## Interfaces
See [packages/quant/contract.md](packages/quant/contract.md).

## Project layout
```
src/quant/data/  src/quant/stats/  src/quant/portfolio/
tests/
```

## Decisions
### AD-01: Python 3.12 single package, managed with uv
**Status:** Accepted · **Date:** 2026-10-15 · **Scope:** system
- **Context:** Laptop only, solo developer.
- **Decision:** One package, uv.
- **Alternatives:** Poetry — slower.
- **Consequences:** One lock file.

### AD-02: ~~CSV storage~~
**Status:** Superseded by AD-03 · 2026-10-15 — too slow for QR-02

### AD-03: Parquet on local disk
**Status:** Accepted · **Date:** 2026-10-15 · **Scope:** system
- **Context:** AD-02 chose CSV; reading 10 years of 500 names took 40 s, against QR-02.
- **Decision:** Parquet via pyarrow.
- **Alternatives:** A database — more than needed.
- **Consequences:** Binary files; needs pyarrow.

## Risks and open questions
- Free delisting data may be incomplete — DATA-02 is checked against a second source.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-15 | Initial architecture | brief.md | AD-01–AD-03 |
| 2026-10-15 | Portfolio component | ideas/classical-portfolios.md | — |
