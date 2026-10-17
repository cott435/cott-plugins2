# Build Planning Examples

Templates first, then worked examples on the quant project: New (cut S1, plan M1), Advance into M2, Replan, a foreign plan, a contract-first Phase 0 across packages, routing milestone skills and references, and cutting a large multi-package stage.

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

**Spine task** (Phase 0). Step is the whole pipeline; Mode is always `solo`. A contract task (multi-package) has Step `contract`; see Example 5.

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
| `Step` | `PL-NN.<function>` from the step table (`task-step`); `PL-NN` on a spine task; `contract` on a contract task |
| `Covers` | Spec IDs the task satisfies |
| `Size` | XS = 1 file, S = 1–2, M = 3–5 in `Files likely` (`task-size`) |
| `Mode` | `split` for checkable behavior, `solo` for contract, spine, refactor, glue, doc-sync |
| `Skills` | Skill names, or `—`. Every skill on the milestone's `**Skills:**` line (else its stage's) lands on at least one task (`skills_unrouted`). A missing skill is still named |
| `Read` | IDs and repo paths, comma-separated. Everything the builder needs, nothing more (`missing-ref`). References by ID with an optional selector: `RF-01:residualize`, `RF-01:outline`, `RF-03:<heading>`; a long one with none warns (`ref-large`). Every milestone reference lands on at least one task (`references_unrouted`) |
| `Acceptance` | ≤ 3 checkbox bullets, each test-backed (`task-acceptance`) |
| `Verify` | Backticked commands joined by ` · `. After Phase 0, includes the smoke command (`verify-smoke`) |
| `Depends on` | Task IDs earlier in the plan, or `—` (`depends`) |
| `Parallel` | Optional `G<n>`. No shared file or contract symbol in a group (`parallel`). Package spines carry one; the contract task and the system spine never do (they count in full toward `milestone-size`) |
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

### Milestone rows

`idea-refine` adds the stage (`S<n>`: Name, Source, and a section with Outline and Skills). When the stage's pipelines are approved, this skill cuts it: one milestone row per slice under the milestone table (add the table below the stage table if it's missing), and a section with the slice's `**Outline:**`, then `**Exit:**`, `**Plan:**` and outcome text once planned. `dt roadmap` writes both `Status*` columns; never edit them.

```markdown
| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | Data + stats | brief | Building |
| S2 | Classical portfolios | ideas/classical-portfolios.md | Planned |

| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Data + stats | quant | PL-01, PL-02 | — | Building |
| M2 | S2 | Classical portfolios | quant | PL-03 | M1 | Planned |

## M2: Classical portfolios
**Outline:** A walk-forward backtest compares min-var with equal weight.
**Exit:** Min-var beats equal weight on out-of-sample variance; TC-04 passes.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

A stage that fits one milestone gets one, and the milestone inherits the stage's Skills and references. A stage cut into several gives each milestone `**Skills:**` and `**References:**` lines from the stage's (Example 7). Later milestones get only the row and a 3–6 line section (Outline, Exit, and Plan once a plan exists).

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
Run `dt roadmap` (M1 → Done, S1 → Done). Kickoff check: `dt status --skill build-planning` prints `drift: none`, `stale_contracts: none` and `stage_to_cut: S2 Classical portfolios`; no queued plan. No gate needed. Grow check for S2: the portfolio code adds no new dependency stack and deploys nothing on its own; passes. S2's one pipeline, PL-03, fits one milestone: cut it into M2 (Stage S2, Depends M1, since PL-03 reads M1's covariance).

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

Write M2's row and section (Packages, Pipelines, Depends, Outline, Exit, Plan link) and run `dt roadmap` (M2 → Planned, S2 → Planned). Run the Review Gate and present it with ASSUMPTIONS (the order above, G1, the M2-T04 override, data-science routed to M2-T03 only). *(Turn ends.)*

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

## Example 5: Contract-first Phase 0 across packages (M3 after Grow)

After `architecture-design` Grow split quant into `data`, `stats`, `portfolio` and `features`, the root defines system pipeline PL-05 Research run (data → stats → features → portfolio, grown from PL-03). `pipeline-design` Grow kept PL-03 Min-variance backtest in `portfolio` as PL-05's portfolio segment (`**Part of:** PL-05`), and its Extend round added PL-06 Feature screening in `features`, also `Part of: PL-05`. M3 builds PL-06 and PL-05; PL-03 already exists.

`features.screen` is new and crosses a boundary: `portfolio` consumes it. Its contract section names the boundary:

```markdown
### features.screen: Screened feature panel
`def screen(panel: FeaturePanel, *, max_features: int = 50) -> FeaturePanel`
- **Invariants:** same index as the input; at most `max_features` columns; no column with NaN share > 5%
- **Errors:** `ValueError` if the panel is empty
- **Boundary:** portfolio · **Fixtures:** tests/contracts/features.screen/ · **Cases:** typical panel, one feature, all-NaN column dropped
- **Used by:** portfolio; PL-05, PL-06
```

Phase 0 freezes that boundary first, then builds both packages side by side, then integrates:

```markdown
## Phase 0: Spine

