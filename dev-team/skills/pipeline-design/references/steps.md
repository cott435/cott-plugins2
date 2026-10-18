# Steps, layout and readability rules

Read before writing or changing a step table or the planned layout. The file format is `template.md`.

## Steps

Per pipeline:
- **Entry** `src/<path>/<entry module>::run_<workflow>`, in the pipeline's own entry module (Layout), **Trigger** (a CLI command or a call from another pipeline), **Covers** (spec IDs, including whole-run `QR-` IDs; a constraint a decision meets, such as a data source's licence under AD-02, goes on the Covers of the step that applies it).
- **Step table**, one row per call in order, plus a row per library class (below): Step (function name; `PL-NN.<function>` is its ID), Owner (one component, or component.module; a step with two owners is two steps), In → Out, Spine version, Covers. A step another pipeline provides says `PL-01 as built`; one following a reference cites it (`as RF-01, per-window fit`).
- **In → Out names contract types.** Every Out, and every In another step's Out feeds, is a contract `type` section (`Demand → Profile` resolves to `### profile.Profile: type`; qualify as `profile.Profile` only when two components define the name), and every CamelCase name in the cell must resolve to one. Entry arguments (dates, regions, a config field) and the last step's plain result (a path, frames) stay lower-case. The build freezes each of these types first, with a sample, so every step's spine and tests start at once against it. A type the contract lacks is a contract change: list it and route to `architecture-design` Revise; never invent it here. `dt lint` checks it (`step-io-types`).
- **Library classes are steps.** A class a factory or lookup step returns, which the pipeline then drives through a Protocol (`make_dataset` returning `SingleCropSet` as a `Dataset`), gets its own row right after its factory's: Step the class name, Owner its module, In → Out its constructor's input → the Protocol, Spine version a minimal real class (200 synthetic leaves, a model guessing at random). The entry sketch never calls it, but the build gives it a spine of its own, so wiring waits on that spine, never on the class's upgrade. Two classes behind one factory are two rows.
- **A provider waiting on a probe** (an external API whose probe isn't Answered or Waived) sits behind a Protocol, and the milestone gets a stand-in: a synthetic class row behind the same factory, in a sibling owner folder (`data.weather_synthetic` → `data/weather_synthetic/`), selected by settings. The real provider keeps its row; `build-planning` plans its spine once the probe is Answered.
- **References** (optional): `**References:** RF-01 (remove_seasonality)` after Covers. Never a `references/` path.
- **Entry sketch** (pre-build): calls to the steps in table order and a return, nothing else. A loop, branch or computation is a missing step.

**Contract `Used by:` lines** get the calling PL IDs after the consumer components; symbol IDs are component-qualified even in a single package (`### profile.fit_seasonality: …`).

**Multi-package:** cross-package *system pipelines* are `architecture-design`'s, in the root. A package-local pipeline that is one segment of one names it: `**Entry:** … · **Trigger:** … · **Part of:** PL-05`. Never edit the root.

## Changing a step table

Revise, and Sync when the doc changes, edit an existing table this way:

- Keep step names where the function survives; a split step gets new rows with new function names. Keep the pipeline's ID: a rebuilt package keeps its PL IDs where it can, so its golden cases still apply.
- If the entry sketch is gone (the spine was built), don't recreate it. The step table is the contract the code must match; the code change becomes a task.
- Keep `Used by:` lines true: add the PL ID to a symbol a new step calls, and remove it from one no step of that pipeline calls any more.

## Layout

One entry module per pipeline, never shared, so two pipelines' wiring never touches one file: `pipeline.py` in the component (single package) or package whose only pipeline it is; where a component runs several, `pipelines/pl<NN>_<workflow>.py` each, and an existing `pipeline.py` stays as it is. One module per step owner (`profile.fit` → `profile/fit.py`; an owner given only as `profile` gets one module per related group of steps). A step whose module needs private helpers owns a folder instead (`core.train` → `core/train/`), holding them; no other step's code goes inside it. A step with its own upgrade beyond the spine gets its own module (`validate/flags.py`, `validate/coverage.py`), so its thicken task never shares a file; only steps built and thickened together share one. In a single package each component gets a subfolder whose `__init__.py` exports its contract only, so a later Grow is a folder move. Modules on no step: only `__init__.py`, the entry modules, `__main__.py` for a `python -m` trigger (dispatching each trigger to its entry), and `types.py`. Test folders sit at the repo root in every layout, multi-package included: `tests/intent/<pkg>/`, `tests/unit/<pkg>/`, never under the package's folder. Plan against `build-setup`'s size bar (500 lines per module, 60 per function, or `CONSTRAINTS.md`'s values): split a module expected to pass it now.

## Readability rules

`build-setup` copies these into `CONSTRAINTS.md`; builders and reviewers enforce them.

- One entry function per pipeline, reading as calls to its named steps; each step owned by one component, its function living there.
- No registries, plugin dispatch or config-driven wiring unless an `AD-NN` says so. A new abstraction needs a second real implementation or a seam the architecture named.
- Every spine version is real and minimal, often the baseline, never a mock, stub or hard-coded return; it stays as what upgrades must beat. Only a step calling another pipeline or package may run against that boundary's fixture-backed fake, until the milestone's system task swaps in the real provider; a step consuming another step's output is built and tested on that type's frozen sample, never on a fake of the step. An object with behavior (a Protocol or class) or a call into another component's function is frozen as its Protocol or signature plus a fixture-backed replay double, which is that type's sample, not a fake.
- A decision-backed exception goes on the row or pipeline, citing it (`dataset lookup by name (AD-06)`).
