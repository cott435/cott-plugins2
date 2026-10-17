---
name: pipeline-design
description: Designs each package's pipelines (docs/packages/{pkg}/pipelines.md) - the workflows the user runs, each one entry function calling named steps with a real, minimal spine version, plus the planned file layout. Use when the architecture is approved and a package has no pipelines.md, when new requirements or components land in a package, when a step must be replaced, split or reordered, after a Grow splits a package, or when entry functions no longer match the documented steps.
---

# Pipeline Design

A pipeline is one workflow the user runs: an entry function reading as calls to named steps, each owned by one component, each with a **spine version** (the simplest real implementation) so the first milestone runs it end to end. The planned layout is pre-build: the pipeline's wiring task replaces it with `dt layout`, and then the code is the truth for layout, the step table for call order.

**Not for:** components or technologies (`architecture-design`), golden cases (`test-planning`), tasks (`build-planning`), code or contract changes. This skill writes `docs/packages/*/pipelines.md`, plus PL IDs appended to `contract.md`'s `Used by:` lines, and nothing else.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. `examples.md` here has the template and two New rounds.

## Modes

Start with `dt status --skill pipeline-design`: the mode per package, `uncovered_ids`, `components_unowned`, `drift`, `retired_refs`, `misplaced` and `next ids`.

| Mode | When | Do |
|---|---|---|
| **Blocked** | The architecture isn't Approved | Say which doc needs approval. Stop |
| **New** | A package in scope has no `pipelines.md` | The process below |
| **Extend** | `uncovered_ids` or `components_unowned` non-empty | `references/modes.md` |
| **Revise** | The build found a step to replace, split or reorder (`dt` reports `revise` until re-approval) | `references/modes.md` |
| **Grow** | The architecture became Multi-package (`misplaced` lists a pipeline) | `references/grow.md` |
| **Sync** | `drift` is non-empty | `references/modes.md` |
| **Current** | Nothing to do | Say so and name the next skill. Stop |

Right after an architecture Grow, the new packages show `new` while the old `pipelines.md` still holds their pipelines: that is Grow, not New.

**In scope:** the next stage's packages, or up front, every package and stage. **Read:** the root and package architecture, each package's `contract.md`, the spec IDs in scope (`dt section STAT-01 …`), `dt layout <pkg>` once code exists, and the `docs/references.md` entries for the stage (references waiting: `reference-intake` first). **Don't read** other packages' `pipelines.md`; their `contract.md` is all a step needs.

## Process (New)

```
STATUS ─→ WORKFLOWS (ask) ─→ STEPS ─→ LAYOUT ─→ WRITE ─→ [gate: stop]
```

**1. Workflows.** A pipeline exists because someone runs it, so never derive workflows from the component list. Show the numbered candidates in your message first (trigger, what it does, milestone), saying nothing is written until they confirm. Then one `AskUserQuestion`, this milestone's workflows recommended: 2–4 as one multi-select; more as "All of them" vs "The core set only (1, 2, 4)". Ask separately, one at a time with a guess and default, only what is genuinely unclear. Infer names, triggers, types, order and module split; list them under ASSUMPTIONS.

**2. Steps.** Read `references/steps.md` first. Per pipeline: an ID from `dt next-id PL` (write the section before the next; never count by hand), Entry, Trigger, Covers, a step table with one owner, `In → Out` in contract types and a real spine version per step, and a pre-build entry sketch of step calls only.

**3. Layout.** One entry module per component or package, one module per step owner, each under `build-setup`'s size bar (`references/steps.md`).

**4. Write** `docs/packages/<pkg>/pipelines.md` from the template, each pipeline about 35 lines (`dt lint` `budget`). Append the calling PL IDs to each called contract symbol's `Used by:` line (`- **Used by:** portfolio; PL-02, PL-03`); that leaves an Approved contract Approved. A step needing a different signature, type or error is a contract change: list it and route to `architecture-design` Revise. Fix what `dt lint` reports on every file touched.

## Review Gate (CRITICAL)

Rerun `dt status --skill pipeline-design`. `retired_refs` must be empty; `uncovered_ids` and `components_unowned` too, or each gap under Open questions with a reason (up front, every stage's IDs land on a pipeline). Present:
1. **What was written:** one line per pipeline (ID, title, trigger, steps); the planned layout.
2. **ASSUMPTIONS:** every name, trigger, type, step order and module split you chose.
3. **Open questions.**
4. **Uncovered:** spec IDs or components on no step, and why.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

**Headless:** write the doc, unconfirmed workflows under Open questions, leave Draft, stop.

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set `Status: Approved` and the date. Offer to commit `pipelines.md` and any `contract.md` whose `Used by:` changed; commit only on a yes | Stop. Next: `test-planning` (optional) or `build-planning` (Replan, after a Revise) |
| "Approved, go ahead" | As above | Start the next planning skill (run its `dt status`). Never start code |
| Approved with a small, fully specified change | Make exactly that edit, set Approved | Stop; list the edit |
| Changes, or a hedge ("looks fine I guess") | Edit or ask again; keep Draft | Repeat this gate |
