# Architecture Example: a multi-package platform

## Multi-Package — Quant Platform (Monorepo)

**Context:** The Factor Lab project has grown. The spec now covers data ingestion on a schedule, a point-in-time store, factor research, backtesting, paper trading, and reporting. Parts run on different schedules (nightly ingestion, interactive research, a long-running paper-trading service), and the team wants research code unable to import trading code.

**Step 1 — Shape:** "Multi-package. Ingestion and paper trading are deployed separately from the research library, and you want `strategies` blocked from importing `execution`, which tooling can enforce between packages. Proposed packages and direction:"

```
reports → backtest → factors → data → core
ingest → data
execution → factors, data
```

The user approves the package map before any package doc is written.

**Result — root `docs/architecture.md` (abridged):**

````markdown
# Factor Lab — Architecture

**Status:** Draft · **Shape:** Multi-package · **Last updated:** 2026-10-14 · **Spec:** [spec.md](spec.md)

## Overview
Nightly, `ingest` pulls prices and fundamentals into a point-in-time store. Researchers use `data`, `factors`, and `backtest` from notebooks. `execution` runs separately, reading signals and placing paper trades. `reports` builds tear-sheets from backtest and live results.

## Packages
| Package | Path | Responsibility | Covers | Depends on | Doc |
|---|---|---|---|---|---|
| `core` | packages/core | Shared types: dates, symbols, calendars, money | QR-03 | — | [core](packages/core/architecture.md) |
| `data` | packages/data | Read-only point-in-time query API | DATA-01–DATA-06 | `core` | [data](packages/data/architecture.md) |
| `ingest` | packages/ingest | Scheduled download, validation, and write to the store | ING-01–ING-04 | `core`, `data` | [ingest](packages/ingest/architecture.md) |
| `factors` | packages/factors | Factor definitions and signal building | FAC-01–FAC-05 | `core`, `data` | [factors](packages/factors/architecture.md) |
| `backtest` | packages/backtest | Vectorized backtests with costs | BT-01–BT-06 | `core`, `data`, `factors` | [backtest](packages/backtest/architecture.md) |
| `execution` | packages/execution | Paper trading service | EXE-01–EXE-04 | `core`, `data`, `factors` | [execution](packages/execution/architecture.md) |
| `reports` | packages/reports | Tear-sheets and comparisons | REP-01–REP-03 | `core`, `backtest` | [reports](packages/reports/architecture.md) |

## Dependency rules
- `core` imports nothing internal.
- Only `ingest` writes to the store; everything else reads through `data`.
- `factors` and `backtest` never import `execution` or `ingest`.
- Enforced by `import-linter` contracts in CI (AD-03).

## Cross-package contracts
- `data.PointInTimeStore` — provided by `data`, used by every package. [Contract](packages/data/contract.md)
- `factors.Signal` (date × symbol → score) — provided by `factors`, used by `backtest` and `execution`. [Contract](packages/factors/contract.md)
- `backtest.Result` (returns, positions, costs) — provided by `backtest`, used by `reports`. [Contract](packages/backtest/contract.md)

## System pipelines
### PL-01: Research backtest
**Trigger:** called from a research notebook · **Covers:** FAC-01–FAC-05, BT-01–BT-06, REP-01
1. `data` → `factors`: `data.PointInTimeStore` (prices and fundamentals as known on each date)
2. `factors` → `backtest`: `factors.Signal`
3. `backtest` → `reports`: `backtest.Result`

### PL-02: Paper trading day
**Trigger:** `execution` service, at each market open · **Covers:** EXE-01–EXE-04
1. `data` → `factors`: `data.PointInTimeStore` (as of the previous close)
2. `factors` → `execution`: `factors.Signal`

*(PL-03, nightly ingest, omitted here.)*

## Project layout
```
packages/core/  packages/data/  packages/ingest/  packages/factors/
packages/backtest/  packages/execution/  packages/reports/
```

## Shared tech stack and tooling
| Area | Choice | Decision |
|---|---|---|
| Workspace | uv workspace, one lockfile | AD-01 |
| Language | Python 3.12 | AD-02 |
| Store | Parquet files + DuckDB queries | AD-04 |
| Market data | Provider B | AD-05 |

Packages are versioned together; one release tag for the repo.

## Decisions
### AD-05: Market data provider
**Status:** Proposed · **Date:** 2026-10-14 · **Scope:** `ingest`, `data`
- **Context:** Checked against DATA-01 (daily prices for all US stocks since 2010, *including delisted*), DATA-03 (fundamentals stamped with the date they became public), and the brief's budget (< $100/month).
- **Decision:** Provider B.
- **Alternatives:** Provider A (free) — fails DATA-01: no delisted companies. Provider C — meets everything but costs about 4× the budget.
- **Consequences:** Ingestion is written against Provider B's API behind `ingest.Source`, so a later switch touches one module.

*(AD-01–AD-04 omitted here.)*

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-14 | Initial architecture | spec.md | AD-01–AD-05 |
````

**Each package** gets a folder. `docs/packages/data/architecture.md` uses the single-package template for that package: its modules, its data layout and its folders, with Interfaces linking to `contract.md` beside it. It carries no Decisions or Changelog; those live in the root. `docs/packages/data/contract.md` holds `### data.PointInTimeStore: …` and the other public symbols, with signatures, invariants and errors. `pipeline-design` later adds each package's `pipelines.md` to the same folder.

Each cross-package symbol names its boundary, so `build-planning` can freeze it before either side is built. `docs/packages/factors/contract.md`:

```markdown
### factors.Signal: Date × symbol score frame
`Signal = DataFrame[SignalSchema]  # index (date, symbol), column score: float64`
- **Invariants:** one row per (date, symbol) in the universe on that date; `score` finite; dates ascending
- **Errors:** constructing one from a frame that fails `SignalSchema` raises `pandera.errors.SchemaError`
- **Boundary:** backtest, execution · **Fixtures:** tests/contracts/factors.Signal/ · **Cases:** two dates × three symbols, a symbol delisted mid-sample, an all-equal cross-section
- **Used by:** backtest, execution
```

Both sides are Python, so the schema is a pandera schema and the fixtures are sample frames. Between runtimes that share no types (a TypeScript service and a Swift app), the schema would be JSON Schema and the fixtures JSON payloads. The contract names the cases; the Phase 0 contract task writes the schema, one fixture per case and a fake `factors` that serves them.

**Notice:**
- The data provider decision is checked against specific `DATA-` requirements and the brief's budget. That's how "which API?" gets answered. The spec stayed vendor-neutral, and the decision lives here.
- The dependency rules are enforceable, not aspirational.
- The root doc stays a map. Detail lives in package docs, so each one stays a readable 1-3 pages.
- System pipelines say which package hands what to which, through which contract. The functions and files inside each package are left to `pipelines.md`.
- Each boundary's cases are named here, so `backtest` and `execution` can build against a fake `factors` in the same milestone instead of waiting for it.
