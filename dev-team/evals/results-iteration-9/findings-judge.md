# Iteration 9: blind judge and mode comparison

**Judge:** four verdicts (rl and quant, each in order AB and in order BA), averaged by `judge_prompt.py average`. Set-1 is incremental and set-2 is all-at-once (`judge-<project>.key.json`). The key sits in `results-iteration-9/` and the sets sit in the scratchpad, so iteration 8's J4 fix (key outside the judge's folder) holds.

## Scores

**rl.** Incremental 7.65, all-at-once 7.45. Each order was won by its Set A: AB went to incremental 7.7 vs 7.1, BA went to all-at-once 7.8 vs 7.6. One item's two orders differ by more than 1: all-at-once milestone_quality, 2 vs 4.

| Item | incremental | all-at-once | Per order (inc AB,BA / aao AB,BA) | Iteration 8 (inc / aao) |
|---|---|---|---|---|
| rl_soundness | **5** | 3.5 | 5,5 / 3,4 | 5 / 3.5 |
| stage_completeness | **5** | 3 | 5,5 / 3,3 | 5 / 4.5 |
| internal_consistency | 3 | **3.5** | 3,3 / 3,4 | 3 / 3 |
| right_sizing | 3 | **4** | 3,3 / 4,4 | 3 / 3.5 |
| milestone_quality | **3.5** | 3 | 4,3 / **2,4** | 4.5 / 3 |
| pipeline_clarity | 3.5 | **4** | 4,3 / 4,4 | 3.5 / 4 |
| interface_quality | **4** | 3.5 | 4,4 / 3,4 | 4 / 3 |
| dependency_graph_soundness | 4 | 4 | 4,4 / 4,4 | 3.5 / 3 |
| task_buildability | **3.5** | 2.5 | 3,4 / 2,3 | 3.5 / 2.5 |
| organization | 4 | 4 | 4,4 / 4,4 | 4 / 4 |
| readability_for_solo_learner | 3.5 | **4** | 3,4 / 4,4 | 3.5 / 4 |
| ease_of_finding_next_build_step | 4 | 4 | 4,4 / 4,4 | 3.5 / 4 |
| layout_sensibility | 3.5 | **4** | 4,3 / 4,4 | 4 / 3.5 |
| content / structure | 3.85 / 3.8 | 3.45 / 4.0 | | 3.9/3.8 · 3.35/3.9 |
| **overall** | **7.65** | 7.45 | 7.7, 7.6 / 7.1, 7.8 | 7.7 / 7.25 |

**quant.** Incremental 7.7, all-at-once 7.45. Again each order was won by its Set A: AB went to incremental 7.8 vs 7.1, BA went to all-at-once 7.8 vs 7.6. No item's two orders differ by more than 1.

| Item | incremental | all-at-once | Per order (inc AB,BA / aao AB,BA) | Iteration 8 (inc / aao) |
|---|---|---|---|---|
| quant_soundness | **4.5** | 4 | 5,4 / 4,4 | 4.25 / 3.5 |
| null_hypothesis_handoff | 5 | 5 | 5,5 / 5,5 | 5 / 4.25 |
| reference_use | **4.5** | 3 | 5,4 / 3,3 | 4 / 4 |
| stage_completeness | 3 | **3.5** | 3,3 / 3,4 | 4.75 / 4 |
| internal_consistency | 3 | **3.5** | 3,3 / 3,4 | 3.25 / 3 |
| right_sizing | 3 | **3.5** | 3,3 / 4,3 | 3 / 3.75 |
| milestone_quality | **4** | 3.5 | 4,4 / 3,4 | 3.25 / 2.5 |
| pipeline_clarity | 4 | **4.5** | 4,4 / 4,5 | 4.75 / 4 |
| interface_quality | 3.5 | **4** | 4,3 / 4,4 | 4.25 / 3.5 |
| dependency_graph_soundness | 4 | 4 | 4,4 / 4,4 | 4 / 4.25 |
| task_buildability | 3.5 | 3.5 | 4,3 / 3,4 | 3.75 / 3.25 |
| organization | **4** | 3.5 | 4,4 / 3,4 | 4 / 4 |
| readability_for_solo_learner | **3.5** | 3 | 3,4 / 3,3 | 3 / 4 |
| ease_of_finding_next_build_step | 4 | 4 | 4,4 / 4,4 | 3.75 / 4 |
| layout_sensibility | 4 | 4 | 4,4 / 4,4 | 4.25 / 3 |
| content / structure | 3.8 / 3.9 | 3.8 / 3.65 | | 4.0/3.8 · 3.65/3.8 |
| **overall** | **7.7** | 7.45 | 7.8, 7.6 / 7.1, 7.8 | 7.8 / 7.45 |

