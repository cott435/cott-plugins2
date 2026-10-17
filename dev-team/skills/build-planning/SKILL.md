---
name: build-planning
description: Cuts each roadmap stage into build-sized milestones once its pipelines are approved, then plans the next milestone in tasks/plan.md and tasks/todo.md - a contract-first Phase 0, small test-backed tasks, skill routing and review checkpoints. Use when the next stage's pipelines are approved and it has no milestone rows or plan, when the build shows tasks must be reordered, split or added, or when the active milestone's tasks and exit checkpoint are done.
---

# Build Planning

The build plan says **in what order** the pipelines get built. Once a roadmap stage's pipelines are approved, this skill cuts it into milestones (`M<n>`), vertical slices each runnable end to end, then writes one milestone at a time into `tasks/plan.md` (agent-skills' `/build` format, extended) and `tasks/todo.md`: small tasks, each ending with a check that leaves the system working. It never builds or runs code, and stops at every gate.

**Not for:** plans from agent-skills' `/plan` (stop and ask; never convert or overwrite one); pipelines, oracles or the quality bar (`pipeline-design`, `test-planning`, `build-setup`); building tasks.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. Take IDs, coverage and lint from `dt`, never by hand. Templates: `examples.md`; worked examples: `references/examples-*.md`.

## Modes

Run `dt status --skill build-planning` first. It prints the mode, the milestone, progress, coverage and routing lists, and `next ids`.

| Mode | When | Do |
|---|---|---|
| **blocked** | A needed `pipelines.md` or `tests.md` is Draft or missing | Name what must come first. Stop |
| **foreign** | `tasks/plan.md` has no `**Milestone:**` header and unchecked tasks | **Stop and ask.** Never overwrite, rename or delete it |
| **New** | No active or archived plan; the roadmap has stages | Cut every designed stage, plan M1 and its todo, write the AGENTS.md doc map |
| **Extend** | A stage is newly designed (`stage_to_cut`), or the next milestone needs a plan | Cut the stage; plan the next milestone at kickoff (in `tasks/queued/` only if asked), never merged into the active plan |
| **Replan** | A task is `Blocked`, or a revised doc was re-approved (`changed_since_plan`) | `references/replan-advance.md` |
| **Advance** | All todo items and the exit checkpoint are ticked | `references/replan-advance.md`, one gate per turn |

No roadmap stage for the work: route to `idea-refine`. In a roadmap from before stages, each milestone row stands for its own stage.

## Shared rules

- **Write only:** `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, the roadmap's milestone table and `## M<n>` sections, and the AGENTS.md doc map. Never the stage table or `## S<n>` sections, anything under `src/`, `tests/` or `scripts/`, or another skill's docs. Never a `Status*` column (`dt roadmap`) or a `todo.md` checkbox (`dt tick`).
- **`tasks/plan.md` is never missing.** Between milestones it holds `dt archive`'s stub; replace it only with a new plan.
- **Interview one question at a time**, with a guess and a default, only on the user's decisions: the cut, what the milestone covers and defers, exit criteria, queued plans, a missing skill, a mode override. Infer the rest as ASSUMPTIONS. For a choice from a list, show the list, then ask once.
- **No live user:** open decisions go under Open questions; leave Draft.
- **References waiting:** route to `reference-intake` before planning.

## Process (New, Extend)

Read only `dt status`, the roadmap, the packages' `pipelines.md`, `contract.md` headings and `tests.md`, the spec sections they cover, the skill list and the `milestone_references` entries.

1. **Grow check, cut the stage, scope the milestone:** `references/cut.md`.
2. **Phase 0** (contract task, package spines, system spine): `references/phase0.md`.
3. **Thicken, route skills and references, build modes, checkpoints, order, write:** `references/tasks.md`.

## Review Gate (CRITICAL)

Before presenting the Draft:
- `dt lint tasks/ docs/roadmap.md AGENTS.md` is clean.
- `dt status --skill build-planning`: `uncovered`, `no_spine`, `mode_violations`, `boundaries_unfrozen`, `references_unrouted`, `skills_unrouted` and `stage_unrouted` empty, or each item explained on its task or under Open questions; `skills_missing` listed for the user.
- `dt context` resolves for every task, under 2,000 lines. A contract symbol that doesn't resolve routes to `architecture-design`; never fix the contract yourself.
- Every plan header field is set; `tasks/plan.md` is ≤ ~400 lines.

Then present:
1. **What was written:** files; any cut (milestones, pipelines, the dependency line between them); scope, exit, phases with task counts, checkpoints.
2. **ASSUMPTIONS:** the cut, boundaries frozen, order, sizes, modes and overrides, parallel groups, skill and reference routing, `Read:` choices.
3. **Open questions:** missing skills, overrides to confirm, anything Deferred.
4. **Uncovered:** each Deferred ID with its target.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set Status `Approved` and the date. Offer to commit the plan and roadmap; commit only on a yes | **Stop.** Point to `build-setup` (New on the first milestone, Extend at kickoff) |
| Yes, with a change | Make exactly that edit. Approve only if it adds, drops or reorders nothing (a re-cut stage is a reorder) | **Stop.** List what changed |
| Changes, or a hedge ("looks fine I guess") on a drop, an override or the exit | Edit, keep Draft | Repeat the gate |

"Approved, go ahead" means `build-setup` next, never building: no `/build`, tests or `src/`.
