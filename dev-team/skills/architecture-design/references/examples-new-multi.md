# Architecture Example: a multi-package platform

## Multi-Package — GridLoad Platform (Monorepo)

**Context:** The GridLoad project has grown. The spec now covers meter and weather ingestion on a schedule, an as-of store, feature research, held-out forecast evaluation, a live day-ahead forecast service, and reporting. Parts run on different schedules (nightly ingestion, interactive research, a long-running day-ahead service), and the team wants research code unable to import the live service's code.

**Step 1 — Shape:** "Multi-package. Ingestion and the day-ahead service are deployed separately from the research library. Proposed packages and direction:"

```
reports → forecast → features → data → core
ingest → data
dispatch → features, data
```

The user approves the package map before any package doc is written.

**Result — root `docs/architecture.md` (abridged):**

````markdown
# GridLoad — Architecture

**Status:** Draft · **Shape:** Multi-package · **Last updated:** 2026-10-14 · **Spec:** [spec.md](spec.md)

## Overview
Nightly, `ingest` pulls the utility's meter export and the weather into an as-of store. Researchers use `data`, `features`, and `forecast` from notebooks. `dispatch` runs separately, building each morning's day-ahead forecast and reserve allocation. `reports` builds accuracy reports from held-out and live results.

## Packages
| Package | Path | Responsibility | Covers | Depends on | Doc |
|---|---|---|---|---|---|
| `core` | packages/core | Shared types: hours, regions, calendars, units | QR-03 | — | [core](packages/core/architecture.md) |
| `data` | packages/data | Read-only as-of query API | DATA-01–DATA-06 | `core` | [data](packages/data/architecture.md) |
| `ingest` | packages/ingest | Scheduled download, validation, and write to the store | ING-01–ING-04 | `core`, `data` | [ingest](packages/ingest/architecture.md) |
| `features` | packages/features | Feature definitions and seasonal profiles | FEAT-01–FEAT-05 | `core`, `data` | [features](packages/features/architecture.md) |
| `forecast` | packages/forecast | Seasonal-naive and boosted forecasts, scored on held-out weeks | FC-01–FC-06 | `core`, `data`, `features` | [forecast](packages/forecast/architecture.md) |
| `dispatch` | packages/dispatch | Day-ahead forecast and reserve service | DSP-01–DSP-04 | `core`, `data`, `features` | [dispatch](packages/dispatch/architecture.md) |
| `reports` | packages/reports | Accuracy reports and comparisons | REP-01–REP-03 | `core`, `forecast` | [reports](packages/reports/architecture.md) |

## Dependency rules
- `core` imports nothing internal.
- Only `ingest` writes to the store; everything else reads through `data`.
- `features` and `forecast` never import `dispatch` or `ingest`.
- Enforced by `import-linter` contracts in CI (AD-03).

## Cross-package contracts
- `data.AsOfStore` — provided by `data`, used by every package. [Contract](packages/data/contract.md)
- `features.Features` (hour × region → feature values) — provided by `features`, used by `forecast` and `dispatch`. [Contract](packages/features/contract.md)
- `forecast.Result` (predictions, errors, baseline errors) — provided by `forecast`, used by `reports`. [Contract](packages/forecast/contract.md)

## System pipelines
### PL-01: Held-out evaluation
**Trigger:** called from a research notebook · **Covers:** FEAT-01–FEAT-05, FC-01–FC-06, REP-01
1. `data` → `features`: `data.AsOfStore` (readings, and the weather forecast as issued, at each forecast time)
2. `features` → `forecast`: `features.Features`
3. `forecast` → `reports`: `forecast.Result`

### PL-02: Day-ahead run
**Trigger:** `dispatch` service, each morning at 06:00 · **Covers:** DSP-01–DSP-04
1. `data` → `features`: `data.AsOfStore` (as of 06:00 that day)
2. `features` → `dispatch`: `features.Features`

