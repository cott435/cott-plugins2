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

**Cut:** PL-02 needs PL-01's prices, but its spine runs on synthetic returns, so both spines fit one milestone: Phase 0 is 2 tasks and the longest chain after it about 3, far under 15. S1 becomes one milestone, M1 Data + stats (`dt next-id M`), which inherits S1's Skills. S2 isn't designed yet, so it stays uncut. Task IDs start at `dt next-id M1-T` (M1-T01).

**Grow check:** no measurable trigger; numpy and pandas only; nothing deploys on its own. Passes.

**One question** (the rest is inferred):

> M1's pipelines cover DATA-01, DATA-02, STAT-01–STAT-04, QR-01 and QR-02. I'd plan all of them, with the exit "PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass". Defer anything? Default: nothing deferred.

**User:** "All of it."

**Written:**
- `tasks/plan.md`: Phase 0 with M1-T01 (PL-01 spine) and M1-T02 (PL-02 spine, which calls PL-01's `load_prices`, so it depends on M1-T01). Phase 1: M1-T03 delisting-aware universe (riskiest: survivorship bias poisons every later number), M1-T04 MP cleaning, checkpoint, M1-T05 shrinkage, M1-T06 planted-factor PCA, exit checkpoint. M1-T03 and M1-T04 share no file or contract symbol, so both are `Parallel: G1`.
- `tasks/todo.md`: six unchecked lines.
- Roadmap: the milestone table with row `| M1 | S1 | Data + stats | quant | PL-01, PL-02 | — | |`, and `## M1: Data + stats` with Outline, Exit and Plan link. S2 keeps its stage row only. Then `dt roadmap` (M1 → Planned, S1 → Planned).
- `AGENTS.md`: the doc map, with `data-science — stats steps`.

**Review gate message:**

> Cut S1 into one milestone, M1 Data + stats (both pipelines, track 5 tasks). Wrote the M1 plan (6 tasks: 2 spine, 4 thicken; checkpoints after M1-T04 and at exit), its todo, the M1 roadmap row and the AGENTS.md doc map. `dt lint` is clean; `uncovered`, `no_spine` and `mode_violations` are empty; every `dt context` packet is under 2,000 lines.
>
> **ASSUMPTIONS:** universe before MP cleaning (survivorship bias is the biggest risk); M1-T03 and M1-T04 run in parallel (G1); spine tasks solo, the four thicken tasks split; data-science routed to the three stats tasks; M1-T02 is M (four files) since every PL-02 step needs a baseline module.
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

One milestone can't hold S1: Phase 0 alone would be a contract task, the longest package's spines (core: 13) and two system spines. Order the pipelines by dependency instead. Every later capability needs synced transactions; categories and transfers need the transaction list; the comparison needs categories. Then cut vertical slices along those lines:

| Milestone | Slice (runs end to end) | Pipelines | Depends |
|---|---|---|---|
| M1 Walking skeleton | Link one account; it syncs through the relay and its transactions list in the app | relay PL-01 link, PL-02 sync; core PL-08 ingest; app PL-20 list; PL-40, PL-41 | — |
| M2 Categories | Transactions get categories; the user corrects one and it sticks | core PL-09–PL-12; app PL-21, PL-22 | M1 |
| M3 Transfers and review | Transfers between own accounts drop out of spending; the user reviews new items | relay PL-03; core PL-13–PL-15; app PL-23–PL-25 | M2 |
| M4 Month comparison | This month vs last, by category | core PL-16–PL-20; app PL-26–PL-28 | M2 |
| … | | | |

Never one milestone per package: "all of the relay" runs nothing a user can see, and it queues `core` and `app` behind it. M3 and M4 both depend only on M2, so they could share a milestone as parallel tracks; they stay apart here because together their track would pass 15.

M1's Phase 0 then has: two contract tasks, one per provider, freezing the boundaries M1 uses: `relay.sync_response` (consumed by `core`) and `core.transaction_list` (consumed by `app`). Each gets a JSON Schema (the three runtimes share no types), one JSON fixture per case the contract lists, and a fake: a fake relay endpoint in `core`'s test support, a fake `core` in `app`'s. Then the four package spines in parallel groups (relay's two chained, since they share files), `core` and `app` running against the fakes; then PL-40 and PL-41's system spines, which swap the fakes for the real relay and core. Track: 2 contract tasks + 2 system spines + the longest chain through the rest (core: PL-08's spine, then its thicken tasks), well under 15.

**Roadmap:**

```markdown
| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Walking skeleton | relay, core, app | PL-01, PL-02, PL-08, PL-20, PL-40, PL-41 | — | Planned |
| M2 | S1 | Categories | core, app | PL-09–PL-12, PL-21, PL-22, PL-41 | M1 | Designed |
| M3 | S1 | Transfers and review | relay, core, app | PL-03, PL-13–PL-15, PL-23–PL-25, PL-40 | M2 | Designed |
| M4 | S1 | Month comparison | core, app | PL-16–PL-20, PL-26–PL-28, PL-41 | M2 | Designed |

## M1: Walking skeleton
**Outline:** One linked account syncs through the relay and its transactions list in the app.
**Skills:** —
**References:** —
**Exit:** A sandbox account's transactions appear in the app list after one sync; PL-40 and PL-41 smoke tests pass.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

PL-41 appears in M2 and M4 again because those slices thicken it. Every pipeline of S1 lands in some milestone, and only M1 gets a plan; `dt roadmap` shows S1 Planned. At the gate, the cut is the first thing presented: the four slices, why each line falls where it does, and the boundaries M1 freezes.
