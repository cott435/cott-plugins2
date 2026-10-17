# Iteration 7: the interface-first checks

**Scope:** the eleven interface-first checks that fail in at least one run, across the four iteration-7 runs: rl incremental (34 turns, stopped `stalled: roadmap has 2 rows for 3 stages`), rl all-at-once (14 turns), quant incremental (54 turns) and quant all-at-once (20 turns). n=1 per trajectory. **Skills:** the runs' own snapshot (`<run>/plugin/dev-team/skills`), the same in all four runs and the same as `dev-team/skills` at `41d2ebd`. **Grader:** `evals/harness/grade.py` at 5e125d4. Raw runs are in `../dev-team-workspace/iteration-7/<trajectory>/with_skill/`.

**Method.** Each run's final `tasks/plan.md` (Kind, Writes:, Depends on, dependency-graph table), its `contract.md` and `pipelines.md`, and the grader's code for each check were read. The grader was re-run on scratch copies of the runs, cut off after `milestone_depends`, with every list printed in full (the evidence in `grading.json` is cut to 5 items). The runs were not touched. Line references like `plan.md:238` point into that run's `project/`.

**Classes:** **grader** (the plan follows the design or skill, and the check is wrong or stricter), **skill** (the skill text is unclear, missing or contradictory), **dt**, **design** (the design doc itself is unclear).

**Headline.** Exclusive `Writes:` works: no run has a single Writes conflict. Most red checks are grader bugs. The plan problems behind them come down to two design or skill gaps that cost real width:
- **Object-typed boundaries have no way to be frozen (F1).** These are Protocols, classes and calls into another component.
- **Separately thickened steps share one module (F2).**

## Top 5 fixes

