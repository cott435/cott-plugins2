# Quant Lab — Spec

**Status:** Approved · **Last updated:** 2026-10-15 · **Brief:** [brief.md](brief.md)

## Features

### Prices (`DATA`)
**Serves:** Goal 1

**Requirements**
- **DATA-01** A command loads daily prices for a date range and universe.
  - Given a stored dataset, when prices for 2015–2020 are requested, then a T×N table of adjusted closes is returned.
- **DATA-02** Delisted names stay in the universe until their delisting date.
  - Given a name delisted in 2018, when 2015–2020 is loaded, then it is present up to 2018 and absent after.
- **DATA-03** ~~Prices are cached in memory.~~ Removed 2026-10-15: not needed at this size.

### Statistics (`STAT`)
**Serves:** Goal 2

**Requirements**
- **STAT-01** PCA of returns reports the variance explained by each factor.
  - Given returns, when PCA runs, then eigenvalues sum to the total variance.
- **STAT-02** Covariance is estimated by sample or shrinkage.
  - Given returns, when shrinkage is chosen, then the estimate is positive definite.
- **STAT-03** Random-matrix cleaning removes eigenvalues below the Marchenko–Pastur edge.
  - Given pure noise, when cleaned, then no eigenvalue exceeds the edge.
- **STAT-04** A covariance report is written for a run.
  - Given a run, when it finishes, then a report lists the top factors.

### Portfolios (`PORT`)
**Serves:** Goal 3

**Requirements**
- **PORT-01** A minimum-variance portfolio is built from a covariance estimate.
  - Given a covariance, when min-var runs, then weights sum to one.
- **PORT-02** Portfolios are compared on out-of-sample variance against equal weight.
  - Given two portfolios, when compared, then realized variance is reported for each.

### Quality
- **QR-01** Every run is reproducible from its seed.
  - Given the same seed and data, when a run repeats, then outputs match exactly.
- **QR-02** A full covariance report runs in under a minute on a laptop.
  - Given 500 names and 10 years, when the report runs, then it finishes in under 60 s.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-15 | Initial spec | brief.md | DATA-01–DATA-03, STAT-01–STAT-04, QR-01, QR-02 |
| 2026-10-15 | Classical portfolios | ideas/classical-portfolios.md | PORT-01, PORT-02; DATA-03 (removed) |
