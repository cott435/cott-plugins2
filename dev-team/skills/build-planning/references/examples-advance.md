# Example: Advance — M1 done, M2 kickoff

**State:** all fourteen M1 todo items ticked, both checkpoints ticked. Assume `test-planning` Extend added a PL-03 Strategy row (smoke `python -m gridload.reserve evaluate --smoke`) and TC-04 (the optimized reserve allocation for a two-region closed form).

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
tasks/archive/M1-ingest-clean.md
```
Append the outcome and repoint M1's plan link:
```markdown
## M1: Ingest & clean
**Exit:** The Fourier profile and the residual spectrum run on 10y of hourly load; PL-01 and PL-02 golden cases pass.
**Plan:** [../tasks/archive/M1-ingest-clean.md](../tasks/archive/M1-ingest-clean.md)
**Outcome:** Done 2026-11-02 — the spectrum waited on the Fourier fit (Replan 2026-10-28).
```
Run `dt roadmap` (M1 → Done, S1 → Done). Kickoff check: `dt status --skill build-planning` prints `drift: none`, `stale_contracts: none` and `stage_to_cut: S2 Seasonality & baselines`; no queued plan. No gate needed. Grow check for S2: the reserve code adds no new dependency stack and deploys nothing on its own; passes. S2's one pipeline, PL-03, fits one milestone: cut it into M2 (Stage S2, Depends M1, since PL-03 reads M1's seasonal profile).

One scope question:

> The M2 idea mentions a peak-weighted split and a chance-constrained allocation, but the spec has only RES-01 (optimized allocation) and RES-02 (out-of-sample comparison). Plan M2 for those two? Default: yes; the other two need `spec-writing` Extend first.

*(Turn ends.)*

**Turn 4 — next plan.** User: "Yes, just those two." Write `tasks/plan.md` (replacing the stub) and `tasks/todo.md`:

````markdown
# M2: Seasonality & baselines — Plan

**Milestone:** M2 · **Status:** Draft · **Base:** — · **Last updated:** 2026-11-02 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** The optimized allocation beats the equal split on held-out reserve shortfall; TC-04 passes.
**Covers:** RES-01, RES-02 · **Deferred:** none
**Skills:** data-science (allocate)

## Phase 0: Interface

### M2-T01: PL-03 interface
**Package:** gridload · **Step:** contract · **Kind:** interface · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-03, reserve.Allocation, reserve.Comparison, reserve.allocate, reserve.compare
**Acceptance:**
- [ ] `Allocation` and `Comparison` are code in `reserve/types.py`; each sample in `tests/contracts/reserve.<Type>/` validates
- [ ] `allocate` and `compare` import with their contract signatures, bodies `raise NotImplementedError("M2-T02")` and `("M2-T03")`; `reserve/__init__.py` exports the contract
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/gridload/reserve/**, tests/contracts/reserve.Allocation/, tests/contracts/reserve.Comparison/

## Phase 1: Step spines

M2-T02 `allocate` spine (equal split) as in `../examples.md`; M2-T03 `compare` spine (realized shortfall only), the same shape.

## Phase 2: Wiring and thicken

### M2-T04: Wire PL-03
**Package:** gridload · **Step:** PL-03 · **Kind:** wiring · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-03, profile.fit_seasonality, RES-01
**Acceptance:**
- [ ] `python -m gridload.reserve evaluate --smoke` runs end to end on synthetic load, every step at its spine version; committed as PL-03's smoke test
- [ ] PL-03 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m gridload.reserve evaluate --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T02, M2-T03 · **Writes:** src/gridload/reserve/pipeline.py, src/gridload/reserve/__main__.py, tests/unit/gridload/test_pl03_smoke.py

M2-T05 Out-of-sample comparison (`compare`, split, RES-02, on M2-T03): Given a walk-forward split, each allocation uses only load before its week; realized held-out shortfall is reported next to the equal split. M2-T06 Optimized reserve allocation as in `../examples.md`.

### Checkpoint after M2-T06
…

### M2-T07: Fourier profile as the allocation default
**Package:** gridload · **Step:** PL-03.fit_seasonality · **Kind:** thicken · **Covers:** STAT-02 · **Size:** XS · **Mode:** solo
**Reason:** wiring only; the Fourier fit's behavior is already tested by M1-T12
**Read:** PL-03, profile.fit_seasonality
**Acceptance:**
- [ ] The allocation uses the Fourier profile by default; `--profile means` still selects the baseline
- [ ] PL-03 smoke test still passes
**Verify:** `python -m gridload.reserve evaluate --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T04 · **Writes:** src/gridload/reserve/pipeline.py

### Checkpoint: milestone exit
…

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M2-T03 compare spine | M2-T02 allocate spine | data | reserve.Allocation sample (M2-T01) |
| M2-T04 wire PL-03 | M2-T02 allocate spine | order | none: integration: the smoke runs it |
| M2-T04 wire PL-03 | M2-T03 compare spine | order | none: integration: the smoke runs it |
| M2-T05 comparison | M2-T03 compare spine | code | none: thickens the same module |
| M2-T06 optimized allocation | M2-T02 allocate spine | code | none: thickens the same module |
| M2-T07 Fourier default | M2-T04 wire PL-03 | code | none: changes the entry it wrote |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Look-ahead in the allocation window | the optimized allocation looks better than it is | M2-T02 comes first and pins the walk-forward split |

## Open questions

## Replan notes
````

Why this shape: `fit_seasonality` is M1's, built and real, so PL-03 needs no fake and M2 no system task. M2-T03 doesn't wait for M2-T02: it builds on the `Allocation` sample. The comparison is the evaluation and the riskiest step, but nothing needs to wait for it, so risk adds no edge; its tester starts in wave 1 like M2-T06's. Critical path 4 (M2-T01 → M2-T02 → M2-T04 → M2-T07), widest wave 4 (two spines, two testers). M2-T07 changes a default, which is behavior, so `solo` needs the `Reason` line.

Write M2's row (Depends `M1 (profile.fit_seasonality)`) and section (Packages, Pipelines, Outline, Exit, Plan link) and run `dt roadmap` (M2 → Planned, S2 → Planned). Run the Review Gate and present it with ASSUMPTIONS (the shape above, the unmitigated edges, the M2-T07 override, data-science routed to M2-T06 only). *(Turn ends.)*

**Turn 5.** User: "Approved." Set Status `Approved`; offer the commit. "Next is `build-setup` Extend: M2 adds the `gridload.reserve` module, so its import contracts change. Once the bar is approved and committed, it sets the plan's `Base` with `dt base`." *(Turn ends.)*
