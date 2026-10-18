# Iteration 9: the interface-first checks (findings-interface.md)

**Scope.** This covers every failing check in the four iteration-9 runs except the probe, secret and flow checks. Each one is compared with iteration 8 as re-graded by today's grader (`results-iteration-8/regraded/`, "8r" below).
- The runs: rl incremental (36 turns), rl all-at-once (16), quant incremental (58) and quant all-at-once (50, stopped at `max_turns`). n=1 per trajectory.

**Method.**
- I ran `dtprobe.py` on each final project, using each run's own `dt` snapshot (identical to the repo's `skills/` and `scripts/dt.py`).
- I copied the runs and the harness into the scratchpad and re-graded them there, with evidence untruncated and a dump of the grader's internal state. The scores came out exactly as before: 64, 61, 79 and 82.
- I recomputed every tied critical path with `dtrun`, plus the critical path with selected edges dropped.
- Nothing in the repo or the workspace was written.
- Line references like `plan.md:484` point into `../dev-team-workspace/iteration-9/<run>/with_skill/project/`.

**Verdicts:** **real** (a plan defect, naming the rule that should have stopped it) or **grader** (a grader bug, naming the function). Owners: design, a named skill, dt, harness (grade.py, dtrun.py, planexport.py), driver, workflow-analyzer.

## Headline

- **Iteration 8's F1, F2, F3 and F14 are fixed in all four runs.**
  - Every pipeline has its own entry module (for example `lab/pipelines/pl01_train.py`), and the interface task writes `__main__.py`.
  - There are no wiring→wiring edges.
  - Every faked symbol has a `**Boundary:**` line.
  - Library classes are steps, each with a spine or a fold task.
  - No wiring task waits on a thicken that isn't a fold.
  - rl all-at-once stayed one package (AD-11).
- **Targets:**
  - rl incremental critical path ≤ 4: **met** (4).
  - rl incremental widest wave ≥ 12: **met** (19).
  - quant all-at-once critical path ≤ 5: **missed** (6).
- **Three new serializers each cost one step. All three are real and in quant only:**
  - F1: in quant all-at-once, thickens wait on wiring through a shared `conftest.py`.
  - F2: in both quant runs, one system task waits on the other.
  - F3: in quant incremental, the view spines wait on the theme spine for a design-direction approval.
  - Each quant run has two of them. Dropping both gives a critical path of 4.
- **N/CP roughly doubled:** 7.75, 7.5, 7.67 and 8.0, against 3.38, 3.29, 6.33 and 5.0 in iteration 8.
- **Most failures are grader reasons.** The grader hasn't caught up with this iteration's skill changes, which put later-stage library classes in M1's pipelines and add in-package cross-pipeline fakes. It also doesn't credit skills opened by a slash command.
- **Scores after the grader fixes (estimates):** rl incremental 67/67, rl all-at-once 66/67, quant incremental 83/92, quant all-at-once 87/92. Actual: 64, 61, 79, 82. Iteration 8 regraded: 60, 61, 78/91, 85.
- **Driver validity issue (F11).**
  - rl incremental ran all 36 turns in one agent session.
  - In the other runs, one session ran 6–7 skills.
  - `session_step` keeps a session whenever the agent moves on to the next skill by itself, so iteration 9 is only partly "a fresh session per skill".

## Targets and graph shape (M1)

| Run | N (8 / 7) | Critical path (8 / 7) | Widest wave, whole tasks (8 / 7) | N/CP (8 / 7) | Critical path with the real serializers dropped |
|---|---|---|---|---|---|
| rl inc | 31 (27 / 22) | **4** (8 / 6) | **19** (18 / 8) | 7.75 (3.38 / 3.67) | at its floor (interface → spine → wiring → system) |
| rl aao | 30 (23 / 26) | **4** (7 / 5) | 17 (12 / 16) | 7.5 (3.29 / 5.2) | at its floor |
| quant inc | 46 (38 / 38) | 6 (6 / 6) | 27 (26 / 21) | 7.67 (6.33 / 6.33) | 5 without F3 or without F2; 4 without both |
| quant aao | 48 (25 / 34) | **6** (5 / 8) | 27 (17 / 19) | 8.0 (5.0 / 4.25) | 5 without F1 or without F2; 4 without both |

