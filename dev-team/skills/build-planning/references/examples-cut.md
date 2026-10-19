# Example: cutting a large multi-package stage

**State:** a spending tracker with three packages in three runtimes: `relay` (a serverless worker that talks to the bank aggregator), `core` (a library that syncs, categorizes and compares), `app` (the UI). Stage S1 See my spending covers linking, sync, categories, transfers, review, the transaction list and month comparison; its Source says success is "I see this month's spending by category against last month's". Every `pipelines.md` is Approved: 29 pipelines (relay PL-01–PL-07, core PL-08–PL-20, app PL-21–PL-29) and system pipelines PL-40 Sync (relay → core) and PL-41 Show (core → app).

```
stage_to_cut: S1 See my spending
pipelines_inferred: PL-01, PL-02, …, PL-41
milestone_skills: —
```

One milestone can't hold S1: 29 pipelines make well over a hundred tasks, far past `tasks/plan.md`'s ~400 lines and any one review. M1 carries the success criterion in its thinnest form: one account, the bank's own categories, this month against last. Later slices deepen it, along dependency lines: own categories need the synced transactions, and transfers and the fuller comparison need own categories.

| Milestone | Slice (runs end to end) | Pipelines | Depends |
|---|---|---|---|
| M1 Walking skeleton | Link one account; it syncs through the relay, its transactions list in the app, and this month is compared with last by the bank's categories | relay PL-01 link, PL-02 sync; core PL-08 ingest, PL-16 compare; app PL-21 list, PL-27 compare; PL-40, PL-41 | — |
| M2 Categories | Transactions get the user's categories; a correction sticks and the comparison uses it | core PL-09–PL-12; app PL-22, PL-23; PL-41 | M1 (core.Transaction, PL-08 output) |
| M3 Transfers and review | Transfers between own accounts drop out of spending; the user reviews new items | relay PL-03; core PL-13–PL-15; app PL-24–PL-26 | M2 (core.Category) |
| M4 Months in depth | Every month against the one before, each category's trend | core PL-17–PL-20; app PL-28, PL-29 | M2 (core.Category) |
| … | | | |

Never one milestone per package: "all of the relay" runs nothing a user can see, and it queues `core` and `app` behind it. Never one per function either: sync, then the list, then the comparison shows the user what they asked for only in the last. M3 and M4 both depend only on M2, so they could share a milestone as parallel tracks; they stay apart here because together their critical path would pass 15. M4 builds after M3, but its Depends still says only `M2 (core.Category)`: a build order is never a Depends entry.

M1 then starts with two interface tasks, one per provider, freezing the boundaries M1 uses: `relay.sync_response` (consumed by `core`) and `core.transaction_list` and `core.month_comparison` (consumed by `app`), plus each package's step types and signatures. Each boundary gets a JSON Schema (the three runtimes share no types), one JSON fixture per case the contract lists, and a fake: a fake relay endpoint in `core`'s test support, a fake `core` in `app`'s. Then every step spine of all three packages at once; the six wirings, `core` and `app` on the fakes; then PL-40 and PL-41's system tasks, which swap the fakes for the real relay and core. Critical path: interface, spine, the longest thicken chain, system, well under 15.

**Roadmap:**

```markdown
| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Walking skeleton | relay, core, app | PL-01, PL-02, PL-08, PL-16, PL-21, PL-27, PL-40, PL-41 | — | Planned |
| M2 | S1 | Categories | core, app | PL-09–PL-12, PL-22, PL-23, PL-41 | M1 (core.Transaction, PL-08 output) | Designed |
| M3 | S1 | Transfers and review | relay, core, app | PL-03, PL-13–PL-15, PL-24–PL-26, PL-40 | M2 (core.Category) | Designed |
| M4 | S1 | Months in depth | core, app | PL-17–PL-20, PL-28, PL-29, PL-41 | M2 (core.Category) | Designed |

## M1: Walking skeleton
**Outline:** One linked account syncs through the relay; the app lists its transactions and compares this month's spending with last month's by the bank's categories.
**Skills:** —
**References:** —
**Exit:** After one sync, a sandbox account's transactions appear in the app list and its two months are compared by category; PL-40 and PL-41 smoke tests pass.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

PL-41 appears in M2 and M4 again because those slices thicken it. Every pipeline of S1 lands in some milestone, and only M1 gets a plan; `dt roadmap` shows S1 Planned. At the gate, the cut is the first thing presented: the four slices, why each line falls where it does, and the boundaries M1 freezes.
