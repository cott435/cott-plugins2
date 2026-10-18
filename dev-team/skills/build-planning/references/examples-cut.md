# Example: cutting a large multi-package stage

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

Never one milestone per package: "all of the relay" runs nothing a user can see, and it queues `core` and `app` behind it. M3 and M4 both depend only on M2, so they could share a milestone as parallel tracks; they stay apart here because together their critical path would pass 15. M4 builds after M3, but its Depends still says only `M2 (core.Category)`: a build order is never a Depends entry.

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
