# Steps, layout and readability rules

Read before writing or changing a step table or the planned layout. The file format is the template in `../examples.md`.

## Steps

Per pipeline:
- **Entry** `src/<path>/pipeline.py::run_<workflow>`, **Trigger** (a CLI command or a call from another pipeline), **Covers** (spec IDs, including whole-run `QR-` IDs).
- **Step table**, one row per call in order: Step (function name; `PL-NN.<function>` is its ID), Owner (one component, or component.module; a step with two owners is two steps), In → Out in contract types, Spine version, Covers. A step another pipeline provides says `PL-01 as built`; one following a reference cites it (`as RF-01, per-window fit`).
- **References** (optional): `**References:** RF-01 (remove_market)` after Covers. Never a `references/` path.
- **Entry sketch** (pre-build): calls to the steps in table order and a return, nothing else. A loop, branch or computation is a missing step.

**Contract `Used by:` lines** get the calling PL IDs after the consumer components; symbol IDs are component-qualified even in a single package (`### stats.estimate_cov: …`).

**Multi-package:** cross-package *system pipelines* are `architecture-design`'s, in the root. A package-local pipeline that is one segment of one names it: `**Entry:** … · **Trigger:** … · **Part of:** PL-05`. Never edit the root.

## Layout

One `pipeline.py` entry module per component (single package) or package; one module per step owner (`stats.cov` → `stats/cov.py`; an owner given only as `stats` gets one module per related group of steps). In a single package each component gets a subfolder whose `__init__.py` exports its contract only, so a later Grow is a folder move. Modules on no step: only `__init__.py`, `pipeline.py`, `__main__.py` for a `python -m` trigger, and `types.py`. Test folders: `tests/intent/<pkg>/`, `tests/unit/<pkg>/`. Plan against `build-setup`'s size bar (500 lines per module, 60 per function, or `CONSTRAINTS.md`'s values): split a module expected to pass it now.

## Readability rules

`build-setup` copies these into `CONSTRAINTS.md`; builders and reviewers enforce them.

- One entry function per pipeline, reading as calls to its named steps; each step owned by one component, its function living there.
- No registries, plugin dispatch or config-driven wiring unless an `AD-NN` says so. A new abstraction needs a second real implementation or a seam the architecture named.
- Every spine version is real and minimal, often the baseline, never a mock, stub or hard-coded return; it stays as what upgrades must beat. Only a step calling another package may run against that boundary's `contract fake` until the system spine swaps in the real provider.
- A decision-backed exception goes on the row or pipeline, citing it (`env lookup by name (AD-06)`).
