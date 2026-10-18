# GridLoad — Roadmap

**Last updated:** 2026-10-17

| Milestone | Name | Source | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | Ingest + seasonality | brief | gridload | PL-01, PL-02 | — | Planned |
| M2 | Seasonal-naive forecast | brief | gridload | — | M1 (profile.Profile from PL-02) | Designed |

*Written by `dt roadmap` from doc statuses and todo checkboxes; never hand-edited.

## M1: Ingest + seasonality
**Exit:** PL-01 and PL-02 run end to end on a synthetic export.
**Plan:** [../tasks/plan.md](../tasks/plan.md)

## M2: Seasonal-naive forecast
**Exit:** A day-ahead forecast per region from the M1 profile.
