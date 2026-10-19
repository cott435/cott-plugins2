# Iterations 8 and 9 regraded with the iteration-10 grader (fix-plan group 1)

These are the baselines for iteration 10. They come from the "Harness: grader" table in [../findings.md](../findings.md), fixed in `grade.py`, `dtrun.py`, `probegrade.py`, `planexport.py` and `selftest/`, on branch `claude/iter10-grader-5fd0f8`.

- **Grades:** `grading-<trajectory>.json` here for iteration 9, and in [../../results-iteration-8/regrade/](../../results-iteration-8/regrade/) for iteration 8. [smoke-10-grading-rl-all-at-once.json](smoke-10-grading-rl-all-at-once.json) is the ten-turn smoke run.
- **How they were made:** each run was copied from `dev-team-workspace/` into a scratch folder without its venvs and `flow/`, then graded there. The workspace was only read.
- **quant all-at-once (iteration 9):** graded at `9ece2e6` (`turn 50`). Two build sessions committed to that project folder after the run. `adjudicate.py` now does the same (`AT_COMMIT`).
- **Iteration-11 grader:** the `grading-*.json` files were regraded again with the G1–G5 fixes ([../../results-iteration-10/regrade/README.md](../../results-iteration-10/regrade/README.md)). No outcome, evidence or check text moved; only the scratch `dt` path differs.
- **"Before":** the grader at `65cd08e` (dev-team 0.5.0), run on the same copies.
  - Its iteration-9 scores are 64, 61, 80 and 82. At run time they were 64, 61, 79 and 82.
  - quant incremental's `docs_before_probe` passes now because group 0 added Sharadar's `data.nasdaq.com` docs to `scenarios.json`.

## Scores

| Run | Iteration 9 before → after | Iteration 8 before → after | Interface-agent estimate (it9) |
|---|---|---|---|
| rl incremental | 64/67 → **67/67** | 60/67 → 60/67 | 67/67 |
| rl all-at-once | 61/67 → **66/67** | 60/67 → 60/67 | 66/67 |
| quant incremental | 80/92 → **85/92** | 78/89 → 78/89 | 83/92 |
| quant all-at-once | 82/92 → **85/91** | 85/90 → 85/90 | 87/92 |

**No iteration-8 result moved.** The only change in iteration 8 is the new "outside the milestone" listing:
- rl incremental lists `PL-02.train_seeds` (Deferred QR-02).
- quant all-at-once lists `PL-06.read_universe`.
- Both are call steps, which were never spined. So iteration 8 stays like for like with the old grades.

**Iteration 9, check by check:**

| Run | Fixed (fail → pass) | Moved the other way | Still failing, all ruled real |
|---|---|---|---|
| rl incremental | `wave_width`, `phase0_split`, `fakes_only_cross_pipeline` | — | none |
| rl all-at-once | `phase0_split`, `fakes_only_cross_pipeline`, `types_in_contract`, `gate_discipline`, `skills_invoked` | — | `writes_disjoint` (F9: the factory and the writer) |
| quant incremental | `wave_width`, `edges_mitigated`, `phase0_split`, `skills_invoked`, `probe_code_in_probe_turns` | — | `writes_disjoint` (F9), `no_edge_to_code_when_interface` and `sim_ready_2` (F3), `types_in_contract` (now only `StagedRun`, F8 real), `data_sources_suggested` (F13), `planted_facts_reached_design` (flow F4), `crosscheck_facts_reached_design` (PB-03 never Answered) |
| quant all-at-once | `edges_mitigated`, `phase0_split`, `types_in_contract`, `skills_invoked` | `data_sources_suggested` pass → **fail**: the EDGAR match was for SIC codes (flow §6 predicted this). `crosscheck_facts_reached_design` fail → **n/a**: nobody named a cross-check | `finished` and `plan_docs_approved` (F12 budget), `writes_disjoint` (F9), `unmitigated_reasoned`, `data_sources_suggested`, `planted_facts_reached_design` (flow F3) |

About quant all-at-once's `unmitigated_reasoned`:
- It now fails on F1's real serializer: eight thickens wait on wire PL-09 for its `conftest.py`.
- Its old reason, the system task's swap rows (F6), is gone.
- quant all-at-once is 85/91 rather than the estimated 87/92 for two reasons: this fix, and the `data_sources_suggested` fix. The estimate counted neither.

## Each item

