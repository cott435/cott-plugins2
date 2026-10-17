# Iteration 7: the first interface-first run

**Skills:** branch `interface-first-design` at `41d2ebd` (interface-first planning; every skill restructured as its role plus one file per mode). **Grader:** the same commit. **Models:** Opus 5.5 agent, Sonnet simulated user, Opus 5.5 blind judge (both orders). n=1 per trajectory, no cost cap. Run on 2026-10-17. Raw runs are in `../../../../dev-team-workspace/iteration-7/`; the packaged runs are in `bench/` there.

**Flow pages** (workflow-analyzer, drawn by `runviz.py` at the end of `run.sh`, then copied here in the workspace's layout so their links hold):
- all runs: [runflow/index.html](runflow/index.html)
- one run: `<trajectory>/with_skill/flow/flow.html`, e.g. [quant-incremental](quant-incremental/with_skill/flow/flow.html) (turn and agent pages in `turns/`, `units/`)
- its plan map: `<trajectory>/with_skill/flow/plan/index.html`, and the M1 build view `…/plan/M1.html`, e.g. [quant all-at-once M1](quant-all-at-once/with_skill/flow/plan/M1.html)

Before the run: `dryrun.py` was as pinned, `simulate.py` passed, and the one-turn smoke run cost $0.19 with all 8 `dev-team:*` skills listed and `evalperm` connected.

Detail: [findings-interface.md](findings-interface.md) (the interface-first checks, F1–F13, R1–R5), [findings-flow.md](findings-flow.md) (the rl-incremental stall, missing milestone rows, the older checks, cost; its F1–F8 are cited here as flow-F1…), [findings-judge.md](findings-judge.md) (blind judge and mode comparison, H1–H4).

## Results

| Run | Checks | Turns | Agent cost | Wall clock | Milestones | Stop | Judge (both orders) |
|---|---|---|---|---|---|---|---|
| rl incremental | 57/68 | 34 | $28.12 | 66 min | 2 (S1 only) | stalled | 7.3 |
| rl all-at-once | 61/68 | 14 | $10.05 | 30 min | 5 | finished | 7.2 |
| quant incremental | 67/81 | 54 | $45.53 | 105 min | 6 | finished | 7.95 |
| quant all-at-once | 67/81 | 20 | $19.12 | 51 min | 2 (S1 only) | finished | 8.15 |

- **Total:** $102.82 for the agents (+17% on iteration 6), $10.60 for the judge.
- **Exclusive `Writes:` works:** zero real write conflicts in any run.
- **M1 width:** widest waves 8, 16, 21 and 19; critical paths 6, 5, 6 and 8; N/CP 3.67, 5.2, 6.33 and 4.25.
- **Judge:** both projects are ties (margins 0.1 and 0.2, under the ~0.3 position bias). rl all-at-once's milestone_quality rose from 2 to 4.
- **Most red checks are grader bugs.** The real plan problems are two design/skill gaps (object-typed boundaries, shared thicken modules), stages left uncut, and all-at-once pipeline-design stopping at S1 again.

## Fix plan for iteration 8, by owner

Each group writes disjoint files, so the groups run in parallel. Fixes land on top of the probe build (`api-probe`, `design/probes.md`).

### 1. Design (`design/interface-first-design.md`)

- §4.1: a row for object-typed boundaries (Protocols, classes, calls into another component): frozen as the Protocol or signature plus a fixture-backed replay double, which is the type's sample, not a mock of a step (interface F1).
- §4.2: planning names cases; the interface task writes samples (interface F8). Generated cross-runtime types are written by the providing interface task; interface tasks never depend on each other (interface F5).
- §6.2: a step's owner may be a folder holding its private helpers (`train/loop/**`) (interface F6).
- §9.1: "integration" (wiring and system tasks run the steps they wire) is an allowed unmitigated reason (interface F3); a routed Revise round trip across two turns passes `gate_discipline` (flow-F6).

### 2. Skills (`skills/**`)

- build-planning: `phase0.md` replay doubles and generated types (F1, F5); `tasks.md` narrows `code` to "changes code", a spine never has a `code` edge to another step, two thickens on one module split the module in the interface layout, a split task's `Read:` names its step's function, a whole-pipeline TC belongs to wiring (F1, F2, F9, Smaller); folds recorded as `**Reason:** fold: <rule>` and allowed only when they don't lengthen the critical path (F4); `extend.md` and `advance.md` cut any designed stage with no rows now, rows only (flow-F1c); `new.md` step 0: a stage below Designed in all-at-once routes to pipeline-design (flow-F3).
- pipeline-design: up front, recommend every stage's workflows and restore the gate line "no package is left `new`" (flow-F3); a separately thickened step gets its own module (F2); replay doubles (F1); the multi-package layout keeps test folders at the repo root (flow-F6/N3); a constraint met by a decision goes on the Covers of the step that applies it (flow-F7b); fix `budget` warnings too (flow-F7d); a gate row "Approved, plus an upstream change: route it to the owner's Revise and stop" (flow-F6).
- architecture-design: `contracts.md` requires a `Boundary:` line for every type crossing step owners, and a Protocol or class type's case is a replay double (F1, F8).
- test-planning: the same upstream-change gate row (flow-F6).
- spec-writing: cost, licence and budget limits are `QR-` items (flow-F7a).

### 3. dt (`scripts/**`)

- `stage_to_cut` computed on its own, whatever earlier milestones wait; an uncut stage is Designed only when every live spec ID it adds is on an Approved pipeline (flow-F1a, F1b).
- build-planning New is `blocked` while a brief-sourced stage is below Designed, naming the packages without `pipelines.md` (flow-F3).
- `model.spine_pipeline` counts `Kind: system` for system pipelines (interface F7).
- A `type-cases` lint: a type crossing step owners with no case (interface F8).
- The derived stage status `Cut` is renamed `Split`, which reviewers read correctly (judge H2).
- Low: resolve task IDs in Acceptance text and graph reasons (interface Smaller).

### 4. Harness (`evals/harness/**`, `evals/README.md`)

- grade.py: structural `unmitigated_reasoned` (F3); owner-to-path `writes_disjoint` with package-local tests and one folder glob (F6); `phase0_split` grouped by owner module, system pipelines and folds accepted (F7); `interface_coverage` against the interface task's Writes and Out → In matching (F8); `tester_starts_early` methods and the task's own step (F9); `fakes_only_cross_pipeline` cross-package calls and replay doubles (F1, F10); `wave_width` by owner module, spines and tester halves only (F11); `no_edge_to_code_when_interface` skips file edges and checks wiring → provider spines (F13); `first_planned_rest_designed` sees stages without rows (flow-F4); `gate_discipline` accepts a routed two-turn Revise and attributes skills by `dt status --skill` calls and reference reads (flow-F6, F7e); `spec_ml_beats_classical` regex (flow-F7c); `types_in_contract` also resolves types inside contract fields (judge H3).
- dtprobe.py: milestone Depends from `ms.depends`, the parenthetical kept as `needs` (F12).
- driver.py: readiness by stages, not row counts; changes counted from the previous turn's commit so the agent's own commits count; concrete asks in the re-ask note; "fully planned" redefined; all-at-once can't finish while a stage is below Designed (flow-F2, F3).
- judge_prompt.py / package.py: neutral copies without `transcript.md` and `doc_evolution.md`; `--both` creates the output folder (judge H1).
- planexport.py: carry the last invoked skill forward (R3).
- Re-grade iterations 6 and 7 with the fixed grader so iteration 8 compares like for like.

### 5. workflow-analyzer (`workflow-analyzer/scripts/planmap.py`)

- Tester halves start after the milestone's interface tasks, not in W0 (R1); the mitigated tile counts data and call edges only, plus unmitigated rows by reason class (R2); the wave tile says which unit it counts (R4); longer box labels or wrapped titles (R5).

## Iteration 8 is done when

- All four trajectories finish (no `stalled`), and every stage has milestone rows in both modes.
- No interface-first check fails for a grader reason; any remaining failure is a real plan defect named in the evidence.
- rl incremental's M1 critical path ≤ 4 and widest wave ≥ 12 (F1); quant all-at-once's critical path ≤ 5 (F2).
- The mode delta is inside its band, or each miss is explained by a mode effect, not a defect.