## Critical paths and the kinds along them (question 2)

**No wiring→wiring edge exists in any run** (0 Depends-on pairs). Grader commit 9236a3d's new rule therefore never fires.

| Run | Ties | Path (kinds), with the edge reasons |
|---|---|---|
| rl inc | 40 whole-task paths | T01 interface → T02–T06 spine or T13/T14/T15/T18 fold → T21/T22 wiring (`order`, integration) → T31 system (`file`: settings/**) |
| rl aao | 35 | T01 → spine or fold (T02–T09, T18) → T19/T20/T21 wiring → T30 system |
| quant inc | 1 | T03 interface → T25 createTheme spine → **T35 RunsView spine** ("learning: QR-07 sets the direction", `plan.md:458`) → T43 wire PL-14 → T45 system (file) → **T46 system** ("learning: needs the version PL-01 commits", `plan.md:501`) |
| quant aao | 65 | T01 → T02–T08 spine → T29 wire PL-09 → **T37–T44 thicken** ("TC-23's store is built by the real download (conftest.py)", `plan.md:484-488`) → T47 system → **T48 system** ("TC-24 serves a store PL-01 promoted", `plan.md:522`) |

## Results: failing checks in iteration 9

| Check | rl inc | rl aao | quant inc | quant aao |
|---|---|---|---|---|
| `wave_width` | **grader** F4 | pass | **grader** F4 | pass |
| `writes_disjoint` | pass | real F9 | real F9 | real F9 (+ grader nit) |
| `edges_mitigated` | pass | pass | **grader** F6 | **grader** F6 |
| `unmitigated_reasoned` | pass | pass | pass | **grader** F6 |
| `no_edge_to_code_when_interface` | pass | pass | real F3 (+ nit F14) | pass |
| `phase0_split` | **grader** F4 | **grader** F4 (+ nit F14) | **grader** F4 | **grader** F4 |
| `fakes_only_cross_pipeline` | **grader** F5 | **grader** F5 | pass | pass |
| `types_in_contract` | pass | **grader** F8 | grader F8 + real (StagedRun) | **grader** F8 |
| `gate_discipline` | pass | **grader** F10 (+ driver) | pass | pass |
| `skills_invoked` | pass | **grader** F7 | **grader** F7 | **grader** F7 |
| `sim_ready_2` | pass | pass | real F3 | pass |
| `data_sources_suggested` | — | — | real, weak (F13) | pass |
| `finished`, `plan_docs_approved` | pass | pass | pass | budget F12 |

Passing in all four: graph_metrics, plan_parallelism, edge_table_consistent, step_tasks_small, tester_starts_early, interface_coverage, milestone_size, milestone_depends, doc_budgets, roadmap_rows, rl_single_package and dt_lint_clean.

## Check by check against iteration 8 regraded (question 6)

| Run | Newly pass | Newly fail | Still fail |
|---|---|---|---|
| rl inc | plan_docs_approved, writes_disjoint, edges_mitigated, tester_starts_early, gate_discipline | wave_width (F4), fakes_only (F5) | phase0_split (now F4, deferred steps) |
| rl aao | edges_mitigated, unmitigated_reasoned, rl_single_package | phase0_split (F4), fakes_only (F5), skills_invoked (F7) | writes_disjoint (F9), types_in_contract (F8), gate_discipline (F10) |
| quant inc | brief_size, brief_goal_count, brief_goals_stage_neutral, doc_budgets, milestone_depends, gate_discipline | wave_width (F4), edges_mitigated (F6), phase0_split (F4), skills_invoked (F7), sim_ready_2 (F3); docs_before_probe and probe_code_in_probe_turns are probe checks (not covered here) | writes_disjoint, no_edge_to_code, types_in_contract, data_sources_suggested |
| quant aao | fakes_only, gate_discipline, data_sources_suggested | finished, plan_docs_approved (F12), writes_disjoint (F9), edges_mitigated (F6), phase0_split (F4), skills_invoked (F7) | unmitigated_reasoned (F6), types_in_contract (F8) |

## Findings, ordered by impact on parallelism

### F1. quant aao: thicken golden cases wait on wire PL-09 for its `conftest.py`. **real** (build-planning + design), +1 on the critical path

**Evidence.**
- T29 (wire PL-09) writes `tests/intent/data/conftest.py`, "the shared conftest.py that builds each golden case's store" (`plan.md:249,253`).
- All eight thickens T37–T44 depend on T29, 11 rows in all: "TC-23's store is built by the real download (conftest.py)" (`plan.md:484-488`). T39 and T42 also wait on T31, and T41 on T32.
- **It's a regression.** Iteration 8 had no thicken→wiring edge in any run.
- **No check fails for it:**
  - `dtrun.unmitigated_class` passes any `order` row with a reason (`dtrun.py:334`).
  - The plan map bins these rows as "side-effect order", one of its "can never be mitigated" classes.

**Rule broken.** `build-planning/references/tasks.md:11`: "no thicken waits on wiring". Neither design §4.1's shared-module row nor `tasks.md:33` names shared test helpers.

**Fix:**
- **Design §4.1 and `tasks.md:33`:** a shared test helper (`conftest.py`, a golden-case store builder) is a shared module written by the interface task. Each golden case builds its store from its own `input.json`, so no thicken depends on wiring.
- **Grader:** `unmitigated_class` fails thicken→wiring and thicken→system whatever the row's kind, as it already does for wiring → non-fold thicken.

### F2. Two system tasks chained. **real** (design + build-planning), +1 on the critical path in both quant runs

**Evidence:**
- **quant aao:** T48 (PL-02 system) → T47 (PL-01 system), "TC-24 serves a store PL-01 promoted" (`plan.md:522`).
- **quant inc:** T46 → T45, "learning: needs the version PL-01 commits through the app" (`plan.md:501`).

**Cause.** Design §5.1 ("Phase 3 system (solo)") and `phase0.md:30` ("one per new system pipeline") never say whether system tasks may depend on each other.

**Fix.** `phase0.md:30` and design §5.1: system tasks don't depend on each other. Each builds its golden-case store from fixtures, or the cases that need another system pipeline's real output join that pipeline's system task.

### F3. quant inc: six view spines wait on the createTheme spine. **real** (build-planning + design), +1 on the critical path, 6 spines out of wave 1

**Evidence.**
- T28–T32 and T35 each depend on T25 (createTheme spine), "learning: QR-07 sets the direction before any view is built" (`plan.md:453-458`).
- QR-07 passes "when the user approves the direction before the views are built" (`spec.md:702`).
- Checks that fail on it:
  - `no_edge_to_code` flags T28→T25 and T29→T25: across a declared boundary, because design.Theme has a sample.
  - `sim_ready_2` reports T28–T32 and T35 as not ready after the interface.

**Rule broken.** Design §6.1: "A spine never has a `code` edge to another step's task; it runs on that boundary's sample". A human approval written as `order` slips past it.

**Fix.** Design §5.1 and `phase0.md`: a human approval that a requirement places before several steps runs in phase 0, in the interface task's acceptance ("direction approved; design.Theme sample written") or during planning. The views run on the Theme sample.

### F4. phase0_split and wave_width count deferred and probe-blocked steps, folds into wiring, and an owner shared by two packages. **grader**

**Cause.** Now that library classes are steps (commit 0caf5fb), each pipeline lists every stage's classes, while M1 plans only its own.

**Evidence and causes:**
- **Deferred steps:**
  - rl inc misses FishTank, PredatorPrey, ReinforceAgent, PPOAgent, ScriptedPredator, ScriptedPrey, RandomSwimmer, OpponentPool and ScriptedFish. All of them cover FISH, HUNT, PG, SELF or BASE-04–08 IDs that the plan defers (`plan.md:7`).
  - rl aao misses FishTank, PredatorPrey, PPO, FishRule, PreyRule and PredatorRule.
  - quant inc misses mount_studies, deferred to M5 (`plan.md:7`).
  - quant aao misses FredSource ("DATA-06, PANEL-06 (to M2: `FredSource`)").
- **Interface lacks** OpponentPool (rl inc) and BookStatus and StudyReader (quant inc): all types of deferred steps.
- **Probe-blocked steps with a spined stand-in** (design §6.2):
  - quant inc SharadarSource (PB-01; SyntheticPrimarySource is spined as T05).
  - quant aao SharadarSource and EdgarSicSource ("waits on PB-01/PB-02"; SyntheticSource is spined as T04).
- **A fold into wiring recorded in the Reason line:** rl inc T23, "`print_scores` is trivial, so this task builds it (fold)" (`plan.md:218`). `phase0_misses` searches only the wiring task's title and acceptance.
- **The same owner in two packages:** quant inc `api.schema` is both qserver's (PL-11, T24) and explorer's (PL-15, T36). `step_units` keys units by owner alone, so each step "has 2 spine tasks".
- **wave_width:**
  - The same deferred steps inflate the units: rl inc 28 → 18 (19 ready ≥ 14.4).
  - In quant inc, `mount_static` and `serve` are folded into wiring (T40 writes `api/static.py` and `api/serve.py`) but still counted as units: 35 → 32 (27 ready ≥ 25.6).
  - Both runs pass with the fix.

**Fix:**
- `dtrun.phase0_misses`, `wave_units`, `covering_tasks` and `step_units` (`dtrun.py:423-516`): drop a step from the milestone when one of these holds:
  - (a) its Covers meet the plan's Deferred and no task names it;
  - (b) its spine cell says "waits on PB-NN" and a stand-in step with the same Out type is spined;
  - (c) the interface doesn't declare it and no task names it. List these as "outside the milestone" in the evidence.
- Search wiring Reasons for folds.
- Key units by package and owner.
- "Interface lacks" counts only the types of in-scope steps.
- Residue: rl aao's PPO covers only CHECK-01 and appears nowhere in the plan. See F14.

### F5. fakes_only rejects in-package fakes between pipelines. **grader**

**Evidence:**
- **rl inc:** `evaluate.evaluate` fake on rows T06/T07/T09/T12 → T18 (`plan.md:323-327`). It has a Boundary line ("train, reference, lab") and "Used by … PL-01, PL-02, PL-03, PL-04, PL-05" (`contract.md:331-332`). Its owner step is PL-03's.
- **rl aao:** `train.run_train`, PL-02's entry, has "Boundary: PL-03" (`contract.md:219`). PL-03's run_parallel calls it ("PL-02 as built").
- **The current check is inconsistent.** quant aao's `data.returns_panel` fake (PL-10 → PL-11, both in `data`) passes only because other packages also use it.

**Cause.** `fake_ok` (`grade.py:506`) accepts a call step named after the symbol, or a "Used by" from another package. Design §4.1 now gives a fake to any entry or function "whose Used by names another pipeline or package".

**Fix.** In `fake_ok`, accept a symbol that has a Boundary line and whose "Used by" names a pipeline other than the one owning it, when the consumer's pipeline is one of them.

### F6. A system task's row to the provider's wiring is graded as an unmitigated call. **grader** (plus skill wording)

**Evidence:**
- **quant inc:** T45→T37 and T46→T38, `call`, "none: the real download replaces the fake" (`plan.md:497,500`). edges_mitigated reads 5/7.
- **quant aao:** T47→T31, T47→T32 and T48→T32, `call`, "system task swaps in the real provider" (`plan.md:506-507,516`). edges_mitigated reads 4/7, and unmitigated_reasoned reads "[no allowed structure]".

**Cause:**
- That un-faking is what a system task does (design §5.1). No fake can mitigate it.
- `edges_mitigated` (`grade.py:399`) counts the row as data or call.
- `dtrun.wired_pipelines` (`dtrun.py:279`) adds only the PL IDs a system task names. T47 reads `data.returns_panel`, PL-11's entry, not "PL-11", so `runs_in` fails.

**Fix:**
- **Grader:** skip rows from a system task to the wiring of a pipeline it swaps in. In `wired_pipelines`, add the pipelines whose entry function a system task reads.
- **Skill:** `phase0.md:30` names the row: `order · none: integration: swaps in the real <provider>`, per design §6.1.

### F7. skills_invoked ignores skills opened by a slash command. **grader**

**Evidence.** The driver opens each fresh session with `/dev-team:<skill>` (`driver.py:628`), and no Skill tool call follows. The "missing" skills:
- rl aao: idea-refine (session 1, turns 1–3) and architecture-design (session 3, turn 7).
- quant inc: spec-writing (sessions 2 and 5).
- quant aao: idea-refine and spec-writing.

**Cause.** `grade.py:860` reads only `t["skills"]`. `dtrun.turn_skill_map` already counts `session.new` (`dtrun.py:683-689`), and grade.py computes it as `turn_skills` at line 837.

**Fix.** `skills_used = sorted(set().union(*turn_skills.values()))`. `extra.skill_sequence` needs the same change.

### F8. types_in_contract: field types defined in forms the grader doesn't read. **grader**, plus one **real**

**Grader:**
- **rl aao:** `Direction` and `Settings` are aliases in the contract's preamble (`contract.md:5`). `contract_text` (`grade.py:624`) joins symbol sections only. Fix: include each contract.md's whole text.
- **quant inc, mirror forms:**
  - "`CompanyMsg` mirrors `qdata.query.Company`", a three-part path (`qserver/contract.md:78`).
  - "mirrors one `qdata.query.Actions` row".
  - "`DayDiffMsg` mirroring `DayDiff`".
  - "`CheckCountsMsg` mirrors `CheckCounts`".
  - `defined_in` (`dtrun.py:640`) accepts only `pkg.Type`. Fix: accept dotted paths of any depth, "mirrors one … row", "mirroring", and a bare name with its own section.
- **quant inc, qualified library types:** `JSX.Element` and `duckdb.DuckDBPyConnection`. Fix: `field_types` (`dtrun.py:600`) skips `module.Type` when the module isn't a contract package.
- **quant aao, backticked notes:** "- `BarSchema`: index …" and "`VendorRowSchema`: …" (`data/contract.md:82,206`). The note regex has no room for the backtick. Also, `NaN` is read as a type. Fix: allow `` `Name`: `` and add NaN to `LIBRARY_TYPES` (`dtrun.py:181`).

**Real (quant inc).** `StagedRun` is returned by `VersionedStore.begin` and passed back to `commit`, but is defined only in a code comment (`qdata/contract.md:83`). Design §4.1 says an object with behavior passed between calls needs a Protocol and a replay double. Owner: architecture-design (`contracts.md`).

### F9. Spine Writes go beyond the owner module. **real** (minor, no width cost; pipeline-design), one grader nit

**Evidence:**
- **rl aao:**
  - T08 writes `methods/factory.py`, "also builds the methods factory (`make_learner`, `load_policy`)" (`plan.md:87,93`).
  - T09 writes `runlog/writer.py`, "also builds `runlog.RunWriter`" (`plan.md:98,104`).
  - Both are contract functions or classes that no step owns. It is iteration 8's F11 again: the library-classes-as-steps rule reached the classes, not the factory function or the writer.
- **quant inc:**
  - T25 writes `design/tokens.css` beside `theme.ts`.
  - T36 writes `api/schema-tools.ts`. Its owner `api.schema` collides with the generated `api/schema.ts` that T02 writes.
- **quant aao:**
  - T02 writes `runs/events.py`.
  - T06 writes `store/parts.py` (`store.append_parts`, no step).
  - T22 writes `routes/errors.py`, a shared error mapping.
  - T26 writes `no-dataset.tsx`.
- **Grader nit:** T02's Step cell "PL-09.open_run, PL-09.close_run" resolves to owner "?" in `writes_disjoint`.

**Fix:**
- **pipeline-design:** a contract function or class a step calls (factory, writer, `append_parts`) is its own step, or sits in that step's folder owner (`train/loop/**`). An owner name doesn't collide with a generated file. A shared helper across routes goes to the interface task.
- **dt:** lint a contract function or class with no owning step that a spine's Reason claims.
- **Grader:** split a multi-step Step cell before looking up the owner.

### F10. rl aao gate_discipline, turn 13 (arch + plan). **grader**, with a driver cause

**Evidence.** The user's message: approve the tests, "then make the two routed fixes (the TRAIN-03 count in the spec and AD-09's corridor in the architecture) and continue to the next planning step". Turn 13 then committed, in order:
- the spec fix (`eefd88a`);
- the architecture and contract fix (`9881dd9`, 14 lines);
- AD-11 (`88f4a11`, recording the user's turn-8 "Stay single package");
- the M1 plan.

Every architecture change was a fix the user had approved. Only the plan was a new draft.

**Cause.** `dtrun.routed_revise` (`dtrun.py:718`) allows only arch + pipelines or tests.

**Fix:**
- **Grader:** also allow arch (≤ ~25 lines) plus one drafted layer when the previous turn named the routed fixes and this turn's user message tells the agent to make them.
- **Driver:** see F11. The session stayed test-planning, so one turn ran four skills.

### F11. The driver keeps one session across skills. **driver** (validity)

**Evidence.**
- rl inc ran 1 session for all 36 turns, through 7 skills (`summary.json` sessions).
- rl aao session 3 ran 10 turns through 7 skills. quant inc session 5 ran 33 turns through 7 skills. quant aao had 13 sessions.

**Cause.** In `driver.session_step` (`driver.py:259-271`), "a skill the session already ran (its own, or one the agent moved on to) keeps the session". When the agent moves on in the turn that approves a gate (the simulated user says "continue"), `seen` grows, and `just_approved` never fires because `before.skill ≠ skill`.

**Effect.** The single-context confound from iterations 1–8 remains in rl inc and partly elsewhere.

**Fix:**
- Open a fresh session whenever `dt next`'s skill differs from the session's opening skill, or after any approved gate.
- Or have the simulated user approve without "continue".

### F12. quant aao hit `max_turns` (50) before build-setup finished. **budget** (driver or scenario), not a plan defect

- `CONSTRAINTS.md` is missing, which fails `finished` and `plan_docs_approved`.
- The 13 sessions include 4 extra architecture-design rounds and 4 api-probe sessions (turns 12–15, 29–33, 44–46).
- Fix: raise `max_turns` for quant all-at-once, or count only planning turns. The probe-loop share belongs to the probe findings.

### F13. quant inc data_sources_suggested. **real, weak** (idea-refine), or a question about the check's premise

- The approved docs name Tiingo and Stooq but no fundamentals source.
- The brief put "Fundamentals … not needed until a signal asks for them" in Not doing (`brief.md:37`).
- At turn 35 the agent raised it only as a scope line ("unless you reverse that"), so the scenario's "would like its suggestion" was never reached.
- Decide whether scoping fundamentals out with a reason should pass. If it should, the harness reads it as n/a or pass. If it shouldn't, idea-refine should name candidate sources when it defers a data category.

### F14. Small residue. **real** nits, no cost

- **quant inc T41 (wire PL-11) → T20 (create_app spine)**, although `api.create_app` has a fake (`plan.md:480`). The smoke needs the real app's schema. It costs nothing (T20 is in wave 1). It fails `no_edge_to_code` alongside F3.
- **rl aao's PPO step** (covers only CHECK-01) appears nowhere in the plan, and its Deferred lists requirement IDs only. build-planning: name deferred steps when a step's only covered ID stays in the milestone.

## Grader-reason failures

| Check | Runs | Function | Fix |
|---|---|---|---|
| phase0_split | all four | `dtrun.phase0_misses`, `covering_tasks`, `step_units` (`dtrun.py:423-516`) | Drop deferred, probe-blocked and unnamed out-of-scope steps; search wiring Reasons for folds; key units by package and owner; "interface lacks" only for in-scope steps (F4) |
| wave_width | rl inc, quant inc | `dtrun.wave_units` (`dtrun.py:454`) | Same scope rule; skip steps folded into wiring (F4) |
| fakes_only_cross_pipeline | rl inc, rl aao | `fake_ok` (`grade.py:506`) | Accept a symbol with a Boundary line whose Used by names another pipeline (F5) |
| edges_mitigated | quant inc, quant aao | `grade.py:399` (`dep_rows`) | Skip system → swapped-in provider wiring rows (F6) |
| unmitigated_reasoned | quant aao | `dtrun.wired_pipelines` (`dtrun.py:279`) | Add pipelines whose entry symbol a system task reads (F6) |
| skills_invoked | rl aao, quant inc, quant aao | `grade.py:860` | Use `turn_skills`, which includes `session.new` (F7) |
| types_in_contract | rl aao, quant inc (part), quant aao | `grade.py:624` (`contract_text`), `dtrun.defined_in` (`:640`), `field_types` (`:600`), `LIBRARY_TYPES` (`:181`) | Whole-file text; mirror forms; qualified library types; backticked notes; NaN (F8) |
| gate_discipline | rl aao | `dtrun.routed_revise` (`dtrun.py:718`) | Allow approved routed fixes plus one drafted layer (F10) |
| writes_disjoint (nit) | quant aao T02 | `grade.py` spine owner lookup | Split a multi-step Step cell |
| (leniency, nothing fails) | quant aao | `dtrun.unmitigated_class` (`dtrun.py:334`) | Fail thicken → wiring or system rows (F1) |

## Mode deltas (question 7: computed with `modecmp.compare`, no judge, nothing written)

| Project | N/CP inc vs aao (within 20%) | Max width (within 1) | Pass interface_coverage, types_in_contract, writes_disjoint in both modes | frozen_interface_churn (expect aao ≤ inc) |
|---|---|---|---|---|
| rl | 7.75 vs 7.5, Δ3%: **ok** | 19 vs 17: **out** (Δ2) | **no**: aao fails types (grader F8) and writes (real F9) | 26 vs 0: as expected |
| quant | 7.67 vs 8.0, Δ4%: **ok** | 27 vs 27: **ok** | **no**: both fail types (aao grader only; inc has StagedRun) and writes (real F9) | 11 vs 0: as expected |

After the grader fixes, rl still fails the must-pass set on writes_disjoint (aao), and quant on writes_disjoint in both modes and types in incremental.

rl inc's churn of 26 comes from AD-09 (batch-first core) and AD-13 (teams), adopted before the build in S2 and S3 (`plan.md:392-393`). quant inc's 11 come from turns 28 and 39.

## Pipelines and packages (questions 3 and 4)

**Entry modules:**
- Every pipeline has a distinct entry. Either `<component>/pipelines/plNN_*.py`, or `<component>/pipeline.py` when the component holds only one pipeline (quant inc `load/`, `query/`, `runs/`). No entry file is shared in any run.
- `__main__.py` sits under the interface task's Writes:
  - rl inc T01 `src/rllab/lab/**`: "`__main__.py` dispatches train, eval, report and replay" (`plan.md:20`).
  - rl aao T01 `cli/__main__.py` (`plan.md:16`).
  - quant inc T02 "`__main__.py` dispatches `export-openapi`" (`plan.md:29`).
- Each wiring task writes only its own entry and smoke test.

**Library classes:**
- They are steps with a spine or a fold task:
  - rl inc: Snake, Corridor, TabularAgent, the players and ReferencePlayer are folds T13–T17 and T08; DQNAgent is spine T05.
  - rl aao: CheckDiscrete, Snake, DQN, RandomPolicy, SnakeRule.
  - quant aao: SyntheticSource (T04) behind the make_sources spine (T03).
- Residue (F9): rl aao's factory and writer.

**Fakes across pipelines:**
- Every faked symbol has a Boundary line: `evaluate.evaluate`, `runs.open_run`, `train.run_train`, `load.download`, `api.create_app`, `data.returns_panel`, `data.membership_as_of` and `server.get_membership`.
- The wirings run on them. For example, rl aao T21: "runs end to end on the `train.run_train` fake" (`plan.md:218`).

**rl all-at-once is one package** (`architecture.md:3,158`, AD-11). Iteration 8 had 4 packages.

## Iteration-8 findings in iteration 9

| Finding | Status |
|---|---|
| F1 shared entry module | **Fixed**: distinct entries, no wiring→wiring edges, `__main__.py` written by the interface task |
| F2 unfaked calls between pipelines | **Fixed**: Boundary lines and fakes in all runs; the grader lags (F5) |
| F3 library classes / wiring on thickens | **Fixed**: wiring → non-fold thicken is 0 everywhere; factory and writer residue (F9) |
| F4–F8 grader | **Fixed**; the new grader gaps are F4, F5, F6 and F8 |
| F10 nested field types | **Partly**: mostly grader forms (F8); one real (StagedRun) |
| F11 spine Writes beyond owner | **Open** (F9) |
| F12 interface misses a type | **Fixed in substance**: the remaining "lacks" are deferred steps (F4) |
| F13 Depends cycle | **Fixed** (milestone_depends passes) |
| F14 rl aao multi-package | **Fixed** |
| No thicken waits on wiring | **Regressed** in quant aao (F1) |

## Plan map (`flow/plan/M1.html`)

- **R6 landed, but hides the new serializers.** rl inc reads "integration 42 · same module 5 · shared file 3", which matches the rows. But the "side-effect order" class sits in the "can never be mitigated" group:
  - quant aao "side-effect order 11": F1's thicken→wiring rows.
  - quant inc "side-effect order 6": F3's theme rows.
  - Fix: show thicken→wiring, spine→spine and system→system `order` rows as "worth a look".
- **R7 landed.** The widest-wave tile reads "24 boxes (19 whole tasks)".
- **R8 landed, but the lanes count boxes and the tile counts tasks (new R9).**
  - rl inc's tile reads "critical path (tasks) 4 · 6 lanes tie", while the drawn lanes are the 5-box paths through split folds (T01 → T13 → T21 → T31, and so on).
  - The producer's path T01 → T02 → T21 → T31, one of 40 tied whole-task paths, is not drawn bold.
  - Fix: draw the whole-task critical paths in `_critical_path` and `_cp_lanes` (`planmap.py:440-520`), or label the lanes as boxes.
- **Shared-entry marker.** It is in the legend. No pair qualifies, so none is drawn: correct.
- **Stale skill label (new R10, harness).** The headers read "as of T35 · idea-refine" (rl inc) and "as of T57 · reference-intake" (quant inc). Both turns were test-planning or build-planning. `planexport.turn_skills` (`planexport.py:154`) carries the last Skill call forward, and in long sessions that is many turns old. Fix: attribute with `dtrun.turn_skill_map`, or with the turn's `dt next` skill.

## Fix list for iteration 10

**Design** (`design/interface-first-design.md`)
1. §4.1 and §5.1: shared test helpers (`conftest.py`) are interface-task modules (F1).
2. §5.1: system tasks never chain (F2).
3. §5.1: a human approval required before several steps runs in phase 0 or during planning (F3).

**build-planning**
1. `tasks.md:33`: the shared test helper rule (F1).
2. `phase0.md:30`: no system→system edge; the provider row is `order · integration` (F2, F6).
3. Approval gates go in the interface task (F3).
4. Deferred names deferred steps (F14).

**pipeline-design.** Factory functions and writers are steps or folder owners; owner names don't collide with generated files (F9).

**architecture-design.** A returned object passed back between calls gets a section (StagedRun, F8).

**dt.** Lint contract functions or classes that no step owns but a spine's Reason claims (F9).

**Harness**
1. The grader table above.
2. `driver.session_step`: a fresh session per skill (F11).
3. `max_turns` for quant aao (F12).
4. `planexport.turn_skills` (R10).

**workflow-analyzer.** R6 classes, R9 lanes.

Files: `/Users/connorott/plugins/plugins-worktrees/dev-team/evals/results-iteration-9/grading-*.json`, `/Users/connorott/plugins/dev-team-workspace/iteration-9/<traj>/with_skill/{project/tasks/plan.md,project/docs/packages/*/{pipelines,contract}.md,turns.json,summary.json,flow/plan/M1.html}`, `/Users/connorott/plugins/plugins-worktrees/dev-team/evals/harness/{grade.py,dtrun.py,driver.py,planexport.py,modecmp.py}`, `/Users/connorott/plugins/plugins-worktrees/workflow-analyzer/scripts/planmap.py`, `/Users/connorott/plugins/plugins-worktrees/dev-team/skills/build-planning/references/{phase0.md,tasks.md}`. The scratch re-grade and dumps are in `/private/tmp/claude-501/-Users-connorott-plugins-plugins-worktrees/445b9ae6-e69e-44ac-b502-4727457a4120/scratchpad/ifa/`.
