# Iteration 7: run-flow problems and the older failing checks

**Scope:** the rl-incremental stop, the missing milestone rows, the checks that predate the redesign, and cost against iteration 6. The new interface-first checks (`phase0_split`, `writes_disjoint`, `unmitigated_reasoned`, `interface_coverage` and the rest) are in [findings-interface.md](findings-interface.md).

**Sources:**
- Runs in `dev-team-workspace/iteration-7/<trajectory>/with_skill/`, read only.
- The harness at HEAD `41d2ebd`.
- Each run's skill snapshot. It is identical to `dev-team/skills/` at `41d2ebd` (`diff -r` is empty), so the file:line references below hold for both.

**Owner classes:** skill (`dev-team/skills/**`), dt (`dev-team/scripts/devteam/**`), grader (`evals/harness/grade.py`, `dtprobe.py`), driver (`evals/harness/driver.py`).

## Ranked fixes for iteration 8

1. **dt, `stage_to_cut` (F1a, F1b):** compute it on its own, whatever earlier milestones are waiting. A stage reads Designed only when its new spec IDs are on Approved pipelines. Files: `scripts/devteam/commands/roadmap.py:115-148`, `status/build_planning.py:264`.
2. **driver, readiness (F2, F3):**
   - Base readiness on stages: block on any revealed stage with no milestone row (`driver.py:99`), and in all-at-once on any stage below Designed.
   - Count the agent's own commits as changes (`driver.py:303`).
   - Turn readiness reasons into concrete asks in the re-ask note, and update the "fully planned" rule (`driver.py:182`, `:339`).
