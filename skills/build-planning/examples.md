# Build Planning Examples

Templates first, then worked examples on the quant project: New (M1), Advance into M2, Replan, a foreign plan, a multi-package system spine, and routing milestone skills and references.

`dt` below means `python3 ../../scripts/dt.py`, run from the project root.

---

## Templates

### `tasks/plan.md` skeleton

A queued plan (`tasks/queued/M<n>-<slug>.md`) uses the same skeleton and has no todo until it's promoted.

`**Base:** —` means pending. build-planning always writes `—`; `build-setup` runs `dt base` after its bar is approved and committed, which sets it to HEAD's short sha.

````markdown
# M<n>: <Milestone name> — Plan

**Milestone:** M<n> · **Status:** Draft · **Base:** — · **Last updated:** YYYY-MM-DD · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** <the capability, and the cases that prove it, in one sentence>
**Covers:** <spec IDs; ranges use an en dash, STAT-01–STAT-04> · **Deferred:** <ID (to M<k>: reason)>, or none
**Skills:** <skill (which steps)>, or none

## Phase 0: Spine

### M<n>-T01: <PL-NN spine with its baseline>
…

## Phase 1: Thicken

### M<n>-T02: <one step upgrade>
…

### Checkpoint after M<n>-T03
…

### Checkpoint: milestone exit
…

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| <risk> | <what goes wrong> | <the task or case that catches it> |

## Open questions

## Replan notes
````

Status runs Draft → Approved → In progress → Done, then `dt archive` replaces the file with the stub.

### Task templates

**Spine task** (Phase 0). Step is the whole pipeline; Mode is always `solo`.

```markdown
### M2-T01: PL-03 spine with equal weights
**Package:** quant · **Step:** PL-03 · **Covers:** — · **Size:** M · **Mode:** solo
**Skills:** —
**Read:** PL-03, portfolio.min_variance, stats.estimate_cov, PORT-01
**Acceptance:**
- [ ] `python -m quant.portfolio backtest --smoke` runs end to end on synthetic returns, every step at its spine version
- [ ] The smoke run is committed as PL-03's smoke test
- [ ] PL-03 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** — · **Files likely:** src/quant/portfolio/__init__.py, src/quant/portfolio/__main__.py, src/quant/portfolio/pipeline.py, src/quant/portfolio/minvar.py, src/quant/portfolio/compare.py
```

**Thicken task.** One step, one package, at most 3 bullets, smoke command in Verify.

```markdown
### M2-T03: Minimum-variance weights
**Package:** quant · **Step:** PL-03.min_variance · **Covers:** PORT-01 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-03, TC-04, PORT-01, portfolio.min_variance
**Acceptance:**
- [ ] TC-04 passes within tolerance; equal weight stays selectable as the baseline
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k minvar` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Parallel:** G1 · **Files likely:** src/quant/portfolio/minvar.py, tests/unit/quant/test_minvar.py
```

| Field | Rule (lint code) |
|---|---|
| `Package` | One package id (`task-fields`) |
| `Step` | `PL-NN.<function>` from the step table (`task-step`); `PL-NN` on a spine task |
| `Covers` | Spec IDs the task satisfies |
| `Size` | XS = 1 file, S = 1–2, M = 3–5 in `Files likely` (`task-size`) |
| `Mode` | `split` for checkable behavior, `solo` for spine, refactor, glue, doc-sync |
| `Skills` | Skill names, or `—`. Every skill on the roadmap section's `**Skills:**` line lands on at least one task (`skills_unrouted`). A missing skill is still named |
| `Read` | IDs and repo paths, comma-separated. Everything the builder needs, nothing more (`missing-ref`). References by ID with an optional selector: `RF-01:residualize`, `RF-01:outline`, `RF-03:<heading>`; a long one with none warns (`ref-large`). Every milestone reference lands on at least one task (`references_unrouted`) |
| `Acceptance` | ≤ 3 checkbox bullets, each test-backed (`task-acceptance`) |
| `Verify` | Backticked commands joined by ` · `. After Phase 0, includes the smoke command (`verify-smoke`) |
| `Depends on` | Task IDs earlier in the plan, or `—` (`depends`) |
| `Parallel` | Optional `G<n>`. No shared file or contract symbol in a group (`parallel`) |
| `Files likely` | Comma-separated paths |
| `Reason` | Optional one line: a mode override, or a second package or step |
| `Blocked` | Added when a task is paused; Replan removes it once resolved |

Title rule: no " and " (`task-title`). Required fields: Package, Step, Size, Mode, Read, Acceptance, Verify (`task-fields`).

### Checkpoint blocks

Every 2–3 tasks:

```markdown
### Checkpoint after M2-T03
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition
```

Last, after the final task: the same list under `### Checkpoint: milestone exit`, plus `- [ ] The Scope's Exit holds`.

