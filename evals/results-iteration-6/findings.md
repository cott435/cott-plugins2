# Iteration 6: re-run after the S1, S3, S4 and S5 fixes

**Skills:** commit 55e91af (contract-heading lint, up-front scope, per-track milestone cap, per-unit doc budgets). **Grader:** 1947e13, which adds `milestone_depends`; iteration 5 was re-graded with it. **Models:** Opus 5.5 agent, Sonnet simulated user. n=1 per trajectory. Run on 2026-10-16. Raw runs are in `../dev-team2-workspace/iteration-6/`, and the packaged runs are in `bench/`.

Before the run: `plugin.py` validated the plugin, `simulate.py` passed 8/8, and `dryrun.py` scored 45/57 (the grader then had 57 checks). The one-turn smoke run cost $0.36: all seven `dev-team2:*` skills were listed and `evalperm` was connected.

## Results

| Run | Checks | Iter. 5 (re-graded) | Turns | Agent cost | Wall clock | Milestones (iter. 5) | Stop |
|---|---|---|---|---|---|---|---|
| rl incremental | 47/47 | 46/47 | 40 | $25.84 | 69 min | 4 (7) | finished |
| rl all-at-once | 46/47 | 43/47 | 19 | $12.67 | 37 min | 4 (4) | finished |
| quant incremental | 54/58 | 52/58 | 61 | $36.55 | 96 min | 10 (5) | finished |
| quant all-at-once | 52/58 | 53/58 | 15 | $13.00 | 32 min | 5 (5) | finished |

- **Total cost:** $88.06 for the agents plus $0.36 for the smoke run. That's at the bottom of the expected $85–175.
- **Driver:** no errors and no `stalled: …` stops. The H1–H3 fixes held. Every stage change was clean: rl at turns 19 and 30, quant at 19, 33 and 46. Both incremental runs finished without a loop.
- **Turns:** every run is within the expected ranges.

| Failing check | rl inc | rl aao | quant inc | quant aao | Finding |
|---|---|---|---|---|---|
| `spec_on_pipeline_or_deferred` | | | | 33 of 92 IDs | S3 |
| `first_planned_rest_designed` | | | | M2–M5 Specced | S3 |
| `milestone_depends` | | | | M2–M5 have none | S3, S8 |
| `sim_replan_1` | | | | mode `new` (4 packages have no pipelines) | S3 |
| `nh_routed_in_plan` | | | | null-hypothesis-testing is only on M2+, which have no tests | S3 |
| `gate_discipline` | | turn 8 | turn 11 | | N2 |
| `quant_grow_at_features` | | | never grew | | S7 |
| `intake_subagent_per_file` | | | turn 46 not seen as intake | | N1 |
| `spec_gwt` | | | DATA-03 | | small miss |
| `spec_pca_mp` | | | | grader regex | G3 |

## Iteration-5 findings: status

**S1. Stages split into several milestones: partly fixed; the splitting moved upstream.**
- **Fixed:** no run produced a `milestone-size` lint error. The only plan-budget warnings were transient (quant incremental at 404 and then 420 lines; it ended at 396). rl incremental went from 7 milestones to 4, and Snake is no longer split four ways.
- **Not fixed: size-driven splits still happen, in two new places:**
  - **rl all-at-once, build-planning (turn 12):** M1 "needs about 18 first-version tasks" (9 pipelines, with a 5-file limit per task). The cap counts the whole Phase 0 spine plus the longest chain, so the agent pre-emptively carved off **M4 "Snake verified and reported"** (CartPole check, SB3 reference, algorithm check, statistics, report) through an idea file.
    - This is the same leftover pattern as iteration 5's "Snake replays + reference". M1 now ends without a "does it beat the baselines" verdict, and the build order reads M1 → M4 → M2 → M3.
    - **Cause:** the track counts the entire spine. A spine of 9 independent pipelines counts as 9 serial tasks, so any milestone with many pipelines goes over 15 before Phase 1 starts.
  - **quant incremental, idea-refine:** each stage was pre-split at the idea stage, every time citing "the 15-task limit on the longest path" (turns 21, 34 and 48). The result is 4 stages → 10 milestones (iteration 5: 5).
    - The splits follow dependency lines (M4 portfolios need M3's estimates, M6 models need M5's screens), so they aren't leftovers. But M2 (EDA, 1 pipeline) and M8 (forecast portfolios, 1 pipeline) are small, and the cap is now shaping stages before any plan exists.
- **Proposed:** count the spine as parallel by pipeline (the longest single spine chain plus the longest Depends chain), or exempt spine tasks from the cap. idea-refine shouldn't argue from a task cap it can't measure yet.

**S2. Incremental runs plan only the active milestone: still resolved (G2).** Three of four runs pass `first_planned_rest_designed`. quant all-at-once fails it for S3 reasons, not S2.

