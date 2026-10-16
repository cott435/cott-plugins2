# Iteration 5: first full planning-stage run

**Skills:** commit 1f59a5c (unchanged by f2e7e45, which only removed old status scripts). **Models:** Opus 5.5 agent, Sonnet simulated user. n=1 per trajectory. Run on 2026-10-16. Raw runs are in `../dev-team2-workspace/iteration-5/`, and the packaged runs are in `bench/`.

## Results

| Run | Checks | Turns | Agent cost | Wall clock | Stop |
|---|---|---|---|---|---|
| rl incremental | 46/47 | 44 | $23.22 | 76 min | finished (re-run on the fixed driver) |
| rl all-at-once | 43/47 | 18 | $11.28 | 30 min | finished |
| quant incremental | 52/58 | 64 | $39.92 | 70 min | killed at turn 64, stuck in a finish loop (see H3) |
| quant all-at-once | 53/58 | 17 | $12.45 | 33 min | finished |

- **Total cost:** about $104 including the discarded first rl incremental run ($16.73, 26 turns). That's near the bottom of the expected $85–175.
- **Turns:** within the expected ranges, except quant incremental at 64, which includes 18 empty loop turns.
- **Scores:** graded with the grader fixes G1 and G2, and the `milestone_depends` check added afterwards.

| Failing check | rl inc | rl aao | quant inc | quant aao | Finding |
|---|---|---|---|---|---|
| `first_planned_rest_designed` | | M2, M3 Specced | M5 Idea | M2–M5 Specced | S3 |
| `milestone_depends` | | M3 (predator–prey) has none | M5 (PPO agents) has none | | S8 |
| `doc_budgets` | ✗ | ✗ | | ✗ | S5 |
| `gate_discipline` | | turn 14 | | turn 14 | S4 |
| `spec_on_pipeline_or_deferred` | | | 3 IDs | 16 IDs | S3, S6 |
| `quant_grow_at_features` | | | grew at structure | never grew | S3, S7 |
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

- **G2. The grader assumed one milestone per stage** (S1, S2). `roadmap_rows`, `refs_milestones` and `skills_on_structure_tasks` found a stage's milestone by its position. Incremental runs also had to plan every milestone, which the design deliberately doesn't do.
  - **Fix:** rows map to stages by Source (incremental) or by stage keywords (all-at-once), and a stage may have several rows. Both modes are now graded on `first_planned_rest_designed`, so their final roadmaps compare like for like. A reference must be on at least one milestone of its own stage, and later milestones that reuse it may list it too.

The driver fixes were tested on `fake_claude.py`. With G2 the dry run passes 45 of 57 checks (M2 Designed without a plan now passes).

## Skill and design findings (not fixed)

**S1. Stages split into several milestones.** This happened in all four runs; rl incremental turned 3 stages into 7 milestones.
- **Cause:** build-planning's size rule, "about 5–15 tasks. Bigger means two milestones" ([SKILL.md:72](../../skills/build-planning/SKILL.md)). Each stage here holds 18–20 tasks, so the agent proposes a split and the simulated user accepts. quant splits forecasting + agents, the stage the evals deliberately merged.
- **Grader side:** fixed (G2). Splitting a stage is allowed.
- **Skill side:** the size rule is applied unevenly. rl's snake stage split four ways, while quant's data milestone kept 24 tasks. Only one milestone is active at a time, and parallel work happens inside a milestone through `**Parallel:** G<n>` groups, so splitting independent tracks into separate milestones makes them run one after the other. Enforcing the size rule is in progress.

**S2. Incremental runs plan only the active milestone.** This follows the design: "task-level plans only for the next milestone", with queued plans written only when the user asks ([planning-stage.md:20](../../design/planning-stage.md)). But `incremental_all_planned` and the README expect every milestone to have a plan.
- **Resolved (G2):** both modes are graded at the same bar. Whether incremental and all-at-once produce milestones of similar quality is a question for the blind judge, which should be run once S3 is fixed. Until then, all-at-once has no designed milestones after M1 to compare.

**S3. All-at-once leaves later milestones below Designed.** There are two causes:
- **quant:** spec-writing wrote "Initial spec: M1 in full, M2–M5 outlined". The agent proposed this itself in idea-refine's handoff (turn 5: "I'd go deep on M1 and keep the later stages short"), and the simulated user agreed. No skill tells it to do this, and it contradicts "design everything known". With M2+ only outlined, nothing downstream designed them: 16 spec IDs (every STRUCT, PORT, FEAT, FCST and AGENT requirement) sit on no pipeline, and the architecture never grew past one package.
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

**Diagnosis: the budgets are too low for the content, not padded by the skill.** The cost per unit is steady across all seven package docs: about 4–6 lines per contract symbol, 21–32 per pipeline (step table included) and 5–8 per test case. The overshoot tracks how much one package holds: rl keeps 13 pipelines, 54 test cases and 22 symbols in one package. quant incremental stays in budget only because it Grew into four packages, and even then three docs sit exactly at the limit (60/60, 120/120, 119/120), which suggests content squeezed to fit. The design also contradicts itself: [planning-stage.md:77](../../design/planning-stage.md) says one contract section per component, while dt and pipeline-design need one per symbol. A 60-line contract holds about 10 symbols.
- **Proposed fix:** budget per unit instead of per file. Roughly: contract ≤ 8 lines per symbol, pipelines ≤ 35 per pipeline plus the layout, tests ≤ 10 per case. Keep a per-file ceiling as the point where architecture-design should consider a Grow.

**S6. Small misses (quant incremental):**
- DATA-06, LOAD-04 and LOAD-06 sit on no pipeline and aren't Deferred.
- One brief goal is worded for a stage: "Fast, stable access… daily returns load in seconds" is about the data stage.

**S7. quant incremental grew at the structure stage, not features.** `qrisk` became its own package at turn 22. The check encodes §13's expectation that the shape grows at features. Read AD-xx before deciding whether the check or the skill is wrong.

**S8. Milestone quality was never judged.** The grader checked milestone structure, and the blind-judge rubric had no milestone item. A manual read:
- **quant: good in both modes.** Each milestone is one runnable capability in dependency order, and splitting the PPO agents off is clean. Flaw: quant incremental's M5 has no Depends.
- **rl incremental: good content, over-split.** Snake became four milestones; M4 (a 5-seed tabular study) is mostly M1 again. Rows are never renumbered, so the build order reads M1 → M4 → M2 → M3, and M2–M4 have no Exit lines.
- **rl all-at-once: weakest.** M4 ("Snake replays + reference") is a leftover carved off M1 only to cut its size. M3 (predator–prey "in the same tank") has no Depends on M2.
- **Pattern:** splits made at build-planning to hit a size number leave leftover milestones. Splits from the user's own stages at idea-refine come out clean.
- **Added:** a `milestone_depends` grader check, which catches both Depends flaws, and a `milestone_quality` item in the blind-judge rubric.

## Not done

- **Blind judge:** not run. The prompt builder is `judge_prompt.py`, and there's no earlier iteration of the four-stage evals to compare against.
- **Re-runs:** quant incremental wasn't re-run on the fixed driver. Its stage changes happened to go cleanly (each stage's build setup finished before the user moved on), so H1 and H2 didn't affect it. H3 did, but only after all four stages were planned.