### M3-T01: Freeze the features.screen contract
**Package:** features · **Step:** contract · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** features.screen
**Acceptance:**
- [ ] A pandera schema for the screened panel; each case's sample frame validates against it
- [ ] `portfolio`'s test support has a fake `screen` that returns the sample frames and nothing else
**Verify:** `pytest tests/contracts/features.screen` · `scripts/check.sh gate --pkg features`
**Depends on:** — · **Files likely:** packages/features/src/features/schemas.py, tests/contracts/features.screen/test_contract.py

### M3-T02: PL-06 spine with a univariate screen
**Package:** features · **Step:** PL-06 · **Covers:** FEAT-01 · **Size:** M · **Mode:** solo
**Read:** PL-06, features.screen, FEAT-01
**Acceptance:**
- [ ] `python -m features screen --smoke` runs end to end on synthetic features; its output validates against the M3-T01 schema
- [ ] PL-06 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m features screen --smoke` · `scripts/check.sh gate --pkg features`
**Depends on:** M3-T01 · **Parallel:** G1 · **Files likely:** packages/features/src/features/__init__.py, packages/features/src/features/pipeline.py, packages/features/src/features/screen.py

### M3-T03: PL-03 on screened features, against the contract fake
**Package:** portfolio · **Step:** PL-03 · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-03, features.screen
**Acceptance:**
- [ ] `python -m portfolio backtest --smoke` runs end to end on every `features.screen` fixture through the fake
**Verify:** `python -m portfolio backtest --smoke` · `scripts/check.sh gate --pkg portfolio`
**Depends on:** M3-T01 · **Parallel:** G1 · **Files likely:** packages/portfolio/src/portfolio/pipeline.py, packages/portfolio/tests/support/fake_screen.py

### M3-T04: PL-05 system spine across packages
**Package:** data · **Step:** PL-05 · **Covers:** — · **Size:** S · **Mode:** solo
**Reason:** system spine
**Read:** PL-05, data.load_prices, stats.estimate_cov, features.screen
**Acceptance:**
- [ ] `python -m portfolio research --smoke` runs data → stats → features → portfolio on synthetic prices with the real `screen`, no fake
- [ ] The real `screen` output still validates against the M3-T01 schema; the smoke run is committed as PL-05's smoke test
**Verify:** `python -m portfolio research --smoke` · `scripts/check.sh gate --pkg data`
**Depends on:** M3-T02, M3-T03 · **Files likely:** packages/portfolio/src/portfolio/research.py
```

M3-T02 and M3-T03 share no file, and the only contract symbol both read is the one M3-T01 froze, which is read-only for the rest of the milestone, so both run in G1 (`dt lint`'s `parallel` check skips symbols a contract task froze). The fake in M3-T03 is allowed because it is built from the contract's schema and fixtures, and both sides test against them: M3-T02 asserts its output validates, M3-T03 consumes the fixtures. Neither spine mocks a step of its own package.

**Track:** the contract task and the system spine have no group, so they count in full (2); the chain through the rest is M3-T02 plus the longest thicken chain after it. With the old order (system spine first, then each package spine, all serial), Phase 0 alone would have counted 4.

The system spine's Package is `data`, the owner of PL-05's first step (system pipelines have no Entry). `--pkg data` scopes the gate to data and everything that depends on it, which here is every package. PL-05 is in the root, which has no pre-build sections; PL-06's spine (M3-T02) clears `features`' planned layout. Moving the code under `packages/` (the drift `pipeline-design` Grow listed) is its own solo task, omitted here.

Multi-package Verify lines scope the gate with `--pkg`. Phase 1 tasks for PL-06's null test name `null-hypothesis-testing` in `Skills:`. If it isn't installed, it's still named, `dt status` lists it under `skills_missing`, and the gate asks the user whether to install it or accept the gap.

---

## Example 6: Routing milestone skills and references

A variant of M2, Structure + classical portfolios, where PL-03 runs a `remove_market` step before `estimate_cov`. `idea-refine` wrote stage S2's `**Skills:** data-analysis, null-hypothesis-testing`, and `reference-intake` assigned RF-01 (market decomposition) to S2. S2 was cut into the single milestone M2, which inherits both.

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

---

## Example 7: Cutting a large multi-package stage

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
