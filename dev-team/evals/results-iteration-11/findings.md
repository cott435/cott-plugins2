# Iteration 11: wave-1 fixes; rl only, quant crashed

## Run conditions

- **Plugin and harness:** branch `interface-first-design` at `390ef5d` (2026-10-19): iteration 10's fix plan, wave 1, merged and checked as wave 2 ([../results-iteration-10/findings.md](../results-iteration-10/findings.md), "Fix plan for iteration 11"):
  - driver H1–H5: the fake Sharadar behind the closed proxy on its real host with no base URL, `uv run --script <path> <step>`, no api-probe switch during another skill's gate, a sim user that claims nothing it can't do, per-turn `working_skill`;
  - dt D1–D8, `request-number` noise, `interface-barrier`, `step-io-types` as a warning while a route names the type, `grow_held`;
  - skills S1–S9, and build-planning's contract-gap proposals 1, 2, 3, 4 (as the probe rule the user chose), 6a and 6c;
  - grader G1–G4 (G5 kept), with iterations 9 and 10 regraded in `regrade/`.
- **Before the run:** 571 dt tests, `check.py` 7/7 and 8/8, grader selftest 220/220, `selftest/sessions.py` 60/60, `dryrun.py` as pinned. Smokes: the driver session's 16-turn quant run ($8.12) recorded PB-01 Answered through the proxy; a 10-turn rl all-at-once run on the merged tree ($5.22, `smoke-13`) held one session per skill and reached pipeline-design at turn 9 (iteration 10: api-probe at turn 9).
- **Models:** Opus 5.5 agent, Sonnet simulated user, Opus 5.5 judge with iteration 10's anchored prompt, 3 repeats in both orders.
- **Scope:** n=1 per trajectory. **Only the two rl runs completed.** Both quant runs crashed (Q1), and the user chose not to rerun them: quant waits for iteration 12.

**Flow pages:** [runflow/index.html](runflow/index.html), each run against iteration 10 (`runflow/<traj>-vs-iteration-10.html`).

## Results

| Run | Checks (iteration 10 → 11) | Turns | Agent cost | Wall clock | Sessions | M1: N / CP / widest | Judge (it10 → it11) |
|---|---|---|---|---|---|---|---|
| rl incremental | 66/70 → **69/70** | 69 → 72 | $37.85 → $48.85 | 153 min | 30 → 32 | 24 / 7 / 16 | 6.20 ± 0.22 → **6.77 ± 0.25** |
| rl all-at-once | 72/77 (regraded) → 66/70 | 43 → **36** | $29.63 → **$20.32** | 71 min | 15 → 14 | 24 / 5 / 15 | 7.03 ± 0.31 → 7.25 ± 0.09 |
| quant incremental | crashed at turn 17 (38/84 partial) | — | — | — | — | — | not judged |
| quant all-at-once | crashed at turn 21 (48/84 partial) | — | — | — | — | — | not judged |

- **rl incremental's stale M1 is gone.** iteration 10's four failures from it (`dt_lint_clean`, `tasks_well_formed`, `wave_width`, `phase0_split`) all pass, and the judge's interface_quality went 2 → 4, task_buildability 2 → 3.5, ease_of_finding_next_build_step 2.2 → 3.7: a gain of +0.57, over the 0.25 bar and 2.5 × its SD.
- **rl all-at-once stayed one package and got cheaper:** `rl_single_package`, `sim_advance_3`, `sim_ready_3`, `fakes_only_cross_pipeline` and `doc_budgets` now pass; 7 fewer turns and 31% less cost. Its judge score is a tie (+0.22).
- **The mode comparison is unreadable this iteration:** each order went to its set A, 3 of 3 (position effect +0.88 ± 0.29), larger than the margin (all-at-once ahead by 0.48 ± 0.19).
- **The user's facts held:** `requests_*` pass in both rl runs.

## Findings

