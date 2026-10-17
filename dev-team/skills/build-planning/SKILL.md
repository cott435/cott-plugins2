---
name: build-planning
description: Cuts each roadmap stage into build-sized milestones once its pipelines are approved, then plans the next milestone in tasks/plan.md and tasks/todo.md - a contract-first Phase 0, small test-backed tasks, skill routing and review checkpoints. Use when the next stage's pipelines are approved and it has no milestone rows or plan, when the build shows tasks must be reordered, split or added, or when the active milestone's tasks and exit checkpoint are done.
---

# Build Planning

## Overview

The pipelines say **what runs**; the build plan says **in what order it gets built**. A roadmap stage (`S<n>`, from `idea-refine`) is an outcome the user agreed, unsized. Once its pipelines are approved, this skill cuts it into milestones (`M<n>`): build-sized vertical slices along dependency lines, each runnable end to end. It owns those milestone rows. Then it writes one milestone at a time into `tasks/plan.md` (agent-skills' `/build` format, extended) and `tasks/todo.md`. Every task is small, names its package, step, build mode and skills, lists the IDs a builder must read, and ends with a check that leaves the system working.

It plans; it never builds. It writes no code, runs no code, and stops at every gate.

## When to Use

- Every package in the next stage has an `Approved` `pipelines.md`, and the stage has no milestone rows yet (`stage_to_cut`)
- The next milestone has no task plan
- A new idea was specced and designed, and its stage needs cutting into milestones (and later a plan)
- The build taught something: a step was revised, a task is `Blocked`, or a major bug needs new tasks
- Every todo item and the exit checkpoint of the active milestone are ticked

**Not for:**
- Plans from agent-skills' `/plan`. If one is in `tasks/plan.md`, this skill stops and asks; it never converts or overwrites it
- Designing pipelines or steps (`pipeline-design`), oracles (`test-planning`), or the quality bar (`build-setup`)
- Building tasks, or deciding how a task gets built (`/build` and the build phase)

## How to run `dt`

`dt` is the plugin's doc tool. Run it as `python3 ../../scripts/dt.py <command>`, with the path relative to this skill's own folder, from the project root. (The session-start summary also prints the resolved path.) Below, `dt` means that command. Take IDs, modes, coverage and lint from `dt`; never count by hand.

## Modes

Run `dt status --skill build-planning` first. It prints `mode`, `milestone`, `base`, `progress`, `next_task`, `blocked_tasks`, `uncovered`, `no_spine`, `mode_violations`, `boundaries_unfrozen`, `draft_pipelines`, `changed_since_plan`, `stage_to_cut`, `pipelines_inferred`, `skills_missing`, `skills_available`, `milestone_skills`, `milestone_references`, `skills_unrouted`, `references_unrouted`, `stage_unrouted`, `grow_triggers`, `drift`, `stale_contracts`, `queued`, `references_unindexed`, `references_changed`, `references_missing` and `next ids`.

| Mode | When | Do |
|---|---|---|
| **blocked** | An upstream gate isn't met: a `pipelines.md` of the next stage or milestone is Draft or missing, or a Revise is open (a `pipelines.md` or `tests.md` the active milestone uses is Draft) | Name the skill or approval that must come first; tasks on the revised docs stay paused. Stop |
| **foreign** | `tasks/plan.md` has no `**Milestone:**` header and has unchecked tasks | **Stop and ask.** Never overwrite, rename or delete it. Offer: finish it first, or the user moves or discards it themselves |
| **New** | No active or archived plan; the roadmap has stages | Cut every designed stage into milestones (not only S1), write the M1 plan and todo, write the AGENTS.md doc map |
| **Extend** | A stage is newly designed (`stage_to_cut`), or the next milestone needs a plan | Cut the stage into milestone rows. No active milestone: plan the next one. Active milestone: plan it at kickoff, or in `tasks/queued/` if the user asks. Never merge it into the active plan unless asked |
| **Replan** | A task is `Blocked`, or a revised doc was re-approved after the plan (`changed_since_plan`) | Reorder, split or add tasks. List every drop for approval |
| **Advance** | All todo items and the exit checkpoint are ticked | Run the [Advance sequence](#advance) one gate per turn |

If `docs/roadmap.md` is missing or has no stage for the work, stop and route to `idea-refine`: it owns stage rows. Milestone rows are this skill's. A roadmap from before stages has only milestone rows, each standing for its own stage: fill in their cells as before, and cut new stages as below.

## Shared Rules

- **Write only your row of the write matrix:** `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, the roadmap's milestone table and `## M<n>` sections (`**Outline:**`, `**Skills:**`, `**References:**`, `**Exit:**`, `**Plan:**` and outcome text), and the AGENTS.md doc map. Never the stage table or `## S<n>` sections (`idea-refine`'s), anything under `src/`, `tests/`, `scripts/`, or another skill's docs. Never a `Status*` column: run `dt roadmap`. Never `todo.md` checkboxes: `dt tick` owns them.
- **`tasks/plan.md` is never missing.** Between milestones it holds the stub `dt archive` writes. Replace it only with a new plan.
- **Interview one question at a time**, each with your guess and a default. Ask only what the user must decide: where a stage is cut, what the milestone covers and defers, its exit criteria, writing queued plans, a missing skill, a mode override. Infer order, sizes, groups and file lists, and list them as ASSUMPTIONS. Choosing from a list (what to defer, which tasks to drop): show the whole list, then ask once.
- **No live user:** don't invent confirmations. Write the plan, put the open decisions under Open questions, leave it Draft.
- **References waiting:** if `references_unindexed`, `references_changed` or `references_missing` is non-empty, stop and route to `reference-intake` before planning. A changed reference may change what a task should read.

## Process (New, Extend)

```
STATUS ─→ GROW CHECK ─→ CUT (a new stage) ─→ SCOPE ─→ PHASE 0 (contract → spines → system spine) ─→ THICKEN ─→ ROUTE SKILLS + REFERENCES ─→ MODES ─→ CHECKPOINTS ─→ ORDER ─→ WRITE ─→ [gate]
```

Read only: `dt status`, the roadmap, the stage's or milestone's packages' `pipelines.md`, `contract.md` headings and `tests.md`, the spec sections in their Covers, the skill list, and the index entries of `milestone_references` (`dt section RF-01 …`). Not the archive, and not the reference files themselves.

### 1. Grow check

Before planning, check the Grow triggers. `grow_triggers` lists the measurable ones (> 3 pipelines, > 12 modules, package docs > 2,000 lines). Check the others yourself:
- The milestone brings a dependency stack the rest shouldn't carry (torch, gym).
- A one-way dependency is worth enforcing (data must never import models).
- A part runs or deploys on its own (a paper-trading service).

If one fires and no `AD-NN` already records the decision to stay single, **stop** and route to `architecture-design` Grow. Plan after Grow, pipeline-design Grow and build-setup Extend have caught up.

### 2. Cut the stage into milestones

When `stage_to_cut` names a stage, its pipelines are `pipelines_inferred`: the ones covering the stage's spec IDs. **Up front, cut every designed stage in New mode.** When the brief lists every stage, each stage's Source is `brief` and the spec's only Changelog row says IDs `all`, so `dt` can't tell which pipelines belong to which stage and `pipelines_inferred` comes back empty: assign each approved pipeline to the stage whose outcome it delivers, by its Covers.

- **Order by dependency.** Which pipeline needs another's outputs? A consumer needs its provider's *contract*, not its finished build: a boundary frozen in Phase 0 lets both sides build in the same milestone.
- **The first milestone is a walking skeleton:** the thinnest end-to-end path through every package the stage touches, one pipeline per package at spine version, joined across each boundary, so the user can run it end to end.
- **Each later milestone is a vertical slice:** it adds a capability the user can run end to end (categories, transfers, the review screen), thickening the skeleton. Never a horizontal layer ("all of the relay", "every model"), which can't run on its own.
- **Cut along dependency lines,** where a later milestone needs an earlier one's outputs. Independent tracks stay in one milestone as parallel groups: one milestone is active at a time, so splitting them only serializes them.
- **Size each one** against the track cap (step 3): serial Phase 0 plus the longest chain, at most about 15. Cut until each fits; fewer, larger milestones beat many thin ones. A stage that fits one milestone gets one.
- **Every pipeline lands** in the milestone that builds its spine; a later slice that thickens it lists it again. Every spec ID of the stage lands in a milestone or is Deferred later.

Write each milestone, IDs from `dt next-id M` (write the row before asking again). If the roadmap has no milestone table, add it under the stage table:

```markdown
| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Walking skeleton | relay, core, app | PL-01, PL-08, PL-15 | — | |

## M1: Walking skeleton
**Outline:** One linked account syncs through the relay and its transactions list in the app.
```

When a stage gets more than one milestone, give each section a `**Skills:**` and a `**References:**` line from the stage's (`milestone_skills`, `milestone_references`); every stage skill and reference lands on at least one milestone (`stage_unrouted` empty). A single milestone inherits its stage's. Then `dt roadmap` (the stage → Cut). The cut is presented with the first plan at the gate; until a milestone is Planned, its row may be re-cut, and a dropped row becomes a retired line whose ID is never reused.

### 3. Scope the milestone

From the milestone row and the pipelines: the spec IDs, packages, pipelines and exit criteria. A milestone row from before stages may still have Packages or Pipelines `—`; `dt` then infers them as `pipelines_inferred`: confirm them and write them into the row.

**Size is counted per track:** the serial Phase 0 tasks (the contract task and the system spine, which have no Parallel group) plus the longest chain of `Depends on` tasks through everything else, package spines included, at most about 15 (`dt lint` errors `milestone-size` above 15). Tasks in different parallel groups that don't depend on each other don't add up, so independent tracks (relay beside core, prices beside fundamentals) stay in one milestone as parallel groups, whatever the plan's total. Over the cap: shorten the chain, put package spines in parallel against the contract, or re-cut the stage (step 2) along a dependency line. A single task belongs in an existing milestone.

Every spec ID the milestone's pipelines cover lands on a task or under `**Deferred:**` with a target and reason (`PORT-07 (to M4: needs forecasts)`). `uncovered` must end empty.

### 4. Phase 0: contract, spines, integration

`## Phase 0: Spine` makes every new pipeline of the milestone run end to end, contract first, so packages build in parallel instead of queueing behind one task.

**a. Contract task** (multi-package, when the milestone crosses a package boundary). One solo task, first, `**Step:** contract`, no Parallel group, `**Package:**` the provider's. Boundaries that don't fit one M task, or have different providers, get one contract task each, still serial and first. It freezes each boundary the milestone uses (every contract symbol with a `**Boundary:**` line naming a consumer in the milestone) as executable artifacts in the symbol's `**Fixtures:**` folder:
- a schema: JSON Schema or a typed model for a payload; for a Python or data project, a pandera schema for a frame
- golden fixture payloads that validate against it (a sample frame for data), one per case the contract section lists
- a fixture-backed fake of the provider side, written where the consumer's tooling can load it, serving only those fixtures

Its Acceptance: every fixture validates against the schema; the fake serves each fixture. Its `Read:` is the boundary symbols. A boundary already frozen by an earlier milestone isn't frozen again.

**b. Package spines.** One task per new package pipeline, `**Step:** PL-NN`, solo. Each depends on the contract task, and on an earlier spine of the same package only when it calls it or shares its files. Spines of different packages share no file, and the boundary symbols they both read are frozen, so they carry a `**Parallel:**` group and build side by side. A consumer's spine runs against the contract fake; a provider's spine asserts that its output validates against the boundary schema.

**c. System spine, last.** One task per new system pipeline, no Parallel group, depending on the package spines it joins: the integration. It swaps each fake for the real provider and runs the system pipeline end to end; the boundary fixtures still validate against the real output. System pipelines have no Entry, so its Package is the package that owns the system pipeline's first step, with `**Reason:** system spine`. The root has no pre-build sections, so its acceptance has no `dt layout` bullet; each package spine clears its own package's.

Single package, or a milestone whose packages share no boundary: no contract task, no system spine; spines as in b, with `Depends on` where one calls another.

Every spine task (b and c):
- builds every step at its spine version (a real baseline), so the pipeline runs end to end on fixture or synthetic data
- commits the smoke command, and replaces the pipeline's pre-build sections with a `dt layout` pointer (`dt tick` prompts `dt prebuild-clear`)

**Fakes.** A boundary fake generated from an approved contract is allowed: both sides are tested against the same fixtures (the provider asserts its output validates, the consumer consumes the fixtures), so neither can drift from the contract unseen. Mocking a step inside a package is still forbidden: a spine step is the real baseline from the step table. Changing a frozen schema or fixture is a contract change: `architecture-design` Revise, never an edit to make a test pass. The bar enforces it (CR-09): once a contract folder exists at a task's base, the implementer can't write it and `dt guard` asks before any edit no open contract task covers. The re-freeze after a Revise is a new contract task naming the symbol in `Read:`; it runs in the main session, since the implementer's guard blocks a folder frozen at the base.

### 5. Thicken

`## Phase 1: Thicken`: one task per step upgrade, **riskiest first**. In data and ML work that means data loading, leak checks and the evaluation before any model. **Contract changes come first**, then the tasks that use them.

**Split a task** when it needs more than one session, has more than 3 acceptance bullets, touches two packages or two steps, or has "and" in its title. Sizes (lint-enforced by `Files likely` count): XS = 1 file, S = 1–2, M = 3–5. Nothing larger.

**Acceptance is test-backed.** Each bullet is checkable: a `TC-NN` passes, a Given/When/Then, a model criterion by ID, the smoke command. With no `tests.md`, write the criterion so a tester can encode it.

### 6. Route skills and references

**Skills.** Start from `milestone_skills` (the milestone's `**Skills:**` line, else its stage's): each goes on the `**Skills:**` of every task it fits, and at least one. Then add others whose descriptions fit a task (project `.claude/skills/*/SKILL.md`, `skills_available`). The plan's Scope lists the milestone's skills. A task that needs a skill that isn't installed names it anyway (`dt status` reports it under `skills_missing`) and goes under Open questions. Never quietly plan the step without it.

**References.** Each `RF-NN` in `milestone_references` goes in the `Read:` of the tasks whose step it informs; its entry's *Use for* and *Key parts* say which. Cite the ID, never the `references/` path. Over 300 lines, add a selector so the packet stays small: `RF-01:residualize` (one function or class), `RF-01:outline`, or `RF-03:<heading>` for a doc. With no selector a long file prints as its outline and `dt lint` warns `ref-large`. Whether to reuse the code is the builder's call; don't write it into Acceptance.

### 7. Build mode

- `split` (tester, then implementer) when the task adds or changes behavior with a checkable outcome: anything a TC case, Given/When/Then or model criterion covers.
- `solo` for contract, spine, refactor, glue and doc-sync tasks.

`mode_violations` flags a task that breaks the rule. An override needs `**Reason:** <one line>` on the task. **A split task only tests symbols that already exist** (from the spine or an earlier solo task), so the tester never writes against a guess.

### 8. Checkpoints

`### Checkpoint after M<n>-T<nn>` every 2–3 tasks, and `### Checkpoint: milestone exit` last. Use the block in `examples.md`. A separate read-only reviewer runs each one; its findings are recorded under the block with `dt finding`, not by this skill.

### 9. Order, dependencies, parallel groups, Verify

- `**Depends on:**` resolves, points only backward (to a task earlier in the plan; position counts, not ID number) and is acyclic.
- Package spines of different packages, and after Phase 0 independent tasks, get `**Parallel:** G<n>`. Tasks that share a `Files likely` path or a `Read:` contract symbol never share a group, except a symbol the contract task froze.
- The contract task's `Verify:` runs the schema check over every fixture. **Every `Verify:` after Phase 0 includes its pipeline's smoke command** (tests.md Strategy, else the Trigger plus ` --smoke`), so each task leaves the system working. Add the focused tests and `scripts/check.sh gate` (`--pkg <pkg>` in multi-package). Only the modes `fast`, `gate` and `full` exist.
- `**Read:**` lists the IDs (references as `RF-NN[:selector]`) and paths a builder needs, and nothing else. Check each packet with `dt context <task>`: it must resolve and stay under 2,000 lines.

### 10. Write

Templates are in `examples.md`. Task IDs start at `dt next-id M<n>-T` and count up.
- **Next milestone only.** Later milestones stay as roadmap outlines. Write `tasks/queued/M<n>-<slug>.md` only when the user asks.
- `tasks/plan.md` with Status `Draft` and `**Base:** —` (pending). Never record a sha yourself: `build-setup` runs `dt base` after its bar is approved and committed.
- `tasks/todo.md`: one unchecked line per task, IDs matching the plan.
- Milestone rows and sections (step 2), the planned milestone's `**Exit:**` and `**Plan:**`, then `dt roadmap`.
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

No next milestone: if the next stage is designed (`stage_to_cut`), cut it (step 2) and plan its first milestone. Otherwise leave the stub, say so, and name the skill that comes next (`idea-refine` for a new stage, or the first upstream skill whose doc isn't Approved).

## Review Gate (CRITICAL)

Before presenting the Draft:
- `dt lint tasks/ docs/roadmap.md AGENTS.md` is clean. It checks sizes, acceptance count, titles, fields, depends, parallel groups, smoke in Verify, todo vs plan, budgets.
- `dt status --skill build-planning`: `uncovered`, `no_spine`, `mode_violations` and `boundaries_unfrozen` (a `**Boundary:**` symbol with a consumer in the milestone, not yet frozen, in no contract task's `Read:`) are empty (or each is explained on the task or under Open questions); `skills_missing` is listed for the user.
- `references_unrouted` (milestone references in no task's `Read:`), `skills_unrouted` (milestone skills on no task) and `stage_unrouted` (stage skills and references on no milestone) are empty, or each item has a one-line reason under Open questions.
- `dt context` resolves for every task, under 2,000 lines. A contract symbol that doesn't resolve (often a heading naming several) routes to `architecture-design`; never fix the contract yourself.
- Every plan header field is set and `tasks/plan.md` is ≤ ~400 lines.

Then present:
1. **What was written:** files; the cut, when a stage was cut (each milestone, its pipelines, and the dependency line between them); the milestone's scope and exit, phases with task counts, checkpoints.
2. **ASSUMPTIONS:** the cut, the boundaries the contract task freezes, order, sizes, modes and overrides, parallel groups, skill and reference routing, `Read:` choices.
3. **Open questions:** missing skills, mode overrides to confirm, anything Deferred.
4. **Uncovered:** each Deferred ID with its target.
5. Ask the user to approve or request changes. **STOP YOUR TURN.**

**Handling the reply.**

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes | Set Status `Approved`, update the date. Offer to commit the plan and roadmap; commit only on a yes | **Stop.** Point to `build-setup` (New on the first milestone, Extend at kickoff) |
| Yes, with a change | Make exactly that edit. Approve only if it adds, drops or reorders nothing (a re-cut stage counts as a reorder) | **Stop.** List what changed |
| Changes requested, or a hedge ("looks fine I guess") on a drop, an override or the exit | Edit, keep Draft | Repeat the gate |

**After approval this skill is done.** "Approved, go ahead" means run `build-setup` next, never start building. Don't run `/build`, write tests, or touch `src/`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The old `tasks/plan.md` is stale, I'll overwrite it" | Its unchecked tasks may be mid-build elsewhere. Stop and ask. |
| "I'll detail every milestone now" | Task lists are the most perishable doc. Plan the next milestone; outline the rest. |
| "The stage is the milestone" | A stage is an outcome, unsized. Cut it once its pipelines exist, so each milestone fits the track cap. |
| "One milestone per package: relay, then core, then app" | Horizontal layers can't run end to end, and they serialize independent work. Slice vertically; the first slice is a walking skeleton. |
| "The system spine has to come first or nothing integrates" | Then every package waits on one task. Freeze the contract first; packages build against its fake in parallel and the system spine integrates last. |
| "No skill fits, I'll build without one" | Flag it. The user decides whether to install one or accept the gap. |
| "The builder will find the reference" | Only what's in `Read:` reaches the packet. An unrouted reference is invisible at build time; `references_unrouted` catches it. |
| "The spine can stub this step" | A spine step is the real baseline from the step table, or upgrades have nothing to beat. Only the other package across a frozen boundary may be faked. |
| "The consumer can mock the provider its own way" | A fake not built from the contract's schema and fixtures drifts silently. Both sides test against the same fixtures. |
| "This task is M-and-a-bit, close enough" | Over five files or three bullets is two tasks. Lint will fail it anyway. |
| "The tester can write the test before the function exists" | It then tests a guess. Split tasks test symbols the spine or a solo task already made. |
| "The smoke command is obvious, I'll leave it out of Verify" | Then a task can pass while the pipeline is broken. Every post-spine Verify runs it. |
| "This requirement can wait, I'll leave it off" | Put it under Deferred with a target. Silent gaps are how coverage gets lost. |
| "The user said go ahead, I'll start the first task" | Approval of the plan starts `build-setup`, not code. |

## Red Flags

- A split task testing a symbol nothing has built yet
- Parallel tasks sharing a file or a contract symbol
- A track (serial Phase 0 plus the longest `Depends on` chain) over 15 tasks, or independent tracks split into sequential milestones
- A stage cut into horizontal layers, a first milestone that isn't runnable end to end, or a stage row or section edited by this skill
- Package spines serialized behind one task, a consumer spine waiting on its provider's spine instead of the contract fake, or a system spine before the package spines
- A task over M, more than 3 acceptance bullets, or "and" in a title
- A new pipeline with no Phase 0 task, a spine that mocks a step, or a boundary fake with no schema and fixtures behind it
- A post-spine `Verify:` without the smoke command
- A `Depends on` pointing forward or in a cycle
- A mode override with no `**Reason:**`
- A task needing a skill that isn't installed, with no flag
- A milestone skill or reference on no task with no reason; a `references/` path in `Read:`; a long reference with no selector
- Spec IDs on no task and not Deferred
- Up front: a stage with approved pipelines and no milestone rows
- Task plans written for more than the next milestone without being asked
- A foreign `tasks/plan.md` overwritten, or `tasks/plan.md` deleted
- Code, tests or `src/` touched; `/build` started; more than one gate in a turn

## Verification

- [ ] `dt status --skill build-planning` ran first and set the mode
- [ ] Grow triggers checked; none fired, or the skill routed to `architecture-design` Grow
- [ ] `dt lint` clean on `tasks/`, the roadmap and AGENTS.md; plan header has `**Base:** —` until `dt base` sets it
- [ ] Every live spec ID in scope is on a task or Deferred; every new pipeline has a Phase 0 spine task
- [ ] Each cut stage: milestones are vertical slices along dependency lines, the first a walking skeleton; `stage_unrouted` empty; New mode, up front: every designed stage is cut, and `dt roadmap` shows it Cut or later
- [ ] Multi-package: a solo contract task freezes each boundary first (schema, fixtures, fake); package spines in parallel groups; the system spine last
- [ ] Every task: resolvable `Read:` IDs, size M or smaller, ≤ 3 test-backed acceptance bullets, a Verify step, Mode by rule (or a Reason), skills routed
- [ ] `skills_unrouted` and `references_unrouted` empty or explained; references cited by `RF-NN`, with selectors for long files
- [ ] Dependencies ordered backward with no cycles; checkpoints every 2–3 tasks plus the exit
- [ ] The track (serial Phase 0 plus the longest `Depends on` chain) is ≤ 15 tasks; any cut follows a dependency line, never one between independent tracks
- [ ] `dt context` packets under 2,000 lines; plan ≤ ~400 lines; AGENTS.md doc map ≤ 25 lines
- [ ] Only the write-matrix files changed; no existing plan overwritten without the user's say
- [ ] The turn ended at the gate; the user approved in a later turn; nothing was built

Read `examples.md` in this skill directory for the templates, the AGENTS.md doc map, and worked New, Advance, Replan, foreign-plan, contract-first Phase 0, stage-cut and skill-and-reference routing examples.
