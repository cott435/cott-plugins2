# Examples: New mode and cutting a stage

`dt` means `python3 ../../scripts/dt.py`, run from the project root.

## New — quant M1

**State:** brief Accepted, spec and architecture Approved (single package `quant`), `pipelines.md` Approved with PL-01 (load prices) and PL-02 (covariance report), `tests.md` Approved with TC-01–TC-03. `idea-refine` wrote stages S1 Data + stats and S2 Classical portfolios; S2's idea isn't specced yet. No milestone rows, no `tasks/`.

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
stage_to_cut: S1 Data + stats
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

**Cut:** PL-02 needs PL-01's prices, but only through `data.load_prices`, which the interface task freezes with a fake, so both pipelines fit one milestone: a critical path of 4, far under 15. S1 becomes one milestone, M1 Data + stats (`dt next-id M`), which inherits S1's Skills. S2 isn't designed yet, so it stays uncut. Task IDs start at `dt next-id M1-T` (M1-T01).

**Grow check:** no measurable trigger; numpy and pandas only; nothing deploys on its own. Passes.

**One question** (the rest is inferred):

> M1's pipelines cover DATA-01, DATA-02, STAT-01–STAT-04, QR-01 and QR-02. I'd plan all of them, with the exit "PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass". Defer anything? Default: nothing deferred.

**User:** "All of it."

**Written:**
- `tasks/plan.md`, the 14 tasks of `examples-phase0.md`: M1-T01 interface; six step spines M1-T02–M1-T07; wiring M1-T08 (PL-01) and M1-T09 (PL-02, on the `load_prices` fake); thicken M1-T10 delisting-aware universe, M1-T11 MP cleaning, M1-T12 shrinkage, M1-T13 planted-factor PCA; checkpoint after M1-T13; M1-T14 system; exit checkpoint; the dependency graph.
- `tasks/todo.md`: fourteen unchecked lines.
- Roadmap: the milestone table with row `| M1 | S1 | Data + stats | quant | PL-01, PL-02 | — | |`, and `## M1: Data + stats` with Outline, Exit and Plan link. S2 keeps its stage row only. Then `dt roadmap` (M1 → Planned, S1 → Planned).
- `AGENTS.md`: the doc map, with `data-science — stats steps`.

**Review gate message:**

> Cut S1 into one milestone, M1 Data + stats (both pipelines). Wrote the M1 plan (14 tasks: interface, 6 spines, 2 wiring, 4 thicken, system; critical path 4, 10 agents in wave 1; checkpoints after M1-T13 and at exit), its todo, the M1 roadmap row and the AGENTS.md doc map. `dt lint` is clean; `uncovered`, `no_spine` and `mode_violations` are empty; `dt ready` lists only M1-T01; every `dt context` packet is under 2,000 lines.
>
> **ASSUMPTIONS:** M1-T01 freezes six types, every step signature and the `load_prices` fake; the only unmitigated edges are stubs, spines under their thicken tasks and wiring, and the system task; no folds; interface, spines, wiring and system solo, the four thicken tasks split; data-science routed to the three stats thicken tasks.
>
> **Open questions:** none. **Uncovered:** none deferred.
>
> Approve, or tell me what to change.

*(Turn ends.)*

**User:** "Approved, go ahead."

Set Status `Approved`, offer to commit `tasks/`, `docs/roadmap.md` and `AGENTS.md`. Then: "The M1 plan is approved. Next is `build-setup` (New): it writes CONSTRAINTS.md and the check scripts before anything is built, then sets the plan's `Base` with `dt base`." *(Turn ends; nothing is built.)*

---

## Cutting a large multi-package stage

**State:** a spending tracker with three packages in three runtimes: `relay` (a serverless worker that talks to the bank aggregator), `core` (a library that syncs, categorizes and compares), `app` (the UI). Stage S1 See my spending covers linking, sync, categories, transfers, review, the transaction list and month comparison. Every `pipelines.md` is Approved: 29 pipelines (relay 7, core 13, app 9) and system pipelines PL-40 Sync (relay → core) and PL-41 Show (core → app).

```
stage_to_cut: S1 See my spending
pipelines_inferred: PL-01, PL-02, …, PL-41
milestone_skills: —
```

One milestone can't hold S1: 29 pipelines make well over a hundred tasks, far past `tasks/plan.md`'s ~400 lines and any one review. Order the pipelines by dependency instead. Every later capability needs synced transactions; categories and transfers need the transaction list; the comparison needs categories. Then cut vertical slices along those lines:

| Milestone | Slice (runs end to end) | Pipelines | Depends |
|---|---|---|---|
| M1 Walking skeleton | Link one account; it syncs through the relay and its transactions list in the app | relay PL-01 link, PL-02 sync; core PL-08 ingest; app PL-20 list; PL-40, PL-41 | — |
| M2 Categories | Transactions get categories; the user corrects one and it sticks | core PL-09–PL-12; app PL-21, PL-22 | M1 (core.Transaction, PL-08 output) |
| M3 Transfers and review | Transfers between own accounts drop out of spending; the user reviews new items | relay PL-03; core PL-13–PL-15; app PL-23–PL-25 | M2 (core.Category) |
| M4 Month comparison | This month vs last, by category | core PL-16–PL-20; app PL-26–PL-28 | M2 (core.Category) |
| … | | | |

Never one milestone per package: "all of the relay" runs nothing a user can see, and it queues `core` and `app` behind it. M3 and M4 both depend only on M2, so they could share a milestone as parallel tracks; they stay apart here because together their critical path would pass 15.

M1 then starts with two interface tasks, one per provider, freezing the boundaries M1 uses: `relay.sync_response` (consumed by `core`) and `core.transaction_list` (consumed by `app`), plus each package's step types and signatures. Each boundary gets a JSON Schema (the three runtimes share no types), one JSON fixture per case the contract lists, and a fake: a fake relay endpoint in `core`'s test support, a fake `core` in `app`'s. Then every step spine of all three packages at once; the four wirings, `core` and `app` on the fakes; then PL-40 and PL-41's system tasks, which swap the fakes for the real relay and core. Critical path: interface, spine, the longest thicken chain, system, well under 15.

**Roadmap:**

```markdown
| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Walking skeleton | relay, core, app | PL-01, PL-02, PL-08, PL-20, PL-40, PL-41 | — | Planned |
| M2 | S1 | Categories | core, app | PL-09–PL-12, PL-21, PL-22, PL-41 | M1 (core.Transaction, PL-08 output) | Designed |
| M3 | S1 | Transfers and review | relay, core, app | PL-03, PL-13–PL-15, PL-23–PL-25, PL-40 | M2 (core.Category) | Designed |
| M4 | S1 | Month comparison | core, app | PL-16–PL-20, PL-26–PL-28, PL-41 | M2 (core.Category) | Designed |

## M1: Walking skeleton
**Outline:** One linked account syncs through the relay and its transactions list in the app.
**Skills:** —
**References:** —
**Exit:** A sandbox account's transactions appear in the app list after one sync; PL-40 and PL-41 smoke tests pass.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

PL-41 appears in M2 and M4 again because those slices thicken it. Every pipeline of S1 lands in some milestone, and only M1 gets a plan; `dt roadmap` shows S1 Planned. At the gate, the cut is the first thing presented: the four slices, why each line falls where it does, and the boundaries M1 freezes.
