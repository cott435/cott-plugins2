# Grow check, cutting a stage, scoping a milestone

Read before planning a milestone, before any task is written. Example: `examples-cut.md` (a large stage cut into slices).

Read only `dt status`, the roadmap, the stage's Source (*What success looks like*), the packages' `pipelines.md`, `contract.md` headings and `tests.md`, the spec sections they cover, the skill list and the `milestone_references` entries.

## 1. Grow check

Before planning, check the Grow triggers. `grow_triggers` lists the measurable ones (> 3 pipelines, > 12 modules, package docs > 2,000 lines). Check the others yourself:
- The milestone brings a dependency stack the rest shouldn't carry (torch, CUDA).
- A part runs or deploys on its own (a paper-trading service).

If one fires and no `AD-NN` already records the decision to stay single, **stop** and route to `architecture-design` Grow. Plan after Grow, pipeline-design Grow and build-setup Extend have caught up.

## 2. Cut the stage into milestones

When `stage_to_cut` names a stage, its pipelines are `pipelines_inferred`: the ones covering the stage's spec IDs. When the brief lists every stage, each stage's Source is `brief` and the spec's only Changelog row says IDs `all`, so `dt` can't tell which pipelines belong to which stage and `pipelines_inferred` comes back empty: assign each approved pipeline to the stage whose outcome it delivers, by its Covers.

- **Milestones are slices of the user's success criteria:** what the stage's Source says success looks like, and its `## S<n>` Outline.
- **The first milestone delivers every criterion end to end, in its thinnest form.** It is the walking skeleton: each criterion's path through every package it touches, joined across each boundary, at its smallest. rl's M1 trains the agent on a short budget, compares it with both baselines and plays its replay. Its exit runs each criterion's check once; a criterion with no check there is a gap in the cut.
- **Each later milestone deepens that slice**, end to end: more of a criterion (ablations, five seeds and the statistics, five fish after one) or a capability the criteria name. The stage's bar (the snake beats both baselines) is in the exit of the first milestone whose slice can meet it.
- **Never layered by function:** training, then baselines, curves and replay, then the study leaves the user nothing they asked for until the last. Never a horizontal layer ("all of the relay", "every model"), which can't run on its own. Viewers, comparisons and write-ups go in the first milestone whose output they show.
- **A consumer needs its provider's *interface*,** not its finished build: a boundary the interface task freezes lets both sides build in the same milestone.
- **Cut along dependency lines,** only where a later milestone needs an earlier one's outputs, and name them in the row's `Depends`: `M1 (profile.Profile, PL-01 output)`. Depends lists only the milestones whose outputs this one needs, never a build order or a note naming another milestone: `dt` reads every `M<n>` in the cell as an edge. Independent tracks stay in one milestone as parallel waves: one milestone is active at a time, so splitting them only serializes them.
- **Size each one** against the cap (step 3): a critical path of at most about 15 tasks. Cut until each fits; fewer, larger milestones beat many thin ones. Every stage is cut by these rules, so milestones stay of a size: never one holding a whole stage (seven pipelines, both tank versions, the library check) beside slice-sized ones. A stage gets one milestone only when it is no bigger than a slice; else its first milestone is its own skeleton (one fish trains, is compared and replays).
- **Every pipeline lands** in the milestone that first wires it; a later slice that thickens it lists it again. Every spec ID of the stage lands in a milestone or is Deferred later.

Write each milestone, IDs from `dt next-id M` (write the row before asking again). If the roadmap has no milestone table, add it under the stage table:

```markdown
| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Walking skeleton | relay, core, app | PL-01, PL-08, PL-16, PL-21, PL-27 | — | |
| M2 | S1 | Categories | core, app | PL-09, PL-21 | M1 (core.Transaction, PL-08 output) | |

## M1: Walking skeleton
**Outline:** One linked account syncs through the relay; the app lists its transactions and compares this month's spending with last month's by the bank's categories.
```

When a stage gets more than one milestone, give each section a `**Skills:**` and a `**References:**` line from the stage's (`milestone_skills`, `milestone_references`); every stage skill and reference lands on at least one milestone (`stage_unrouted` empty). A single milestone inherits its stage's. Then `dt roadmap` (the stage → Split). The cut is presented with the first plan at the gate; until a milestone is Planned, its row may be re-cut, and a dropped row becomes a retired line whose ID is never reused.

## 3. Scope the milestone

From the milestone row and the pipelines: the spec IDs, packages, pipelines and exit criteria. A milestone row from before stages may still have Packages or Pipelines `—`; `dt` then infers them as `pipelines_inferred`: confirm them and write them into the row.

**Size is the critical path:** the longest `Depends on` chain, interface and system tasks included, at most about 15 (`dt status` `critical_path`; `dt lint` errors `milestone-size` above 15). Tasks that don't depend on each other don't add up, so independent tracks (relay beside core, meter readings beside weather) stay in one milestone, whatever the plan's total. Over the cap: mitigate an edge with an interface, fold (`phase0.md`), or re-cut the stage (step 2) along a dependency line. A single task belongs in an existing milestone.

Every spec ID the milestone's pipelines cover lands on a task or under `**Deferred:**` with a target and reason (`RES-07 (to M4: needs day-ahead forecasts)`), and so does every step of those pipelines that gets no task, by name (`PL-03.PPOAgent (to M3: fish need it first)`). Check each pipeline's step table row by row, rows a later stage's design added included (a library call such as `PL-07.daily_bars`). `uncovered` and `steps_unplanned` must end empty.