| Item (finding) | Done | What changed |
|---|---|---|
| `phase0_misses`, `wave_units`, `covering_tasks`, `step_units` (interface F4) | yes | **`dtrun.outside_milestone`**: a step no task builds (no spine, recorded fold or wiring fold) is outside the milestone when one of these holds:<br>(a) its Covers meet the plan's Deferred, and its other Covers are covered by steps the milestone builds;<br>(b) its spine says `waits on PB-NN`, and a built step has its Out type;<br>(c) it is undeclared, no task names it, and every one of its Covers is covered by a built step.<br>Outside steps are dropped from both checks, "interface lacks" included, and listed in the evidence and in `metrics.items.outside_milestone`.<br>**Other changes:** units are keyed by package and owner (`unit_key`). A wiring task's Reason, or its Writes of the owner module, counts as a fold (`wiring_folds`). `covering_tasks` reads multi-step Step cells.<br>**Two deliberate narrowings of the finding's wording:**<br>• (a) asks that no task *builds* the step, not that no task *names* it. quant inc's T02 names `mount_studies` only to leave it out.<br>• (c) also needs the step's Covers to be built elsewhere. Without that, the it8 bare-owner bad case (a step with no Covers that the interface doesn't declare) would pass. |
| `fake_ok` (F5) | yes | `dtrun.boundary_fake_ok` accepts a fake when the symbol has a `**Boundary:**` line, its Used by names a pipeline other than the owner's (a non-call step of that name, or the pipeline whose entry it is), and the consumer's pipeline is in Used by. |
| `edges_mitigated`, `wired_pipelines` (F6) | yes | **`edges_mitigated`:** skips a system task's rows to the wiring it swaps in (`dtrun.swaps_in`).<br>**`wired_pipelines`:** adds pipelines whose entry function the system task reads (`entry_pipelines`).<br>**One addition beyond the finding:** a pipeline whose smoke test the system task's Verify runs also counts. Without it, quant aao's T47→T32 still read as unmitigated: T47 never names PL-12, but its Verify runs `test_pl12_smoke.py`.<br>`unmitigated_class` uses the same rule for integration. |
| `skills_invoked` via `turn_skills` (F7, flow §6) | yes | **Attribution:** `dtrun.turn_skill_seq` and `turn_skill_map` credit a turn whose user message opens with `/dev-team:<skill>`. A new session explicitly marked `slash: false` is not credited.<br>**What reads it now:** `skills_invoked`, `test_planning_invoked`, `reference_intake_invoked` and `extra.skill_sequence`, instead of `t["skills"]`. |
| `types_in_contract` (F8, J4) | yes | **`dtrun.contract_text`:** the whole contract files, preambles included.<br>**`defined_in`:**<br>• mirror paths of any depth;<br>• "mirrors one … row";<br>• "mirroring";<br>• a bare mirror target that has a section or an inline definition (`CheckCounts`, `DayDiff`);<br>• `` - `Name`: `` notes with typed fields.<br>**`field_types(text, modules)`:** skips types qualified by a non-contract module (`JSX.Element`, `duckdb.DuckDBPyConnection`). `NaN` is in `LIBRARY_TYPES`. |
| `routed_revise` (F10) | yes | New `dtrun.routed_fixes`. It passes architecture plus one other layer when all three hold:<br>• the architecture change is ≤ 25 lines;<br>• the previous turn named routed fixes;<br>• the user's message says to make them.<br>`grade.py` records lines added per layer to feed it. |
| `unmitigated_class` (F1) | yes | A thicken task waiting on a wiring or system task fails, whatever the row's kind. |
| `writes_disjoint` (F9 nit) | yes | `dtrun.step_ids` splits a multi-step Step cell. The shared owner is used, so T02 resolves to `runs.record`, not "?". |
| `probe_code_in_probe_turns` (flow §6) | yes | `probegrade.written_before_switch`: probe writes made before a turn shows another skill stay with the api-probe turn before it, in the same session. |
| `crosscheck_facts_reached_design` (flow §6) | yes | n/a when no user message, brief, spec or architecture names Yahoo, yahooquery or yfinance, and there is no Yahoo probe (`dtrun.crosscheck_named`). |
| `data_sources_suggested` (flow §6) | yes | A fundamentals source counts only in a sentence, list item or table cell about fundamentals (`dtrun.FUNDAMENTALS`). |
| `planexport.turn_skills` (R10) | yes | Uses `turn_skill_seq`: the last skill a turn shows, carried forward only over turns that show none, within a session.<br>rl inc's T35 and quant inc's T57 now read build-planning. They used to read idea-refine and reference-intake. |
| F13's open question: does scoping fundamentals out with a reason pass? | skipped | Not a grader-table row. Its fix is in idea-refine and the driver (F7), so the check still fails quant incremental. |

## Pins and corpus

- **`selftest/checks.py`:** 201/201 cases over 24 checks, up from 143 over 20.
  - Each fix has a good case (the iteration-9 form) and a bad case (the defect the check must still catch).
  - `planexport_turn_skills` is a new check id.
  - `step()` takes optional Covers.
- **`dryrun.py`:** "dry run: as pinned". Every replay kept its score, so nothing was re-pinned. `selftest/mutate.py` is also as pinned.
- **`adjudicate.py`** against iterations 7–9 agrees with 129 of 130 records:
  - `selftest/adjudicated/iteration-9.json` is new, with 33 records from findings-interface and flow §6. Records may now expect `na`.
  - The one disagreement predates this work: iteration 7 quant all-at-once's `sim_ready_1`, a false pass.
  - No failing iteration-9 check is left without a record.
  - The old grader disagrees with 22 of the 33 iteration-9 records.

## smoke-10

- It grades cleanly: 31/56, and no check crashes.
- `skills_invoked` now credits the four skills the ten turns ran: idea-refine, spec-writing, architecture-design and pipeline-design. Each was opened with `/dev-team:<skill>`. Before, it read `used: []`.
- It still fails, because the smoke stopped inside pipeline-design: build-planning and build-setup never ran. A full run that reaches them passes.
- `test_planning_invoked` fails for the same reason.
