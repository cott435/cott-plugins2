# Iteration 7: blind judge and mode comparison

**Judge:** `claude -p --model claude-opus-5-5` (Opus 5.5, the agent's model; iteration 6 didn't record its judge model). Each order ran as its own fresh session with `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, `--setting-sources project`, and only Read, Glob, Grep and Write, from a neutral scratch folder. Four sessions (rl and quant, AB and BA) cost $10.60 in total and took 3–5 minutes each. Prompts came from `judge_prompt.py --both` with labels `incremental all_at_once`, and `judge_prompt.py average` combined the two orders. Files: `judge-rl.json`, `judge-quant.json` and `mode_delta.json` here and in `dev-team-workspace/iteration-7/`.

**Blinding.** The README's command gives the judge `bench/eval-*/<mode>/run-1/outputs` paths, which name the mode. Those folders also hold `transcript.md` and `doc_evolution.md`, and the prompt says "Read every file". To keep the judge blind, each `outputs/` folder was copied without those two files to `set-1` (incremental) and `set-2` (all-at-once), and the prompts point at those copies. No prompt contains a mode word. See H1 below.

## Scores (averaged over both orders)

**rl.** 7.3 incremental against 7.2 all-at-once. Set A won both orders: incremental won AB and all-at-once won BA.

| Item | incremental | all-at-once | Per order (inc / aao) |
|---|---|---|---|
| rl_soundness | **5.0** | 3.0 | 5,5 / 3,3 |
| stage_completeness | 3.0 | **4.0** | 3,3 / 4,4 |
| internal_consistency | **3.0** | 2.5 | 3,3 / 2,3 |
| right_sizing | 3.0 | **3.5** | 3,3 / 3,4 |
| milestone_quality | 3.0 | **4.0** | 3,3 / 4,4 |
| pipeline_clarity | **4.0** | 3.0 | 4,4 / 3,3 |
| interface_quality | **4.0** | 2.5 | 4,4 / 2,3 |
| dependency_graph_soundness | 2.5 | **4.0** | 3,2 / 4,4 |
| task_buildability | **4.0** | 2.5 | 4,4 / 2,3 |
| organization | 4.0 | 4.0 | |
| readability_for_solo_learner | 3.0 | **4.0** | |
| ease_of_finding_next_build_step | 4.0 | 4.0 | |
| layout_sensibility | 4.0 | 4.0 | |
| content / structure | 3.5 / 3.8 | 3.2 / 4.0 | |
| **overall** | **7.3** | **7.2** | 7.4, 7.2 / 7.0, 7.4 |

**quant.** 7.95 incremental against 8.15 all-at-once. Set A won both orders again: incremental won AB and all-at-once won BA.

| Item | incremental | all-at-once | Per order (inc / aao) |
|---|---|---|---|
| quant_soundness | **5.0** | 4.5 | 5,5 / 4,5 |
| null_hypothesis_handoff | 5.0 | 5.0 | |
| reference_use | 3.5 | **4.0** | 4,3 / 4,4 |
| stage_completeness | **4.0** | 3.0 | 4,4 / 3,3 |
| internal_consistency | 3.0 | **3.5** | 3,3 / 3,4 |
| right_sizing | 3.0 | **4.0** | 3,3 / 4,4 |
| milestone_quality | **4.0** | 3.5 | 4,4 / 4,3 |
| pipeline_clarity | **5.0** | 4.0 | 5,5 / 4,4 |
| interface_quality | **4.0** | 3.5 | 4,4 / 3,4 |
| dependency_graph_soundness | 4.0 | 4.0 | |
| task_buildability | **4.0** | 3.5 | 4,4 / 3,4 |
| organization | 4.0 | 4.0 | |
| readability_for_solo_learner | 3.0 | **4.0** | |
| ease_of_finding_next_build_step | 4.5 | **5.0** | |
| layout_sensibility | 4.0 | 4.0 | |
| content / structure | 4.05 / 3.9 | 3.85 / 4.3 | |
| **overall** | 7.95 | **8.15** | 8.1, 7.8 / 8.0, 8.3 |

- **No order disagreements.** No item's two scores differ by more than 1. But the set shown as A won every verdict, by about +0.3 overall (rl 7.4 against 7.1, quant 8.2 against 7.9). Both margins (0.1 and 0.2) are smaller than that bias, so read both projects as ties.
- **Quant was not blocked.** The iteration-6 blocker (S3: all-at-once had no Designed milestones after M1) has a new form here. Quant all-at-once has milestones only for S1 (M1, M2); S2–S4 are Specced, and the eval, ml and paper packages have no pipelines. Incremental has M1–M6 across every stage. Both modes have a planned M1, so the M1-level items (interface, graph, buildability) still compare like for like; the scope gap shows as stage_completeness 3 against 4. rl has the mirror image: incremental has milestones only for S1 because the run stopped `stalled: roadmap has 2 rows for 3 stages`, while all-at-once has M1–M5.

## Defects the judge quoted

Both orders found these; quotes are from the docs.

**rl incremental**
- `tasks/plan.md`: "M1-T10 evaluate spine | M1-T02 corridor | code | none: evaluation plays real episodes" is false serialization. T11, T12 and T13 do the same, e.g. "M1-T13 train_agent spine … Depends on: M1-T09, M1-T10, M1-T02, M1-T05". The spines could run on the interface samples. This drives dependency_graph_soundness 2.5.
- `roadmap.md`: S2 and S3 are "Designed" with no milestone row, so they have no Depends or Exit.
- `CONSTRAINTS.md`: "CR-14 Only `dqn` imports PyTorch (AD-04)" contradicts AD-04, which now allows dqn, pg and selfplay. The Boundaries line omits tank, forage, pg, selfplay and xplay.
- `brief.md`: success covers "Snake:" only, though the spec spans three environments.
- `tasks/plan.md`: "`gridlab train ... --smoke` runs end to end", but no task defines or owns `--smoke` (M1-T19). No task writes the "built-in sample recording" that M1-T20 opens.
- `tasks/plan.md`: M1-T03 is sized XS but covers "SNAKE-01–SNAKE-09, SNAKE-14, SNAKE-15, CORE-01–CORE-04, CORE-08, QR-03".
- `architecture.md`: "The contract is about 600 lines, over the 200-line ceiling". AD-10 keeps the history of superseded decisions. In tests.md, TC-48 sits between TC-39 and TC-40.
- Unbuildable: M1-T13's packet has no `evaluate.evaluate` signature and no EvalResult. M1-T03's packet lacks the coordinate and action conventions its TCs assume.

**rl all-at-once**
- `contract.md`: "RunConfig: … world: WorldSettings; learners: dict[str, LearnerSettings | PolicyRef]". WorldSettings, LearnerSettings, DQNSettings and PPOSettings are never defined. This drives interface_quality 2.5 and task_buildability 2.5.
- `contract.md` core.StepResult: "done: dict[str, bool]". There is no terminated/truncated split, so the hunger limit (SNAKE-06) and the 1,000-step limits (TANK-08, PREY-08) can't bootstrap correctly. This drives rl_soundness 3.
- `pipelines.md` PL-04: "`build_comparison` | evaluate.compare | ScoreReport → ComparisonTable" doesn't match the contract's "`def build_comparison(runs: Sequence[RunDir], baselines: Sequence[PolicyRef])`". reference_check, write_note and world_status disagree the same way. The sketch's "score_policies(runs, config.baselines)" uses a field RunConfig doesn't have.
- `pipelines.md` Open questions: "Contract Revise needed before approval … add evaluate.EvaluationDir, …" is stale; the contract already has these types and is Approved.
- `tasks/plan.md`: "M1-T18 Snake world … Depends on: M1-T05" is false serialization, and so are T19→T09 and T20→T10. M1-T19 writes `baselines/make.py`, which is not in the layout.
- `roadmap.md`: "| S2 | Fish tank escape | brief | Cut |" while M3–M5 for those stages read Designed (see H2).
- Unbuildable: M1-T18 has no set_state hook for the golden-case bodies. M1-T09 uses the undefined WorldSettings and can't inject the ParallelEnv fake. M1-T24's learners.load_policy has no M1 owner. M1-T08 needs make_policy("reference:…"), which nothing implements.

**quant incremental**
- `architecture.md` Dependency rules: "Research packages depend on `data` alone." The next bullet and AD-18 contradict it; AD-01 and data/architecture.md repeat it.
- `tasks/plan.md` M1-T38: "serves the version T41 built". No T41 exists (it should be M1-T37), and the stale ID is also in the graph.
- `builder/tests.md` TC-04: "(convention pending the contract change in data's Open questions)"; AD-16 already settled it.
- `tasks/plan.md`: M1-T02 has "Depends on: —", though builder.BuildError extends data.DataError from M1-T01.
- `references.md`: "Milestones: S2" and "S4" name stages rather than the milestones M3 and M5 that serve them.
- `roadmap.md`: the user's single stage 4 is split into S4 and S5. M2 has no Exit line. M1 defers WebSocket progress to M2.
- Unbuildable: M1-T09, M1-T02 and M1-T18 name schemas (SecuritySchema, ReturnSchema and others) with no columns. M1-T38 points at T41.

**quant all-at-once**
- `roadmap.md`: S2–S4 are "Specced" with no milestones or pipelines, "so the plan stops at stage 1".
- `server/pipelines.md`: the get_flags and get_coverage routes have no data API behind them (data.Loader has no flags or coverage method), so that boundary has no type.
- `web/pipelines.md`: "charts/ ECharts wrappers, palette, themes" is a module no task writes. There is no design-direction task before the six view spines.
- `data/architecture.md`: the layout "packages/data/src/data/{source,...,cli}/" and "packages/data/tests/" contradicts pipelines.md's flat modules and root tests/intent/data/.
- `research/pipelines.md`: "The contract says `run_eda(loader)`, but the entry takes `as_of`" is left open.
- `data/contract.md` Membership: "495 ≤ members per date ≤ 510" is a data-quality bound used as a type invariant; a 3-date contract sample can't satisfy it.
- `tasks/plan.md`: M1-T17 is a research spine attached to "Step: PL-13.mount_dataset_routes". M1-T33 is labelled package data but writes server and web files. M1-T01's acceptance names runs.emit, which is not in the contract.
- Unbuildable: M1-T13 lacks the response models (UniverseResponse, StockMatch, StockHistory, FlagsPage, Coverage). M1-T19 has no HTTP paths and an unowned web.charts. M1-T05 has no Sharadar column layout. M1-T06's oracle TC-01 skips without a real download.

## Mode delta (mode_delta.json)

| Band item | rl inc | rl aao | rl | quant inc | quant aao | quant |
|---|---|---|---|---|---|---|
| N/CP (\|Δ\| ≤ 20% of larger) | 3.67 (22/6) | 5.2 (26/5) | **out**, 29% | 6.33 (38/6) | 4.25 (34/8) | **out**, 33% |
| Max wave width (\|Δ\| ≤ 1) | 8 | 16 | **out**, Δ 8 | 21 | 19 | **out**, Δ 2 |
| interface_coverage / types_in_contract / writes_disjoint | fail / pass / fail | pass / pass / fail | **out** | fail / pass / fail | fail / pass / fail | **out** |
| Judge interface_quality (Δ ≤ 1) | 4.0 | 2.5 | **out**, −1.5 | 4.0 | 3.5 | in, −0.5 |
| Judge dependency_graph_soundness (Δ ≤ 1) | 2.5 | 4.0 | **out**, +1.5 | 4.0 | 4.0 | in, 0 |
| Judge task_buildability (reported) | 4.0 | 2.5 | −1.5 | 4.0 | 3.5 | −0.5 |
| frozen_interface_churn (expect aao ≤ inc) | 21 | 0 | as expected | 0 | 0 | as expected |

- rl: parallelism, max width, must-pass checks and judge are all out of band. quant: parallelism, max width and must-pass checks are out; the judge is in band.
- **`writes_disjoint` fails all four runs** because every spine also writes its own unit test, e.g. "M1-T08 (owner experiments.build): src/gridlab/experiments/build.py, tests/unit/gridlab/test_build.py". There are 0 real conflicts in every run, and the README's rule allows "its unit test", so this looks like a grader false negative, not a mode difference. It alone keeps both_pass_coverage_types_writes out of band for both projects.
- **The max-width band is absolute.** On quant, widths of 21 and 19 miss it by a difference of 2; a 1-task band is strict at that width.

## What the two modes do differently

- **rl.** All-at-once froze one interface for the whole roadmap. Incremental froze it at turn 13 and revised it 21 times at turn 19 (core.Agent, core.Env, core.Frame and others) when the later stages arrived; that churn is the expected cost of incremental. All-at-once gets the wider, shallower M1: 16 spines ready after the interface task, 0 no_edge_to_code_when_interface violations against incremental's 10, and judge dependency_graph_soundness 4 against 2.5. But its contract is thinner: undefined settings types, step tables that disagree with the contract, and no termination split. That costs it interface_quality, task_buildability and rl_soundness. Incremental's contract is complete (interface_quality 4) but its graph makes the spines wait on library tasks. No grader check catches all-at-once's undefined types (H3).
- **quant.** Incremental designs every stage down to pipelines and M1–M6: 9 packages, 35 pipelines, about $45.5. All-at-once stops at S1's milestones: 7 packages, 14 pipelines, about $19. Incremental's M1 is wider (N/CP 6.33 against 4.25). All-at-once's M1 has a serialized validate.py thicken chain T29→T30→T31→T32, which makes its critical path 8. The judge prefers all-at-once's readability and size (right_sizing 4 against 3, readability 4 against 3) and incremental's completeness and rigour (stage_completeness, pipeline_clarity, quant_soundness).
- **Both projects.** Whichever mode milestoned every stage scored higher on stage_completeness: rl all-at-once and quant incremental. In rl the other mode's run stalled; in quant it stopped at Specced.

## Against iteration 6 (rl)

| | Iter. 6 aao | Iter. 7 aao | Iter. 6 inc | Iter. 7 inc |
|---|---|---|---|---|
| Overall | 8.0 | 7.2 | 7.9 | 7.3 |
| milestone_quality | 2 | **4.0** | 3 | 3.0 |
| pipeline_clarity | 5 | 3.0 | 4 | 4.0 |
| task_buildability | 3 | 2.5 | 3 | 4.0 |
| rl_soundness | 5 | 3.0 | 5 | 5.0 |

- **milestone_quality for all-at-once rose from 2 to 4.** The S1 leftover milestone is gone: M1 is a walking skeleton over every S1 pipeline, and M2–M5 have Depends cells. The judge called it "the better roadmap". Incremental stays at 3 because S2 and S3 got no milestones before the run stalled.
- **Overall scores are not directly comparable.** Iteration 6 was one shuffled order, scored before interface_quality and dependency_graph_soundness joined the rubric; iteration 7 averages two orders. The roughly 0.7 drop in both modes comes mainly from the two new items (2.5 each in rl) and from all-at-once's contract gaps. It is a tie again, now in incremental's favour by 0.1.

## Harness notes

- **H1. The README's blind-judge command is not blind.** It passes bench/…/<mode>/run-1/outputs, so the mode is in the prompt's paths, and package.py puts transcript.md and doc_evolution.md in outputs/ while the prompt says to read every file. A fix is for judge_prompt.py to copy each folder to a neutral path without those two files, or for package.py to keep them outside outputs/. Separately, judge_prompt.py --both crashes writing the key file when the output JSON's folder doesn't exist; it should create it.
- **H2. dt's stage status "Cut" reads as "dropped".** roadmap.py derives "Cut" for a stage whose milestones are all below Planned. Both judges read it as removed scope and docked internal_consistency, in rl all-at-once and quant incremental. A clearer word, such as "Split", would avoid this.
- **H3. types_in_contract misses undefined field types.** It resolves only the CapWords names in step-table In → Out cells, so rl all-at-once passes although RunConfig's fields use four types that are never defined.
- **H4. Position bias.** Set A won all four verdicts by about +0.3. With n=1 per mode, an averaged margin under about 0.3 is a tie.

## The three most important quality defects

1. **rl all-at-once's contract is incomplete.** "RunConfig: … world: WorldSettings; learners: dict[str, LearnerSettings | PolicyRef]" uses WorldSettings, LearnerSettings, DQNSettings and PPOSettings, none of which is defined. The step tables disagree with the contract signatures (build_comparison, reference_check, a nonexistent config.baselines). Packets M1-T02, T09 and T24 are unbuildable, and the grader doesn't see it (H3).
2. **rl incremental's spines are falsely serialized.** "M1-T10 evaluate spine | M1-T02 corridor | code | none: evaluation plays real episodes", and T11–T13 do the same, so the spines wait on library and real-env tasks instead of the interface samples. It matches the grader's 10 no_edge_to_code_when_interface violations and gives a max width of 8 against all-at-once's 16.
3. **Later stages are left without milestones.** rl incremental's S2 and S3 are "Designed" with no milestone row, and the driver stopped `stalled: roadmap has 2 rows for 3 stages`. Quant all-at-once's S2–S4 are "Specced" with no pipelines or milestones, so "the plan stops at stage 1". It is the iteration-6 S3 gap in a new form.

Also notable: rl all-at-once's StepResult has only `done` (no terminated/truncated split), so time limits can't bootstrap. In quant, both modes' packets name schemas and response models without their fields (M1-T09, M1-T13).
