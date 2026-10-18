# GridLoad — Architecture

**Status:** Approved · **Shape:** Single package · **Last updated:** 2026-10-17 · **Spec:** [spec.md](spec.md)

## Overview
One Python package, `gridload`, with three components: `ingest` reads the meter export, `profile` fits seasonality, `forecast` makes day-ahead forecasts from the profile.

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `ingest` | Load hourly readings per region | LOAD-01, LOAD-02 | — |
| `profile` | Fit and report seasonal profiles | PROF-01, PROF-02 | `ingest` |
| `forecast` | Day-ahead forecasts | FC-01 | `profile` |

## Interfaces
See [packages/gridload/contract.md](packages/gridload/contract.md).

## Decisions
### AD-01: Python 3.12 single package, managed with uv
**Status:** Accepted · **Date:** 2026-10-17 · **Scope:** system
- **Context:** Laptop only, one analyst.
- **Decision:** One package, uv.
- **Alternatives:** Poetry — slower.
- **Consequences:** One lock file.
- **Probe:** none — no external service

### AD-02: Hourly weather from the public weather API
**Status:** Proposed · **Date:** 2026-10-17 · **Scope:** ingest
- **Context:** Forecasts need the weather that was forecast at the time, not the actuals.
- **Decision:** The public API's hourly history endpoint, stored locally.
- **Alternatives:** A paid feed — over budget.
- **Consequences:** One free key, held by the user.
- **Probe:** PB-01 — does the history reach 2015, and in local time or UTC?

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-17 | Initial architecture | brief.md | AD-01, AD-02 |