3. **skill + dt, all-at-once pipeline-design (F3, iteration 6's S3, third time):**
   - Restore the up-front gate line and recommend every stage's workflows (`pipeline-design/SKILL.md:32-36`).
   - `dt` blocks build-planning New while a brief-sourced stage is below Designed (step 0 in `build-planning/references/new.md`).
4. **grader, two roadmap checks (F4, F5):** `first_planned_rest_designed` must see stages that have no rows (`grade.py:629`). Depends notes need the leading `M\d+` parsed out (`dtprobe.py:190`).
5. **skill, test paths (F6/N3):** in the multi-package layout template, test folders sit at the repo root (`pipeline-design/references/template.md:29-33`, `steps.md:28`).
6. **Decide N2 under interface-first (F6):**
   - The grader accepts a routed arch+pipelines or arch+tests Revise round trip (`grade.py:773-781`).
   - Add an "Approved, plus an upstream change: route and stop" row to the test-planning and pipeline-design gates.
7. **skill, backstop for fix 1 (F1c):** `extend.md` cuts any designed stage that has no rows, rows only (`build-planning/references/extend.md:5`, `advance.md:13`).
8. **grader, turn attribution and a regex (F6, F7c, F7e):** match skills to turns by `dt status --skill` calls and reference reads, not `Skill` calls (`grade.py:777`, `:922`). Widen the `spec_ml_beats_classical` regex (`grade.py:823`).
9. **skill, small items (F7a, F7b, F7d):** cost and licence limits become `QR-` items (`spec-writing/references/spec.md`). pipeline-design's write step also fixes `budget` warnings (`pipeline-design/references/new.md:15`).

## Summary

| # | Finding | Runs | Class | Status vs iteration 6 |
|---|---|---|---|---|
| F1 | `dt` hides a designed stage that has no milestone rows behind an earlier milestone that is still Designed, so `stage_to_cut: none` | rl inc (quant inc worked around it) | dt + skill | new (the stage table is new) |
| F2 | The driver's readiness compares the number of milestone rows with the number of stages, and the stall counter misses the agent's own commits | rl inc | driver | new |
| F3 | All-at-once pipeline-design still covers only S1 | quant aao | skill + dt + driver | known S3, not fixed |
| F4 | `first_planned_rest_designed` ignores stages that have no rows | rl inc, quant aao | grader | new false pass |
| F5 | Notes in parentheses in the Depends cell break `milestone_depends` | all 4 | grader | new false fail |
| F6 | `gate_discipline`: N2 is wider and N3 is still unfixed | rl inc, quant aao, quant inc | skill + grader | known, worse (2 → 9 turns) |
| F7 | `spec_gwt`, `spec_ml_beats_classical`, `doc_budgets`, `intake_subagent_per_file` | quant inc | mixed | see the table in section 3 |
| F8 | Cost per turn went up in all four runs | all | — | +17% in total |

## 1. Why rl-incremental stopped at turn 34

**Verdict:** the driver's stall detector stopped it. It was not a skill loop, and build-planning did not refuse to cut.

**What happened, turn by turn:**
- **Turns 11–12, build-planning New:** cut S1 into M1 (Planned) and M2 (Designed). `dt` said `stage_to_cut: S1`.
- **Turn 17, idea-refine:** added S2. `dt roadmap` already showed S2 as Designed, before any TANK pipeline existed (F1b).
- **Turn 22, replan of M1:** `dt` said `mode: replan` and `stage_to_cut: none`. Readiness was `[]`, but only because there were 2 rows for 2 stages and both rows belong to S1. The sim user moved on with `next_stage`.
- **Turns 23–30:** the full S3 chain ran. Readiness reported `roadmap has 2 rows for 3 stages` from turn 23. The sim user chose "finish" at turns 27 and 30, but docs changed in those turns, so the stall counter reset.
- **Turn 31:**
  - The agent read `build-planning/references/extend.md`. `dt` said `mode: extend`, `stage_to_cut: none`.
  - It offered "Cut S2 and S3 into milestones now, as rows only", then said: "My recommendation is neither."
  - Stall count 1.
- **Turn 32:**
  - The sim user replied: "Don't queue M2 or cut S2/S3 now, going with your recommendation." Its prompt at `driver.py:213` says "take its recommendation".
  - Stall count 2, even though the agent committed `d77f28e` in this turn.
- **Turn 33:** the agent said "Cutting S2 and S3 into milestones: waiting on M2 being planned". Stall count 3.
- **Turn 34:** the agent said "Nothing is pending, so planning is done for now." Stall count 4: stop with `stalled: roadmap has 2 rows for 3 stages`. Turns 31–34 cost $1.88.

**The step that never ran:** build-planning Extend, step 1 in `extend.md:5` ("Grow check, then cut the stage"). That mode is keyed to `stage_to_cut` (`extend.md:3`), and `dt` printed `none` at turns 22, 31 and 32.

**Quant incremental shows the gap is in `dt`:** it got the same `dt` output (`stage_to_cut: none`) and cut S2 anyway at turn 28: "S2 still needs cutting into milestones. That's a roadmap decision I can make with you now." It did the same at turns 40 and 54.

### F1. Uncut stages are masked (dt; skill is secondary)

**F1a. `next_unit` stops at the first unit below Planned.**
- `commands/roadmap.py:131-148` walks `[M1, M2, S2, S3]` and returns M2, which is Designed by design.
- `status/build_planning.py:264` then sets `extend` with M2 as the focus, so line 307 prints `stage_to_cut: none`.
- That contradicts `build-planning/SKILL.md:3`: "Cuts each roadmap stage into build-sized milestones once its pipelines are approved".
- **Fix (dt):**
  - Compute `stage_to_cut` as the first stage with no rows whose pipelines are Approved, whatever milestones are pending.
  - Make the mode `extend` whenever it is set.
  - Add a test: M1 Planned, M2 Designed and S2 Designed with no rows must print `stage_to_cut: S2`.

**F1b. A stage reads Designed before its own pipelines exist.**
- At `89d3b9d` (turn 17), S2 inferred `PL-01`–`PL-06`: the S1 pipelines that cover the CORE IDs the fish spec marks as changed. None has a TANK step, yet S2 read Designed.
- S3 read Designed at turn 26, before PL-10 and PL-11 existed (turn 29).
- **Fix (dt, `roadmap.py:115-122` / `pipelines_approved`):** an uncut stage is Designed only when every live spec ID it adds is on an Approved pipeline step or Covers line.

**F1c. The skill text disagrees with itself.**
- `advance.md:13` cuts the next stage only when there is "No next milestone".
- The description and `extend.md` cut once the stage's pipelines are approved.
- **Fix (skill, `extend.md`):** "A designed stage with no rows is cut now, rows only, even while an earlier milestone waits for its plan." Align `advance.md:13` with that.

### F2. Driver (all in `driver.py`)

- **F2a. Readiness counts the wrong rows.** `driver.py:99` checks `len(facts["roadmap"]) < stage_no`. That was correct in iteration 6, when idea-refine wrote one row per stage. Now S1 alone produced 2 rows, so the fish stage passed with no fish row. **Fix:** use `facts["stages"]` and block on every revealed stage with no row, naming each one.
- **F2b. The change detector misses the agent's commits.** `changed` comes from `git show --stat HEAD` at `driver.py:303`. When the agent commits itself (`d67ba2c` and `7d25f23` at turn 31, `d77f28e` at turn 32), the driver's `turn N` commit is empty, so the turn is counted as unchanged. **Fix:** `git diff --stat <previous turn sha> HEAD`.
- **F2c. The re-ask note and the stage rule are stale.**
  - The re-ask note at `:339` says "answer or approve what the assistant just asked", so the sim user declined the cut the agent advised against.
  - `:182` defines "fully planned" by "its build plan has been written".
  - **Fix:** put a concrete ask in the note ("ask for S2 and S3 to be cut into milestone rows"). Redefine "fully planned" as: pipelines approved and milestone rows exist; for the first stage, also an approved plan and an approved bar.

## 2. The missing milestone rows (`roadmap_rows`) and `first_planned_rest_designed`

| Run | roadmap_rows | Stages with no row | first_planned_rest_designed | Uncut stages' status |
|---|---|---|---|---|
| rl inc | FAIL `{'snake': ['M1','M2']}` | fish, foraging | PASS | S2, S3 Designed |
| quant aao | FAIL `{'data': ['M1','M2']}` | structure_portfolios, features_ml, forecasting_agents | PASS | S2–S4 Specced |
| rl aao | PASS (M1–M5) | — | PASS | — |
| quant inc | PASS (M1–M6) | — | PASS | — |

**rl inc:** the stages were designed but never cut. F1 and F2 cover this.

**quant aao:** S2–S4 never reached Designed, so build-planning New correctly cut only S1.
- `new.md:3` and `new.md:5` still say "Cut every designed stage" and "Up front, cut every designed stage, not only the first".
- The agent read `new.md` and `cut.md` in its build-planning turn.
- The real gap is upstream, in F3.

**Compared with iteration 6:**
- Iteration 6 had no stage table. idea-refine wrote one row per stage, and New filled "Packages and Pipelines for every designed row, not only M1's" (old `SKILL.md:38`). So the same quant aao gap then showed as `first_planned_rest_designed` FAIL with `roadmap_rows` PASS. Iteration 7 flips the pair.
- The sentence moved from a bold line in `cut.md` (`8e86483`) to `new.md:5`. `extend.md` never had the incremental counterpart (see F1c).

**F4 (grader, `grade.py:629`):** `rest` is built from milestone rows only, so stages without rows are invisible. **Fix:** also fail on every stage in `facts["stages"]` that has no row or is below Cut, and list those stages in the evidence.

## 3. The older failing checks

| Check | Iter. 6 | Iter. 7 | Class | Status | Cause |
|---|---|---|---|---|---|
| gate_discipline | rl aao t8, quant inc t11 | rl inc t22, t29; quant aao t12, t19; quant inc t10, t11, t14, t17, t51 | skill + grader | known, worse | F6 |
| spec_gwt | quant inc DATA-03 | quant inc DATA-08 | skill | known noise | F7a |
| spec_on_pipeline_or_deferred | quant aao, 33 IDs off | quant aao, 6 off | skill | known S3, improved | F3, F7b |
| spec_ml_beats_classical | pass | quant inc FAIL | grader | new false fail | F7c |
| doc_budgets | pass | quant inc FAIL (`features/pipelines.md`, 180 lines vs a budget of 171) | skill | new, minor | F7d |
| nh_routed_in_plan | quant aao | quant aao ("tests.md mentions: 0") | skill | known S3 | F3 |
| intake_subagent_per_file | quant inc (N1) | quant inc (same) | grader | known N1 | F7e |
| sim_replan_1 | quant aao `mode=new` | quant aao (`eval`/`ml`/`paper` `new`) | skill | known S3 | F3 |
| skills_on_structure_tasks | pass | quant aao FAIL ("no structure_portfolios milestone") | skill | regression in the outcome, same cause | F3 |
| milestone_depends | quant aao only | all 4 FAIL ("unknown") | grader | new false fail | F5 |

### F3. All-at-once pipeline-design stops at S1 (skill + dt + driver)

**What happened in quant aao:**
- At turn 10 the agent proposed: "My plan is to design S1's pipelines now and leave S2–S4's until each of those stages comes up." The sim user agreed.
- In the final state, `dt status --skill pipeline-design` reports `eval=new, ml=new, paper=new`.
- This one gap fails five checks: `roadmap_rows`, `skills_on_structure_tasks`, `nh_routed_in_plan`, `sim_replan_1`, and four of the six IDs in `spec_on_pipeline_or_deferred` (APP-09–11, QR-08).

**Why `spec_on_pipeline_or_deferred` looks better than in iteration 6:** the interface-first architecture has system pipelines PL-03–PL-08 for S2–S4 (`docs/architecture.md:62-93`). Both the grader and `dt`'s `uncovered_ids` count those, so the gap is hidden rather than fixed.

**Why the skill text allows it:**
- The restructure shrank the up-front rule. Iteration 6's `SKILL.md:48` said "every package and every milestone's workflows (a single package gets the pipelines of every stage, not only M1's)". Now `pipeline-design/SKILL.md:32` says only "or up front, every package and stage".
- The gate checklist line from iteration 6 (`:221`) is gone: "Up front: every stage's workflows have pipelines, in every package".
- `SKILL.md:36` still recommends "this milestone's workflows".

**Fixes:**
- **skill (`pipeline-design/SKILL.md:36`):** up front, recommend every stage's workflows, and restore the gate line ("no package is left `new`").
- **dt:** when every stage's Source is `brief`, build-planning New is `blocked` while any stage is below Designed, naming each stage's packages that have no `pipelines.md`.
- **skill (`build-planning/references/new.md`):** add step 0: a stage below Designed means stop and route to pipeline-design.
- **driver:** in all-at-once, block "finish" while any stage is below Designed.

### F5. Notes in parentheses break `milestone_depends` (grader)

- Example of the failure: `unknown: {'M2': ['M1 (PL-01 output, runstore.RunDir)']}`.
- The skill prescribes this format: `cut.md:23` says "name them in the row's Depends: `M1 (stats.Cov, PL-01 output)`".
- **Fix (`dtprobe.py:190`):** keep only `re.match(r"M\d+", …)` from each item.

### F6. gate_discipline

**The flagged turns:**
- **N2: architecture changes in a pipeline-design turn (5 turns).**
  - **rl inc 29:** "Option 1… Go ahead with the contract additions."
  - **quant aao 12:** a properly routed Revise. Turn 11 asked "may I run the architecture revision…"; turn 12 ran it and re-synced the Draft pipelines.
  - **quant inc 10:** "Go ahead with the architecture revision for the internal hand-off types too."
  - **quant inc 11:** the architecture Grow and the pipeline Grow in one turn.
  - **quant inc 51:** AD-33 plus 11 workflows.
- **N2 from test-planning gates (2 turns).**
  - **quant inc 14, arch + tests:** "Apply fixes 1 and 2" (a `ret_delist` contract Revise and a pipeline Revise), done inside the build-planning turn.
  - **rl inc 22, plan + tests:** "make the T1 relative-compass change … Then replan M1." Spec, contract, TC-31, TC-48 and the replan all went into one turn.
- **N3: test-path rewrites at build-setup (2 turns).**
  - **quant aao 19, plan + setup:** build-setup moved the tests to root `tests/intent/<pkg>/` and replanned M1 (107 lines).
  - **quant inc 17, plan + setup:** the same, 110 lines.

**Cause:**
- **N2 is now structural.** Interface-first steps need typed `In → Out` from the contract (`pipeline-design/references/new.md:9`). `new.md:15` routes missing types to an architecture-design Revise, so the Revise and the pipelines that use it land in the same turn.
- **The watch misses it.** "types added in pipeline-design turns" stays `[]` because it only counts turns with a `Skill` call (`grade.py:777`).
- **N3:** the layout block in `template.md:29-33` starts at `src/<pkg>/`. In a multi-package layout the agent prefixed the whole block with `packages/<pkg>/`, test folders included: `packages/data/tests/intent/data/`.

**Fixes:**
- **skill (`template.md`, `steps.md:28`):** give the explicit multi-package form, with test folders always at the repo root.
- **grader (`grade.py:773-781`):** allow arch+pipelines or arch+tests when the previous turn left that doc Draft and asked for the Revise (quant aao 12, quant inc 14). Keep failing the single-turn case.
- **skill (the gate tables in `test-planning/SKILL.md:53-58` and pipeline-design):** add the row "Approved, plus an upstream change: route it to the owner's Revise and stop."
- **Decide (carried over from iteration 6):** if N2 is acceptable under interface-first, relax the check for arch+pipelines.

### F7. Small items

- **F7a. `spec_gwt` (skill).**
  - quant inc `spec.md:739` reads "DATA-08 … cost no more than $50 a month", with only a QR-style check line under it.
  - **Fix (`spec-writing/references/spec.md:47`, `:65`):** cost, licence and budget limits are `QR-` items.
- **F7b. `spec_on_pipeline_or_deferred` (skill).**
  - In quant aao, DATA-05 and DATA-06 were left uncovered as "met by AD-02".
  - quant inc put the same kind of ID on the download step's Covers (`builder/pipelines.md:12`) and passed.
  - **Fix (`steps.md`):** a constraint met by a decision goes on the Covers of the step that applies it.
- **F7c. `spec_ml_beats_classical` (grader).**
  - The quant inc spec states the bar against a named benchmark: ENV-07 "S2's best strategy is named…", AGENT-05 "against S2's benchmark…", and line 6 "scored against S2's best strategy".
  - **Fix (`grade.py:823`):** add `S2'?s? (best|named|benchmark)|best (classical|strategy)|benchmark` to the second group.
- **F7d. `doc_budgets` (skill).**
  - The agent raised the warning at turn 38 ("That's a warning…") and the user approved.
  - `new.md:15` says "Fix what `dt lint` reports"; the agent read that as errors only.
  - **Fix:** say "errors and `budget` warnings".
- **F7e. `intake_subagent_per_file` (grader).**
  - Turn 41 correctly sent one subagent per TFT file, but it had no `Skill` call, so `grade.py:922` doesn't treat it as an intake turn.
  - **Fix:** detect intake turns by a change to `docs/references.md` or by Agent descriptions matching `Summarize .*\.py`.
  - More generally, attribute skills to turns by their `dt status --skill X` calls and `skills/X/references/*` reads.

## 4. Cost and turns against iteration 6

| Run | Iter. 6 | Iter. 7 | Δ cost | $/turn (6 → 7) | Wall clock (min) | Stop |
|---|---|---|---|---|---|---|
| rl inc | $25.84 / 40 turns | $28.12 / 34 turns | +9% | 0.65 → 0.83 | 69 → 66 | stalled |
| rl aao | $12.67 / 19 | $10.05 / 14 | −21% | 0.67 → 0.72 | 37 → 30 | finished |
| quant inc | $36.55 / 61 | $45.53 / 54 | +25% | 0.60 → 0.84 | 96 → 105 | finished |
| quant aao | $13.00 / 15 | $19.12 / 20 | +47% | 0.87 → 0.96 | 32 → 51 | finished |
| **Total** | **$88.06** | **$102.82** | **+17%** | | | |

**Why cost per turn rose in every run:**
- **Context size drives spend.** The costliest turns are build-setup's, with 7.6–12M tokens read from cache: rl inc t14 $2.28, rl aao t13 $2.54, quant aao t18 $3.36, quant inc t17 $3.01.
- **Bigger docs.** Contract type sections grew the architecture docs: rl inc 8,193 → 11,178 words, quant inc 12,248 → 18,920, quant aao 9,040 → 11,728. rl aao shrank (7,441 → 5,570) and is the run that got cheaper.
- **New web research in quant.**
  - quant inc made 116 WebSearch/WebFetch calls; iteration 6 made 7.
  - Its turn 13, "Verify public-record test facts" (61 calls), cost $4.14, the costliest turn in any run.
  - quant aao made 44 calls, in its data-budget research at turn 8.

**Turns:**
- **quant inc** is now multi-package from the data stage: 18 package docs, 35 pipelines, 201 spec IDs. It still ran 7 fewer turns, with 6 milestones (iteration 6 had 10).
- **rl inc** isn't comparable: it stopped before the S2 and S3 cuts, which would take about 2–4 more turns.
- **rl aao** improved: 14 turns, no leftover split, no gate breach.

**The restructure isn't the cause:** each run read only 2–10 `references/*.md` files.
