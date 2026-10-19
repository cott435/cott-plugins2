---
name: build-planning
description: Cuts each roadmap stage into build-sized milestones once its pipelines are approved, then plans the next milestone in tasks/plan.md and tasks/todo.md - an interface task first, small test-backed tasks with exclusive Writes, a dependency graph, skill routing and review checkpoints. Use when the next stage's pipelines are approved and it has no milestone rows or plan, when the build shows tasks must be reordered, split or added, or when the active milestone's tasks and exit checkpoint are done.
---

# Build Planning

This skill cuts each stage with approved pipelines into milestones (`M<n>`), vertical slices each runnable end to end, then plans one milestone at a time in `tasks/plan.md` and `tasks/todo.md`: small tasks, many built at once.

**Not for:** plans from agent-skills' `/plan` (foreign); pipelines, oracles or the quality bar (`pipeline-design`, `test-planning`, `build-setup`); building tasks. A fix their docs need goes to `dt route <owner> "<change>" --from build-planning`.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root; write it out each call, never as a shell variable. IDs, coverage and lint come from `dt`, never by hand. Templates: `examples.md`.

## Documents and IDs

- **Write only:** `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, the roadmap's milestone table and `## M<n>` sections, and the AGENTS.md doc map. Never the stage table or `## S<n>` sections, anything under `src/`, `tests/` or `scripts/`, or another skill's docs. Never a `Status*` column (`dt roadmap`) or a `todo.md` checkbox (`dt tick`).
- **`tasks/plan.md` is never missing.** Between milestones it holds `dt archive`'s stub; replace it only with a new plan.
- **IDs:** milestones `M<n>` from `dt next-id M`, tasks `M<n>-T<nn>` from `dt next-id M<n>-T`.

## Preconditions

- No roadmap stage for the work: route to `idea-refine`.
- **References waiting:** route to `reference-intake`.
- **Probes:** a milestone is planned only once `probes_blocking` is empty and a `PB-NN` sample backs the record type of each external source its pipelines read (`docs/probes.md`). A few records make a sample; a batch over every member is the user's step (`../api-probe/references/safety.md`). Else name the probe, or the source's type, and go to `api-probe`. Cutting rows (`cut.md` steps 1–2) still runs; one queued plan at most. Waivers are api-probe's.

## Modes

Run `dt status --skill build-planning` first; read the mode's file and only what it names.

| Mode | When | Do |
|---|---|---|
| **blocked** | A needed `pipelines.md` or `tests.md` is Draft or missing (in New up front, every stage's), or `probes_blocking` names the milestone | Name what must come first. Stop: next run |
| **current** | The plan is in step; no milestone is ready to plan | Stop: next run |
| **foreign** | `tasks/plan.md` has no `**Milestone:**` header and unchecked tasks | **Stop and ask.** Never overwrite, rename or delete it |
| **New** | No active or archived plan; the roadmap has stages | `references/new.md` |
| **Extend** | A stage is newly designed (`stage_to_cut`), or the next milestone needs a plan | `references/extend.md` |
| **Replan** | A task is `Blocked`, or a doc changed after the plan (`changed_since_plan`); before the next cut if nothing is ticked | `references/replan.md` |
| **Advance** | All todo items and the exit checkpoint are ticked | `references/advance.md`, one gate per turn |

A foreign plan's question: `references/examples-foreign.md`. **Next run:** with nothing left for this skill, go on to the run `dt next` names; never end on "say the word".

## Asking

- **Interview one question at a time**, with a guess and a default, only on the user's decisions: the cut, scope and deferrals, the exit, queued plans, a missing skill, a mode override. Infer the rest as ASSUMPTIONS. List a choice's options, then ask once.
- **The user's words:** record them and honour yours (`requests_open`) per `../idea-refine/references/requests.md`.
- **No live user:** open decisions go under Open questions; leave Draft.

## Review Gate (CRITICAL)

Before presenting the Draft:
- `dt lint tasks/ docs/roadmap.md AGENTS.md` is clean.
- `dt status --skill build-planning`: `uncovered`, `no_spine`, `mode_violations`, `boundaries_unfrozen`, `references_unrouted`, `skills_unrouted` and `stage_unrouted` empty, or each item explained on its task or under Open questions; `skills_missing` listed for the user. `dt ready` lists only the interface task(s).
- `dt context` resolves for every task, under 2,000 lines; a contract symbol that doesn't resolve is routed (Not for).
- Every plan header field is set.

Then present:
1. **What was written:** files; any cut; scope, exit, phases, critical path, widest wave, checkpoints.
2. **ASSUMPTIONS:** interfaces frozen, every unmitigated edge with its reason, folds, sizes, modes and overrides, skill and reference routing, `Read:` choices.
3. **Open questions:** missing skills, overrides to confirm, routed fixes.
4. **Uncovered:** each Deferred ID with its target.
5. Ask for approval or changes. **STOP YOUR TURN.**

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set Status `Approved` and the date. Offer a commit only if `git status` shows changes; commit only on a yes | **Stop:** next run (`build-setup`, never `/build`) |
| Yes, with a change | Make exactly that edit. Approve only if it adds, drops or reorders nothing (a re-cut stage is a reorder) | List what changed. **Stop:** next run once approved |
| Changes, or a hedge on a drop, an override or the exit | Edit, keep Draft | Repeat the gate |