1. **Give object-typed boundaries a freeze form (design, with contradictory skill text).** The interface task writes a fixture-backed replay double as the type's sample. Owners: design §4.1; `build-planning/references/phase0.md:18,35`; `pipeline-design/references/steps.md:36`; `architecture-design/references/contracts.md:12`; `build-planning/references/tasks.md:41` (narrow `code` to "changes code", so a spine never has a `code` edge to another step); grader `grade.py` `fake_ok`. rl incremental serializes 6 of its 9 spines this way (critical path 6); rl all-at-once used such a fake for `core.ParallelEnv`, got a wave of 16, and fails `fakes_only_cross_pipeline` for it.
2. **One module per separately thickened step (skill).** Owners: `pipeline-design/references/steps.md:28`, `build-planning/references/tasks.md` §9. quant all-at-once chains T29 → T30 → T31 → T32 on `validate.py`, 4 of its 8 critical-path tasks; the fix brings the path to about 5.
3. **Judge `none:` edges by structure, not wording (grader).** Owner: `grade.py:219-226,392-397`; add "integration" to design §9.1's allowed reasons. The check rejects the skill's own example reason, "none: the smoke runs it" (`examples-phase0.md:71`): 30/30, 30/33, 33/39 and 27/30 false alarms that hide the real spine edges.
4. **Group by owner module, map owners to paths, handle system pipelines (grader, plus one dt fix).** `grade.py` `writes_disjoint` (line 366 compares a dotted owner with a path; 0 real conflicts in all four runs), `phase0_split` (439-466), `wave_width` (338-345); dt `scripts/devteam/model.py:790` `spine_pipeline` must count `Kind: system` for system pipelines.
5. **Read milestone Depends the way dt does (grader).** `dtprobe.py:190`: use `ms.depends` (dt's `model.py:513-514` is right; `dt roadmap --check` exits 0) and keep the parenthetical as `needs`. Fails `milestone_depends` in all four runs.

Next in line: cross-runtime interfaces (F5, `phase0.md:23`) and `interface_coverage` (F8: samples are build output, so planning names cases only).

## Results

| Failing check | rl inc | rl aao | quant inc | quant aao | Finding |
|---|---|---|---|---|---|
| `writes_disjoint` | 9/9 spines flagged | 16/16 spines | 9/9 spines | 11/11 spines | F6 (0 real conflicts) |
| `unmitigated_reasoned` | 30 of 30 `none:` rows | 30 of 33 | 33 of 39 | 27 of 30 | F3; F1 for the rl inc spine rows |
| `no_edge_to_code_when_interface` | 10 | | | 2 | F1 (9), F13 (3) |
| `phase0_split` | 3 misses | 4 | 16 | 19 | F7; F4 |
| `interface_coverage` | 5 | | 14 | 14 | F8; F1 (Agent, Env, RunWriter, App, Route) |
| `tester_starts_early` | | 2/3 | 10/13 | (8/10 passes) | F9 |
| `fakes_only_cross_pipeline` | | `core.ParallelEnv` fake | `data.trading_days` fake | | F1 (rl aao), F10 (quant inc) |
| `wave_width` | (false pass) | | | 23 vs 23.2 | F11 |
| `sim_ready_1` | | | T04 waits on T03 | (hidden order) | F5 |
| `sim_ready_2` | T10–T15 not ready | | | | F1 |
| `milestone_depends` | `M1 (…)` unknown | same | same | same | F12 |

## Findings, ordered by impact on parallelism

### F1. Object-typed step boundaries have no freeze form, so rl incremental serializes its spines. **design** (with contradictory skill text)

**What happens.** A step's input is often an object with behavior, not a data payload. Examples are `core.Env` and `core.Agent` (Protocols), `runstore.RunWriter` (a class with methods), `server.App` (a FastAPI app the `mount_*` steps extend), and `web.Route`. Other inputs are calls into another component's function in the same package: `load_agent` calls `make_env`, and `record_highlights` calls `record_episode`.
- **The design gives two freeze forms.** §4.1 freezes a data edge with "a sample payload" and a cross-pipeline call with a fake. It also says "within a pipeline, a type and a sample".
- **The skill forbids the obvious answer.** `phase0.md:35` reads: "Mocking a step is forbidden … its consumer builds against the type's sample". You can't hand a sample payload of an `Env` to `evaluate`.
- **Two runs resolved this in opposite ways:**
  - **rl incremental took the serial route.** It wrote `code` edges: `plan.md:238-250` has "none: the loop's test runs a real environment", "none: evaluation needs a real agent", "none: save_outputs calls the writer's methods" and more. The skill allows them in so many words: `tasks.md:41` defines `code` as "A task changes **or runs** code another task writes". That contradicts `phase0.md:25`: "One per new step, each depending only on the interface task".
  - **The result in rl incremental:** 6 of its 9 spines (T10–T15) wait on library thicken tasks (T02 corridor, T05 baselines, T07 tabular, T09). `sim_ready_2` fails, and `no_edge_to_code_when_interface` lists 9 violations. Wave 1 has 8 tasks out of 22, the critical path is 6 tasks, and N/CP is 3.67.
  - **rl all-at-once took the parallel route.** It froze the Protocol with a replay fake. `contract.md:35` reads: "**Cases:** a fixture-backed fake replaying a recorded 5-step Snake episode". Three spines run on it (`plan.md:61,85,117`; the graph row is at `plan.md:295`). Wave 1 has 16 of 26 tasks. `fakes_only_cross_pipeline` fails for exactly this.
- **Library classes behind a factory step aren't steps.** rl incremental puts the corridor and Snake envs, the baselines and the tabular agent under a "Phase 1: Library thicken" heading (`plan.md:22`). They are thicken tasks of `PL-01.make_env` and `make_agent`, whose step is only a name lookup. The design's "one spine per step" doesn't cover them.
- **interface_coverage.** `core.Env`, `core.Agent` and `runstore.RunWriter` (rl inc `contract.md:30,48,389`) have no case, because no sample payload fits a Protocol.

**Fix:**
- **Design §4.1.** Add a boundary row: "Step → step passing an object with behavior (a Protocol or class), or a call into another component's function: frozen as the Protocol or signature plus a fixture-backed replay double in `tests/contracts/<id>.<Type>/`". The double is the type's sample, not a mock of a step. Say whether a trivial real implementation (the corridor, the random agent) may be written by the interface task instead (§11's open alternative).
- **Skill `build-planning/references/phase0.md:18,35` and `pipeline-design/references/steps.md:36`.** Allow that double: "a Protocol type's sample is its replay double".
- **Skill `build-planning/references/tasks.md:41`.** Narrow `code` to "a task changes code another task writes (a thicken after its spine, two thickens of one module)". Add: "a spine never has a `code` edge to another step's task". Running the spines is the wiring's edge (F3).
- **Skill `architecture-design/references/contracts.md:12`.** Add: "a Protocol or class type's case is a replay double".
- **Grader `grade.py:483-496` (`fake_ok`).** Accept a fake of a type whose contract Cases name a fake or double. `sample_of` (`grade.py:557-561`) already accepts it through Fixtures.

