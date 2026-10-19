# Example: New — gridload M1

**State:** brief Accepted, spec and architecture Approved (single package `gridload`), `pipelines.md` Approved with PL-01 (load meter readings) and PL-02 (seasonality report), `tests.md` Approved with TC-01–TC-03. `idea-refine` wrote stages S1 Ingest & clean and S2 Seasonality & baselines; S2's idea isn't specced yet. No milestone rows, no `tasks/`.

```
$ dt status --skill build-planning
skill: build-planning
mode: new
docs: brief Accepted · spec Approved · architecture Approved (Single package) · roadmap ok · plan missing · constraints missing
next ids: AD-04 PL-03 TC-04 M1
milestone: none
progress: 0/0
next_task: none
blocked_tasks: none
uncovered: none
no_spine: none
mode_violations: none
draft_pipelines: none
changed_since_plan: none
stage_to_cut: S1 Ingest & clean
pipelines_inferred: PL-01, PL-02
skills_missing: none
skills_available: data-science
milestone_skills: data-science
milestone_references: none
skills_unrouted: none
references_unrouted: none
stage_unrouted: none
grow_triggers: none
drift: none
stale_contracts: none
queued: none
base: pending
references_unindexed: none
references_changed: none
references_missing: none
```

With no plan yet, `uncovered`, `no_spine` and the unrouted lists have nothing to check; they count at the gate's re-run. S1 has no milestone rows, so it is the stage to cut, and `dt` inferred its pipelines, PL-01 and PL-02, from its Source (the brief's spec IDs). `milestone_skills` comes from S1's section (`**Skills:** data-science`); S1 has no references.

**Cut:** PL-02 needs PL-01's readings, but only through `data.load_readings`, which `data`'s contract task freezes with a fake, so both pipelines fit one milestone: a critical path of 5, far under 15. S1 becomes one milestone, M1 Ingest & clean (`dt next-id M`), which inherits S1's Skills. S2 isn't designed yet, so it stays uncut. Task IDs start at `dt next-id M1-T` (M1-T01).

**Grow check:** no measurable trigger; numpy and pandas only; nothing deploys on its own. Passes.

**One question** (the rest is inferred):

> M1's pipelines cover DATA-01, DATA-02, STAT-01–STAT-04, QR-01 and QR-02. I'd plan all of them, with the exit "the Fourier profile and the residual spectrum run on 10y of hourly load; TC-01–TC-03 pass". Defer anything? Default: nothing deferred.

**User:** "All of it."

**Written:**
- `tasks/plan.md`, the 16 tasks of `examples-phase0.md`: M1-T01 types; contract tests M1-T02 (`data`) and M1-T03 (`profile`); six step spines M1-T04–M1-T09; wiring M1-T10 (PL-01) and M1-T11 (PL-02, on the `load_readings` fake); thicken M1-T12 registry-aware load, M1-T13 least-squares amplitudes, M1-T14 Fourier seasonality, M1-T15 seasonal removal; checkpoints after M1-T03 (barrier) and M1-T15; M1-T16 system; exit checkpoint; the dependency graph.
- `tasks/todo.md`: fourteen unchecked lines.
- Roadmap: the milestone table with row `| M1 | S1 | Ingest & clean | gridload | PL-01, PL-02 | — | |`, and `## M1: Ingest & clean` with Outline, Exit and Plan link. S2 keeps its stage row only. Then `dt roadmap` (M1 → Planned, S1 → Planned).
- `AGENTS.md`: the doc map, with `data-science — profile steps`.

**Review gate message:**

> Cut S1 into one milestone, M1 Ingest & clean (both pipelines). Wrote the M1 plan (16 tasks: types, 2 contract, 6 spines, 2 wiring, 4 thicken, system; critical path 5, 10 agents once the interface lands; checkpoints after M1-T03 (barrier), M1-T15 and at exit), its todo, the M1 roadmap row and the AGENTS.md doc map. `dt lint` is clean; `uncovered`, `no_spine` and `mode_violations` are empty; `dt ready` lists only M1-T01; every `dt context` packet is under 2,000 lines.
>
> **ASSUMPTIONS:** M1-T01 freezes six types and every step signature, M1-T02 and M1-T03 their samples and the `load_readings` fake; the only unmitigated edges are stubs, spines under their thicken tasks and wiring, and the system task; no folds; interface tasks, spines and wiring solo; the four thicken tasks and the system task split, since each names a TC case; data-science routed to the three profile thicken tasks.
>
> **Open questions:** none. **Uncovered:** none deferred.
>
> Approve, or tell me what to change.

*(Turn ends.)*

**User:** "Approved, go ahead."

Set Status `Approved`; `git status` shows `tasks/`, `docs/roadmap.md` and `AGENTS.md` changed, so offer to commit them. `dt next` names `build-setup` New, so go on to it: it writes CONSTRAINTS.md and the check scripts before anything is built, then sets the plan's `Base` with `dt base`. *(Nothing is built.)*