*(PL-03, nightly ingest, omitted here.)*

## Project layout
```
packages/core/  packages/data/  packages/ingest/  packages/features/
packages/forecast/  packages/dispatch/  packages/reports/
```

## Shared tech stack and tooling
| Area | Choice | Decision |
|---|---|---|
| Workspace | uv workspace, one lockfile | AD-01 |
| Language | Python 3.12 | AD-02 |
| Store | Parquet files + DuckDB queries | AD-04 |
| Weather data | Provider B | AD-05 |

Packages are versioned together; one release tag for the repo.

## Decisions
### AD-05: Weather data provider
**Status:** Proposed · **Date:** 2026-10-14 · **Scope:** `ingest`, `data`
- **Context:** Checked against DATA-01 (hourly weather for every service region since 2015), DATA-03 (forecasts stamped with the hour they were issued, *not only actuals*), and the brief's budget (< $100/month).
- **Decision:** Provider B.
- **Alternatives:** Provider A (free) — fails DATA-03: actuals only, no archived forecasts. Provider C — meets everything but costs about 4× the budget.
- **Consequences:** Ingestion is written against Provider B's API behind `ingest.Source`, so a later switch touches one module.

*(AD-01–AD-04 omitted here.)*

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-14 | Initial architecture | spec.md | AD-01–AD-05 |
````

**Each package** gets a folder. `docs/packages/data/architecture.md` uses the single-package template for that package: its modules, its data layout and its folders, with Interfaces linking to `contract.md` beside it. It carries no Decisions or Changelog; those live in the root. `docs/packages/data/contract.md` holds `### data.AsOfStore: …` and the other public symbols, with signatures, invariants and errors. `pipeline-design` later adds each package's `pipelines.md` to the same folder.

Each cross-package symbol names its boundary, so `build-planning` can freeze it before either side is built. `docs/packages/features/contract.md`:

```markdown
### features.Features: type
`Features = DataFrame[FeatureSchema]  # index (hour, region), columns temp_forecast, lag_24h, lag_168h: float64`
- **Invariants:** one row per (hour, region) for regions with an active meter that hour; values finite; hours ascending
- **Errors:** constructing one from a frame that fails `FeatureSchema` raises `pandera.errors.SchemaError`
- **Boundary:** forecast, dispatch · **Fixtures:** tests/contracts/features.Features/ · **Cases:** two days × three regions, a meter decommissioned mid-sample, a region with a flat-load day
- **Used by:** forecast, dispatch

### features.build_features: Hourly features
`def build_features(store: AsOfStore, start: datetime, end: datetime) -> Features`
- **Invariants:** each hour uses only weather forecasts issued before it (DATA-03)
- **Errors:** `ValueError` if `end` is not after `start`
- **Boundary:** forecast, dispatch · **Fixtures:** tests/contracts/features.build_features/ · **Cases:** the two-day sample above
- **Used by:** forecast, dispatch
```

Both sides are Python, so the schema is a pandera schema and the fixtures are sample frames. Between runtimes that share no types (a TypeScript service and a Swift app), the schema would be JSON Schema and the fixtures JSON payloads. The contract names the cases; the milestone's interface task writes the schema and one fixture per case. `build_features` is a function other packages call, so its Boundary line gets a fake `features` too; a type needs only its samples.

**Notice:**
- The data provider decision is checked against specific `DATA-` requirements and the brief's budget. That's how "which API?" gets answered. The spec stayed vendor-neutral, and the decision lives here.
- The dependency rules are enforceable, not aspirational.
- The root doc stays a map. Detail lives in package docs, so each one stays a readable 1-3 pages.
- System pipelines say which package hands what to which, through which contract. The functions and files inside each package are left to `pipelines.md`.
- Each boundary's cases are named here, so `forecast` and `dispatch` can build against the frozen `Features` samples in the same milestone instead of waiting for `features`.
