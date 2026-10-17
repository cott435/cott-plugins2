# Grow

Read when `dt status --skill pipeline-design` reports `grow`, or right after an `architecture-design` Grow. Ends at the Review Gate in `../SKILL.md`.

`architecture-design` Grow has split the package and written the root's System pipelines, each with a new ID, naming the package pipeline it grew from. If it hasn't, stop and route there.

1. Move each `PL-NN` section of the old `pipelines.md`, unchanged, to `docs/packages/<owner>/pipelines.md`, where the owner is the package that owns its entry function. Steps owned by another package stay as calls to that package's contract, allowed only along the dependency direction.
2. A pipeline a system pipeline grew from keeps its ID as the owning package's segment: step table and Entry kept (step 4 changes only the path), plus `· **Part of:** PL-NN` (the system pipeline's ID) on its Entry line. Never delete it or reuse its ID in the root: TCs and tasks cite it.
3. For each system pipeline, check that every package segment with two or more steps has a package-local pipeline (an existing one, or a new ID from `dt next-id PL` with `**Part of:**` on its Entry line). A one-step segment is just a contract call.
4. Update each `Entry` path (and the Trigger's module) to the package's source folder from the architecture's project layout. Moving the code is a build task, so `dt layout` reports drift until then; list it.
5. Split the planned layout per package, or note that `dt layout` already covers it. Move Retired lines to the package whose pipeline they replaced.
6. Every touched doc goes to Draft. Delete the old `pipelines.md` once it's empty. Then the Review Gate.

IDs never change on a move, and no two live sections share one. That's what keeps every task's `Read:` and every `TC-NN` valid.

## Example: quant M3 splits into packages

**Context:** at the end of M2, `quant/pipelines.md` holds PL-01 Load prices, PL-02 Covariance report, PL-03 Min-variance backtest (`estimate_cov` → `min_variance` → `compare`) and the retired line for PL-04. M3 brings feature engineering with torch. `architecture-design` Grow made the repo Multi-package (`data`, `stats`, `portfolio`, `features`, under `packages/<pkg>/src/<pkg>/`) and added one system pipeline, with a new ID from `dt next-id PL`, grown from PL-03:

```markdown
## System pipelines
### PL-05: Research run
**Trigger:** `python -m portfolio backtest` (PL-03's entry) · **Covers:** FEAT-01, PORT-01, PORT-02
1. `data` → `stats`: `data.load_prices`
2. `stats` → `features`: `stats.estimate_cov`
3. `features` → `portfolio`: `features.screen`
```

`dt status --skill pipeline-design` reports the four new packages as `new`, but `quant/pipelines.md` still holds their pipelines and the architecture's Grow is approved, so this is Grow, not New. (Once a moved section's Entry points into another package's folder, `dt` reports `grow` itself, with the pipeline under `misplaced`.)

**Moves:**

| Section in `quant/pipelines.md` | Goes to | Why |
|---|---|---|
| PL-01 Load prices | `docs/packages/data/pipelines.md` | entry `run_load_prices` is owned by data |
| PL-02 Covariance report | `docs/packages/stats/pipelines.md` | entry in stats; step `load_prices` stays a call to data's contract (stats → data is allowed) |
| PL-03 Min-variance backtest | `docs/packages/portfolio/pipelines.md`, as PL-05's portfolio segment | entry in portfolio; keeps its ID, step table and Entry, and gains `· **Part of:** PL-05` |
| `~~PL-04: Raw eigen dump~~` | `stats` Retired list | it was folded into PL-02 |

Each moved section keeps its ID, title, table and Covers. Only the Entry path and the Trigger's module change, to the new source folder:

```markdown
## PL-03: Min-variance backtest
**Entry:** `packages/portfolio/src/portfolio/pipeline.py::run_backtest` · **Trigger:** `python -m portfolio backtest` · **Part of:** PL-05
```

PL-03 is not deleted or merged into the root: TC-04 and M2's tasks cite it, and the root's PL-05 is a different ID, so no two live sections share one.

**Other segments of PL-05:** data and stats each hand over one contract call (`data.load_prices`, `stats.estimate_cov`), so they need no segment pipeline. `features` has no pipeline yet, so the gate lists it as uncovered and the next round (Extend) asks the user about the feature-screening workflow and adds PL-06 with `**Part of:** PL-05`, plus a planned layout for it (it's new and unbuilt). The same round adds a `screen` row (owner features) to PL-03, so the portfolio segment calls `features.screen`; that new step needs no planned layout, since PL-03 is built.

**Gate message (excerpt):**

```
Grow: moved PL-01 → data, PL-02 → stats, PL-03 → portfolio (now PL-05's portfolio segment,
marked Part of: PL-05); PL-04's retired line moved to stats. Deleted docs/packages/quant/pipelines.md (empty).
All three pipelines.md files are Draft.
Drift until the code moves: every Entry path now points under packages/<pkg>/src/ (a build-planning task).
Uncovered: features owns no pipeline; the feature-screening workflow needs your input (next: Extend).
```
