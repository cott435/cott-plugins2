# Iteration 8: the interface-first checks (findings-interface.md)

**Scope.** The interface-first checks that fail in at least one of the four iteration-8 runs. I read each run's final `tasks/plan.md`, `pipelines.md` and `contract.md`, the grader code behind each check (`evals/harness/grade.py`, `dtrun.py`, `probefacts.py`), and the plan maps. The runs are rl incremental (41 turns), rl all-at-once (20), quant incremental (68) and quant all-at-once (41). All four finished. n=1 per trajectory.

**Method.** I ran `dtprobe.py` read-only on each run (output in the scratchpad) and recomputed the checks' complete lists with `dtrun`'s own functions, because the evidence in `grading.json` is cut to 4–6 items. I also recomputed each critical path with selected edges dropped. Nothing in the repo or the runs was written. Line references like `plan.md:308` point into `../dev-team-workspace/iteration-8/<run>/with_skill/project/`.

**Verdicts:** **real** (a plan defect, with the rule that should have stopped it) or **grader** (a grader bug, with function and line). Owners are design, skill, dt, harness and workflow-analyzer.

## Headline

- **The fixes from iteration 7 worked.**
  - Replay doubles are in every run: rl inc `contract.md:61,75,81`; rl aao `worlds/contract.md:39,55` and `learn/contract.md:45`; quant inc `qdata/contract.md:140`; quant aao `data/contract.md:87` and `ingest/contract.md:49`.
  - Steps that are thickened separately now get their own modules (quant aao's `validate/*.py`).
  - rl inc wave 1 went from 8 to 18 tasks, and quant aao's critical path from 8 to 5.
- **A new serializer sets the critical path in all four runs (F1).** Every wiring task of a component or package writes the same entry module (`pipeline.py`, plus `__main__.py`), so those tasks chain.
  - Dropping only the wiring→wiring edges gives critical paths of **4 / 4 / 5 / 4**, against the actual **8 / 7 / 6 / 5**.
- **Targets:**
  - rl inc widest wave ≥ 12: **met** (18).
  - rl inc critical path ≤ 4: **missed** (8).
  - quant aao critical path ≤ 5: **met** (5; it has 25 tasks and its widest wave is 17, not 25).
- **The bar is not met.** In 10 check-runs, a check fails for a grader reason only. rl inc tester_starts_early; rl aao wave_width and phase0_split; quant inc edges_mitigated, unmitigated_reasoned, no_edge_to_code_when_interface and phase0_split; quant aao phase0_split, fakes_only_cross_pipeline and runner_split.
- **Scores after those fixes (estimates):** rl inc 62/67, rl aao 61/67, quant inc 73/89, quant aao 83/90. Actual: 61, 59, 69, 80. Iteration-7 baseline: 58, 64, 71, 67.

## Results: failing checks in iteration 8

| Check | rl inc | rl aao | quant inc | quant aao |
|---|---|---|---|---|
| `wave_width` | pass (16 ≥ 7.2) | **grader** F4 | pass | pass |
| `writes_disjoint` | real F11 | real F11 | real F11 (+1 grader) | pass |
| `edges_mitigated` | real F3 (T12→T11) | real F2 (T18→T17) | **grader** F6 | pass |
| `unmitigated_reasoned` | pass | real F2 | **grader** F6 | pass |
| `no_edge_to_code_when_interface` | pass | pass | **grader** F7 | pass |
| `phase0_split` | grader F4 + real F12 | **grader** F4 | **grader** F4 | **grader** F4 |
| `tester_starts_early` | **grader** F5 | pass | pass | pass |
| `fakes_only_cross_pipeline` | pass | pass | pass | **grader** F8 |
| `types_in_contract` | pass | real F10 (+1 grader) | real F10 (minor) + grader | real F10 |
| `milestone_depends` | pass | pass | real F13 | pass |
| `doc_budgets` | pass | pass | real (brief 514 words) | pass |
| `rl_single_package` | pass | real F14 | — | — |
| `runner_split` | n/a | n/a | pass | **grader** F9 |

Passing in all four: graph_metrics, plan_parallelism, edge_table_consistent, step_tasks_small, interface_coverage (17, 33, 290 and 142 boundaries, none missing), milestone_size, roadmap_rows, first_planned_rest_designed, sim_ready_1–3 and dt_lint_clean. The type-cases lint is in the snapshot (`lint.py:34`).

### Per-M1 critical path, with the edges that lengthen it

| Run | Tasks | Critical path (iteration 7) | Widest wave (iteration 7) | Critical path traced | Without wiring→wiring edges |
|---|---|---|---|---|---|
| rl inc | 27 | **8** (6) | 18 (8) | T01 → T11 Snake views → T12 Snake rules (`plan.md:308`, F3) → T22 wire PL-01 (waits on 5 library thickens, `plan.md:244`, F3) → T23 → T24 → T25 → T26 (all write `lab/pipeline.py` and `__main__.py`, `plan.md:326,328,336,339`, F1) | 4 (3 if T12→T11 also goes) |
| rl aao | 23 | **7** (5) | 12 (16) | T02 → T08 → T17 wire PL-11 → T18 wire PL-15 (`learn.train` has no fake, `plan.md:286`, F2) → T19 → T20 (lab `pipeline.py`, `plan.md:288,291`, F1) → T23 | 4 |
| quant inc | 38 | **6** (6) | 26 (21) | T01 → T05 → T31 wire PL-16 → T32 wire PL-09 → T33 wire PL-07 (qdata `pipeline.py` and `__main__.py`, `plan.md:362,374`, F1) → T38 | 5 (T38 → T37 system→system, "needs the snapshot T37 stores", `plan.md:396`, is a real side-effect order) |
| quant aao | 25 | **5** (8) | 17 (19) | Two tied lanes: T01 → T03 → T21 → T22 (`loader/pipeline.py`) → T25, and T02 → T11 → T23 → T24 (ingest `pipeline.py`) → T25 (F1) | 4 |

**Why the fixes didn't shorten rl inc.**
- **They removed what set the path in iteration 7.** All 9 spines are in wave 1 on the doubles: `sim_ready_2` passes and `no_edge_to_code` went from 10 to 0. The thicken modules are all distinct; the only same-module chains left are spine→thicken (T20→T05, T21→T09), off the critical path.
- **The path moved to the wiring lane.** All six pipeline entries sit in `src/rllab/lab/pipeline.py` (`pipelines.md:6,25,41,67,87,105`), behind one `__main__.py` (`pipelines.md:130`). In iteration 7 the entries were spread across `train/`, `viewer/` and `cli/pipeline.py`. Five wiring tasks now chain, which adds 4.
- **Library classes add 2 more (F3).**

## Findings, ordered by impact on parallelism

### F1. Wiring tasks serialize on a shared entry module. **design + skill** (real)

**Evidence.**
- **The chains:**
  - rl inc: T22→T23→T24→T25→T26, "both write `lab/pipeline.py` and `__main__.py`" (`plan.md:326-339`).
  - rl aao: T16→T15 and T18→T19→T20 (`plan.md:278,288,291`).
  - quant inc: T31→T32→T33 (`plan.md:362,374`).
  - quant aao: T22→T21 (`data/pipelines.md:6,26` share `loader/pipeline.py`) and T24→T23 (ingest `pipeline.py`).
- **The cost:** +4, +3 (one of them F2's call edge), +1 and +1 on the critical path.
- **No check fails for it.** `no_edge_to_code` lists these pairs as "serial on a shared file (not counted)".
- **quant aao half-solved it unprompted.** Its T02 interface already writes `__main__.py` ("dispatches build, update, validate and explain", `plan.md:31`), but PL-08 and PL-11 still share `pipeline.py`.

**Cause.**
- `pipeline-design/references/steps.md:28` says "One `pipeline.py` entry module per component … or package", and `template.md:11,31` say the same.
- `build-planning/references/phase0.md:28` gives each wiring task "the entry function, its `__main__.py` trigger".
- `tasks.md:33` gives shared files to "the interface, wiring or system task" without saying which one.
- Design §4.1 (`interface-first-design.md:77`) lists only `types.py` and `__init__.py` as shared modules. §5.1's "wiring ∥" (line 113) assumes disjoint entries.

**Fix:**
- One entry module per pipeline (for example `lab/pipelines/pl01_train.py`, with `pipeline.py` only re-exporting).
- The interface task writes `__main__.py` whole, routing every milestone trigger to its entry stub.
- A wiring task writes only its own entry module and smoke test.

### F2. Calls between pipelines at wiring level are left unfaked. **skill + dt** (real)

**Evidence.**
- **rl aao:** T18 (wire PL-15) → T17 (wire PL-11), call, "`learn.train` has no fake, so the smoke trains for real" (`plan.md:286`). This fails edges_mitigated (6/7) and unmitigated_reasoned. `learn.train` says "Used by: lab" but has no `**Boundary:**` line (`learn/contract.md:48-52`), so the interface lists no fake for it (`phase0.md:20` builds fakes from Boundary lines).
- **rl inc, hidden under `file` rows:**
  - T23→T22: "PL-02 also runs PL-01 as built" (`plan.md:326`; `pipelines.md:30`).
  - T24→T23: "the smoke evaluates PL-02's runs" (`plan.md:328`).

**Rule broken:** `phase0.md:28`: "A call to another pipeline or package runs against that boundary's fake, so wiring PL-02 never waits for PL-01."

**Fix:**
- `architecture-design/references/contracts.md:12`: a pipeline entry or contract function consumed by another package or pipeline gets a Boundary line and a fake.
- dt: a lint for a function whose "Used by" names another package with no Boundary line (the type-cases lint covers types only).

### F3. Library classes behind a factory step: wiring waits on their thickens. **design** (open §11.2) **+ skill**, real; it also hides a grader leniency

**Evidence (rl inc).**
- Nine library thickens carry "Reason: library module behind `build`" (`plan.md:115-228`): Snake views and rules, corridor, schedule, table learner, bots, play, compare, lineup.
- T22 waits on T12, T13, T14, T15 and T27 (`plan.md:244`, rows 319-323). T24 waits on T16–T19 (`plan.md:264`).
- T12 waits on T11: "none: every `step` builds its observation with the view functions" (`plan.md:308`). That is a call into another module, which design §4.1 and `phase0.md:21` freeze with a signature and replay double.
- **Cost:** +2 on the critical path. edges_mitigated fails at 8/9, a real failure.
- **quant aao:** T23 → T11 (a non-fold thicken).

**Rule broken:** `phase0.md:28`, wiring "never on their thicken tasks".

**Grader leniency.**
- `dtrun.unmitigated_class` passes every `order` row with any reason (`dtrun.py:309-310`).
- `same_step_unit` (`dtrun.py:266-271`) calls T12→T11 "same module" because both tasks have `Step: PL-01.build`, although they write `game.py` and `views.py`.

**Fix:**
- **Design:** decide §11.2. Either library classes reached through a Protocol become steps with their own spine (a minimal real class), or the interface task writes a trivial real implementation.
- **Skill:** wiring depends only on spines and fold tasks; a golden case that needs real collaborators belongs to the system task.

### F4. phase0_split and wave_width count a bare owner's steps one by one, and drop call steps. **grader**

**Evidence:**
- **rl aao:** 9 misses, e.g. `PL-10.make_world`, `PL-11.close_run`, `PL-16.judge`. Every one is named in a spine's Reason as sharing its module (`plan.md:50,61,89,128`). wave_width counts 20 units (`cli` gives 7 alone), so 13 < 16. With the units grouped there are 11, so 13 ≥ 8.8: pass.
- **quant inc:** `PL-12.searchSecurities`, `fetchPrices` and `fetchFlags` are covered by T27, "the four PL-12 fetches share `api/client.ts`" (`plan.md:230`).
- **quant aao:** 5 misses, all named by T03, T10 and T19 (`plan.md:40,112,204`).
- **rl inc:** `PL-02.report_runs` and `PL-03.load_agents` are covered by T04 (`plan.md:47`). The grader drops the call step `train_seeds` ("PL-01 as built") from the `lab.runs` unit, then matches spines by Step ID, and T04's Step is that call step.

**Cause.**
- `dtrun.step_unit` (`dtrun.py:244-248`) treats an owner without a dot as one unit per step. In a multi-package repo, `cli`, `core`, `runs` and `snake` are modules, and `steps.md:28` lets a bare owner hold "one module per related group of steps".
- `phase0_misses` (`dtrun.py:382-383`) drops call steps from a unit; line 401 matches spines by Step ID.

**Fix:**
- A step's unit is the spine (or fold) task whose Writes own its owner path (`dtrun.owns`), or whose Reason names the step.
- Call steps stay in their module's unit, and spines are matched by unit (also in `wave_units`, `dtrun.py:360-362`).
- dt residue: rl aao's `no_spine` still lists PL-02 and PL-03. T23 names them only in Read and Reason (`plan.md:246-247`; `model.spine_pipeline`).

### F5. tester_starts_early ignores "every contract class". **grader**

**Evidence (rl inc, 7/12).**
- Counted late: T13 `corridor.CorridorEnv`, T15 `tabular.TableAgent`, T16 `bots.RandomBot`, T17 `bots.ScriptedBot` and T20 `lab.LADDER`.
- T01's acceptance reads "Every M1 step and contract class imports with its contract signature" (`plan.md:18`), and its Writes is `src/rllab/**`.

**Cause.** `interface_writes_symbols` (`dtrun.py:342-357`) skips type and class sections (lines 351-352).

**Fix:** include class and type sections when the acceptance names every contract class or type. That gives 11/12 = 0.92, a pass. T20's `lab.LADDER` is a constant and stays late, a real nit.

### F6. A dependency on an interface task is counted as an unmitigated data edge. **grader** (plan nit)

**Evidence (quant inc).**
- The row: "T27 API client spine | T03 server interface | data | none: the generated `api/types.ts` comes from the server interface" (`plan.md:358`).
- That row is the F5 fix from iteration 7 working: T03 writes `packages/cockpit/src/api/types.ts` (`plan.md:37`).
- `tasks.md:45` says a dependency on the interface task "needs none" (no row), so the row itself is superfluous.

**Cause.** `edges_mitigated` (`grade.py:379`) and `unmitigated_reasoned` (`grade.py:389`, `dtrun.unmitigated_class`) don't skip rows whose To is an interface task. `edge_table_consistent` already skips them.

**Fix:** skip those rows. That gives 3/3, and both checks pass.

### F7. `call_step` reads "as in PL-06" as a call. **grader**

**Evidence (quant inc).** no_edge_to_code_when_interface flags T33 → T08. That is wiring PL-07 waiting on its own pipeline's `read_tables` spine, an integration edge (`plan.md:363`).

**Cause.**
- `read_tables`' spine cell says "as in PL-06" (`qdata/pipelines.md:12`). `dtrun.call_step` (`dtrun.py:238`) treats any other PL ID in the cell as a call.
- `wiring_crosses_frozen` (`dtrun.py:428-434`) then matches the declared `qdata.read_tables` fake, which exists for server and qops.
- The same rule drops `PL-11.require_local` ("as in PL-10") from the units.

**Fix:** treat a step as a call only when its cell says "PL-NN as built" (or names the call); "as in" means the same function is reused.

### F8. A fake glob `data.load_*` is read as the symbol `data.load_`. **grader**

**Evidence (quant aao).** T01 writes "the `data.load_*` / `data.security_info` fakes" (`plan.md:20`).

**Cause.** `SYMBOL` (`grade.py:221`) stops at `*`, and `fake_ok` can't resolve `load_` (`grade.py:514`). The real symbols, `data.load_returns`, `load_prices` and `load_universe`, are in T01's Read and are cross-package.

**Fix:** expand `pkg.prefix_*` against the contract's symbols.

### F9. runner_split matches "python3 probe.py" inside string literals. **grader** (probe family)

**Evidence (quant aao).** Turns 26 and 28 are heredoc Python scripts that edit `probe.py`. The match comes from string literals in them, such as `sys.exit("usage: python3 probe.py bulk|checks|update")`, not from any run.

**Cause.** `probefacts.runs_user_script` (`probefacts.py:243-258`) splits a command into segments on newlines but scans heredoc bodies.

**Fix:** drop heredoc bodies and quoted strings before matching.

### F10. Nested field types are undefined. **real** (skill), with two grader misses

**Real:**
- **rl aao:**
  - `worlds.Scene` uses `Circle | Cell | Line`, defined nowhere (`worlds/contract.md:24`).
  - `BreakIt(line, removed, prediction, outcome)` has no field types (`lab/contract.md:70`).
  - `LearnerEntry(…, settings)` leaves `settings` untyped.
- **quant aao:** `models.AgentConfig` (`models/contract.md:54`) and nine server view row types (`server/contract.md:14,32,37`) are undefined.
- **quant inc:** `TestCompanyRow`'s `company` field is untyped (`qdata/contract.md:156`).

**Grader:**
- `FixedEntry(spec: str)` (`learn/contract.md:6`) is fully typed in constructor form.
- quant inc's four `*Dto` types are defined as "mirror their `qdata` types field for field" (`server/contract.md:31,37`).
- `dtrun.defined_in` (`dtrun.py:515-520`) accepts neither form.

**Fix:**
- `architecture-design/references/contracts.md:10`: every type a field annotation uses gets a section or a typed inline definition.
- Grader: accept the constructor form, and "mirrors `pkg.Type`" when that section exists.

### F11. Spine Writes go beyond the owner module. **real** (minor, no width cost; skills lag design §6.2), one grader strictness

**Evidence:**
- **rl inc:** T03 writes `train/log.py` (`train.load_log`, a contract function no step owns) beside `loop.py` (`plan.md:42`).
- **rl aao:**
  - T08 writes an intent test (TC-28 on a spine, `plan.md:94`).
  - T10 writes `qtable.py`, a library class (F3) (`plan.md:113`).
  - T14 writes `draw.py`, a private helper (`plan.md:151`).
- **quant inc:**
  - T19, T22 and T29 are folds (`Reason: fold:`) labelled `Kind: spine`, and they write intent tests (`plan.md:162,188,248`). `phase0.md:33` makes a fold "one split thicken task".
  - T20 writes `sources/synthetic.py` under owner `sources.sharadar`. It is a stand-in while the Sharadar spine waits on PB-01, which no rule covers (`plan.md:170-177`).
  - T27's "2 source entries" (`client.ts` and `validate.ts`, both under owner `api/`) is **grader** strictness (`dtrun.py:221-222`).

**Fix:**
- Carry design §6.2's folder owner (`train/loop/**`) into `steps.md:28` and `phase0.md:25`.
- A fold's Kind is thicken.
- Design: say how a step blocked on a probe gets its milestone stand-in.

### F12. The interface misses a type that a milestone step's signature names. **real** (skill)

**Evidence (rl inc).**
- `PL-05.load_summaries` has Out `list[Summary], list[CrossPlay]` (`pipelines.md:92`). T01's Read has no `evaluate.CrossPlay` (`plan.md:15`).
- The plan's Open questions claim "no M1 step passes them" (`plan.md:350`).

**Fix.** `phase0.md:19`: the interface declares every type named in a milestone step's In → Out, because the signature needs it.

### F13. A milestone Depends cell carries build-order notes, and they form a cycle. **real** (skill + dt)

**Evidence (quant inc).**
- M6's Depends cell: "M4 (build order: after M4, before M5, by the user's choice)".
- M5's: "M12 (build order: M4 → M6 → M9 → M12 …)" (`docs/roadmap.md:19-20`).
- dt reads every `\bM\d+\b` in the cell (`model.py:513-514`), so M5↔M6 is a cycle in dt's own graph. Yet `dt roadmap --check` exits 0.

**Fix:**
- `build-planning/references/cut.md:23`: Depends lists only the milestones whose outputs are needed.
- dt: `roadmap --check` errors on a cycle.

### F14. rl all-at-once goes multi-package. **real** (skill)

**Evidence.** AD-02 sets up four packages (`architecture.md:125-129`). Its reasons are three dependency stacks and "one 360-line contract that every task loads". `shape.md:8` says "A proof of concept is almost always a single package". Import-linter enforces dependency direction inside one package, and `dt context` loads only the sections a task reads.

**Effect.** It costs 3 interface tasks in wave 0. Wave 1 drops from 16 to 12, partly because one `cli` spine (T12) covers 8 steps.

**Fix.** `architecture-design/references/shape.md:8`: neither reason justifies a split.

### Smaller

- **quant inc brief is 514 words** (doc_budgets and brief_size). Real; owner idea-refine.
- **Grader evidence is truncated** (`split_miss[:6]`, `spine_bad[:4]`), which hid quant inc's T29 and 3 of rl aao's phase0 misses. Owner: harness.

## Iteration-7 findings in iteration 8

| Finding | Status | Evidence |
|---|---|---|
| F1 object boundaries | **Fixed** | Replay doubles in all runs (contract lines above). rl inc sim_ready_2 passes, no_edge_to_code 10 → 0, wave 1 8 → 18; rl aao fakes_only passes. Library-class residue is F3 |
| F2 shared thicken modules | **Fixed** | quant aao `validate/consistency.py`, `crosscheck.py`, `status.py` (`plan.md:180,190,200`); no thicken→thicken chain left anywhere; quant aao critical path 8 → 5 |
| F3 unmitigated wording | **Fixed** (grader structural; `none: integration:` in every plan) | Remaining failures are real (rl aao, F2) or the new F6. New leniency: the `order` class accepts anything (F3) |
| F4 folds / wiring on thicken | **Partly** | Folds recorded: 12 in quant aao, 3 in quant inc, 1 in rl aao, 0 in rl inc. rl inc wiring waits on 9 non-fold thickens; quant aao T23→T11 |
| F5 cross-runtime types | **Fixed** | quant inc T03 writes the generated `api/types.ts` (`plan.md:37`); T04 has `Depends on: —`; sim_ready_1 passes in all four |
| F6 writes_disjoint mapping | **Fixed** (grader) | Conflicts 0 in all four. The failures left are F11 residue; design §6.2's folder owner never reached the skills |
| F7 phase0_split | **Partly** | Dotted owners, folds, system tasks and package-local smoke tests are fixed; bare owners and call steps still fail in all four (F4). dt no_spine still off for rl aao |
| F8 interface_coverage | **Fixed** | Passes in all four; type-cases lint present |
| F9 tester_starts_early | **Partly** | Methods and the task's own step are fixed (3/3, 3/3, 13/13); contract classes aren't (rl inc 7/12, F5) |
| F10 fakes cross-package | **Fixed** | quant inc passes (qdata fakes, `qdata.Loader` double); new glob bug F8 |
| F11 wave_width | **Partly** | Counted in owner units with honest numerators (rl inc 16 vs 7.2); bare owners inflate rl aao (F4) |
| F12 milestone_depends | **Fixed** | Parses in all four; quant inc fails for a real cycle (F13) |
| F13 no_edge_to_code | **Fixed** | File edges are reported separately and the wiring→provider rule works; one false positive (F7) |
| Smaller: thicken after wiring | **Fixed** | No spine or thicken task depends on a wiring or system task in any run |

## Plan map (`flow/plan/M1.html`, workflow-analyzer)

- **R1 landed.** Wave 0 holds only interface tasks (1, 3, 4 and 2 boxes). The legend says "A tester waits only on the interface: the interface tasks among its task's ancestors, else all of the milestone's". Split tasks that depend on spines (rl inc T12, T20, T21) draw their tester in wave 1.
- **R2 landed, but mislabelled (new R6).** The tile reads "8/9 89% data and call edges mitigated", plus unmitigated rows by class. But `reason_class` (`planmap.py:534-539`) checks `order` before integration, and wiring before `file`. So rl inc shows "integration 4 · side-effect order 18" where the truth is 18 integration rows and 4 shared-file rows. That swap hides exactly the F1 chain.
- **R3 landed.** No blank skill on the 19, 10, 42 and 21 full snapshots. The blanks are `same_as` duplicates.
- **R4 landed.** "9 waves of boxes (tester and implementer apart) · whole tasks: 8". Minor (R7): "agents in the widest wave 21" counts boxes while the producer line says 18; show both.
- **R5 landed.** Box labels wrap onto two lines.
- **New R8.** When paths tie, the map highlights only one. quant aao has two critical-path lanes of 5, each with a shared-entry pair, and the map shows only the ingest lane while the grader shows the data lane.

## Fix list for iteration 9

**Design** (`design/interface-first-design.md`)
1. §4.1 row 77 and §5.1 line 113: `__main__.py` and per-pipeline entry modules are shared modules, written by the interface task. The §6.1 `file` row says two wiring tasks never share an entry module. §9.1 adds a check: no wiring→wiring edge except through a fake (F1).
2. Decide §11.2: library classes behind a factory step, either as their own steps or as trivial real implementations written by the interface task (F3).
3. A step blocked on a probe gets its milestone stand-in behind the Protocol, with a folder owner (F11).
4. §9.1 types_in_contract: field types resolve to a section, a typed inline definition, or "mirrors `pkg.Type`" (F10).

**Skills**
1. `pipeline-design/references/steps.md:28` and `template.md:11,31`: one entry module per pipeline. `build-planning/references/phase0.md:23,28` and `tasks.md:33`: the interface task writes `__main__.py` and the re-exporting `pipeline.py`; each wiring task writes only its own entry (F1).
2. `architecture-design/references/contracts.md:12` and `phase0.md:20`: a pipeline entry or function consumed across pipelines or packages has a Boundary line and a fake (F2).
3. `phase0.md:28`: wiring depends on spines and fold tasks only; a golden case needing real collaborators goes to the system task (F3).
4. `phase0.md:33`: a fold is Kind thicken, Mode split. `steps.md:28` and `phase0.md:25`: folder owners for steps with private helpers (F11).
5. `phase0.md:19`: declare every type named in a milestone step's In → Out (F12). `contracts.md:10`: nested field types (F10).
6. `cut.md:23`: Depends holds only needed milestones, no order notes (F13). `shape.md:8`: contract size and in-package dependency direction aren't reasons to split (F14). idea-refine: brief ≤ 500 words.

**dt** (`scripts/**`)
1. `dt lint writes`: warn when two wiring tasks write one entry module or `__main__.py` (F1).
2. A lint for a contract function used by another package or pipeline with no Boundary line (F2).
3. `dt roadmap --check`: error on a Depends cycle (F13).
4. `model.spine_pipeline`: count a system task for the system pipelines it names in Read or Reason (F4 residue).
5. `boundaries_unfrozen`: report a type in a milestone step's In → Out that is missing from the interface (F12).

**Harness / grader**
1. `dtrun.step_unit`, `wave_units` and `phase0_misses` (`dtrun.py:244-248, 360-362, 382-383, 400-401`): unit by spine Writes or Reason; call steps kept; spines matched by unit (F4).
2. `interface_writes_symbols` (`dtrun.py:342-357`): include classes and types (F5).
3. `grade.py:379,389` and `dtrun.unmitigated_class`: skip rows to an interface task (F6).
4. `dtrun.call_step` (`dtrun.py:238`): only "PL-NN as built" is a call (F7).
5. `grade.py:221,514`: expand `*` globs (F8).
6. `probefacts.runs_user_script` (`probefacts.py:247-258`): ignore heredoc bodies and string literals (F9).
7. `dtrun.defined_in` (`dtrun.py:515-520`): accept the constructor and mirror forms (F10).
8. `dtrun.spine_writes_problem` (`dtrun.py:221-222`): files inside the owner folder count as the folder (F11).
9. Tighten the leniencies:
   - Flag wiring or system → non-fold thicken (`dtrun.py:309-310`).
   - `same_step_unit` (`dtrun.py:266-271`) needs a shared module, not just a shared Step.
   - Check `file` rows between wiring tasks for a missing fake (F1, F2, F3).
   - Once skill fix 1 lands, count `serial_on_shared_file` between wiring tasks as a failure.
10. Print full lists in evidence or metrics.

**workflow-analyzer** (`workflow-analyzer/scripts/planmap.py`)
1. `reason_class` (lines 534-539): test `file` and integration before generic `order`, matching `dtrun.unmitigated_class` (R6).
2. Draw every tied critical path (R8).
3. Widest-wave tile reads "21 boxes (18 whole tasks)" (R7).
4. Mark wiring→wiring shared-entry edges on the map (F1).

Files: `/Users/connorott/plugins/cott-plugins2/dev-team/evals/results-iteration-8/grading-*.json`, `/Users/connorott/plugins/dev-team-workspace/iteration-8/<traj>/with_skill/project/tasks/plan.md`, `/Users/connorott/plugins/cott-plugins2/dev-team/evals/harness/{grade.py,dtrun.py,probefacts.py}`, `/Users/connorott/plugins/cott-plugins2/workflow-analyzer/scripts/planmap.py`, and `/Users/connorott/plugins/cott-plugins2/dev-team/skills/{pipeline-design/references/steps.md,build-planning/references/phase0.md,build-planning/references/tasks.md}`.
