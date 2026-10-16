# Iteration 5: first full planning-stage run

**Skills:** commit 1f59a5c (unchanged by f2e7e45, which only removed old status scripts). **Models:** Opus 5.5 agent, Sonnet simulated user. n=1 per trajectory. Run on 2026-10-16. Raw runs are in `../dev-team2-workspace/iteration-5/`, and the packaged runs are in `bench/`.

## Results

| Run | Checks | Turns | Agent cost | Wall clock | Stop |
|---|---|---|---|---|---|
| rl incremental | 43/46 | 44 | $23.22 | 76 min | finished (re-run on the fixed driver) |
| rl all-at-once | 42/46 | 18 | $11.28 | 30 min | finished |
| quant incremental | 50/57 | 64 | $39.92 | 70 min | killed at turn 64, stuck in a finish loop (see H3) |
| quant all-at-once | 50/57 | 17 | $12.45 | 33 min | finished |

- **Total cost:** about $104 including the discarded first rl incremental run ($16.73, 26 turns). That's near the bottom of the expected $85–175.
- **Turns:** within the expected ranges, except quant incremental at 64, which includes 18 empty loop turns.
- **Scores:** graded with the fixed `gate_discipline` (G1).

| Failing check | rl inc | rl aao | quant inc | quant aao | Finding |
|---|---|---|---|---|---|
| `roadmap_rows` | 7 rows / 3 stages | 4 / 3 | 5 / 4 | 5 / 4 | S1 |
| `incremental_all_planned` / `upfront_m1_planned` | M2–M7 unplanned | M2, M3 Specced | M2–M5 unplanned | M2–M5 Specced | S2, S3 |
| `doc_budgets` | ✗ | ✗ | | ✗ | S5 |
| `gate_discipline` | | turn 14 | | turn 14 | S4 |
| `spec_on_pipeline_or_deferred` | | | 3 IDs | 16 IDs | S3, S6 |
| `quant_grow_at_features` | | | grew at structure | never grew | S3, S7 |
| `refs_milestones`, `skills_on_structure_tasks` | | | ✗ | ✗ | S1, S2 |
| `brief_goals_stage_neutral` | | | 1 goal | | S6 |
| `finished` | | | ✗ (killed) | | H3 |

## Harness bugs (fixed in this iteration)

- **H1. A blocked stage change leaked the next stage.** When `readiness()` blocked a `next_stage`, the driver downgraded the action to `reply` but still sent the message, which already introduced the next stage. In the first rl incremental run, fish leaked at turn 13 while the driver still counted one stage. Foraging was never revealed.
  - **Fix:** a blocked move re-asks the simulated user with a note saying why. If it still tries to move on, the reply falls back to "Approved. Please continue."
- **H2. The simulated user ended incremental runs at stage 1's build setup.** Its rules said "if it offers to start building, say planning is done", and that offer first comes right after stage 1's build setup.
  - **Fix:** with a next stage pending, the rule is now to decline building and introduce the next stage. A `finish` while a stage is still unrevealed is re-asked as `next_stage`.
- **H3. A finish loop with no exit.** quant incremental left `ideas/ppo-allocation-agents.md` Accepted. `readiness()` kept blocking `finish` on it, and the agent kept replying "nothing to do", for 18 turns.
  - **Fix:** `STALL_LIMIT = 4`. After 4 blocked moves in a row with no doc change, the run stops with `stop_reason: "stalled: …"`.
- **G1. `gate_discipline` counted pipeline-design's `Used by:` appends to `contract.md` as architecture edits.** pipeline-design is allowed to make those edits, so this produced 4 false positives across the two incremental runs.
  - **Fix:** `Used by:` lines are no longer counted. Re-grading leaves only the real breaches (S4).

All four fixes were tested on `fake_claude.py`. The dry run still passes 44 of 57 checks.

## Skill and design findings (not fixed)