## Findings

### J1. No mode winner: a tie within position bias

The per-order margins split into a mode part and a position part. The mode part is the mean of incremental's margin over the two orders. The position part is half the difference between them.

| | inc − aao, AB | inc − aao, BA | Mode effect | Position effect (for Set A) |
|---|---|---|---|---|
| rl, iteration 9 | +0.6 | −0.2 | **+0.2** | **0.4** |
| quant, iteration 9 | +0.7 | −0.2 | **+0.25** | **0.45** |
| rl, iteration 8 | +0.7 | +0.2 | +0.45 | 0.25 |
| quant, iteration 8 | +0.5 | +0.3 | +0.35 | 0.15 |

- **The bias is in the scores, not just the pick.** Set A got 7.7–7.8 and an output_quality of 8 in all four verdicts. Set B got 7.1 (6) when it was all-at-once and 7.6 (7) when it was incremental.
- **Incremental leans ahead by the same small amount in both projects.** But in each project the mode effect is about half the position effect, and the winner flips with order. Read it as a tie.
- **Iteration 8's two-order win did not repeat.**

### J2. What each set was cited for

The judge's defect lists are stable across orders: each set gets the same defects whichever position it is in. Only the weighting moves. In rl BA the judge said all-at-once wins "on plan quality" while incremental's design "fits the user's stages and RL lessons better". In AB, the same trade-off went the other way.

**rl incremental.**
- Credited:
  - Faithful to the scenario: circular tank, survival-time score, one learning predator, opponent pool with a cross-play table.
  - Concept ladders: tabular → DQN → CNN, and REINFORCE → PPO.
  - Checkable golden numbers (GAE 1.3775).
  - Frozen observation layouts.
- Cited:
  - M1 is the whole of S1 in 31 tasks, not a walking skeleton.
  - M1-T05 "DQNAgent spine (MLP, memory, target copy)" is sized XS.
  - M2 and M3 have no Exit.
  - PL-01's step table lists FishTank, PredatorPrey and OpponentPool steps that the entry never calls.
  - Stale brief and process narration in the architecture: AD-09 "adopted before M1 is built"; "TC-01–TC-49 don't change".
  - M1-T06's packet lacks core.Transition.
  - M1-T26 and M1-T27 both thicken the DQN agent.

**rl all-at-once.**
- Credited:
  - A check-world gate: a two-exit corridor with a hand-derived Q*.
  - Honest minimal spines: online Q-learning, and REINFORCE as the PPO spine.
  - Four milestones, each with an Exit.
- Cited:
  - Square tank (FISH-01), score of hits per fish with respawn (FISH-04), 2 predators (PREY-01), and no opponent pool.
  - M2 "See, check and explain the snake" is a leftover milestone.
  - M1's "tested verdict" doesn't require the snake to beat the baselines.
  - The snake observation layout is never frozen, so M1-T15 SnakeRule is unbuildable.
  - M1-T28 and M1-T29 don't list `charts/curve.py` in Writes.
  - Stale Open questions in pipelines.md.

**quant incremental.**
- Credited:
  - Marchenko–Pastur bands, per-window PCA, synthetic known-answer gates.
  - LightGBM permutation gain in S3.
  - A Yahoo cross-check plus CHECK-09 on the user's 10 delisted names.
  - RF-01/02/03 placed on milestones.
  - CONSTRAINTS.md present, and a vertical M1.