### Q1. Both quant runs crashed: an agent-run probe longer than the driver's turn limit (harness and api-probe)
- With H1 fixed, probes reach the fakes, so the agent ran its own keyless Yahoo check (`public.py`, the agent's half of the runner split) inside its turn. Both checks were paced over every current member: quant incremental's PB-03 `paced` waits 10 s between requests (500+ symbols, about 80 minutes); quant all-at-once's PB-04 `current` paced similarly. The fake answers instantly; the pauses are the probe's own `time.sleep`.
- The turn passed `agent_turn`'s 1,800 s `subprocess.run` timeout. `TimeoutExpired` isn't caught, so `run_loop` died: no `summary.json`, quant incremental at turn 17, quant all-at-once at turn 21. The stream shows nothing for the hung turn, because the driver reads the agent's output only when the process ends. Logs: [crash-quant-incremental.log](crash-quant-incremental.log), [crash-quant-all-at-once.log](crash-quant-all-at-once.log).
- **Before the crash, H1 worked:** quant all-at-once's PB-01 and PB-02 and quant incremental's PB-02 were recorded **Answered** (verdict fail, from the planted facts), the first Answered probes in any iteration. quant incremental's PB-01 was Waived at the sim user's word.
- **Fix (iteration 12):**
  - Driver: catch a timed-out turn, kill it, record it in `turns.json` (`timed_out`), tell the next turn what happened, and carry on; never lose the run.
  - api-probe: a check the agent runs finishes in a few minutes (a sample of symbols, not every member); a long paced batch is a user step in the README, with its time and spend stated. The proposal-4 probe rule and the iteration-10 S9 wording are the passages to extend.

### R1. rl all-at-once: wiring waits on real spines it only calls (build-planning)
`no_edge_to_code_when_interface`, `edges_mitigated`, `unmitigated_reasoned` and `sim_ready_2` fail, all new. The plan gives wire PL-04 (M1-T20) `order` edges to five spines with the reason "none: integration: the smoke runs it" or "records a real snake episode", and M1-T10 waits on M1-T09 because "the store.RunDir double can't stand in for its constructor". Wiring should run on the interface task's fakes. Likely cause: wave 1's new wording, the S4 rule (a call into another component's function gets a replay double, not a fake) read together with proposal 6a's smoke rule, so the planner made the smoke run real code. Check both passages in `phase0.md` and `tasks.md`: a smoke test checks that the pipeline runs on the fakes and doubles and the shape of what it writes.

### R2. rl incremental: four thickens of one step in a chain (build-planning)
`unmitigated_reasoned` fails on M1-T15 → T16 → T17 → T18, each "thickens the same step, DQNAgent", the cause of the critical path of 7 (iteration 10: 6). Each thickens its own concern (memory, frozen targets, exploration, loading) but in one module. Either split the step's module by concern so the thickens can run in parallel, or fold them; a chain of thickens on one step is the serializer phase0.md warns about.

### R3. Turns and cost
- rl all-at-once fell from 43 to 36 turns; rl incremental rose from 69 to 72 and $37.85 to $48.85, with architecture-design the largest working skill (20 turns). No "say the word" endings remain in either run (S2).
- Commit offers remain at 22 gates in rl incremental: the rule now offers a commit only when `git status` shows changes, and during a turn it always does, because the harness commits after the turn. This costs no turn (the sim user answers inside the approval) and is right for a real user; leave it, or have the driver tell the sim user to ignore commit offers.
- Not analysed further with n = 2 runs; read with iteration 12's quant.

## Fix plan for iteration 12

1. **Q1 first:** the driver's timeout handling and api-probe's short agent checks. Then a quant smoke that runs a Yahoo agent check end to end and a deliberately long turn that times out without killing the run.
2. **R1, R2 (build-planning):** wiring on fakes and doubles, never on spines it only calls; no chain of thickens on one step.
3. Iteration 12 runs all four trajectories; quant is compared against iteration 10 (its last complete quant runs), judged 3 × both orders.
