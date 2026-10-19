# Iterations 9 and 10 regraded with the iteration-11 grader (wave 1, session 6)

These grades come from items G1–G5 ("Harness: grader") in [../findings.md](../findings.md). The fixes are in `grade.py`, `dtrun.py`, `dtprobe.py`, `simulate.py` and `selftest/`, on branch `claude/iter11-grader-35cd92`.

- **Grades:** `grading-<trajectory>.json` here for iteration 10, and in [../../results-iteration-9/regrade/](../../results-iteration-9/regrade/) for iteration 9.
- **How they were made:** `adjudicate.py` copied each run from `dev-team-workspace/` into a scratch folder, leaving out venvs and `flow/`, and graded it there. The workspace was only read. Iteration 9's quant all-at-once was graded at `9ece2e6` (`AT_COMMIT`).
- **"Before":** the grader at `ce7ee79`, run on copies made the same way. Its iteration-10 scores match those published in [../findings.md](../findings.md).

## Scores

| Run | Iteration 10 before → after | Iteration 9 before → after |
|---|---|---|
| rl incremental | 66/70 → 66/70 | 67/67 → 67/67 |
| rl all-at-once | 71/77 → **72/77** | 66/67 → 66/67 |
| quant incremental | 85/95 → **87/95** | 85/92 → 85/92 |
| quant all-at-once | 52/84 → 52/84 | 85/91 → 85/91 |

**No iteration-9 check moved.** Its outcomes, evidence and check texts are identical to the iteration-10 grader's. The only difference in its `grading-*.json` is the scratch `dt` path.

**Iteration 10, check by check:**

| Run | Fail → pass | Evidence changed, same outcome |
|---|---|---|
| rl all-at-once | `sim_ready_3` (G3) | `phase0_split`, `wave_width`: the outside list reads "Deferred by name". It gains `PL-01.GaussianPPO` and `PL-02.judge_close`, which were counted as built through an owner module (G4). The unit count stays 10.<br>`spec_on_pipeline_or_deferred`: the deferred count includes the named steps (40 → 54); nothing is off either way. |
| quant incremental | `spec_classical` (G1), `probe_not_guess` (G2) | `phase0_split`: still fails, now only on `PL-07.daily_bars` and its `BarFrame` (G4; real: D7, S4).<br>`wave_width`: units 22 → 20.<br>`planted_facts_reached_design`: AD-11 has left its decision list (G2); it still fails (H1).<br>`spec_on_pipeline_or_deferred`: deferred count 31 → 47. |

Every check that still fails in iteration 10 is ruled real in `selftest/adjudicated/iteration-10.json`. That makes "no check fails for a grader reason" true for iteration 10.

## Each item

| Item | Done | What changed |
|---|---|---|
| G1 `spec_classical` | yes | Matches `risk[- ]parity` (`dtrun.spec_classical`). `ML_BEATS_CLASSICAL` accepts the hyphen too. |
| G2 `probe_not_guess` | yes | `source_decisions` leaves out a decision that only suggests a source for a later stage: its `**Scope:**` or its heading says "later", "future" or "next stage" (`dtrun.later_stage_decision`). quant incremental's AD-11 ("Suggested fundamentals source for a later stage: Sharadar SF1", `**Scope:** later stage`) is no longer the stage's data-source decision. The same filter applies to the decision list the planted-facts checks read. |
| G3 `sim_ready_3` | yes | `simulate.wiring_spines` picks the wiring task and the spines it must wait on. Two kinds of spine are left out:<br>• a call step's spine (`dtrun.call_step`, as `phase0_split` skips them). This is M1-T14, `PL-01.train_dqn` in package `dqn`, which lab's wire PL-01 runs on its fake.<br>• the spine of a step its pipeline needs only later (Deferred by name, or all its Covers Deferred), when the wiring doesn't wait on it. This is M1-T06, `PL-01.load_agent`: POOL-03 and POOL-04, Deferred to M6, built now for PL-02's call.<br>**One addition beyond the finding:** skipping call steps alone moved the held spine to M1-T06, which T19 doesn't wait on either, so the check still failed. The "doesn't wait on" condition keeps iteration 9 quant incremental's M1-T04 (`PL-04.open_primary`, DATA-01 Deferred): its wiring depends on it. A first version without that condition dropped M1-T04 from the check text. |
| G4 `phase0_split` / `dtprobe` | yes | **`dtprobe`:** adds the step IDs a plan's Deferred cell names (`dtrun.named_steps`, `PL-07.raise_finding`) to the plan's `deferred` list. `md.expand_refs` keeps only `PL-07` from them, and that stays in the list too.<br>**`dtrun.outside_milestone`:** a step Deferred by name is outside the milestone unless a task's Step cell names it. That holds even when another step's spine builds its owner module: `PL-09.useReport` shares `api.queries` with M1-T19's step, so the owner grouping had counted it as built and asked the interface for `Report`. The reason reads `Deferred by name (<its Deferred Covers>)`. `wave_width` reads the same list. |
| G5 `runner_split` | **kept** | api-probe's `references/new.md` §5 says: "Never run `probe.py`, not even with a dry-run flag." quant all-at-once's turn 9 copied PB-01's and PB-03's `probe.py` into its scratchpad, started its own fake Sharadar on 127.0.0.1:8765, and ran them with a dummy key. That is a run of `probe.py`, so the check is right and still fails the run. It is pinned as a bad case; the good case is `public.py` run under `env -i`. |

**Known gap:** `probefacts.script_runs` doesn't see `uv run -q probe.py` (an option word after `uv run`), so turn 9's PB-01 run isn't listed; only the PB-03 `python3 probe.py` run is. The outcome is the same. `probefacts.py` isn't in this session's files, so this goes to a follow-up.

## Pins and corpus

- **`selftest/checks.py`:** 220/220 cases over 27 checks, up from 201 over 24. G1–G5 each have a good case (the iteration-10 form) and a bad case (the defect the check must still catch). `spec_classical`, `probe_not_guess` and `sim_ready_3` are new check ids there.
- **`dryrun.py`:** "dry run: as pinned". Every replay kept its score, so nothing was re-pinned. `selftest/mutate.py` is also as pinned.
- **`adjudicate.py`** over iterations 7–10 agrees with 181 of 182 records across 16 runs.
  - `selftest/adjudicated/iteration-10.json` is new, with 52 records from findings.md: G1–G3 as grader fails, G4 as mixed (`daily_bars` must stay, the named deferrals must go), G5 as real, D/S/H items as real, and quant all-at-once's 26 plan checks as truncation.
  - The one disagreement predates this work: iteration 7 quant all-at-once's `sim_ready_1`, a false pass.
  - No failing iteration-10 check is left without a record.
- **`evals/README.md`:** the `phase0_split` and `probe_not_guess` rows and Ready simulation step 3 describe the new rules.
