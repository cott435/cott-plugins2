---
name: pipeline-design
description: Designs each package's pipelines (docs/packages/<pkg>/pipelines.md) — the workflows the user actually runs, each as one entry function that calls named steps, every step owned by one component and given a real, minimal spine version — plus the planned file layout that follows from them. Use when the architecture is approved and a package in scope has no pipelines.md, when new spec requirements or components land in a package, when the build shows a step must be replaced, split or reordered, when an architecture Grow has split a package, or when entry functions in the code no longer match the documented steps.
---

# Pipeline Design

## Overview

The architecture says which components exist and what they promise. A pipeline says how one workflow the user runs moves through them: an entry function that reads top to bottom as calls to named steps, each step a function owned by one component. Each step also has a **spine version**, the simplest real implementation (sample covariance, equal weight, a random agent), so the first build task can run the whole pipeline end to end before anything gets clever.

The file layout follows from the pipelines: one entry module, one module per step owner. It's written as a pre-build section that the spine task replaces with a pointer to `dt layout`. After that, the code is the truth for layout and the step table is the truth for call order.

## When to Use

- `docs/architecture.md` is `Approved` and a package in scope has no `pipelines.md`
- New spec IDs or components landed in a package (an Extend round of the architecture)
- The build found a step must be replaced, split or reordered
- An architecture Grow split a package and its pipelines must move
- An entry function in the code no longer calls what the step table says (`dt layout` reports drift)

**Not for:**
- Choosing technologies, components or dependency direction (use `architecture-design`)
- Golden cases and expected outputs (use `test-planning`)
- Ordering work into tasks or milestones (use `build-planning`)
- Writing or running code, or changing a contract. This skill writes `docs/packages/*/pipelines.md`, plus PL IDs appended to `contract.md`'s `Used by:` lines

## Running `dt`

`dt` below means `python3 ../../scripts/dt.py`, resolved relative to this skill's own folder, run from the project root. dev-team2 must be installed as a whole plugin for that path to exist. The SessionStart hook also prints the resolved command (`dt: python3 …`).

## Modes

Start every run with `dt status --skill pipeline-design`. It prints the mode per package (`packages: stats=new, data=current`), `uncovered_ids`, `components_unowned`, `drift`, `retired_refs`, `misplaced` and `next ids`.

| Mode | When | Do |
|---|---|---|
| **Blocked** | The architecture isn't Approved | Say which doc needs approval. Stop |
| **New** | A package in scope has no `pipelines.md` | Full process below |
| **Extend** | `uncovered_ids` or `components_unowned` is non-empty for an existing `pipelines.md` | Add pipelines or steps. Existing IDs and rows stay untouched |
| **Revise** | The build caught something: a step is replaced, split or reordered. `dt` reports `revise` once `pipelines.md` is Draft but Approved at `HEAD` | Edit the step table; Status back to Draft; list the tasks affected |
| **Grow** | The architecture became Multi-package. `dt` reports `grow` when `misplaced` lists a pipeline whose Entry lies in another package's source folder | Move each `PL-NN` section to its new package by owner |
| **Sync** | `drift` is non-empty | List mismatches; the user picks which side changes |
| **Current** | Nothing to do | Say so and name the next skill. Stop |

`dt status` reports every mode. Two cases need judgment: a Revise starts from what the build found (the `revise` mode then holds until re-approval), and right after an architecture Grow the new packages show `new` while the old `pipelines.md` still holds their pipelines; that is Grow, not New.

**In scope:** the next milestone's packages, or every package when the user plans up front. **Read:** the root and package architecture, each package's `contract.md`, the spec IDs in scope (`dt section STAT-01 STAT-02 …`, not the whole spec), and `dt layout <pkg>` once code exists. **Don't read** other packages' `pipelines.md`; their `contract.md` is all a step needs.

## The Process (New Mode)

```
STATUS ─→ WORKFLOWS (ask) ─→ STEPS ─→ LAYOUT ─→ CHECK ─→ WRITE ─→ [gate: stop]
```

### Step 1: Ask Which Workflows the User Will Actually Run

A pipeline exists because someone runs it. Don't derive workflows from the component list. Ask, one question at a time, each with your guess and the default you'll use if they don't care (agent-skills `interview-me`):

```
Q:       Which commands will you actually run in M1?
GUESS:   `load` to pull prices for a date range, then `cov-report` to see PCA and cleaning.
DEFAULT: those two; the backtest waits for M2.
```

