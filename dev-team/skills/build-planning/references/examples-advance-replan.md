# Examples: Advance and Replan

`dt` means `python3 ../../scripts/dt.py`, run from the project root.

## Advance — M1 done, M2 kickoff

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

## Replan — MP cleaning needs shrinkage first

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