**Expected effect:** rl incremental's T10, T11, T13 and T14 join wave 1 (wave 1 goes from 8 to about 12–14 tasks), and the critical path drops from 6 to about 4.

### F2. Several separately thickened steps share one module, so their thicken tasks chain. **skill**

**Where it happens:**
- **quant all-at-once.** PL-11 gives six steps the owner `data.validate`, one module (`pipelines.md:72-78`). build-planning wrote four thicken tasks that all write `packages/data/src/data/validate.py`. Each one waits on the last: T29 → T30 → T31 → T32 (`plan.md:368-370`, "none: both write validate.py"). They make up 4 of the 8 tasks on M1's critical path (T01 → T09 → T29 → T30 → T31 → T32 → T33 → T34), and they are the 4 trailing width-1 waves.
- **Smaller cases.** rl incremental T04 → T03 on `snake/env.py` (`plan.md:253`), and quant incremental T35 → T17 on `views/stock.tsx`.

**Cause.**
- `pipeline-design/references/steps.md:28` says "one module per step owner". So an owner given as `component.module` holds as many steps as the agent likes.
- `phase0.md:25` accepts it: "steps sharing one module share one spine task".
- Nothing tells build-planning that two thicken tasks on one module serialize, or to split the module.

**Fix:**
- **`steps.md:28`.** Add: "a step that gets its own thicken task in the milestone gets its own module (`validate/flags.py`, `validate/coverage.py`); only steps built and thickened together share one".
- **`tasks.md` §9 (the `file` row).** Add: "two thicken tasks writing one module: move the split into the interface task's layout (each step its own file, the old module re-exporting), never chain them".

**Expected effect:** quant all-at-once's critical path goes from 8 to about 5.

### F3. `unmitigated_reasoned` rejects the skill's own canonical reason. **grader** (the design's reason list is also short)

**Every run fails, nearly row by row.**
- **Wiring rows.** The flagged rows are mostly wiring → its own steps: "none: the smoke runs it". That is the exact text of the skill's worked example (`build-planning/references/examples-phase0.md:71`) and of `phase0.md:27` ("It depends on its pipeline's spines, since the smoke runs them").
- **`file` rows** ("both write viewer/pipeline.py", "both write validate.py").
- **System rows** ("the real chain runs them", "runs its smoke on the real server").

**Cause.**
- The grader matches free text against `REASON_KINDS` (`grade.py:219-226`). That list follows design §9.1 ("same module, unsplittable shared file, real side-effect order"), which has no entry for integration edges.
- §5.1 and §9.1's own replay check ("wiring isn't ready until its pipeline's spines are ticked") require exactly those edges.

