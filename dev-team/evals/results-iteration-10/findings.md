# Iteration 10: requests, new lints, fix-plan groups 0–5, a fresh session per skill run

## Run conditions

- **Plugin:** dev-team 0.5.0 plus fix-plan groups 1–5, branch `interface-first-design` at `135dbca`, staged at the start of each run on 2026-10-18. This covers:
  - `docs/requests.md` (the user's words, verbatim, traced; `dt request`), the request lints and `dt explain`;
  - the plan-review lints (`packet-type-closure`, `milestone-lines`, `milestone-order`, `exit-cases-in-scope`, `kind-title`, `covers-vs-deferred` and others) and packet closure in `dt context`;
  - group 2 (design: shared test helpers, unchained system tasks, approvals in phase 0), group 3 (skills), group 4 (`dt next` test-planning scope, `scripts/dt`, `spine-claim`).
- **Harness:** the same commit. Group 0 (driver: a fresh session after every approved gate, approvals without "continue", sim-user retries, fake Sharadar's SDK header, user runs as the README gives them, quant all-at-once `max_turns` 70), group 1 (grader fixes, with iterations 8 and 9 regraded in `../results-iteration-9/regrade/`), group 5 (plan map R6, R9) and the judge's score anchors and `--repeats`.
- **Models:** Opus 5.5 agent, Sonnet simulated user, Opus 5.5 blind judge, 3 repeats in both orders.
- **Scope:** n=1 per trajectory, no cost cap. Raw runs in `dev-team-workspace/iteration-10/`, packaged in `bench/` there.
- **Before the run:** 560 dt tests, `check.py` 7/7 (dev-team) and 8/8 (workflow-analyzer), the grader selftest 201/201, `dryrun.py` as pinned. A 10-turn quant all-at-once smoke run (`dev-team-workspace/smoke-11/`, $6.96): four sessions, each carrying the last reply on; `skills_invoked` saw every skill that ran; 52 requests recorded and traced; `dt lint` clean.

**Flow pages:** [runflow/index.html](runflow/index.html), each run against iteration 9 (`runflow/<traj>-vs-iteration-9.html`), and each run's `<traj>/with_skill/flow/flow.html` and `flow/plan/M1.html`.

## Results

| Run | Checks (iteration 9 regraded) | Turns (it9) | Agent cost (it9) | Wall clock | Sessions (it9) | M1: N / CP / widest | Stop |
|---|---|---|---|---|---|---|---|
| rl incremental | 66/70 (67/67) | 69 (36) | $37.85 ($24.46) | 127 min | 30 (1) | 20 / 6 / 13 | finished |
| rl all-at-once | 71/77 (66/67) | 43 (16) | $29.63 ($14.80) | 107 min | 15 (3) | 23 / 4 / 18 | finished |
| quant incremental | 85/95 (85/92) | 138 (58) | $72.17 ($42.57) | 267 min | 45 (5) | 35 / 4 / 23 | finished |
| quant all-at-once | 52/84 (85/91) | 70 (50) | $33.39 ($35.23) | 112 min | 23 (13) | no plan | **max_turns** |

- **Total:** $173.04 for the agents (iteration 9: $117.06). Per turn it fell from $0.70–0.92 to $0.48–0.69, and the largest context in any call from 607k to 279k tokens. The rise is all turns.
- **Every skill run now has its own session** (15–45 per run; iteration 9 ran rl incremental in one). So this is the first iteration whose cost and context can be compared between modes, and the first to measure what fresh sessions cost.
- **The user's facts held.** `requests_captured`, `requests_honoured` and `requests_append_only` pass in all four runs (62–135 requests each). Every fact iteration 9 lost reached the design: rl all-at-once's circular tank (TANK-01), survival scoring (TANK-08), one learning predator (PREY-02) and self-play against past versions (POOL-01); quant's WebSocket and yahooquery in both modes.
- **Judge** (3 repeats × both orders; mean ± SD of a pair's overall). The judge prompt gained score anchors this iteration, so iteration 9 was re-judged with the same prompt and repeats (`baseline-it9/`); its published scores (7.65, 7.45, 7.7, 7.45) are on the old scale.

  | Run | Iteration 9, re-judged | Iteration 10 | Δ | Read as |
  |---|---|---|---|---|
  | rl incremental | 7.35 ± 0.20 | 6.20 ± 0.22 | **−1.15** | a real drop: the stale M1 (D4). interface_quality 3.5 → 2, task_buildability 2.8 → 2, ease_of_finding_next_build_step 4.2 → 2.2 |
  | rl all-at-once | 6.80 ± 0.33 | 7.03 ± 0.31 | +0.23 | a tie within noise, though task_buildability rose 2.7 → 4 and dependency_graph_soundness 2.8 → 3.8 |
  | quant incremental | 7.12 ± 0.08 | 7.58 ± 0.08 | **+0.47** | a real gain: stage_completeness 2.3 → 4 (the user's facts kept), dependency_graph_soundness 3 → 4, interface_quality 3 → 3.8 |
  | quant all-at-once | 6.88 ± 0.18 | 5.52 ± 0.06 | **−1.37** | truncation: no plan, so every plan item scores 1 |

  - A margin counts when it is at least 0.25 and over 2.5 × its SD (evals/README.md, Blind judge). The two drops are the two runs that broke (truncation, stale plan), and both have a named cause below. The two runs that finished cleanly gained or held.
  - Mode comparison: quant incremental wins all six verdicts (+2.07 ± 0.10, from all-at-once's missing plan). rl all-at-once wins five of six (+0.83 ± 0.36), where iteration 9 re-judged had incremental ahead (+0.55 ± 0.26).

## Iteration 10 against its bar

| Criterion | Result |
|---|---|
| All four finish, every stage has milestone rows in both modes | **Not met.** quant all-at-once hit 70 turns in pipeline-design Extend. It could not have finished: `dt next` held build-planning on "S1–S4 below Designed" because QR-04, a cost limit, is on no step (D1). |
| A fresh session per skill run; no answer lands in a session that didn't ask | **Met for sessions.** Answers mostly landed right; quant incremental's api-probe/build-planning bounce (turns 46–55, five sessions for one plan approval) is the exception (H3). |
| No check fails for a grader reason | **Not met:** `spec_classical`, `probe_not_guess`, `sim_ready_3`, part of `phase0_split` (G1–G4). |
| rl incremental M1 critical path ≤ 4, widest wave ≥ 12 | **Half:** widest 13, critical path 6. Its M1 is stale: an architecture Revise at turn 59 changed interfaces under an unbuilt, approved M1, and `dt next` ranked cutting S3 above replanning it (D4). |
| quant all-at-once critical path ≤ 5 | **n/a:** no plan. quant incremental's is 4. |
| Each quant run's probes run through the fakes, a planted fact reaches each design | **Not met.** No probe was ever Answered (H1, H2). |
| Mode delta in band; cost and context comparable | Cost and context are comparable now. The mode delta is dominated by quant all-at-once's truncation and rl incremental's stale M1. |

## Where the turns went

Turns rose from 250 to 320 (and quant incremental alone from 58 to 138). Per-skill turn counts in `summary.json` are by the skill a session *opened* with; a resumed session can run several skills, so read them with care.

1. **Route rounds in their own sessions: about 40–80 turns, all four runs.** pipeline-design drafts steps whose types the contract lacks (`step-io-types`: 41 errors at quant all-at-once turn 22), routes to architecture-design, which routes back to remove "not in the contract yet" notes; test-planning routes again. Each round is a fresh session, a draft turn and an approval turn. 84 turns sat in route-opened sessions, $40 of cost. In iteration 9 the same edits were folded into "approved, continue" turns.
2. **The probe loop: about 36 turns, quant only (H1–H3).**
3. **Fresh-session overhead:** 24 hand-off-only turns ("Next is X, say the word"), about 11 bare "continue" turns, 83 replies opening with "nothing to commit" (the gate asks "Shall I commit?" though the harness commits every turn), and decisions asked again by a new session (the package split, the probes). First turns of fresh sessions average 7–10 tool calls before the first write, resumed ones about 2.
4. **Smaller:** one question per turn where defaults exist (test-planning, build-setup: about 12 turns); quant all-at-once's optional test-planning for S2–S4 packages (about 20 turns with its routes, D2); rl all-at-once's package split (about 10, S3).

The new lints caused no separate fix turns: only two replies name one. `docs/requests.md` costs tool calls (27–87 `dt request` calls per run), not turns.

## Findings by owner

### Harness: driver
- **H1. The fake Sharadar is reached through a visible `SHARADAR_BASE_URL=http://127.0.0.1:<port>`** (`vendor_env`). The agent rightly refuses localhost evidence as Sharadar's ("Run `unset SHARADAR_BASE_URL`", quant incremental turn 11); the sim user claims it unset it (turns 12, 49) and the driver sets it again. No probe was ever Answered, which fails `planted_facts_reached_design` and `crosscheck_facts_reached_design` in both quant runs. Fix: route Sharadar through the closed proxy on its real host, as Yahoo already is, and set no base URL.
- **H2. `script_cmd` misses `uv run --script <path> <step>`.** PB-03's `compare` step was dropped: 15 runs with no step, each a usage error. Fix and pin with PB-03's README.
- **H3. "A reported run opens api-probe" fights an open build-planning gate:** quant incremental turns 46–55. Don't switch to api-probe while another skill's gate is open.
- **H4. The sim persona** must not claim to change its shell environment. Its JSON parse failed 42 times (prose instead of JSON): 4 fallback turns. Ask for structured output, or take prose as the message.
- **H5. Report each turn's working skill** (from Skill calls or files changed), not only the session's opening skill.

### dt
- **D1. A QR- limit blocks every stage.** `stage_designed` needs every spec ID on an Approved pipeline; QR-04 ("data costs nothing beyond the subscription") sits on no step, so S1–S4 stayed below Designed in quant all-at-once from turn 3 to 70. Either the cost/licence QR items count as covered by the decision that meets them, or pipeline-design must put them on the step that applies them (steps.md already says so) and `uncovered` must say so; and `dt next` should name the blocking IDs.
- **D2. Optional test-planning scope before the first cut.** All four stages come from the brief, so `inferred_pipelines` gives every stage every pipeline, and group 4's active-milestone scoping has nothing to anchor to. Scope by each feature's `**Stage:**` line.
- **D3. `request-trace` after `dt archive`.** Plan requests trace to task IDs; archiving moves them and `check_request_trace` looks up with `archive=False`, so every archived plan fails lint (`sim_advance_3`: 7 and 11 errors). Look in the archive.
- **D4. Extend ranks above Replan of a stale active plan** (`status/build_planning.py`): rl incremental cut S3 at turn 68 while M1 read a retired symbol (`registry.make_agent`, retired by AD-16 at turn 59) and `interfaces_changed` was set.
- **D5. Grow triggers ignore the user's "one package".** rl all-at-once: the user said "Keep it as one package, no split" (UR-34, turn 8); a later architecture Revise raised the split again from `grow-size` (contract 505 lines, 8 pipelines) and the sim user, who follows recommendations, agreed: 12 packages, `rl_single_package` fails. Suppress the trigger when a request or accepted decision records the shape.
- **D6. The pipelines budget doesn't scale with step rows,** now that library classes and called contract functions are steps (`doc_budgets` in two runs).
- **D7. No check that an unbuilt step is Deferred by name,** only that spec IDs are covered (quant incremental's `PL-07.daily_bars`, cut.md:46).
- **D8. Covered IDs reported as uncovered:** rl all-at-once's `lab` pipeline lists `PREY-01–PREY-08` and `DATA-01` in its Covers, yet `dt status --skill pipeline-design` reports them uncovered, and `dt next` kept opening pipeline-design sessions that did nothing (turns 32–43). The range parser expands these correctly; the cause is elsewhere and unconfirmed.
- **Noise:** `request-number` warns on plain numbers that aren't facts.

### Skills
- **S1. pipeline-design and architecture-design: close a missing-type route in one round.** One combined gate for pipelines plus their contract additions, or `step-io-types` as a warning while an open route names the type, and no "not in the contract yet" notes that need a tidy-up route.
- **S2. Every gate (shared writing rules):** no "Shall I commit?" on a clean tree; when the session's skill has nothing to do, go on to the run `dt next` names instead of ending "say the word".
- **S3. architecture-design Grow (`shape.md`):** never recommend a split for size alone, and not against a recorded "one package"; the file contradicts itself ("~3 pipelines" as a trigger beside "a proof of concept is almost always a single package").
- **S4. build-planning:** a within-package call labelled a fake (rl all-at-once T15, T18); a step neither spined nor Deferred (quant incremental `PL-07.daily_bars`).
- **S5. pipeline-design:** Owner `stock.view` against the layout's `StockView.tsx` (`writes_disjoint`); QR-04 on no step.
- **S6. spec-writing:** run-time budgets filed as feature requirements without Given/When/Then (PORT-20, INFO-19, FCST-15, AGENT-17): they are QR- items.
- **S7. idea-refine:** the brief grew to 530 words over the stage Extends (`brief_size`); no fundamentals source suggested in quant all-at-once.
- **S8. test-planning, build-setup:** ask all questions that have defaults in one turn.
- **S9. api-probe (minor):** rl all-at-once probed a library's feasibility (SB3 PPO), not an external service (`no_needless_probe`).

### Harness: grader
- **G1. `spec_classical`:** match `risk[- ]parity` (grade.py:963).
- **G2. `probe_not_guess`:** a later-stage fundamentals suggestion (AD-11) is counted as the data-source decision.
- **G3. `sim_ready_3`:** picks a cross-package spine that the wiring legitimately fakes; skip call steps as `phase0_split` does.
- **G4. `phase0_split` / `dtprobe`:** named-step deferrals (`PL-07.raise_finding`) are reduced to the pipeline ID by `expand_refs`, and owner grouping counts a Deferred step as built.
- **G5. `runner_split` (arguable):** flags the agent's dry runs of a probe copy in its own scratchpad against its own fake.

### Truncation, not defects
quant all-at-once's 25 plan checks (no `tasks/plan.md`, no `CONSTRAINTS.md`) and rl incremental's `dt_lint_clean`, `tasks_well_formed`, `wave_width` and `phase0_split`, all from its stale M1 (D4).

## Fix plan for iteration 11, in waves

Each session in a wave owns whole folders or files, so a wave runs in parallel; the next wave starts once the last one is merged and passes `pytest`, `check.py` and `dryrun.py`. Every session branches from `interface-first-design`, commits on its own branch, and never merges or pushes.

The wave also takes build-planning's proposals from build eval b1's contract-gap review (`dev-team/design/contract-gap-proposals.md` on `claude/contract-gap-fixes-398dd0`, reference shape `dev-team/design/examples/contract_first_pipeline.py` on `build-phase` at 6805e9c). That branch and `build-phase` hold the dt behaviour some of the new wording points at (`dispatch.added_barriers`, floor_guard's `stub-pinned`, `dt context`'s Conformance block), so that text reads true once those branches merge.

**Wave 1 (six sessions, in parallel)**

| Session | Owns | Fixes |
|---|---|---|
| 1. Driver | `evals/harness/driver.py`, `fakevendor/`, `scenarios.json`, `selftest/sessions.py` | H1–H5 |
| 2. dt | `scripts/**` | D1–D8, `request-number` noise; contract-gap proposal 2's optional `interface-barrier` warning (lint.py has one owner) |
| 3. build-planning | `skills/build-planning/**` | contract-gap proposals 1, 2 (the `tasks.md:31` line), 3, 6a, 6c; S4; S2 for its own gate |
| 4. pipeline-design + architecture-design | `skills/pipeline-design/**`, `skills/architecture-design/**` except `references/contracts.md` (the contract-gap branch edits it) | S1, S3, S5; S2 for their gates |
| 5. Other skills | `skills/{idea-refine,spec-writing,test-planning,build-setup,api-probe,reference-intake}/**` | S2, S6, S7, S8, S9 |
| 6. Grader | `evals/harness/{grade,dtrun,dtprobe,simulate,probegrade}.py`, `selftest/checks.py`, `selftest/adjudicated/` | G1–G5, with pins; regrade iterations 9 and 10 into `results-iteration-{9,10}/regrade/` |

Both 1 and 6 can move `dryrun.py`'s pins; whichever merges second re-pins.

**Not in this wave:**
- Contract-gap proposal 4 (a real vertical slice before the freeze): it changes the milestone shape `PURPOSE.md` describes, so it waits for the user's decision. Its cheaper alternative (ask for an `api-probe` when no probe sample backs an external record type) can go to session 3 if chosen.
- Contract-gap 6b (architecture-design `contracts.md`) and 6d (the build skill's `escalation.md`): done on the contract-gap branch.

**Wave 2 (integration):** merge wave 1; run the dt tests, both `check.py`, the grader selftest and `dryrun.py`; a 3-turn smoke; a quant smoke long enough for a probe Verdict through the proxied fake (H1, H2). Release level for dev-team decided then.

**Wave 3:** iteration 11, judged 3 × both orders, against iteration 10 re-judged if the judge prompt changes.

Iteration 11 is done when all four runs finish without hitting `max_turns`, a planted fact reaches each quant design from a probe Verdict, no check fails for a grader reason, total turns fall back toward iteration 9's 250 with sessions still fresh per skill run, and the user's facts still hold (`requests_*` pass).
