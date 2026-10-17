---
name: build-planning
description: Cuts each roadmap stage into build-sized milestones once its pipelines are approved, then plans the next milestone in tasks/plan.md and tasks/todo.md - an interface task first, small test-backed tasks with exclusive Writes, a dependency graph, skill routing and review checkpoints. Use when the next stage's pipelines are approved and it has no milestone rows or plan, when the build shows tasks must be reordered, split or added, or when the active milestone's tasks and exit checkpoint are done.
---

# Build Planning

The build plan says **in what order** the pipelines get built. Once a roadmap stage's pipelines are approved, this skill cuts it into milestones (`M<n>`), vertical slices each runnable end to end, then writes one milestone at a time into `tasks/plan.md` and `tasks/todo.md`: small tasks, many built at once, each ending with a check that leaves the system working. It never builds or runs code and stops at every gate.

**Not for:** plans from agent-skills' `/plan` (foreign); pipelines, oracles or the quality bar (`pipeline-design`, `test-planning`, `build-setup`); building tasks.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. Take IDs, coverage and lint from `dt`, never by hand. Templates: `examples.md`.

## Documents and IDs

- **Write only:** `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, the roadmap's milestone table and `## M<n>` sections, and the AGENTS.md doc map. Never the stage table or `## S<n>` sections, anything under `src/`, `tests/` or `scripts/`, or another skill's docs. Never a `Status*` column (`dt roadmap`) or a `todo.md` checkbox (`dt tick`).
- **`tasks/plan.md` is never missing.** Between milestones it holds `dt archive`'s stub; replace it only with a new plan.
- **IDs:** milestones `M<n>` from `dt next-id M`, tasks `M<n>-T<nn>` from `dt next-id M<n>-T`.

## Preconditions

- No roadmap stage for the work: route to `idea-refine`.
- **References waiting:** route to `reference-intake` before planning.
- **Probes open:** `probes_blocking` (`PB-01 → service, ledger.BankTxn (M1)`) blocks New and Extend for that milestone: name the probe and route to `api-probe`. Cutting stages into milestone rows (`cut.md` steps 1–2) still runs. Only the user waives a probe, through `api-probe`, and never on a headless run.

## Modes

Run `dt status --skill build-planning` first. It prints the mode, progress, coverage, routing lists and `next ids`. Read the mode's file and only the topic references it names.

| Mode | When | Do |
|---|---|---|
| **blocked** | A needed `pipelines.md` or `tests.md` is Draft or missing (in New up front, every stage's), or `probes_blocking` names the milestone | Name what must come first. Stop |
| **foreign** | `tasks/plan.md` has no `**Milestone:**` header and unchecked tasks | **Stop and ask.** Never overwrite, rename or delete it |
| **New** | No active or archived plan; the roadmap has stages | `references/new.md` |
| **Extend** | A stage is newly designed (`stage_to_cut`), or the next milestone needs a plan | `references/extend.md` |
| **Replan** | A task is `Blocked`, or a revised doc was re-approved (`changed_since_plan`) | `references/replan.md` |
| **Advance** | All todo items and the exit checkpoint are ticked | `references/advance.md`, one gate per turn |

A foreign plan's question: `references/examples-foreign.md`.

## Asking

- **Interview one question at a time**, with a guess and a default, only on the user's decisions: the cut, what the milestone covers and defers, the exit, queued plans, a missing skill, a mode override. Infer the rest as ASSUMPTIONS. For a choice from a list, show it, then ask once.
- **No live user:** open decisions go under Open questions; leave Draft.

## Review Gate (CRITICAL)

Before presenting the Draft:
- `dt lint tasks/ docs/roadmap.md AGENTS.md` is clean.
- `dt status --skill build-planning`: `uncovered`, `no_spine`, `mode_violations`, `boundaries_unfrozen`, `references_unrouted`, `skills_unrouted` and `stage_unrouted` empty, or each item explained on its task or under Open questions; `skills_missing` listed for the user. `dt ready` lists only the interface task(s).
- `dt context` resolves for every task, under 2,000 lines. A contract symbol that doesn't resolve routes to `architecture-design`; never fix the contract yourself.
- Every plan header field is set; `tasks/plan.md` is ≤ ~400 lines.

Then present:
1. **What was written:** files; any cut (milestones, pipelines, the dependency line between them); scope, exit, phases with task counts, critical path and widest wave, checkpoints.
2. **ASSUMPTIONS:** the cut, interfaces frozen, every unmitigated edge with its reason, folds, sizes, modes and overrides, skill and reference routing, `Read:` choices.
3. **Open questions:** missing skills, overrides to confirm, anything Deferred.
4. **Uncovered:** each Deferred ID with its target.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set Status `Approved` and the date. Offer to commit the plan and roadmap; commit only on a yes | **Stop.** Point to `build-setup` (New on the first milestone, Extend at kickoff) |
| Yes, with a change | Make exactly that edit. Approve only if it adds, drops or reorders nothing (a re-cut stage is a reorder) | **Stop.** List what changed |
| Changes, or a hedge ("looks fine I guess") on a drop, an override or the exit | Edit, keep Draft | Repeat the gate |

"Approved, go ahead" means `build-setup` next, never building: no `/build`, tests or `src/`.