**S3. All-at-once leaves later milestones below Designed: fixed for rl, not for quant.**
- **rl all-at-once: fixed.** M2–M4 are Designed. build-planning filled Packages, Pipelines and Depends for every row.
- **quant all-at-once: spec half fixed, pipelines half not.**
  - spec-writing now specs every stage in full: 92 IDs, "Add approved spec for all five milestones".
  - architecture-design grew to six packages (`core`, `data`, `risk`, `signals`, `forecast`, `agents`).
  - But at the pipeline gate (turn 7) the agent proposed "start with `data` and `core`, which M1 needs", and the simulated user agreed. Only those two packages got a `pipelines.md`. `risk`, `signals`, `forecast` and `agents` have only an architecture and a contract.
  - So M2–M5 stay Specced and 33 of 92 IDs are on no pipeline (iteration 5: 16). Five checks fail from this one gap: the four above plus `milestone_depends`, since build-planning fills Depends only for designed rows.
  - **Cause:** pipeline-design's "In scope" line covers up-front planning ("every package and every milestone's workflows"), but nothing in `dt status --skill pipeline-design` flags the other packages. The agent's own default is "the next milestone's packages". In rl the single package made the two readings the same.
  - **Proposed:** in up-front mode, `dt status --skill pipeline-design` reports every package with no `pipelines.md` as `new` (with the uncovered IDs per package), and the gate checklist fails while any is left. Alternatively, build-planning New refuses while any brief row has packages with no pipelines.

**S4. build-planning rewrites the contract: fixed.**
- No run hit a `contract-heading` error, at any turn or at the end.
- No build-planning turn touched any `contract.md`. Contract edits happened only in architecture turns, in Used-by appends, and in the pipeline-time Revise noted in N2.
- Final `dt lint` has 0 errors in all four runs.

**S5. Doc budgets exceeded: fixed by the per-unit rule. The Grow ceiling is ignored, though.**
- No `budget` warnings at the end of any run. Per-unit counts against the budgets:

| Run | `contract.md` lines / symbols / budget | `pipelines.md` lines / pipelines / budget | `tests.md` lines / cases / budget |
|---|---|---|---|
| rl incremental | 312 / 47 / 388 | 201 / 8 / 290 + layout | 296 / 51 / 525 |
| rl all-at-once | 372 / 51 / 420 | 246 / 9 / 325 + layout | 149 / 24 / 255 |
| quant incremental | 561 / 87 / 708 | 687 / 25 / 885 + layout | 811 / 120 / 1215 |
| quant all-at-once (largest package) | 90 / 16 / 140 (`core`) | 105 / 3 / 115 + layout (`data`) | 109 / 18 / 195 (`data`) |

- **New:** the `grow-size` warning fired in three runs (both rl contracts, and all three quant incremental docs at 2.5–4× the ceiling) and was never acted on.
  - quant incremental's AD-13 accepts it explicitly ("builders read them one symbol, pipeline or case at a time through `dt context`").
  - With per-unit budgets nothing else pushes a single package to Grow, so the warning has no teeth (see S7).
- **Harness defect:** `docstats.py` still reports `over_budget` against the old fixed 60/120/120 budgets, so its JSON flags every rl doc. It should use `dt lint`'s per-unit rule.

**S6. Small misses (quant incremental): fixed.**
- `spec_on_pipeline_or_deferred` and `brief_goals_stage_neutral` pass.
- The only new miss: DATA-03 has no Given/When/Then.

**S7. quant grew at the wrong stage: inverted.**
- quant incremental never grew. AD-13 recorded staying one package at turn 15, AD-24 confined PyTorch to an optional extra, and it ended at 87 symbols, 25 pipelines and 120 cases in one package. At turn 47 the agent said the split trigger "fires for real" at Stage 4 (PyTorch), then kept one package.
- quant all-at-once grew at the architecture (six packages, one per stage), so its check passes.
- **Cause:** the per-unit budgets (S5) removed the size pressure that drove iteration 5's Grow at structure, and the `grow-size` warning and pipeline-count trigger are both answerable by an AD.
- **Decide:** is a single 25-pipeline package acceptable for this user? If not, `grow-size` should block planning until a Grow or an AD with a hard reason (not "the docs are read through `dt context`"). If it is, the `quant_grow_at_features` check should be relaxed.

**S8. Milestone quality (manual read, compared against iteration 5):**
- **rl incremental: better.** It has 4 milestones (iteration 5: 7), with no Snake over-split and an Exit line on every milestone.
  - M3 "Library check" (1 pipeline) was split from fish at idea-refine, and the user chose it. It's a clean dependency split, but lopsided.
  - M4 (predator–prey) Depends on M3, though it needs M2's tank, not the library check. That's an unneeded serialization `milestone_depends` can't catch.
- **rl all-at-once: same flaw as iteration 5.** The leftover M4 (S1) is back. M3 now Depends on M2, which fixes iteration 5's missing Depends. M2–M4 have no Exit lines.
- **quant incremental: clean but over-split.** It has 10 milestones, all in dependency order with Depends filled and Exit lines on every row. Iteration 5's missing Depends on M5 is gone.
- **quant all-at-once:** stage-per-milestone (5) as in iteration 5, but with no Depends on M2–M5 (S3).

## New findings