- Cited:
  - PPO agents dropped from S4 and the rented GPU ruled out.
  - yfinance used although probe PB-03 showed it failing.
  - No golden cases in qdata, qserver or explorer.
  - Spines labelled "Kind: thicken".
  - Three interface tasks that import from each other.
  - A $49 Sharadar line counted against the $50 budget.

**quant all-at-once.**
- Credited:
  - Covers all of S4: forecasters, PPO under a 20-configuration budget, GPU bundles.
  - A shared walk-forward engine with a ledger and lockbox.
  - 27 golden cases in M1.
  - One interface task for all three packages.
- Cited:
  - No yahooquery cross-check and no use of the 10 names.
  - **CONSTRAINTS.md missing**.
  - Roadmap M4–M8 have no References lines.
  - S3 tests by rank correlation only.
  - M2 holds 16 pipelines while M5 holds two.

**Spot checks against the docs.** Real unless noted.
1. **rl all-at-once fact drift is real.**
   - The spec has "FISH-01 The tank is a square with walls", "FISH-04 … hits per fish per episode (lower is better)" and "PREY-01 … 6 prey, 2 predators".
   - Turn 1 of `rl-all-at-once/with_skill/turns.json` gave all three facts correctly ("a circular tank…", "survive as long as possible", "a learning predator"). The run lost them; the mode didn't withhold them.
   - Incremental's spec has "FISH-01 The tank is a circle of radius 1" and survival-time rewards.
2. **rl all-at-once M2 leftover milestone is real.**
   - M2's Outline is viewer and video, reference check, write-up, and "the trained snake clearly beats both baselines".
   - That matches the rubric's own example of a leftover milestone ("replays + reference").
   - The AB judge scored it 2. The BA judge praised "four milestones, each with a checkable Exit" and scored it 4, so the one order disagreement is the BA judge missing a rubric-named defect.
3. **quant incremental has no data-stage golden cases: real.**
   - qdata, qserver and explorer `tests.md` hold 0 TC IDs. qdata says "No golden cases yet … (assumed: none for M1)".
   - All-at-once's data `tests.md` has 24.
   - Only the BA judge caught this. The AB judge gave incremental quant_soundness 5 and task_buildability 4.
4. **quant incremental PPO and GPU cut: real.** spec.md lines 22–23: "Learned allocation agents (a later stage…)" and "Cloud compute; every model trains on the user's machine". The scenario has PPO in S4 and an "occasional rented GPU".
5. **quant all-at-once Yahoo cross-check: real.** No final doc in set-2 mentions Yahoo, and LEH/BSC never appear in the spec. The grader agrees (`crosscheck_facts_reached_design`: "no probe of the Yahoo cross-check").
6. **quant all-at-once "M4–M8 have no References or Skills lines": mostly real.**
   - Skills sit on the stage headings (S2–S4), not the milestones. No References line routes RF-01..03 anywhere in the roadmap.
   - `build-planning/references/cut.md` requires a Skills and a References line on each milestone when a stage is split.

### J3. quant all-at-once was truncated, and the judge saw it

- The run stopped at max_turns 50, against 150 for incremental, which finished at turn 58.
- The plan was approved at turn 48–49. build-setup got only turn 50 (10 s, nothing changed). So the project has no CONSTRAINTS.md, `pyproject.toml`, `scripts/` or `.claude/agents`.
- The judged set-2 lacks only `final__CONSTRAINTS.md`; every other planning doc and all 48 packets are complete.
- Both orders cited it:
  - **AB:** as a weakness, and M1-T37 unbuildable.
  - **BA:** "M1-T01..M1-T48: every packet says to read CONSTRAINTS.md".
- **Impact:** likely task_buildability (3 in AB) and internal_consistency (3 in AB). One content item moves the overall by about 0.045 per point (the mean of 11 items). Even a full point on two items, about 0.18, is below the 0.25 margin and far below the 0.45 position effect.
- So truncation cost all-at-once a little but doesn't decide anything.
- The grader also marks quant all-at-once `finished` and `plan_docs_approved` false.
- frozen_interface_churn = 0 is meaningless here: the interface froze at turn 49.