Findings are not written by this skill. The orchestrator records the reviewer's findings with `dt finding`, and they look like this:

```markdown
**Findings:**
- M2-R01 Important · CR-21 · `portfolio/compare.py::compare` complexity 14 → fix task M2-T05
- M2-R02 Nit · readability · column names → won't fix: match the paper's notation
```

A finding whose disposition is a fix task means Replan adds that task.

### `tasks/todo.md`

One line per task, `<ID> <title> (<package>, <size>, <mode>)`. No checkpoints. Lines start unchecked; only `dt tick` checks them.

```markdown
# M2: Classical portfolios — Todo

- [ ] M2-T01 PL-03 spine with equal weights (quant, M, solo)
- [ ] M2-T02 Out-of-sample comparison (quant, S, split)
- [ ] M2-T03 Minimum-variance weights (quant, S, split)
- [ ] M2-T04 Shrinkage as the backtest default (quant, XS, solo)
```

### Stub plan (between milestones)

Written by `dt archive`. Never deleted; replaced only by the next plan.

```markdown
# Between milestones

**Status:** Between milestones · **Last updated:** 2026-11-02 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)
```

### Roadmap fill-ins

`idea-refine` adds the row (Milestone, Name, Source). This skill fills Packages, Pipelines and Depends, and the section's `**Exit:**`, `**Plan:**` and outcome text. `dt roadmap` writes `Status*`; never edit it.