Ask only what the user must decide: which workflows exist, which belong to this milestone, and scope cuts. Infer the rest (names, triggers, types, step order, module split) and list it under ASSUMPTIONS at the gate. Each confirmed workflow becomes one pipeline.

### Step 2: Steps

For each pipeline, take an ID from `dt next-id PL` (write the section before asking for the next one; never count by hand). Then fill in:

- **Entry:** `src/<path>/pipeline.py::run_<workflow>`. One entry function per pipeline.
- **Trigger:** how it runs: a CLI command (`python -m quant.stats cov-report`) or a call from another pipeline.
- **Covers:** the spec IDs the pipeline as a whole satisfies, including `QR-` IDs that apply to the whole run.
- **Step table:** one row per call the entry makes, in order.
  - **Step** is the function name. `PL-NN.<function>` is its ID; tasks cite it.
  - **Owner** is one component (`stats`) or component and module (`stats.cov`). The part before the dot must be a component or package in the architecture. A step with two owners is two steps.
  - **In → Out** uses the contract's types (`Returns → Cov`).
  - **Spine version** is real and minimal (see the rules below). A step another pipeline already provides says so: `PL-01 as built`.
  - **Covers** lists the spec IDs that step satisfies.
- **Entry sketch** (pre-build): the entry function in the project's language, nothing but calls to the steps, in table order, and a return. A loop, branch or computation in the sketch is a missing step.

**Multi-package:** pipelines that cross packages are *system pipelines*. `architecture-design` writes them in the root architecture as package → package steps over contracts. This skill writes the package-local pipelines. A package-local pipeline that is one segment of a system pipeline names it on its Entry line: `**Entry:** … · **Trigger:** … · **Part of:** PL-05`. Never edit the root.

### Step 3: Layout

Derive the planned layout from the pipelines, not from habit:

- One entry module per component (single package) or per package (multi), holding that unit's entry functions: `pipeline.py`.
- One module per step owner: owner `stats.cov` → `stats/cov.py`. An owner given only as `stats` gets one module per related group of steps.
- In a single package, each component gets its own subfolder whose `__init__.py` exports its contract only. Cross-component imports go through that `__init__`. That makes a later Grow a folder move.
- Allowed modules that sit on no step: `__init__.py`, `pipeline.py`, `__main__.py` for a `python -m` trigger, and a `types.py` for contract types. Anything else on no step is a red flag.
- Test folders: `tests/intent/<pkg>/` and `tests/unit/<pkg>/`. Fixtures belong to `test-planning`.

**Size limits:** plan against the bar `build-setup` will enforce: 500 code lines per module and 60 per function, or `CONSTRAINTS.md`'s values (`CR-` size rule) when it exists. A module you expect to pass the limit is split by step now, not after the build hits the gate.

### Step 4: Check the Readability Rules

These rules are standard for every project. `build-setup` copies them into the Readability section of `CONSTRAINTS.md` so builders and reviewers enforce them:

- One entry function per pipeline. It reads top to bottom as calls to its named steps.
- Each step is owned by one component, and its function lives there.
- No registries, plugin dispatch or config-driven wiring unless an `AD-NN` says so.
- A new abstraction needs a second real implementation or a seam the architecture named.
- Every step's spine version is real and minimal, often the baseline (sample covariance, equal weight, TWAP, a random policy). Never a mock, stub or hard-coded return value. It stays in the code as the thing upgrades must beat.

An exception backed by a decision goes on the affected row or pipeline, citing it (`env lookup by name (AD-06)`), so `build-setup` and reviewers can see it.

### Step 5: Write the Draft

Write `docs/packages/<pkg>/pipelines.md` from the template in `examples.md`: header line, one `## PL-NN: Title` section per pipeline with its Entry/Trigger/Covers lines, step table and `### Entry sketch (pre-build — removed by spine task)`, then `## Planned layout (pre-build — removed by spine task)`, `## Open questions` and `## Retired`. Keep the doc to two pages.

**Contract `Used by:` lines.** For each contract symbol a step calls, append the calling PL IDs to that symbol's `Used by:` line in `contract.md`, after the consumer components `architecture-design` wrote: `- **Used by:** portfolio; PL-02, PL-03`. Symbol IDs are component-qualified even in a single package (`### stats.estimate_cov: …`). That append is the only edit this skill makes to `contract.md`, and it doesn't send an Approved contract back to Draft (`dt lint` ignores it). A step that needs a different signature, type or error is a contract change: list it and route to `architecture-design` Revise.