### J4. The judge band holds, and dependency_graph_soundness has gone flat

`judge_within_1` is ok in both projects:
- **rl:** interface_quality Δ −0.5, dependency_graph_soundness Δ 0, task_buildability Δ −1.0 (at the edge).
- **quant:** +0.5, 0, 0.

The interface_quality deltas come from position: rl all-at-once scored 3 then 4, quant incremental 4 then 3. dependency_graph_soundness was 4 in all eight scorings (iteration 8 ranged 3–4.5), so this iteration it measures nothing. That's despite real graph defects the judges named:
- rl incremental: M1-T26 and M1-T27 both edit the DQN agent.
- quant incremental: three interface tasks that import from each other.
- quant all-at-once: system tasks with no allowed edge kind (grader `unmitigated_reasoned` fails).

### J5. Against iteration 8

- **rl margin 0.45 → 0.2.**
  - Incremental is flat (7.7 → 7.65): milestone_quality 4.5 → 3.5 (M1 is the whole of S1; M2 and M3 have no Exit), dependency_graph_soundness 3.5 → 4.
  - All-at-once rose 7.25 → 7.45. It stayed single-package this time ("Single package"; iteration 8's F14 multi-package detour is gone). That lifted interface_quality 3 → 3.5, dependency_graph_soundness 3 → 4 and right_sizing 3.5 → 4.
  - But stage_completeness fell 4.5 → 3 from the fact drift in J2. rl_soundness stays 3.5 for a new reason: iteration 8 was "no reward defined", iteration 9 is drift.
- **quant margin 0.35 → 0.25.**
  - Incremental 7.8 → 7.7: stage_completeness 4.75 → 3 (PPO and GPU cut), interface_quality 4.25 → 3.5, pipeline_clarity 4.75 → 4. It gained on milestone_quality (3.25 → 4) and reference_use (4 → 4.5).
  - All-at-once is flat at 7.45 with a different mix:
    - **Gains:** milestone_quality 2.5 → 3.5, because M1 is now vertical through data, server and app, which fixes iteration 8's layer cut. Also quant_soundness 3.5 → 4, null_hypothesis_handoff 4.25 → 5, layout 3 → 4.
    - **Losses:** reference_use 4 → 3 (no RF lines), readability 4 → 3, stage_completeness 4 → 3.5 (yahooquery and the 10 names dropped), organization 4 → 3.5 (partly the missing CONSTRAINTS.md).
- **Position bias roughly doubled** (0.25/0.15 → 0.4/0.45) while the mode effect halved. Both projects are now inside the noise.

## Mode comparison (`mode_delta.json`)

| Band | rl inc / aao | quant inc / aao |
|---|---|---|
| N/CP within 20% | 7.75 / 7.5 (3%): ok | 7.67 / 8.0 (4%): ok (iteration 8: out) |
| max width within 1 | 19 / 17: **out** | 27 / 27: ok (iteration 8: 26/17, out) |
| interface_coverage, types_in_contract, writes_disjoint pass in both | **out**: types and writes fail in aao | **out**: types and writes fail in both |
| judge within 1 | ok | ok |
| frozen_interface_churn (aao ≤ inc) | 0 ≤ 26: ok | 0 ≤ 11: ok (vacuous) |

What explains each miss, and whether it's a mode effect:

- **rl max width (19 vs 17): a milestone-cut difference. The all-at-once side of it is a defect.**
  - Incremental's M1 holds all of S1. Its wave after the interface has 11 spines plus 8 folded steps marked "fold: spine is the whole behavior", run as tester halves.
  - All-at-once's has 14 spines plus 3.
  - Incremental's M1 includes M1-T07 train_reference, M1-T08 ReferencePlayer and M1-T20 replay viewer. All-at-once moved those into its leftover M2 (J2 check 2). Without them incremental would be 16.
  - So the gap is not interface-first behaviour. It traces to all-at-once's leftover M2, a defect in how build-planning cut the stage.
- **rl must-pass checks.**
  - **types_in_contract (all-at-once): a grader false positive.**
    - It flags `core.TeamSpec: Direction`, `core.WorldSpec: Direction`, `methods.MethodConfig: Settings` and `train.RunConfig: Settings`.
    - These are defined as aliases on contract.md line 5: `` `Direction = Literal["higher", "lower"]`, `Settings = Mapping[...]` … are used throughout ``.
    - `dtrun.defined_in("Direction", <that line>)` returns True. But grade.py builds `contract_text` only from symbol sections, so the preamble above `## core` is never searched.
  - **writes_disjoint (all-at-once): a real defect.**
    - M1-T08 "DQN spine" also writes `src/rllab/methods/factory.py` ("Reason: also builds the methods factory").
    - M1-T09 "train_loop spine" also writes `src/rllab/runlog/writer.py` ("also builds runlog.RunWriter").
    - Two contract owners got no spine of their own and were folded into neighbouring spines. That's the iteration-8 F11 class, not a mode effect.
  - Incremental passes all three checks.
- **quant must-pass checks: both modes fail both checks, so there's no mode differential. Most of it is grader regex gaps.**
  - **types_in_contract, incremental (8 flags):**
    - CompanyMsg, ActionMsg, DayDiffMsg, CheckCountsMsg and ScoreRowMsg are each defined as "mirrors `qdata.query.Company`", "mirrors one `qdata.query.Actions` row", "mirroring `DayDiff`" and so on. `defined_in` returns False on all of them (tested): its mirror regex accepts only a two-part `pkg.Type` path, not "mirrors one…" or "mirroring".
    - `Element` and `DuckDBPyConnection` are library types.
    - `StagedRun` is defined in a code comment.
    - Partly real: the AB judge says M1-T31's packet gives CompanyMsg and ActionMsg only as "mirrors…", with no fields.
  - **types_in_contract, all-at-once (4 flags):** BarSchema, ActionSchema and VendorRowSchema have full field notes (`` - `BarSchema`: index `date`; `open, high, …: float64` ``), but the backtick after the name defeats the `Name:` pattern (tested False). `NaN` is a value, not a type. All false positives.
  - **writes_disjoint, incremental:** M1-T25 (design.theme) also writes `tokens.css`, and M1-T36 (api.schema) also writes `schema-tools.ts`. These are asset or helper files in the owner's own folder. Borderline.
  - **writes_disjoint, all-at-once:** M1-T06 (ingest.fetch) writes `store/parts.py`, which is real (another module). M1-T22 writes `routes/errors.py` and M1-T26 writes `no-dataset.tsx`, both borderline helpers. M1-T02 has an unknown owner.
- **frozen_interface_churn: as expected, and the all-at-once side is structural.**
  - **rl incremental (26):** the revisions in the evidence list all fall at turn 21 (core.Env, core.Agent, core.StepResult, agents.DQNAgent…): S2's team-keyed revision rippling into M1's frozen interface. The judge saw it too ("The teams revision ripples into M1"). This is the expected incremental cost.
  - **quant incremental (11):** revisions at turns 28 and 39.
  - **All-at-once 0 is vacuous:** rl froze at turn 14 of 16, and quant at turn 49 of 50.

**Grader fixes these suggest:**
- Add the contract preamble to `contract_text`.
- `defined_in`: accept `` `Name`: `` field notes, `pkg.module.Type` mirror paths, "mirrors one X row" and "mirroring".
- Skip library types (`Element`, `DuckDBPyConnection`) and the value `NaN`.

With those fixed, rl types would pass in both modes and quant types would be close. The writes failures in rl all-at-once and in quant all-at-once (M1-T06) remain real F11-class defects.

**Two side observations:**
- `skills_invoked` reports idea-refine missing for both all-at-once runs, but quant all-at-once's run log has session 1 as idea-refine (turns 1–3), and rl all-at-once's turn 1 opens with `/dev-team:idea-refine`. This may be a grader miss on slash-command invocations. Not checked further.
- quant all-at-once's cap of 50 turns is a third of incremental's 150, and was too tight this iteration.
