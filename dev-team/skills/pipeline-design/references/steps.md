# Steps, layout and readability rules

Read before writing or changing a step table or the planned layout. The file format is `template.md`.

## Steps

Per pipeline:
- **Entry** `src/<path>/pipeline.py::run_<workflow>`, **Trigger** (a CLI command or a call from another pipeline), **Covers** (spec IDs, including whole-run `QR-` IDs; a constraint a decision meets, such as a data source's licence under AD-02, goes on the Covers of the step that applies it).
- **Step table**, one row per call in order: Step (function name; `PL-NN.<function>` is its ID), Owner (one component, or component.module; a step with two owners is two steps), In → Out, Spine version, Covers. A step another pipeline provides says `PL-01 as built`; one following a reference cites it (`as RF-01, per-window fit`).
- **In → Out names contract types.** Every Out, and every In another step's Out feeds, is a contract `type` section (`Returns → Cov` resolves to `### stats.Cov: type`; qualify as `stats.Cov` only when two components define the name), and every CamelCase name in the cell must resolve to one. Entry arguments (dates, a universe, a config field) and the last step's plain result (a path, frames) stay lower-case. The build freezes each of these types first, with a sample, so every step's spine and tests start at once against it. A type the contract lacks is a contract change: list it and route to `architecture-design` Revise; never invent it here. `dt lint` checks it (`step-io-types`).
- **References** (optional): `**References:** RF-01 (remove_market)` after Covers. Never a `references/` path.
- **Entry sketch** (pre-build): calls to the steps in table order and a return, nothing else. A loop, branch or computation is a missing step.

**Contract `Used by:` lines** get the calling PL IDs after the consumer components; symbol IDs are component-qualified even in a single package (`### stats.estimate_cov: …`).

**Multi-package:** cross-package *system pipelines* are `architecture-design`'s, in the root. A package-local pipeline that is one segment of one names it: `**Entry:** … · **Trigger:** … · **Part of:** PL-05`. Never edit the root.

## Changing a step table

Revise, and Sync when the doc changes, edit an existing table this way:

- Keep step names where the function survives; a split step gets new rows with new function names. Keep the pipeline's ID: a rebuilt package keeps its PL IDs where it can, so its golden cases still apply.
- If the entry sketch is gone (the spine was built), don't recreate it. The step table is the contract the code must match; the code change becomes a task.
- Keep `Used by:` lines true: add the PL ID to a symbol a new step calls, and remove it from one no step of that pipeline calls any more.

## Layout

One `pipeline.py` entry module per component (single package) or package; one module per step owner (`stats.cov` → `stats/cov.py`; an owner given only as `stats` gets one module per related group of steps). A step with its own upgrade beyond the spine gets its own module (`validate/flags.py`, `validate/coverage.py`), so its thicken task never shares a file; only steps built and thickened together share one. In a single package each component gets a subfolder whose `__init__.py` exports its contract only, so a later Grow is a folder move. Modules on no step: only `__init__.py`, `pipeline.py`, `__main__.py` for a `python -m` trigger, and `types.py`. Test folders sit at the repo root in every layout, multi-package included: `tests/intent/<pkg>/`, `tests/unit/<pkg>/`, never under the package's folder. Plan against `build-setup`'s size bar (500 lines per module, 60 per function, or `CONSTRAINTS.md`'s values): split a module expected to pass it now.

## Readability rules

`build-setup` copies these into `CONSTRAINTS.md`; builders and reviewers enforce them.

- One entry function per pipeline, reading as calls to its named steps; each step owned by one component, its function living there.
- No registries, plugin dispatch or config-driven wiring unless an `AD-NN` says so. A new abstraction needs a second real implementation or a seam the architecture named.
- Every spine version is real and minimal, often the baseline, never a mock, stub or hard-coded return; it stays as what upgrades must beat. Only a step calling another pipeline or package may run against that boundary's fixture-backed fake, until the milestone's system task swaps in the real provider; a step consuming another step's output is built and tested on that type's frozen sample, never on a fake of the step. An object with behavior (a Protocol or class) or a call into another component's function is frozen as its Protocol or signature plus a fixture-backed replay double, which is that type's sample, not a fake.
- A decision-backed exception goes on the row or pipeline, citing it (`env lookup by name (AD-06)`).