```markdown
| M2 | Classical portfolios | ideas/classical-portfolios.md | quant | PL-03 | M1 | Planned |

## M2: Classical portfolios
**Exit:** Min-var beats equal weight on out-of-sample variance; TC-04 passes.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

Later milestones get only the row and a 3–6 line section (Exit, and Plan once a plan exists).

### AGENTS.md doc map

Written in New mode, ≤ 25 lines, no script paths (the session-start hook supplies them). Replace only these two sections; leave the rest of the file alone. If the repo has `CLAUDE.md` and no `AGENTS.md`, write them there.

```markdown
## Docs
- Plan with dev-team2's `build-planning`, not agent-skills' `/plan`.
- Your task's context: `dt context <M#-T##>`. Read only what it prints.
- Any section by ID: `dt section <ID>...` (e.g. PL-02 TC-02 STAT-02 AD-03)
- Package docs: `docs/packages/<pkg>/{architecture,contract,pipelines,tests}.md`
- Real layout: `dt layout <pkg>` (planned layouts are gone once the spine lands)
- Quality bar: CONSTRAINTS.md. Oracle files (tests/fixtures/*/expected.json) need user approval to change.
## Project skills
- data-science — stats steps
```

Use real IDs from the project in the `dt section` example. List each project skill with the steps it's routed to.

---

## Example 1: New — quant M1

**State:** brief Accepted, spec and architecture Approved (single package `quant`), `pipelines.md` Approved with PL-01 (load prices) and PL-02 (covariance report), `tests.md` Approved with TC-01–TC-03. `idea-refine` wrote roadmap rows M1 and M2, with Packages, Pipelines and Depends `—`. No `tasks/`.

```
$ dt status --skill build-planning
skill: build-planning
mode: new
docs: brief Accepted · spec Approved · architecture Approved (Single package) · roadmap ok · plan missing · constraints missing
next ids: AD-04 PL-03 TC-04 M3
milestone: none
progress: 0/0
next_task: none
blocked_tasks: none
uncovered: none
no_spine: none
mode_violations: none
draft_pipelines: none
changed_since_plan: none
pipelines_inferred: PL-01, PL-02
skills_missing: none
skills_available: data-science
milestone_skills: data-science
milestone_references: none
skills_unrouted: none
references_unrouted: none
grow_triggers: none
drift: none
stale_contracts: none
queued: none
base: pending
references_unindexed: none
references_changed: none
references_missing: none
```

With no plan yet, `uncovered`, `no_spine` and the two unrouted lists have nothing to check; they count at the gate's re-run. `milestone_skills` comes from M1's roadmap section (`**Skills:** data-science`); M1 has no references. M1's row lists no pipelines, so `dt` inferred PL-01 and PL-02 from its Source (the brief's spec IDs). Task IDs start at `dt next-id M1-T` (M1-T01).

**Grow check:** no measurable trigger; numpy and pandas only; nothing deploys on its own. Passes.

**One question** (the rest is inferred):

> M1's pipelines cover DATA-01, DATA-02, STAT-01–STAT-04, QR-01 and QR-02. I'd plan all of them, with the exit "PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass". Defer anything? Default: nothing deferred.

**User:** "All of it."

**Written:**
- `tasks/plan.md`: Phase 0 with M1-T01 (PL-01 spine) and M1-T02 (PL-02 spine, which calls PL-01's `load_prices`, so it depends on M1-T01). Phase 1: M1-T03 delisting-aware universe (riskiest: survivorship bias poisons every later number), M1-T04 MP cleaning, checkpoint, M1-T05 shrinkage, M1-T06 planted-factor PCA, exit checkpoint. M1-T03 and M1-T04 share no file or contract symbol, so both are `Parallel: G1`.
- `tasks/todo.md`: six unchecked lines.
- Roadmap: M1 Packages `quant` and Pipelines `PL-01, PL-02` (from `pipelines_inferred`), Exit and Plan link. M2 keeps its outline only. Then `dt roadmap` (M1 → Planned).
- `AGENTS.md`: the doc map, with `data-science — stats steps`.

**Review gate message:**

> Wrote the M1 plan (6 tasks: 2 spine, 4 thicken; checkpoints after M1-T04 and at exit), its todo, the M1 roadmap entry and the AGENTS.md doc map. `dt lint` is clean; `uncovered`, `no_spine` and `mode_violations` are empty; every `dt context` packet is under 2,000 lines.
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

## Example 2: Advance — M1 done, M2 kickoff

**State:** all six M1 todo items ticked, both checkpoints ticked. Assume `test-planning` Extend added a PL-03 Strategy row (smoke `python -m quant.portfolio backtest --smoke`) and TC-04 (minimum-variance weights for a two-asset closed form).

**Turn 1 — exit checkpoint.**
```
mode: advance
milestone: M1 In progress
progress: 6/6
```
`dt lint tasks/` shows no `finding-disposition`: M1-R01 and M1-R02 each have one, and neither is Critical. Present: what M1 delivered against its Exit, the findings and their dispositions, the Replan notes. "Approve M1 as done?" *(Turn ends.)*

**Turn 2.** User: "Yes, M1 is done." Set Status `Done`. "Next is `build-setup` Ratchet, to record the measured values and offer tightenings. Come back here afterwards." *(Turn ends.)*

**Turn 3 — archive and kickoff check.** CONSTRAINTS.md now reads `**Ratcheted:** M1` and `dt status --skill build-setup` no longer says `ratchet`, so continue.
```
$ dt archive
tasks/archive/M1-data-stats.md
```
Append the outcome and repoint M1's plan link:
```markdown
## M1: Data + stats
**Exit:** PCA and MP cleaning run on 10y of daily returns; PL-01 and PL-02 golden cases pass.
**Plan:** [../tasks/archive/M1-data-stats.md](../tasks/archive/M1-data-stats.md)
**Outcome:** Done 2026-11-02 — shrinkage moved ahead of MP cleaning (Replan 2026-10-28).
```
Run `dt roadmap` (M1 → Done). Kickoff check: `dt status --skill build-planning` prints `drift: none` and `stale_contracts: none`; no queued plan. No gate needed. Grow check for M2: the portfolio code adds no new dependency stack and deploys nothing on its own; passes.

One scope question:

> The M2 idea mentions risk parity and HRP, but the spec has only PORT-01 (min-var) and PORT-02 (out-of-sample comparison). Plan M2 for those two? Default: yes; risk parity and HRP need `spec-writing` Extend first.

*(Turn ends.)*

**Turn 4 — next plan.** User: "Yes, just those two." Write `tasks/plan.md` (replacing the stub) and `tasks/todo.md`:

````markdown
# M2: Classical portfolios — Plan

**Milestone:** M2 · **Status:** Draft · **Base:** — · **Last updated:** 2026-11-02 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** Min-var beats equal weight on out-of-sample variance; TC-04 passes.
**Covers:** PORT-01, PORT-02 · **Deferred:** none
**Skills:** data-science (min_variance)

## Phase 0: Spine

### M2-T01: PL-03 spine with equal weights
**Package:** quant · **Step:** PL-03 · **Covers:** — · **Size:** M · **Mode:** solo
**Skills:** —
**Read:** PL-03, portfolio.min_variance, stats.estimate_cov, PORT-01
**Acceptance:**
- [ ] `python -m quant.portfolio backtest --smoke` runs end to end on synthetic returns, every step at its spine version
- [ ] The smoke run is committed as PL-03's smoke test
- [ ] PL-03 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** — · **Files likely:** src/quant/portfolio/__init__.py, src/quant/portfolio/__main__.py, src/quant/portfolio/pipeline.py, src/quant/portfolio/minvar.py, src/quant/portfolio/compare.py

## Phase 1: Thicken

### M2-T02: Out-of-sample comparison
**Package:** quant · **Step:** PL-03.compare · **Covers:** PORT-02 · **Size:** S · **Mode:** split
**Skills:** —
**Read:** PL-03, PORT-02
**Acceptance:**
- [ ] Given a walk-forward split, when `compare` runs, then each rebalance uses only returns before its date
- [ ] Realized out-of-sample variance is reported for each portfolio next to equal weight
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k compare` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Parallel:** G1 · **Files likely:** src/quant/portfolio/compare.py, tests/unit/quant/test_compare.py

### M2-T03: Minimum-variance weights
**Package:** quant · **Step:** PL-03.min_variance · **Covers:** PORT-01 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-03, TC-04, PORT-01, portfolio.min_variance
**Acceptance:**
- [ ] TC-04 passes within tolerance; equal weight stays selectable as the baseline
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k minvar` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Parallel:** G1 · **Files likely:** src/quant/portfolio/minvar.py, tests/unit/quant/test_minvar.py

### Checkpoint after M2-T03
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

### M2-T04: Shrinkage as the backtest default
**Package:** quant · **Step:** PL-03.estimate_cov · **Covers:** STAT-02 · **Size:** XS · **Mode:** solo
**Reason:** wiring only; the shrinkage estimator's behavior is already tested by M1-T05
**Skills:** —
**Read:** PL-03, stats.estimate_cov
**Acceptance:**
- [ ] The backtest uses shrinkage by default; `--cov sample` still selects the baseline
- [ ] PL-03 smoke test still passes
**Verify:** `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T03 · **Files likely:** src/quant/portfolio/pipeline.py

### Checkpoint: milestone exit
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition
- [ ] The Scope's Exit holds

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Look-ahead in the rebalance window | min-var looks better than it is | M2-T02 comes first and pins the walk-forward split |

## Open questions

## Replan notes
````

Why this order: the comparison is the evaluation, so it's the riskiest step and is planned first (a leaky evaluation would make every later result meaningless). M2-T02 and M2-T03 share no file and no contract symbol, so they're `G1`. Both split tasks test functions the spine creates (`compare`, `min_variance` at equal weight), so neither tester writes against a guess. M2-T04 changes a default, which is behavior, so `solo` needs the `Reason` line.

Fill in the roadmap (M2: Packages, Pipelines, Depends, Exit, Plan link) and run `dt roadmap` (M2 → Planned). Run the Review Gate and present it with ASSUMPTIONS (the order above, G1, the M2-T04 override, data-science routed to M2-T03 only). *(Turn ends.)*

**Turn 5.** User: "Approved." Set Status `Approved`; offer the commit. "Next is `build-setup` Extend: M2 adds the `quant.portfolio` module, so its import contracts change. Once the bar is approved and committed, it sets the plan's `Base` with `dt base`." *(Turn ends.)*

---

## Example 3: Replan — MP cleaning needs shrinkage first

**State:** mid-M1. The build paused M1-T04:
```markdown
**Blocked:** TC-02 fails on sample covariance when T/N < 5; cleaning needs the shrinkage estimate as input
```
```
mode: replan
blocked_tasks: M1-T04
```

No step changed (PL-02 already runs `estimate_cov` before `clean_eigen`), so no `pipeline-design` Revise is needed; only the task order changes. Had a step changed, `pipeline-design` Revise would run first: while `pipelines.md` is Draft, `dt status` says `blocked` (`waiting for docs/packages/quant/pipelines.md approval`); once it's re-approved with a later `Last updated` than the plan, it says `replan` with `changed_since_plan: docs/packages/quant/pipelines.md`.

**Edits:**
- Move the M1-T05 section above M1-T04. IDs stay; plan position sets the order, and `dt lint` checks `Depends on` by position.
- M1-T05: `**Depends on:** M1-T02` (it depended on M1-T04). M1-T04: `**Depends on:** M1-T05`; remove its `**Parallel:** G1` and the `Blocked` line. M1-T03 is now alone in G1, so remove its `Parallel` too.
- M1-T04 gains no new bullet: TC-02 already covers it.
- Reorder `todo.md` to match.
- `## Replan notes`: `- 2026-10-28: moved M1-T05 ahead of M1-T04 (MP cleaning needs the shrinkage estimate; TC-02 failed on sample cov); dropped none`
- Status → Draft.

**Gate message:** what moved and why, the dependency change, "dropped none". *(Turn ends.)*

**A drop looks like this.** It's listed for approval first ("Drop M1-T06? PCA is already checked by TC-03 in M1-T02's smoke run. Default: keep"). Only after an unambiguous yes, remove the section and todo line, and add under Replan notes:
```markdown
- ~~M1-T06: Planted-factor PCA check~~ Retired 2026-10-28: TC-03 now runs in M1-T02's smoke test
```
`dt next-id` counts the retired ID, so it's never reused, and `dt lint` flags any `Depends on` still pointing at it.

---

## Example 4: Foreign plan

```
mode: foreign
```

`tasks/plan.md` came from agent-skills' `/plan`: no `**Milestone:**` header, 5 of 9 tasks unchecked.

> `tasks/plan.md` is an agent-skills `/plan` plan with 5 unchecked tasks, which may be mid-build. I won't overwrite it. Options:
> 1. Finish it with `/build` first, then run me again. (default)
> 2. Move or discard it yourself, then run me again.
>
> Which one?

*(Turn ends. Nothing is written.)*

---

## Example 5: Multi-package system spine (M3 after Grow)

After `architecture-design` Grow split quant into `data`, `stats`, `portfolio` and `features`, the root defines system pipeline PL-05 Research run (data → stats → features → portfolio, grown from PL-03). `pipeline-design` Grow kept PL-03 Min-variance backtest in `portfolio` as PL-05's portfolio segment (`**Part of:** PL-05`), and its Extend round added PL-06 Feature screening in `features`, also `Part of: PL-05`. The M3 row lists none of this, so its Packages and Pipelines come from `pipelines_inferred`. Phase 0 puts the system spine first:

```markdown
## Phase 0: Spine

### M3-T01: PL-05 system spine across packages
**Package:** data · **Step:** PL-05 · **Covers:** FEAT-01 · **Size:** M · **Mode:** solo
**Reason:** system spine
**Read:** PL-05, PL-03, data.load_prices, stats.estimate_cov, features.screen
**Acceptance:**
- [ ] `python -m portfolio backtest --smoke` runs data → stats → features → portfolio on synthetic prices, each hand-off through its named contract
- [ ] `features.screen` runs at its spine version (keeps every feature)
- [ ] The smoke run is committed as PL-05's smoke test
**Verify:** `python -m portfolio backtest --smoke` · `scripts/check.sh gate --pkg data`
**Depends on:** — · **Files likely:** packages/features/src/features/__init__.py, packages/features/src/features/screen.py, packages/portfolio/src/portfolio/pipeline.py

### M3-T02: PL-06 spine with a univariate screen
…
```

The system spine's Package is `data`, the owner of PL-05's first step (system pipelines have no Entry). `--pkg data` scopes the gate to data and everything that depends on it, which here is every package. PL-05 is in the root, which has no pre-build sections; PL-06's spine (M3-T02) clears `features`' planned layout. Moving the code under `packages/` (the drift `pipeline-design` Grow listed) is its own solo task, omitted here.

Multi-package Verify lines scope the gate with `--pkg`. Phase 1 tasks for PL-06's null test name `null-hypothesis-testing` in `Skills:`. If it isn't installed, it's still named, `dt status` lists it under `skills_missing`, and the gate asks the user whether to install it or accept the gap.

---

## Example 6: Routing milestone skills and references

A variant of M2, Structure + classical portfolios, where PL-03 runs a `remove_market` step before `estimate_cov`. `idea-refine` wrote the roadmap section's `**Skills:** data-analysis, null-hypothesis-testing`, and `reference-intake` assigned RF-01 (market decomposition) to M2.

```
$ dt status --skill build-planning
mode: extend
…
milestone_skills: data-analysis, null-hypothesis-testing
milestone_references: RF-01
references_unindexed: none
references_changed: none
references_missing: none
```

Nothing is waiting for intake, so plan. `dt section RF-01` gives the entry. *Use for* names the market-removal step, *Key parts* lists `residualize`, and *Caveats* says the reference fits PCA on the whole sample. The file is over 300 lines, so the task reads one function through a selector:

```markdown
### M2-T04: Per-window market removal
**Package:** quant · **Step:** PL-03.remove_market · **Covers:** STRUCT-02 · **Size:** S · **Mode:** split
**Skills:** data-analysis
**Read:** PL-03, TC-09, stats.residualize, RF-01:residualize
**Acceptance:**
- [ ] TC-09 passes: the planted factor is removed within tolerance
- [ ] Given a walk-forward split, when `remove_market` runs, then each window's factors are fit only on returns inside that window
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k residualize` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Files likely:** src/quant/stats/residualize.py, tests/unit/quant/test_residualize.py
```

- The second bullet comes from TC-09 and the spec, not from the reference. Acceptance never says "reuse RF-01". Whether to reuse the residual arithmetic is the builder's call; `dt context M2-T04` prints the entry, the reference banner with its Caveats, and only `residualize`.
- `null-hypothesis-testing` goes on M2-T06, the claims task that tests whether the residual structure beats noise. The Scope reads `**Skills:** data-analysis (remove_market, estimate_cov), null-hypothesis-testing (claims)`.
- At the gate, `references_unrouted` and `skills_unrouted` are both `none`. Had a milestone item stayed off every task, it would need a reason under Open questions, such as `- RF-01 unrouted: the per-window fit is specified fully by TC-09; the reference adds nothing`. The user then decides at the gate.
