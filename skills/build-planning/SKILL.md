---
name: build-planning
description: Turns approved pipelines into the build plan for the next milestone — tasks/plan.md and tasks/todo.md with a Phase 0 spine, small test-backed tasks, build modes, skill routing and review checkpoints — and fills in the milestone's roadmap entry. Keeps the plan current through replans and moves the project from one milestone to the next. Use when pipelines.md is approved for every package in the next milestone and that milestone has no task plan, when something learned during the build means tasks must be reordered, split or added, or when every task and the exit checkpoint of the active milestone are done.
---

# Build Planning

## Overview

The pipelines say **what runs**; the build plan says **in what order it gets built**. This skill writes one milestone at a time into `tasks/plan.md` (agent-skills' `/build` format, extended) and `tasks/todo.md`. Every task is small, names its package, step, build mode and skills, lists the IDs a builder must read, and ends with a check that leaves the system working.

It plans; it never builds. It writes no code, runs no code, and stops at every gate.

## When to Use

- Every package in the next milestone has an `Approved` `pipelines.md`, and that milestone has no task plan
- A new idea was specced and designed, and its milestone needs a roadmap entry (and later a plan)
- The build taught something: a step was revised, a task is `Blocked`, or a major bug needs new tasks
- Every todo item and the exit checkpoint of the active milestone are ticked

**Not for:**
- Plans from agent-skills' `/plan`. If one is in `tasks/plan.md`, this skill stops and asks; it never converts or overwrites it
- Designing pipelines or steps (`pipeline-design`), oracles (`test-planning`), or the quality bar (`build-setup`)
- Building tasks, or deciding how a task gets built (`/build` and the build phase)

## How to run `dt`

`dt` is the plugin's doc tool. Run it as `python3 ../../scripts/dt.py <command>`, with the path relative to this skill's own folder, from the project root. (The session-start summary also prints the resolved path.) Below, `dt` means that command. Take IDs, modes, coverage and lint from `dt`; never count by hand.

## Modes

Run `dt status --skill build-planning` first. It prints `mode`, `milestone`, `base`, `progress`, `next_task`, `blocked_tasks`, `uncovered`, `no_spine`, `mode_violations`, `draft_pipelines`, `changed_since_plan`, `pipelines_inferred`, `skills_missing`, `skills_available`, `milestone_skills`, `milestone_references`, `skills_unrouted`, `references_unrouted`, `grow_triggers`, `drift`, `stale_contracts`, `queued`, `references_unindexed`, `references_changed`, `references_missing` and `next ids`.

| Mode | When | Do |
|---|---|---|
| **blocked** | An upstream gate isn't met: a milestone package's `pipelines.md` is Draft or missing, or a Revise is open (a `pipelines.md` or `tests.md` the active milestone uses is Draft) | Name the skill or approval that must come first; tasks on the revised docs stay paused. Stop |
| **foreign** | `tasks/plan.md` has no `**Milestone:**` header and has unchecked tasks | **Stop and ask.** Never overwrite, rename or delete it. Offer: finish it first, or the user moves or discards it themselves |
| **New** | No active or archived plan; the roadmap has rows | Fill in the roadmap (Packages and Pipelines for every designed row, not only M1's), write the M1 plan and todo, write the AGENTS.md doc map |
| **Extend** | A milestone is newly designed | Fill in its roadmap entry. No active milestone: write its plan. Active milestone: plan it at kickoff, or in `tasks/queued/` if the user asks. Never merge it into the active plan unless asked |
| **Replan** | A task is `Blocked`, or a revised doc was re-approved after the plan (`changed_since_plan`) | Reorder, split or add tasks. List every drop for approval |
| **Advance** | All todo items and the exit checkpoint are ticked | Run the [Advance sequence](#advance) one gate per turn |

If `docs/roadmap.md` is missing or has no row for the milestone, stop and route to `idea-refine`: it owns rows. This skill only fills them in.

## Shared Rules

- **Write only your row of the write matrix:** `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, roadmap fill-ins (Packages, Pipelines, Depends cells, which `idea-refine` leaves `—`; the milestone section's `**Exit:**`, `**Plan:**` and outcome text), and the AGENTS.md doc map. Never anything under `src/`, `tests/`, `scripts/`, or another skill's docs. Never the roadmap `Status*` column: run `dt roadmap`. Never `todo.md` checkboxes: `dt tick` owns them.
- **`tasks/plan.md` is never missing.** Between milestones it holds the stub `dt archive` writes. Replace it only with a new plan.
- **Interview one question at a time**, each with your guess and a default. Ask only what the user must decide: what the milestone covers and defers, its exit criteria, writing queued plans, a missing skill, a mode override. Infer order, sizes, groups and file lists, and list them as ASSUMPTIONS.
- **No live user:** don't invent confirmations. Write the plan, put the open decisions under Open questions, leave it Draft.
- **References waiting:** if `references_unindexed`, `references_changed` or `references_missing` is non-empty, stop and route to `reference-intake` before planning. A changed reference may change what a task should read.

## Process (New, Extend)

```
STATUS ─→ GROW CHECK ─→ SCOPE ─→ SPINE ─→ THICKEN ─→ ROUTE SKILLS + REFERENCES ─→ MODES ─→ CHECKPOINTS ─→ ORDER ─→ WRITE ─→ [gate]
```

Read only: `dt status`, the roadmap, the milestone packages' `pipelines.md`, `contract.md` headings and `tests.md`, the spec sections in their Covers, the skill list, and the index entries of `milestone_references` (`dt section RF-01 …`). Not the archive, and not the reference files themselves.

### 1. Grow check

Before planning, check the Grow triggers. `grow_triggers` lists the measurable ones (> 3 pipelines, > 12 modules, package docs > 2,000 lines). Check the others yourself:
- The milestone brings a dependency stack the rest shouldn't carry (torch, gym).
- A one-way dependency is worth enforcing (data must never import models).
- A part runs or deploys on its own (a paper-trading service).

If one fires and no `AD-NN` already records the decision to stay single, **stop** and route to `architecture-design` Grow. Plan after Grow, pipeline-design Grow and build-setup Extend have caught up.

### 2. Scope the milestone

From the roadmap row and the pipelines: the spec IDs, packages, pipelines and exit criteria. While the row's Pipelines cell is `—`, `dt` infers the milestone's pipelines from its Source's spec IDs and prints them as `pipelines_inferred`; confirm them and write them, with their packages, into the row.

**Up front, fill every row in New mode.** When the brief lists every stage, each row's Source is `brief` and the spec's only Changelog row says IDs `all`, so `dt` can't tell which pipelines belong to which row and `pipelines_inferred` comes back empty. Assign each approved pipeline to the row whose stage it delivers, by its Covers, and write Packages and Pipelines for every row. A row left `—` stays below Designed, even when its pipelines are approved.

One milestone is one working capability end to end, about 5–15 tasks. Bigger means two milestones; a single task belongs in an existing one.

Every spec ID the milestone's pipelines cover lands on a task or under `**Deferred:**` with a target and reason (`PORT-07 (to M4: needs forecasts)`). `uncovered` must end empty.

### 3. Phase 0: Spine

One task per new pipeline, in `## Phase 0: Spine`. In multi-package, the **system spine comes first**, then each package spine. A spine task:
- has `**Step:** PL-NN` (the whole pipeline) and `**Mode:** solo`
- builds every step at its spine version (a real baseline, never a mock), so the pipeline runs end to end on fixture or synthetic data
- commits the smoke command, and replaces the pipeline's pre-build sections with a `dt layout` pointer (`dt tick` prompts `dt prebuild-clear`)

A system spine crosses packages by design. System pipelines have no Entry, so its Package is the package that owns the system pipeline's first step, with `**Reason:** system spine`. The root has no pre-build sections, so its acceptance has no `dt layout` bullet; each package segment's own spine clears that segment's.

### 4. Thicken

`## Phase 1: Thicken`: one task per step upgrade, **riskiest first**. In data and ML work that means data loading, leak checks and the evaluation before any model. **Contract changes come first**, then the tasks that use them.

**Split a task** when it needs more than one session, has more than 3 acceptance bullets, touches two packages or two steps, or has "and" in its title. Sizes (lint-enforced by `Files likely` count): XS = 1 file, S = 1–2, M = 3–5. Nothing larger.

**Acceptance is test-backed.** Each bullet is checkable: a `TC-NN` passes, a Given/When/Then, a model criterion by ID, the smoke command. With no `tests.md`, write the criterion so a tester can encode it.

### 5. Route skills and references

**Skills.** Start from `milestone_skills` (the roadmap section's `**Skills:**` line): each goes on the `**Skills:**` of every task it fits, and at least one. Then add others whose descriptions fit a task (project `.claude/skills/*/SKILL.md`, `skills_available`). The plan's Scope lists the milestone's skills. A task that needs a skill that isn't installed names it anyway (`dt status` reports it under `skills_missing`) and goes under Open questions. Never quietly plan the step without it.

**References.** Each `RF-NN` in `milestone_references` goes in the `Read:` of the tasks whose step it informs; its entry's *Use for* and *Key parts* say which. Cite the ID, never the `references/` path. Over 300 lines, add a selector so the packet stays small: `RF-01:residualize` (one function or class), `RF-01:outline`, or `RF-03:<heading>` for a doc. With no selector a long file prints as its outline and `dt lint` warns `ref-large`. Whether to reuse the code is the builder's call; don't write it into Acceptance.

### 6. Build mode

- `split` (tester, then implementer) when the task adds or changes behavior with a checkable outcome: anything a TC case, Given/When/Then or model criterion covers.
- `solo` for spine, refactor, glue and doc-sync tasks.

`mode_violations` flags a task that breaks the rule. An override needs `**Reason:** <one line>` on the task. **A split task only tests symbols that already exist** (from the spine or an earlier solo task), so the tester never writes against a guess.

### 7. Checkpoints

`### Checkpoint after M<n>-T<nn>` every 2–3 tasks, and `### Checkpoint: milestone exit` last. Use the block in `examples.md`. A separate read-only reviewer runs each one; its findings are recorded under the block with `dt finding`, not by this skill.

### 8. Order, dependencies, parallel groups, Verify

- `**Depends on:**` resolves, points only backward (to a task earlier in the plan; position counts, not ID number) and is acyclic.
- After the spine, independent tasks get `**Parallel:** G<n>`. Tasks that share a `Files likely` path or a `Read:` contract symbol never share a group.
- **Every `Verify:` after Phase 0 includes its pipeline's smoke command** (tests.md Strategy, else the Trigger plus ` --smoke`), so each task leaves the system working. Add the focused tests and `scripts/check.sh gate` (`--pkg <pkg>` in multi-package). Only the modes `fast`, `gate` and `full` exist.
- `**Read:**` lists the IDs (references as `RF-NN[:selector]`) and paths a builder needs, and nothing else. Check each packet with `dt context <task>`: it must resolve and stay under 2,000 lines.

### 9. Write

Templates are in `examples.md`. Task IDs start at `dt next-id M<n>-T` and count up.
- **Next milestone only.** Later milestones stay as roadmap outlines. Write `tasks/queued/M<n>-<slug>.md` only when the user asks.
- `tasks/plan.md` with Status `Draft` and `**Base:** —` (pending). Never record a sha yourself: `build-setup` runs `dt base` after its bar is approved and committed.
- `tasks/todo.md`: one unchecked line per task, IDs matching the plan.
- Roadmap fill-ins, then `dt roadmap`.
- **New only:** the AGENTS.md doc map (`## Docs` and `## Project skills`, ≤ 25 lines). If only `CLAUDE.md` exists, write it there. Leave every other section alone.

## Replan

Something learned during the build, or a major bug (after `pipeline-design` or `architecture-design` Revise, if a step or decision changed).
1. Take `blocked_tasks`, the docs under `changed_since_plan` and their revised sections (`dt section <ID>`). Until those docs are re-approved, `dt status` says `blocked`: wait. Reorder, split or add; new IDs from `dt next-id M<n>-T`. Never renumber or reuse an ID.
2. **Never drop an unchecked task silently.** List each drop with its reason for approval. On approval, remove it from plan and todo and keep a retired line under Replan notes: `- ~~M2-T05: Title~~ Retired YYYY-MM-DD: reason`.
3. Remove a `**Blocked:**` line only when the change resolves it. A major bug's regression case becomes an acceptance bullet.
4. Add one dated line to `## Replan notes`, set Status to Draft and update `Last updated` (the plan is then newer than the revised docs, which clears `changed_since_plan`), run the Review Gate. Never touch a checked task.

## Advance

Each gate ends a turn. Re-run `dt status` at the start of each turn to see where you are.

1. **Exit checkpoint.** Every finding under every checkpoint has a disposition (`dt lint` shows no `finding-disposition`), and Critical ones are fixed. Ask the user to approve the milestone. [gate] On approval set Status `Done`.
2. **Ratchet.** Route to `build-setup` Ratchet. [gate, run by build-setup] When you're back with Status `Done`, continue only if `dt status --skill build-setup` no longer says `ratchet` (its CONSTRAINTS.md header reads `**Ratcheted:** M<n>`).
3. **Archive.** Run `dt archive`. It moves the plan to `tasks/archive/`, writes the stub plan and empty todo, and adds `**Outcome:** Done <date>` to the roadmap. Append the outcome in one line (what changed versus the plan), then `dt roadmap`.
4. **Kickoff check.** Run `dt status --skill build-planning`. `drift` (entry calls ≠ step table) routes to `pipeline-design` Sync and `stale_contracts` to `architecture-design` Sync; `dt layout <pkg>` gives the detail. [gate if either is non-empty] Then check a queued plan against what changed: `dt lint tasks/queued/`, the Replan notes, and the Outcome.
5. **Next plan.** Run the Grow check, then Extend: promote the queued plan (move it to `tasks/plan.md`, update it, write the todo) or write a new one. `Base` stays `—` until build-setup sets it. Run the Review Gate. [gate]
6. **build-setup Extend** for new packages, dependencies or Grow; it sets `Base` with `dt base` once approved and committed. [gate, run by build-setup]
7. Build. Not this skill.

No next milestone designed: leave the stub, say so, and name the skill that comes next (`idea-refine` for a new stage, or the first upstream skill whose doc isn't Approved).

## Review Gate (CRITICAL)

Before presenting the Draft:
- `dt lint tasks/ docs/roadmap.md AGENTS.md` is clean. It checks sizes, acceptance count, titles, fields, depends, parallel groups, smoke in Verify, todo vs plan, budgets.
- `dt status --skill build-planning`: `uncovered`, `no_spine` and `mode_violations` are empty (or each is explained on the task or under Open questions); `skills_missing` is listed for the user.
- `references_unrouted` (milestone references in no task's `Read:`) and `skills_unrouted` (milestone skills on no task) are empty, or each item has a one-line reason under Open questions.
- `dt context` resolves for every task, under 2,000 lines. A contract symbol that doesn't resolve (often a heading naming several) routes to `architecture-design`; never fix the contract yourself.
- Every plan header field is set and `tasks/plan.md` is ≤ ~400 lines.

Then present:
1. **What was written:** files, the milestone's scope and exit, phases with task counts, checkpoints.
2. **ASSUMPTIONS:** order, sizes, modes and overrides, parallel groups, skill and reference routing, `Read:` choices.
3. **Open questions:** missing skills, mode overrides to confirm, anything Deferred.
4. **Uncovered:** each Deferred ID with its target.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

**Handling the reply.**

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set Status `Approved`, update the date. Offer to commit the plan and roadmap; commit only on a yes | **Stop.** Point to `build-setup` (New on the first milestone, Extend at kickoff) |
| Yes, with a change | Make exactly that edit. Approve only if it adds, drops or reorders nothing | **Stop.** List what changed |
| Changes requested, or a hedge ("looks fine I guess") on a drop, an override or the exit | Edit, keep Draft | Repeat the gate |

**After approval this skill is done.** "Approved, go ahead" means run `build-setup` next, never start building. Don't run `/build`, write tests, or touch `src/`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The old `tasks/plan.md` is stale, I'll overwrite it" | Its unchecked tasks may be mid-build elsewhere. Stop and ask. |
| "I'll detail every milestone now" | Task lists are the most perishable doc. Plan the next milestone; outline the rest. |
| "No skill fits, I'll build without one" | Flag it. The user decides whether to install one or accept the gap. |
| "The builder will find the reference" | Only what's in `Read:` reaches the packet. An unrouted reference is invisible at build time; `references_unrouted` catches it. |
| "The spine can stub this step" | A spine step is the real baseline from the step table, or upgrades have nothing to beat. |
| "This task is M-and-a-bit, close enough" | Over five files or three bullets is two tasks. Lint will fail it anyway. |
| "The tester can write the test before the function exists" | It then tests a guess. Split tasks test symbols the spine or a solo task already made. |
| "The smoke command is obvious, I'll leave it out of Verify" | Then a task can pass while the pipeline is broken. Every post-spine Verify runs it. |
| "This requirement can wait, I'll leave it off" | Put it under Deferred with a target. Silent gaps are how coverage gets lost. |
| "The user said go ahead, I'll start the first task" | Approval of the plan starts `build-setup`, not code. |

## Red Flags

- A split task testing a symbol nothing has built yet
- Parallel tasks sharing a file or a contract symbol
- A task over M, more than 3 acceptance bullets, or "and" in a title
- A new pipeline with no Phase 0 task, or a spine that mocks a step
- A post-spine `Verify:` without the smoke command
- A `Depends on` pointing forward or in a cycle
- A mode override with no `**Reason:**`
- A task needing a skill that isn't installed, with no flag
- A milestone skill or reference on no task with no reason; a `references/` path in `Read:`; a long reference with no selector
- Spec IDs on no task and not Deferred
- Up front: a roadmap row with approved pipelines whose Packages or Pipelines cell is still `—`
- Task plans written for more than the next milestone without being asked
- A foreign `tasks/plan.md` overwritten, or `tasks/plan.md` deleted
- Code, tests or `src/` touched; `/build` started; more than one gate in a turn

## Verification

- [ ] `dt status --skill build-planning` ran first and set the mode
- [ ] Grow triggers checked; none fired, or the skill routed to `architecture-design` Grow
- [ ] `dt lint` clean on `tasks/`, the roadmap and AGENTS.md; plan header has `**Base:** —` until `dt base` sets it
- [ ] Every live spec ID in scope is on a task or Deferred; every new pipeline has a Phase 0 spine task
- [ ] New mode, up front: every designed roadmap row has its Packages and Pipelines filled in, and `dt roadmap` shows it Designed or later
- [ ] Every task: resolvable `Read:` IDs, size M or smaller, ≤ 3 test-backed acceptance bullets, a Verify step, Mode by rule (or a Reason), skills routed
- [ ] `skills_unrouted` and `references_unrouted` empty or explained; references cited by `RF-NN`, with selectors for long files
- [ ] Dependencies ordered backward with no cycles; checkpoints every 2–3 tasks plus the exit
- [ ] `dt context` packets under 2,000 lines; plan ≤ ~400 lines; AGENTS.md doc map ≤ 25 lines
- [ ] Only the write-matrix files changed; no existing plan overwritten without the user's say
- [ ] The turn ended at the gate; the user approved in a later turn; nothing was built

Read `examples.md` in this skill directory for the templates, the AGENTS.md doc map, and worked New, Advance, Replan, foreign-plan and skill-and-reference routing examples.
