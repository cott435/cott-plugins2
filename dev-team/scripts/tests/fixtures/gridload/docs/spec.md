# GridLoad — Spec

**Status:** Approved · **Last updated:** 2026-10-17 · **Brief:** [brief.md](brief.md)

## Features

### Readings (`LOAD`)
**Serves:** Goal 1

**Requirements**
- **LOAD-01** A command loads hourly readings per region for a date range.
  - Given a meter export, when 2019–2020 is loaded, then an hours × regions table in kWh is returned.
- **LOAD-02** Decommissioned meters stay in the history until their removal date.
  - Given a meter removed in 2020, when 2019–2021 is loaded, then its readings stop at the removal date.

### Seasonality (`PROF`)
**Serves:** Goal 2

**Requirements**
- **PROF-01** Daily and weekly Fourier terms are fitted per region.
  - Given a planted daily sine, when fitted, then the daily term recovers its amplitude.
- **PROF-02** A seasonality report is written for a run.
  - Given a fitted profile, when the run finishes, then a report lists each term's share of variance.

### Forecasts (`FC`)
**Serves:** Goal 3

**Requirements**
- **FC-01** A seasonal-naive forecast is made for the next day.
  - Given a profile, when a day is forecast, then 24 hourly values per region are returned.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-17 | Initial spec | brief.md | LOAD-01, LOAD-02, PROF-01, PROF-02, FC-01 |