**N1. quant incremental stopped invoking skills after stage 2's reference intake.**
- From turn 20 to turn 61 (three stages) no `Skill` call was made. The agent ran each gate from the skill text already in its context, plus `dt` calls. In iteration 5 the same trajectory re-invoked idea-refine, spec-writing, architecture-design and test-planning at every stage. rl incremental re-invoked them at stage 2 (fish) but not at stage 3 (foraging).
- **Effects:**
  - `skills_invoked` still passes, because each skill ran once.
  - The turn-46 intake (one Explore agent per TFT file, done correctly) isn't recognised as an intake turn, so `intake_subagent_per_file` fails.
  - The outputs show no obvious process gaps.
- **Decide:** is reusing the in-context skill acceptable? If yes, the grader should detect gates by `dt` calls and doc changes, not by `Skill` calls. If not, the skills or the plugin's SessionStart hook should say to re-invoke a skill at each new gate.

**N2. pipeline-design revises the architecture in the same turn: rl all-at-once turn 8, quant incremental turn 11.**
- Drafting the pipelines surfaced a missing architecture decision: AD-15 (registry lookups by name) in rl, AD-12 (one entry function per workflow, with new entry symbols) in quant.
- The agent wrote the AD, new contract symbols and the pipelines together, and put the architecture back to Draft. In quant the user asked for exactly that.
- The `gate_discipline` failures are these two turns; nothing else breached it.
- **Decide:** either pipeline-design stops at the gate and routes the Revise to architecture-design as its own turn, or `gate_discipline` allows an architecture Revise that pipeline-design asked for at its gate.

**N3. build-planning and build-setup disagree on test locations (quant all-at-once).**
- The plan and the pipeline layouts put tests in `packages/<pkg>/tests/`, and the smoke data in the protected `tests/fixtures/`.
- build-setup's agents and `check.sh` expect `tests/intent/<pkg>/` and `tests/unit/<pkg>/`. build-setup also writes and protects the `pyproject.toml` files that M1-T01 and T03 listed.
- build-setup caught it, and the plan was revised at turn 15. Neither skill names the multi-package test layout up front.
- **Proposed:** pipeline-design's layout and build-planning take test paths from one place (planning-stage.md or CONSTRAINTS defaults), so build-setup doesn't have to fix the plan.

**N4. The `dataviz` skill is on roadmap Skills lines but not installed.** rl incremental has 3 `roadmap-skill` warnings and rl all-at-once has 2. The agent flagged it under Open questions each time. dt only looks in `.claude/skills` and the plugin, but the agent session has `dataviz` from the user's environment. It doesn't matter for grading, but the routing breaks when the build agents can't see the skill.

**G3. `spec_pca_mp` is a grader false negative (quant all-at-once).** The spec has "eigenvalues below the pure-noise upper edge are replaced by their average" (COV-03) and "eigenvalues above the pure-noise upper edge" (FACT-02). The regex expects `pure noise` with a space and doesn't match "Marchenko" because the spec never names it. Widen it to `pure[- ]noise|noise edge|eigenvalues? (below|above)`.

## Blind judge

**rl** (incremental vs all-at-once). A/B was shuffled with `random.shuffle`, and the key is in `judge-rl-key.json`: **A = all-at-once, B = incremental**. The judge got only the `final__*` docs, the `context__*` packets and `fixtures.txt`. The transcript and `doc_evolution.md` were withheld because they name the mode. The verdict is in `judge-rl.json`.

| Item | all-at-once (A) | incremental (B) |
|---|---|---|
| rl_soundness | 5 | 5 |
| stage_completeness | 5 | 5 |
| internal_consistency | 4 | 4 |
| right_sizing | 4 | 3 |
| milestone_quality | 2 | 3 |
| pipeline_clarity | 5 | 4 |
| task_buildability | 3 | 3 |
| Structure (mean) | 4.0 | 4.0 |
| **Overall** | **8.0** | **7.9** |

- **Result: effectively a tie.** all-at-once wins on pipeline clarity (small single-owner steps). incremental's PL-01 hides two training loops in one `run_episodes` step.
- **Milestone quality:** all-at-once loses on the S1 leftover M4, the build order against the IDs, and M2–M4 having no Exit lines.
- **Incremental defects the judge found:**
  - TC-14, TC-31, TC-32 and TC-47 allow "at most 1 of 20 seeds may reject" at α = 0.05, which a correct test fails about 26% of the time.
  - Split tasks target functions that were moved to the contract's Retired section.
  - The brief's success section covers only Snake and "the second game".
- **Unbuildable packets:** 3 for all-at-once and 4 for incremental. All of them leave out a type or contract the task needs (`EvalResult`, `DQNConfig` and `TestResult` are undefined).

**quant:** not run. Running it required all-at-once to have Designed milestones after M1, and quant all-at-once has none (S3). Comparing its M1 against incremental's 10 milestones would measure the S3 gap, not quality.

## Not done

- **quant blind judge:** blocked on S3 (above).
- **Re-runs:** none. n=1 per trajectory, so the shift from 5 to 10 quant incremental milestones and the rl tie could be noise. S1's idea-refine pre-splitting and S3's quant pipeline scope have clear causes in the transcripts.
