---
name: pipeline-design
description: Designs each package's pipelines (docs/packages/{pkg}/pipelines.md) - the workflows the user runs, each one entry function calling named steps with a real, minimal spine version, plus the planned file layout. Use when the architecture is approved and a package has no pipelines.md, when new requirements or components land in a package, when a step must be replaced, split or reordered, after a Grow splits a package, or when entry functions no longer match the documented steps.
---

# Pipeline Design

A pipeline is one workflow the user runs: an entry function reading as calls to named steps, each owned by one component, each with a **spine version** (the simplest real implementation) so the first milestone runs it end to end. The planned layout is pre-build: the pipeline's wiring task replaces it with `dt layout`, and then the code is the truth for layout, the step table for call order.

**Owns:** `docs/packages/*/pipelines.md` and the `PL-NN` IDs, plus PL IDs appended to `contract.md`'s `Used by:` lines, and nothing else. The file format is `references/template.md`; step, layout and readability rules are `references/steps.md`.

**Not for:** components or technologies (`architecture-design`), golden cases (`test-planning`), tasks (`build-planning`), code or contract changes. A change another skill owns (a contract type, a spec ID) is recorded for its Revise, never made here: `dt route architecture-design "<change>" --from pipeline-design` (or `spec-writing`), and listed at the gate.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root.

## Modes

Start with `dt status --skill pipeline-design`: the mode per package, `uncovered_ids`, `components_unowned`, `drift`, `retired_refs`, `misplaced` and `next ids`. Load the one file the mode's row names.

| Mode | When | Do |
|---|---|---|
| **Blocked** | The architecture isn't Approved | Say which doc needs approval. Stop |
| **New** | A package in scope has no `pipelines.md` | `references/new.md` |
| **Extend** | `uncovered_ids` or `components_unowned` non-empty | `references/extend.md` |
| **Revise** | The build found a step to replace, split or reorder, or `routed_changes` lists one (`dt` reports `revise` until re-approval) | `references/revise.md` |
| **Grow** | The architecture became Multi-package (`misplaced` lists a pipeline) | `references/grow.md` |
| **Sync** | `drift` is non-empty | `references/sync.md` |
| **Current** | Nothing to do | Say so and name the next skill. Stop |

Right after an architecture Grow, the new packages show `new` while the old `pipelines.md` still holds their pipelines: that is Grow, not New.

**In scope:** the next stage's packages, or up front, every package and stage. **Read:** the root and package architecture, each package's `contract.md`, the spec IDs in scope (`dt section STAT-01 …`), `dt layout <pkg>` once code exists, and the `docs/references.md` entries for the stage (references waiting: `reference-intake` first). **Don't read** other packages' `pipelines.md`; their `contract.md` is all a step needs.

## Asking about workflows

A pipeline exists because someone runs it, so never derive workflows from the component list. Show the numbered candidates in your message first (trigger, what it does, milestone), saying nothing is written until they confirm. Then one `AskUserQuestion`, the next stage's workflows recommended (up front, every stage's): 2–4 as one multi-select; more as "All of them" vs "The core set only (1, 2, 4)". Ask separately, one at a time with a guess and default, only what is genuinely unclear. Infer names, triggers, types, order and module split; list them under ASSUMPTIONS.

## Review Gate (CRITICAL)

Rerun `dt status --skill pipeline-design`. `retired_refs` must be empty; `uncovered_ids` and `components_unowned` too, or each gap under Open questions with a reason (up front, every stage's IDs land on a pipeline). Up front, every stage's workflows have pipelines in every package: no package is left `new`. Present:
1. **What was written:** one line per pipeline (ID, title, trigger, steps); the planned layout.
2. **ASSUMPTIONS:** every name, trigger, type, step order and module split you chose.
3. **Open questions.**
4. **Uncovered:** spec IDs or components on no step, and why.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

**Headless:** write the doc, unconfirmed workflows under Open questions, leave Draft, stop.

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set `Status: Approved` and the date; `dt route --done pipeline-design` if `routed_changes` listed any. Offer to commit `pipelines.md` and any `contract.md` whose `Used by:` changed; commit only on a yes | Stop. Next: `test-planning` (optional) or `build-planning` (Replan, after a Revise) |
| "Approved, go ahead" | As above | Start the next planning skill (run its `dt status`). Never start code |
| Approved with a small, fully specified change | Make exactly that edit, set Approved | Stop; list the edit |
| Approved, plus an upstream change (a contract type, a spec ID) | Set Approved; record it with `dt route` (Not for), never make it this turn | Stop; the owner's Revise is next |
| Changes, or a hedge ("looks fine I guess") | Edit or ask again; keep Draft | Repeat this gate |