**S1. Stages split into several milestones.** This happened in all four runs; rl incremental turned 3 stages into 7 milestones.
- **Cause:** build-planning's size rule, "about 5–15 tasks. Bigger means two milestones" ([SKILL.md:72](../../skills/build-planning/SKILL.md)). Each stage here holds 18–20 tasks, so the agent proposes a split and the simulated user accepts. quant splits forecasting + agents, the stage the evals deliberately merged.
- **Grader side:** `roadmap_rows`, `refs_milestones` and `skills_on_structure_tasks` assume one milestone per stage, numbered in stage order.
- **Decision needed:** either the grader accepts N ≥ 1 milestones per stage, mapped by Source (incremental) and by outline (all-at-once), or build-planning keeps a stage as one milestone and splits only on the user's request.

**S2. Incremental runs plan only the active milestone.** This follows the design: "task-level plans only for the next milestone", with queued plans written only when the user asks ([planning-stage.md:20](../../design/planning-stage.md)). But `incremental_all_planned` and the README expect every milestone to have a plan.
- **Recommendation:** grade incremental runs like all-at-once: M1 planned, and every later milestone at least Designed. Have the simulated user ask for a queued plan only if queued plans are meant to be tested.

**S3. All-at-once leaves later milestones below Designed.** There are two causes:
- **quant:** spec-writing wrote "Initial spec: M1 in full, M2–M5 outlined". No skill tells it to do this, and it contradicts "design everything known". With M2+ only outlined, nothing downstream designed them: 16 spec IDs (every STRUCT, PORT, FEAT, FCST and AGENT requirement) sit on no pipeline, and the architecture never grew past one package.
  - **Fix:** spec-writing states that when the user gives every stage up front, every stage is specced in full.
- **rl:** the pipelines really do cover fish and foraging (PL-01 Covers TANK-01–07 and HUNT-01–07), but dt can't attribute them. Every row's Source is `brief`, the only Changelog row says IDs `all`, and dt doesn't expand `all`. So `inferred_pipelines` is empty for M2 and M3, and build-planning New filled only M1's Pipelines cell, even though its own reply listed what it deferred to M2 and M3.
  - **Fix:** in up-front mode, build-planning New fills Packages and Pipelines for every designed row, not only M1. Expanding `all` in dt alone would mark every brief row Designed off M1's pipelines.

**S4. build-planning rewrites the contract.** This happened in both all-at-once runs, at turn 14, with 220 contract lines in rl.
- **Cause:** architecture-design wrote headings with several symbols each (`train.train / train.train_seeds`), against the one-symbol-per-section rule. `dt lint` didn't catch it at the architecture gate. `dt context` failed on those `Read:` IDs at plan time, so the planner split the headings itself and sent the contract back to Draft.
- **Fix:** `dt lint` errors on a contract heading with more than one symbol, so the problem is caught at the architecture gate.

**S5. Doc budgets are exceeded.** Every run except quant incremental goes over:

| Run | `contract.md` (budget 60) | `pipelines.md` (budget 120) | `tests.md` (budget 120) |
|---|---|---|---|
| rl incremental | 91 | 314 | 296 |
| rl all-at-once | 280 | 202 | 211 |
| quant all-at-once | 94 | 141 | 127 (also `tasks/plan.md` at 417 lines, budget 400) |

rl keeps every stage in one package, and with one section per symbol a 60-line contract holds only about 10 symbols.
- **Decision needed:** either these budgets apply per milestone (or scale with the number of symbols and pipelines), or single-package projects are pushed to Grow sooner.

**S6. Small misses (quant incremental):**
- DATA-06, LOAD-04 and LOAD-06 sit on no pipeline and aren't Deferred.
- One brief goal is worded for a stage: "Fast, stable access… daily returns load in seconds" is about the data stage.

**S7. quant incremental grew at the structure stage, not features.** `qrisk` became its own package at turn 22. The check encodes §13's expectation that the shape grows at features. Read AD-xx before deciding whether the check or the skill is wrong.

## Not done

- **Blind judge:** not run. The prompt builder is `judge_prompt.py`, and there's no earlier iteration of the four-stage evals to compare against.
- **Re-runs:** quant incremental wasn't re-run on the fixed driver. Its stage changes happened to go cleanly (each stage's build setup finished before the user moved on), so H1 and H2 didn't affect it. H3 did, but only after all four stages were planned.