Then run `dt lint` on every file touched and fix what it reports.

## Review Gate (CRITICAL)

Run `dt status --skill pipeline-design` again. `uncovered_ids` and `components_unowned` must be empty, or each gap is under Open questions with a reason (a spec ID deliberately left for a later milestone is fine; say which). `retired_refs` must be empty.

Then present:

1. **What was written:** each pipeline as ID, title, trigger and its steps in one line; the planned layout.
2. **ASSUMPTIONS:** every name, trigger, type, step order and module split you chose rather than asked.
3. **Open questions.**
4. **Uncovered:** spec IDs or components on no step, and why.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

**No live user** (headless run): write the doc, put the workflow confirmations you couldn't get under Open questions, leave it at Draft, and stop.

**Handling the reply.** Approval is an unambiguous yes in the user's own words.

| The user says | Do | Then |
|---|---|---|
| Approved | Set `Status: Approved` and the date. Offer to commit `pipelines.md` and any `contract.md` whose `Used by:` lines changed; commit only on a yes | Stop. Next: `test-planning` (optional: golden cases and fixtures) or `build-planning` (Replan, after a Revise) |
| "Approved, go ahead" | As above | Start the next planning skill (run its `dt status`). Never start code |
| Approved with a small, fully specified change (a rename, a reworded trigger) | Make exactly that edit, set Approved | Stop; list the edit |
| Changes requested, or a hedge ("looks fine I guess") on a workflow or a dropped step | Edit or ask again; keep Draft | Repeat this gate |

## Extend Mode

New spec IDs or components arrived. Take `uncovered_ids` and `components_unowned` from `dt status`. For each ID: an existing step covers it (add it to Covers), an existing step changes its In → Out (edit that row; check the contract still matches, else route to `architecture-design` Revise), or a new workflow or step is needed. Ask about new workflows exactly as in New mode. New pipelines get new IDs and their own entry sketch; existing IDs, rows and step names don't change. Append new PL IDs to the `Used by:` lines of the contract symbols they call.

**Layout in Extend.** A `## Planned layout (pre-build — removed by spine task)` section lives only while some pipeline in the doc is unbuilt; `dt lint` flags `prebuild-left` once every pipeline is built. So:
- **A new, unbuilt pipeline:** add its modules to the planned layout. If the spine already removed it, write a new one holding only the new modules, marked against the existing tree from `dt layout <pkg>`.
- **Only new steps on built pipelines:** write no planned layout. Name each new module at the gate (owner → `<owner>/<module>.py`); `build-planning` puts it in the task's `Files likely`.

Status back to Draft, then the Review Gate, highlighting only what changed.

## Revise Mode

The build learned something: a step is replaced, split or reordered (a shrinkage step must come before cleaning). If a decision changed, `architecture-design` Revise goes first; cite its `AD-NN` on the row.

1. Edit the step table. Keep step names where the function survives; a split step gets new rows with new function names. Keep the pipeline's ID: a rebuilt package keeps its PL IDs where it can, so its golden cases still apply.
2. If the entry sketch is gone (the spine was built), don't recreate it. The step table is the contract the code must match; the code change becomes a task.
3. Keep `Used by:` lines true: add the PL ID to a symbol a new step calls, and remove it from one no step of that pipeline calls any more.
4. A pipeline dropped entirely collapses to one line under Retired: `- ~~PL-04: Raw eigen dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)`. Delete its section, and its ID stays retired forever.
5. Set Status to Draft. At the gate, list the tasks whose `Step:` or `Read:` touches the changed rows and tell the user they pause: while this doc is Draft, `dt status --skill build-planning` reports `blocked` (waiting for approval). After approval, `build-planning` Replan follows (its `dt status` reports `replan` and lists this doc under `changed_since_plan`), plus `test-planning` Revise if an expected output changes. This skill never edits `tasks/`.

## Grow Mode

`architecture-design` Grow has split the package and written the root's System pipelines, each with a new ID, naming the package pipeline it grew from. If it hasn't, stop and route there.