**Why it matters for parallelism.** The 30 false alarms hide the rows that do serialize (F1's spine → thicken rows in rl incremental).

**Fix, in `grade.py:392-397`:** classify each `none:` row by its structure, not its wording:
- **(a) Integration:** From is a wiring or system task and To is a spine, thicken or wiring of a pipeline it wires or swaps.
- **(b) `file`:** the two tasks' `Writes:` overlap (check with `write_overlap`).
- **(c) Same module:** a `code` row where From is a thicken and To is the spine or thicken of the same step, or their Writes overlap.
- **(d)** `contract-change`.
- **(e)** `order` with a non-empty reason.
- **Flag the rest**, and separately flag `code` rows between two different steps' spine and thicken tasks (F1).

Add "integration (wiring and system tasks run the steps they wire)" to the allowed list in design §9.1.

### F4. Wiring waits on thicken tasks, so the full behavior lands on the critical path. **skill** (folds), **design** (library classes)

**What the design says.** §5.1 puts wiring beside thicken (Phase 2), after the spines only.

**What the runs did.** Wiring tasks depend on thicken tasks in every run:
- **rl all-at-once.** T21–T25 wait on T18 "Snake world" ("none: the smoke steps the real world", `plan.md:266`). That puts T18 on the critical path: T01 → T05 → T18 → T21 → T22.
- **rl incremental.** T19 waits on T04 and T07 (`plan.md:261-262`).
- **quant incremental.** T27 waits on T18–T20, and T28 on T22–T26 (`plan.md:239-256`).
- **quant all-at-once.** T24 waits on T06–T08.

**Why.**
- **Folds with no spine.** Those steps have only a split thicken task that replaces the stub itself. That is phase0.md's first fold, applied without saying so: quant inc `plan.md:186-237` has no `Reason:` and no "baseline" bullet. Wiring then has to wait for the whole behavior, and phase0.md's condition is broken: "Apply one only where it doesn't lengthen the critical path".
- **Library classes (F1).** The world class isn't a step, so the make_worlds spine can't build a real world.
- **The fold record is invisible.** `phase0.md:31` asks for each fold to be listed "under ASSUMPTIONS". That text lives in the chat, so neither the grader nor a reviewer can see a fold.

**Fix, in `phase0.md:31-33`:**
- Record each fold on its task: `**Reason:** fold: <rule>`.
- Add the fold the agents actually used: "a step whose spine version is its whole behavior and has a golden case is one split thicken task". rl inc wrote exactly this on T17 and T18 (`plan.md:161,170`).
- State that the wiring of a folded step depends on the fold task, so a fold is allowed only when that task is XS.

### F5. Cross-runtime interfaces chain interface tasks, or hide the order. **design** (and skill)

**The two runs.** Both quant runs generate the web package's TypeScript types from the server's schema (AD-12).
- **quant incremental makes the order explicit.** M1-T04 (web interface) has `Depends on: M1-T03` (`plan.md:48`, row `plan.md:378`). `sim_ready_1` fails (ready = T01–T03), and the whole web lane (T15–T17) starts one wave late.
- **quant all-at-once leaves it implicit.** Its T04 has "server types generated from `tests/contracts/server.*` schemas" (`plan.md:44`), but those folders are written by T03, and `Depends on: —`. `dt ready` would dispatch T04 against an empty folder. `sim_ready_1` passes only because the order is invisible.

**What the skill says.** `phase0.md:17,23` say interface tasks have "`Depends on:` —" and are "all solo and first". Neither covers generated types.

**Fix:**
- **Design §4.2 and `phase0.md:23`.** Add: "when one runtime's types are generated from another's schema, the providing interface task runs the generator and writes the generated file too (its Writes claims it); interface tasks never depend on each other". quant inc's T03 already writes `packages/web/src/api/openapi.json` with a Reason (`plan.md:31-40`).
- **Grader `simulate.py:173-174`.** Keep the strict equality.

### F6. `writes_disjoint` compares a dotted owner with a path. **grader**

**The bug.** `grade.py:366` tests `re.escape(owner)` against each Write. With the owner `experiments.build`, the pattern can never match `src/gridlab/experiments/build.py`, so every spine in every run is flagged (`conflicts: []` in all four). Two more rules are stricter than the design:
- **Test paths.** A test is recognized only under the root `tests/`, so `packages/web/tests/*.test.tsx` counts as a second source file.
- **Folder globs.** `any("*" in w …)` rejects a folder glob, which design §6.2 allows ("exact paths or one directory glob owned by the task").

**Real residue after the fix**, worth a line each in the plan review but costing no width:
- **Helper module beside the owner:** rl aao T02 writes `configs/snake-default.toml`, T06 writes `train/checkpoints.py`, and T14 writes `viewer/draw.py`.
- **Data files:** quant inc T08 writes `reference/**`.
- **Mislabelled step:** quant aao T17 writes `research/eda.py` under `Step: PL-13.mount_dataset_routes`. It is a library function, not a step (F1).
- **Spine of a system pipeline:** quant aao T11 is a spine with `Step: PL-01`.

**Fix, in `grade.py:362-368`:**
- Map the owner to a path: drop a leading package id, then dots become `/`, and match `…/<path>(.py|.ts|.tsx|/**)`.
- Count as tests any `tests/` segment, `*.test.ts(x)` or `*.spec.ts`.
- Allow one folder glob.
- **Design decision needed:** does a step's private helper module count as its owner module? If yes, the owner is a folder (`train/loop/**`). Say so in design §6.2 and `phase0.md:25`.

### F7. `phase0_split` misses shared spines, system pipelines and web smoke tests. **grader** + **dt** + skill (F4)

**The grader's four errors:**
- **(a) Spines are counted by the `Step:` field only** (`grade.py:451-458`), though `phase0.md:25` says "steps sharing one module share one spine task". Examples are rl inc T08 (make_env and make_agent, `plan.md:81`), quant inc T07 (save and read snapshots) and T16 (four query hooks), and quant aao T05 (three `data.source` steps) and T09 (six `data.validate` steps).
- **(b) System pipelines must have a wiring task** (`grade.py:459-462`). quant's PL-01 and PL-03 are root system pipelines with no steps; `phase0.md:29` gives them a system task (quant inc T37 and T38, quant aao T33).
- **(c) The smoke test must start with `tests/`.** quant inc PL-11 writes `packages/web/e2e/pl11.spec.ts`, and quant aao PL-14 writes `packages/web/tests/smoke.spec.ts`.
- **(d) A fold is found only by "baseline" in the acceptance** (F4).

**dt has the same blind spot.** `model.spine_pipeline` (`scripts/devteam/model.py:790-799`) counts only `Kind: wiring`, so `dt status` `no_spine` lists PL-01 and PL-03 (`status/build_planning.py:301`).

**Real residue:**
- quant aao T16 builds `createApiClient` and `connectProgress` in one solo task.
- Its wiring T27 builds `render` without saying so.

**Fix:**
- **`grade.py:439-466`:** group steps by owner module; skip `system` pipelines unless no system task names them; recognize package-local test paths; accept `Reason: fold`.
- **dt `model.spine_pipeline`:** also return the pipeline for a `Kind: system` task whose pipeline `is_system`.

### F8. `interface_coverage` wants samples that planning must not write. **design** + **grader** + **skill**

**The rule.** A type passes if its contract section names a `Fixtures:` path, or if `tests/contracts/<id>.<Type>/` exists on disk (`grade.py:557-561`). Neither run family writes samples at planning:
- **The skill says so.** `contracts.md:12` reads "Name the cases; don't write the fixtures", and `phase0.md:18` gives the samples to the interface task (quant inc T02: "one sample each", `Writes: tests/contracts/builder.*/**`).
- **The design contradicts itself.** §9.1's `no_code_during_planning` makes `tests/contracts/` build output, while `interface_coverage` asks for "a sample under `tests/contracts/`" in M1.
- **The grader's comment contradicts the design.** `grade.py:669-670` says samples "are planning output like golden fixtures".

**Two more causes:**
- **Skill gap: contracts.md:12 limits `Boundary:` lines** to "packages in a multi-package repo". So intra-package step types carry no Cases (quant inc `builder.Download`, `RawTables`, `CanonicalTables`, `server.ServerConfig`, at `builder/contract.md:57-86` and `server/contract.md:9-17`), against design §4.1 ("every step boundary that crosses owners").
- **Agent miss:** quant aao's `data.IndexChange` is "Used by: server" but has no Boundary line (`data/contract.md:16-19`).
- **Grader approximation:** boundaries are adjacent table rows (`grade.py:566`), not Out → In matches. For example, rl inc `make_agent → RunWriter.create` names `Agent`, but `RunWriter.create` takes a `RunConfig`.

**Fix:**
- **Design §4.2 and §9.1.** Planning names cases; the interface task writes samples.
- **`grade.py:557-581`.** A type passes when the contract names a case and an interface task's Writes covers its `tests/contracts/<id>.<Type>/`. Match each step's Out against later In cells. Fix the comment at 669-670.
- **`contracts.md:12`.** A `Boundary:` line is required for every type that crosses step owners, components included.
- **dt.** A `dt lint` rule `type-cases` (owner `scripts/devteam/commands/lint.py`).

### F9. `tester_starts_early` misses methods and the interface's own signatures. **grader**

**What's late:**
- **quant inc:** `data.Loader.lookup_ticker`, `data.Loader.search` and `data.Loader.trace` are counted late, though `data.Loader` is declared by T01.
- **rl aao:** `baselines.make_baseline` is counted late, and so is **quant aao's** `server.get_run`. In both, the interface acceptance writes "Every M1 step and contract function … with its signature", but `phase0.md:23` has the interface `Read:` list only types and boundaries.
- **quant aao T31:** it reads no symbol at all.

**Fix, in `grade.py:285-302`:** treat `X.Y.method` as declared when `X.Y` is; when the interface acceptance says it writes every contract function, declare the contract functions of the packages its Writes covers; treat a split task's own `Step:` function as read. **Skill, `tasks.md:48`:** "a split task's `Read:` names its step's function". **Expected effect:** rl aao 3/3, quant inc 13/13, quant aao 9/10.

### F10. `fakes_only_cross_pipeline` misses cross-package calls. **grader**

`call_step` (`grade.py:274-276`) treats a step as a call only when its spine cell names another `PL-NN`. quant inc PL-04's `trading_days` step is owned by the `data` package, and its spine is `data.trading_days(history_start, today)` (`builder/pipelines.md:16`). That is a cross-package call, so the fake that T27 uses is correct. **Fix:** `call_step` is also true when the step's owner is another package (its first segment is in `facts["packages"]` and differs from the pipeline's package).

### F11. `wave_width` counts steps, not spine units, and counts implementer halves as ready. **grader**

**The denominator** is the number of steps (`grade.py:279-283, 341-345`), but steps sharing a module share one spine (F7a). Counted by owner module, the four runs need 8.0, 12.0, 19.2 and 14.4, not 8.8, 15.2, 24 and 23.2. quant aao's failure (23 ready against 23.2) is this bug.

**The false pass.** The numerator counts every task whose deps are all interface tasks, thicken implementers included. So rl inc passes 11/11 while 6 of its 9 spines are not ready.

**Fix:** use distinct non-call owner modules as the denominator; count only spine tasks plus tester halves, as the check's text says.

### F12. `milestone_depends` reads the skill's own `M1 (what it needs)` form as an unknown milestone. **grader** (dt is right)

`cut.md:23` prescribes `M1 (stats.Cov, PL-01 output)`, and every run used it (for example, rl inc `docs/roadmap.md:14`). `dtprobe.py:190` builds `depends` from `md.split_list(ms.row["Depends"])`, so the item is `M1 (PL-01 output, runstore.RunDir)`, which is not an ID. dt's own parser takes `re.findall(r"\bM\d+\b", …)` (`scripts/devteam/model.py:513-514`), and `dt roadmap --check` exits 0 in all four runs. **Fix:** in `dtprobe.py:190`, use `ms.depends` when it exists (else the same `findall`), and report the parenthetical separately as `needs`. Iterations 6 and 7 should be re-graded.

### F13. `no_edge_to_code_when_interface` flags file edges and misses wiring → provider spines. **grader** (one plan defect)

**False positives.** `covered_boundary` (`grade.py:400-411`) ignores the row kind and the Writes. It flags real `file` edges: rl inc T21 → T20 (both write `viewer/pipeline.py`); quant aao T31 → T30 and T32 → T31 (`validate.py`; the real problem there is F2).

**False negative.** It never checks a wiring task against another component's spine. quant aao T26 (wire PL-13) depends on T10, the `data.Loader` spine ("open_loader is its first step", `plan.md:354`). Yet T01 declares a `data.Loader` fake, and `phase0.md:27` says wiring "runs against that boundary's fake". That is a real defect the grader misses. rl inc T22 → T19 ("the smoke trains its run through run_train") is the same pattern.

**Fix:** skip pairs whose Writes overlap and report them as a `serial_on_shared_file` metric instead; for a wiring From, flag a To in another component or package when the step that calls it has a declared fake or sample.

### Smaller

- **quant inc T29 → T28.** A thicken waits on its pipeline's wiring because "TC-15 and TC-17 run the whole pipeline" (`plan.md:382`). That puts T29 on the critical path. **skill:** a TC that runs the whole pipeline belongs to the wiring or system task (`build-planning/references/tasks.md` §5), or test-planning gives it step fixtures.
- **quant inc T38.** It cites "the version T41 built" (`plan.md:359,420`); there is no T41. `dt lint` doesn't resolve task IDs in Acceptance text or in graph reasons. **dt**, low priority.

## The plan map on real data

### Per-M1 width and critical path

| Run | Tasks | Critical path | Waves (whole tasks) | Widest | N/CP | What sets the critical path |
|---|---|---|---|---|---|---|
| rl inc | 22 | 6: T01 → T05 → T10 → T13 → T19 → T22 | 1, 8, 5, 4, 2, 2 | 8 | 3.67 | F1: the evaluate and train_agent spines wait on the baselines and corridor thicken tasks; T22 waits on T19 (F13) |
| rl aao | 26 | 5: T01 → T05 → T18 → T21 → T22 | 1, 16, 4, 4, 1 | 16 | 5.2 | F4: wiring waits on the Snake world thicken; T22 → T21 is a file edge (both write `train/pipeline.py`) |
| quant inc | 38 | 6: T01 → T12 → T28 → T29 → T37 → T38 (weighted 13, through M-sized wiring T30 → T31) | 3, 21, 8, 4, 1, 1 | 21 | 6.33 | T29 after wiring (Smaller); T31 → T30 share the server entry; the T04 → T03 interface chain (F5) |
| quant aao | 34 | 8: T01 → T09 → T29 → T30 → T31 → T32 → T33 → T34 | 4, 19, 5, 2, 1, 1, 1, 1 | 19 | 4.25 | F2: four thicken tasks chained on `validate.py` |

`flow/plan.json`'s `builds[]` and the M1 pages agree with the grader's own graph numbers in every run ("Recomputed here from depends edges: the same").

**Mode comparison.** All-at-once is wider than incremental in rl (16 against 8), and the two are close in quant (19 against 21). rl's gap is F1: the two rl runs met the same object boundary differently. It is not a mode effect.

### Rendering problems seen on this data

- **R1. Tester halves are drawn before the interface.** A split task's tester takes only the interface tasks that appear among its direct `Depends on` (`workflow-analyzer/scripts/planmap.py:363`). A split task that depends on a spine (quant aao T28 → T05, T29 → T09, T30–T32) therefore gets no predecessor, and its tester is drawn in W0 beside the interface diamonds. This happens in every run (quant aao W0 shows 9 "agents": 4 interface plus 5 testers; quant inc T21, T29, T35; rl inc T04, T07, T18; rl aao T18–T20). The design rule is that the tester depends on the interface task. **Fix:** use the milestone's interface tasks, or those among the task's ancestors.
- **R2. The "graph edges mitigated" tile reads as a failure.** It divides all table rows (3/33 9%, 2/32, 4/37, 4/43). Most rows are wiring and system integration edges, which can never be mitigated. **Fix:** show mitigated data and call edges, as the `edges_mitigated` check does, plus a count of unmitigated rows by reason class (F3).
- **R3. The skill row is mostly blank.** `turns.json` names a skill only on the turn that invoked it, and later turns continue it without a `Skill` call. So `plan.json` has `"skill": ""` on 15 of rl inc's 19 plan-changing snapshots and on most of the others (the iteration-6 N1 pattern). **Fix:** `evals/harness/planexport.py:152-161` (`turn_skills`) carries the last invoked skill forward until another one is invoked.
- **R4. The wave tile mixes units.** It counts segment waves (rl inc and quant inc show 7), while the line under it gives the producer's 6 waves of whole tasks and says "the same". **Fix:** label it "waves (tester and implementer as separate boxes)", or show both numbers.
- **R5. Box labels are cut to about 20 characters** ("T09 validate spine (…"), so a 13-spine lane is unreadable without hovering. Minor: the hover text and the wave table have the full titles.
