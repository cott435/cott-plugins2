# Grow

Read when `dt status --skill pipeline-design` reports `grow`, or right after an `architecture-design` Grow. Read `steps.md` (Multi-package) and `template.md` for the sections you move. Ends at the Review Gate in `../SKILL.md`.

`architecture-design` Grow has split the package and written the root's System pipelines, each with a new ID, naming the package pipeline it grew from. If it hasn't, stop and route there.

1. Move each `PL-NN` section of the old `pipelines.md`, unchanged, to `docs/packages/<owner>/pipelines.md`, where the owner is the package that owns its entry function. Steps owned by another package stay as calls to that package's contract, allowed only along the dependency direction.
2. A pipeline a system pipeline grew from keeps its ID as the owning package's segment: step table and Entry kept (step 4 changes only the path), plus `· **Part of:** PL-NN` (the system pipeline's ID) on its Entry line. Never delete it or reuse its ID in the root: TCs and tasks cite it.
3. For each system pipeline, check that every package segment with two or more steps has a package-local pipeline (an existing one, or a new ID from `dt next-id PL` with `**Part of:**` on its Entry line). A one-step segment is just a contract call.
4. Update each `Entry` path (and the Trigger's module) to the package's source folder from the architecture's project layout. Moving the code is a build task, so `dt layout` reports drift until then; list it.
5. Split the planned layout per package, or note that `dt layout` already covers it. Move Retired lines to the package whose pipeline they replaced.
6. Every touched doc goes to Draft. Delete the old `pipelines.md` once it's empty. Then the Review Gate.

IDs never change on a move, and no two live sections share one. That's what keeps every task's `Read:` and every `TC-NN` valid.

## Example: GridLoad M3 splits into packages

**Context:** at the end of M2, `gridload/pipelines.md` holds PL-01 Load readings, PL-02 Seasonality report, PL-03 Held-out forecast (`remove_seasonality` → `forecast_naive` → `score`) and the retired line for PL-04. M3 brings feature engineering with LightGBM. `architecture-design` Grow made the repo Multi-package (`data`, `profile`, `forecast`, `features`, under `packages/<pkg>/src/<pkg>/`) and added one system pipeline, with a new ID from `dt next-id PL`, grown from PL-03:

```markdown
## System pipelines
### PL-05: Research run
**Trigger:** `python -m forecast holdout` (PL-03's entry) · **Covers:** FEAT-01, FC-01, FC-02
1. `data` → `profile`: `data.load_readings`
2. `profile` → `features`: `profile.fit_seasonality`
3. `features` → `forecast`: `features.select`
```

`dt status --skill pipeline-design` reports the four new packages as `new`, but `gridload/pipelines.md` still holds their pipelines and the architecture's Grow is approved, so this is Grow, not New. (Once a moved section's Entry points into another package's folder, `dt` reports `grow` itself, with the pipeline under `misplaced`.)

**Moves:**

| Section in `gridload/pipelines.md` | Goes to | Why |
|---|---|---|
| PL-01 Load readings | `docs/packages/data/pipelines.md` | entry `run_load_readings` is owned by data |
| PL-02 Seasonality report | `docs/packages/profile/pipelines.md` | entry in profile; step `load_readings` stays a call to data's contract (profile → data is allowed) |
| PL-03 Held-out forecast | `docs/packages/forecast/pipelines.md`, as PL-05's forecast segment | entry in forecast; keeps its ID, step table and Entry, and gains `· **Part of:** PL-05` |
| `~~PL-04: Raw periodogram dump~~` | `profile` Retired list | it was folded into PL-02 |

Each moved section keeps its ID, title, table and Covers. Only the Entry path and the Trigger's module change, to the new source folder:

```markdown
## PL-03: Held-out forecast
**Entry:** `packages/forecast/src/forecast/pipeline.py::run_holdout` · **Trigger:** `python -m forecast holdout` · **Part of:** PL-05
```

PL-03 is not deleted or merged into the root: TC-04 and M2's tasks cite it, and the root's PL-05 is a different ID, so no two live sections share one.

**Other segments of PL-05:** data and profile each hand over one contract call (`data.load_readings`, `profile.fit_seasonality`), so they need no segment pipeline. `features` has no pipeline yet, so the gate lists it as uncovered and the next round (Extend) asks the user about the feature-selection workflow and adds PL-06 with `**Part of:** PL-05`, plus a planned layout for it (it's new and unbuilt). The same round adds a `select` row (owner features) to PL-03, so the forecast segment calls `features.select`; that new step needs no planned layout, since PL-03 is built.

**Gate message (excerpt):**

```
Grow: moved PL-01 → data, PL-02 → profile, PL-03 → forecast (now PL-05's forecast segment,
marked Part of: PL-05); PL-04's retired line moved to profile. Deleted docs/packages/gridload/pipelines.md (empty).
All three pipelines.md files are Draft.
Drift until the code moves: every Entry path now points under packages/<pkg>/src/ (a build-planning task).
Uncovered: features owns no pipeline; the feature-selection workflow needs your input (next: Extend).
```