1. Move each `PL-NN` section of the old `pipelines.md`, unchanged, to `docs/packages/<owner>/pipelines.md`, where the owner is the package that owns its entry function. Steps owned by another package stay as calls to that package's contract, allowed only along the dependency direction.
2. A pipeline a system pipeline grew from keeps its ID as the owning package's segment: step table and Entry kept (step 4 changes only the path), plus `· **Part of:** PL-NN` (the system pipeline's ID) on its Entry line. Never delete it or reuse its ID in the root: TCs and tasks cite it.
3. For each system pipeline, check that every package segment with two or more steps has a package-local pipeline (an existing one, or a new ID from `dt next-id PL` with `**Part of:**` on its Entry line). A one-step segment is just a contract call.
4. Update each `Entry` path (and the Trigger's module) to the package's source folder from the architecture's project layout. Moving the code is a build task, so `dt layout` reports drift until then; list it.
5. Split the planned layout per package, or note that `dt layout` already covers it. Move Retired lines to the package whose pipeline they replaced.
6. Every touched doc goes to Draft. Delete the old `pipelines.md` once it's empty. Then the Review Gate.

IDs never change on a move, and no two live sections share one. That's what keeps every task's `Read:` and every `TC-NN` valid.

## Sync Mode

`dt layout <pkg>` printed `PL-02: drift — calls […] vs steps […]`. For each mismatch, show both sides and ask which changes:

- **The doc changes** when the code found a better order or a real extra step. Edit the table (as Revise), Status to Draft.
- **The code changes** when it broke a rule: logic in the entry, a step owned by two components, a registry with no AD. Leave the doc, and list the fix for `build-planning` Replan.

Never rewrite the table to match code that breaks a readability rule.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I can infer the workflows from the components" | Components say what exists, not what the user runs. Inferred workflows produce pipelines nobody triggers. Ask. |
| "A registry keeps it extensible" | It hides the call path the entry function exists to show. It needs an `AD-NN`, a second real implementation, or both. |
| "The spine step can be a mock for now" | A mock passes a smoke test and proves nothing. The baseline is usually a few lines and is what the upgrade must beat. |
| "This step is shared, so two components own it" | Then it's two steps, or the architecture is missing a component. One owner per step. |
| "The entry function needs a bit of logic to glue steps" | Glue is a step with a name and an owner. Logic in the entry is what the reader can't find later. |
| "I'll put everything in one module for now" | The layout comes from the step owners. One module per owner is what makes tasks small and Grow a folder move. |
| "The user said go ahead, so I'll start building" | Go ahead means the next planning skill. Code starts after `build-planning` and `build-setup`. |

## Red Flags

- A pipeline the user never confirmed, or one invented from the component list
- A step with two owners, or an owner that isn't a component in the architecture
- Logic in the entry sketch: a loop, branch or computation instead of a named step
- A spine version that says mock, stub, TODO, "returns zeros" or "hard-coded"
- A layout module that sits on no step, or a step whose owner has no module
- A registry, plugin dispatch or config-driven wiring with no `AD-NN`
- A planned module or entry function expected to pass the size limits
- A renumbered or reused PL ID, two live sections with one ID, or a cited pipeline deleted on Grow; a retired pipeline kept in full
- An edit to the root architecture, `tasks/`, `src/` or any test, or to `contract.md` beyond PL IDs on `Used by:` lines
- Approval taken from a hedge, or code or a build plan started in the same turn

## Verification

- [ ] `dt status --skill pipeline-design` was run first, and again at the gate; `uncovered_ids` and `components_unowned` are empty or each gap is explained under Open questions
- [ ] Every workflow was confirmed by the user (or, headless, listed under Open questions)
- [ ] Every PL has Entry, Trigger, Covers, a step table with a real Spine version on every row, and (pre-build) an entry sketch of calls only
- [ ] Every step has exactly one owner that exists in the architecture
- [ ] The planned layout follows from the owners, and no module is planned past the size limits
- [ ] IDs came from `dt next-id PL`; moved pipelines kept their IDs (a Grow segment marked `**Part of:**` on its Entry line); retired ones are one struck line
- [ ] `dt lint` is clean on every `pipelines.md` touched
- [ ] ASSUMPTIONS, open questions and uncovered items were listed at the gate, and the turn ended there
- [ ] Every contract symbol a step calls lists that PL on its `Used by:` line; nothing else in `contract.md` changed
- [ ] Extend wrote a planned layout only for a new, unbuilt pipeline
- [ ] Nothing outside `docs/packages/*/pipelines.md` and those `Used by:` lines was written

Read `examples.md` in this skill directory for the template, a quant and an RL example, and Revise and Grow rounds.
