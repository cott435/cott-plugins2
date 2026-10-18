# Grader self-test after iteration 8: adjudicated corpus and plan mutations

**Scope:** the grader at `interface-first-design` (`7d4c9aa`), with no fixes. `harness/adjudicate.py` regrades scratch copies of the eight iteration-7 and iteration-8 runs against 92 rulings from `results-iteration-{7,8}/findings-{interface,flow}.md` (`harness/selftest/adjudicated/`). `harness/selftest/mutate.py` plants seven single defects in the known-good interface-first plan. No paid runs, and the archived runs were only read.

## Headline

- **The grader gets 30 of 92 rulings wrong:** 21 false fails, 4 false passes, and 5 mixed failures that still list items ruled false.
  - Iteration 7 accounts for 3 of them. The iteration-7 fixes hold for the other 43 iteration-7 rulings.
  - Iteration 8 accounts for 27 of its 46 rulings.
- **Two of the seven mutations are not caught by their own check:**
  - **Wiring tasks chained on a shared entry module (iteration 8's F1).** No check fails. This defect set the critical path in all four iteration-8 runs.
  - **A Boundary line removed.** Only `dt_lint_clean` fails, through dt's `type-cases` lint. No grader check owns this rule.
- **The other five mutations are each caught by their own check:** a decision Accepted while its probe is Ready, a type missing from the interface, a Depends cycle in a note, a false spine edge, and an unordered shared Writes.
  - dt itself misses two of them: the Depends cycle and the early Accept. That matches iteration 8's dt fix list, items 1 and 2.

## 1. Adjudicated records the grader gets wrong (30)

**False fails (21):**

| Run | Check | Finding |
|---|---|---|
| it7 rl inc | `phase0_split` | it7 F4/F7: T17 and T18 record their folds as "spine folded into the thicken". The grader only accepts a Reason that starts with `fold` |
| it8 rl aao | `wave_width` | F4: bare owners are counted one unit per step |
| it8 rl aao, quant inc, quant aao | `phase0_split` | F4: same cause; a call step is dropped from its unit |
| it8 quant inc | `edges_mitigated`, `unmitigated_reasoned` | F6: a row whose To is an interface task |
| it8 quant inc | `no_edge_to_code_when_interface` | F7: "as in PL-06" is read as a call |
| it8 rl inc | `tester_starts_early` | F5: contract classes are not declared |
| it8 quant aao | `fakes_only_cross_pipeline` | F8: the `data.load_*` glob |
| it8 quant aao | `runner_split` | F9: heredoc string literals |
| it8 quant inc, quant aao | `no_secret_seen` | flow F5: heredocs, `git check-ignore`, `test -e` |
| it8 quant aao | `probe_code_in_probe_turns` | flow F6: turns are attributed by `Skill` calls only |
| it8 quant inc, quant aao | `plan_blocked_while_open` | flow F6: the simulation keeps `tasks/queued/` |
| it8 quant inc | `probe_checks_cover`, `docs_before_probe` | flow F6 |
| it8 quant inc, quant aao | `spec_no_vendors` | flow F8: a vendor the persona names |
| it8 quant inc | `spec_pca_mp` | flow F8: regex |

**False passes (4):**
- **it7 rl inc `wave_width`** (it7 F11, still open). Tester halves of library thicken tasks count as ready, so the check passes 11 ≥ 8 while 6 of 9 spines wait.
- **it7 quant aao `sim_ready_1`** (it7 F5). T04 reads the schemas T03 writes, but has `Depends on: —`. No check sees an order that a task's Read implies but its Depends on omits.
- **it8 rl inc and quant aao `unmitigated_reasoned`** (it8 F3).
  - `order` rows pass with any reason.
  - Wiring waits on non-fold thickens.
  - `same_step_unit` calls T12→T11 "same module" only because both tasks name the same Step.

**Mixed failures (5).** The outcome is right, but the evidence still lists items ruled false:
- it8 quant inc `writes_disjoint`: T27's folder owner.
- it8 rl inc `phase0_split`: `report_runs` and `load_agents`.
- it8 rl aao `types_in_contract`: `FixedEntry` in constructor form.
- it8 quant inc `types_in_contract`: the `*Dto` mirror types.
- it8 quant inc `probe_not_guess`: AD-06 and AD-14 under "without a Probe line".

**Records with basis "derived" (3).** These are it7 `unmitigated_reasoned` in rl aao, quant inc and quant aao. In each, the analyst filed the check under F3, a grader issue, but named the remaining flagged rows as real defects under F4, F5, F13 or Smaller. All three agree with today's grader.

**Failing checks no record covers (9, not counted):**
- `types_in_contract`'s field-type clause on three iteration-7 runs. It was added after iteration 7.
- `data_sources_suggested` (4) and `crosscheck_facts_reached_design` (2). Both checks are new since iteration 8's analysis.

## 2. Mutations

| Mutation | Owner | Outcome | What fails |
|---|---|---|---|
| Two wiring tasks write `__main__.py`, chained by a `file` row | `no_edge_to_code_when_interface` | **gap** | nothing. The pair shows only in `serial_on_shared_file`, which is not counted |
| The same, with no edge between them | `writes_disjoint` | exact | `writes_disjoint` and dt `writes` |
| `stats.Cov` (crosses stats→portfolio in PL-03) loses its Boundary line | `interface_coverage` | **dt only** | `dt_lint_clean` (type-cases) and `sim_advance_3`. `interface_coverage` checks only boundaries crossed inside the milestone, and it accepts a legacy `Sample:` line |
| Spine T06 depends on spine T05 across the `stats.Cov` sample | `no_edge_to_code_when_interface` | exact | it, `sim_ready_2` and dt `edges` |
| AD-04 Accepted while PB-01 is Ready | `probe_not_guess` | exact | only the grader. dt has no lint for it |
| `stats.CovReport` (write_report's Out) missing from the interface's Read | `phase0_split` | exact | only the grader. dt's `boundaries_unfrozen` doesn't report it |
| M1's Depends cell says "— (build order: before M2)" | `milestone_depends` | exact | only the grader. `dt roadmap --check` passes the M1↔M2 cycle |

Two first drafts of these mutations planted a second defect by accident, and dt's `edges` lint caught it:
- **The wiring chain** kept the fake-mitigated `call` row while adding the dependency.
- **The missing type** dropped `data.RawPrices`, a type whose sample mitigates the T03→T02 row.

The pinned versions plant one defect each.

## 3. Grader fixes, ranked

Ranked by harm: a false pass hides a defect that costs width. Ties are broken by how many records the fix corrects.

1. **Tighten the edge rules.** Fixes 2 false passes and 1 mutation gap.
   - In `dtrun.unmitigated_class` (`dtrun.py:309-310`), flag wiring or system → non-fold thicken, and stop passing every `order` row.
   - `same_step_unit` (`dtrun.py:266-271`) should need a shared module, not just a shared Step.
   - Count `serial_on_shared_file` between two wiring tasks as a `no_edge_to_code_when_interface` violation. That is iteration 8's F1, the serializer behind every iteration-8 critical path.
   - Pin the wiring-shared-entry mutation to `exact` once the skill fix (one entry module per pipeline) lands.
2. **Spine units by Writes and Reason, with call steps kept.** Fixes 6 records.
   - Change `dtrun.step_unit`, `wave_units` and `phase0_misses` (`dtrun.py:244-248, 360-362, 382-383, 400-401`).
   - Recognize a fold by structure, or by "fold" anywhere in the Reason, not only at its start (it7 rl inc).
3. **Probe-check precision.** Fixes 6 records.
   - `simulate.simulate_probes` sets `tasks/queued/` aside.
   - `probe_code_in_probe_turns` uses `turn_skill_map`.
   - `docs_before_probe` checks each probe against its own vendor's domain.
   - `probe_checks_cover` counts only source-delivery requirements.
   - `probe_not_guess` treats a decision as a source choice only when its heading picks the source.
4. **Strip heredoc bodies and quoted strings before matching commands.** Fixes 3 records, including both `no_secret_seen` false alarms on the security check.
   - Applies to `probefacts.secret_reads` and `runs_user_script`.
   - Flag reading verbs only.
5. **Skip rows to interface tasks** in `edges_mitigated` and `unmitigated_reasoned` (`grade.py:379,389`). Fixes 2 records.
6. **Spec regexes.** Fixes 3 records.
   - `spec_no_vendors` exempts vendors the persona names.
   - `spec_pca_mp` adds "eigenvalue", "components above the edge" and "factor model".
7. **`wave_width` numerator** (it7 F11, half fixed). Fixes 1 false pass.
   - Count a tester half only for a spine's or fold's split task, not a library thicken's.
8. **Read-implied order.** Fixes 1 false pass. This needs a new check.
   - It fails when a task's Read or Acceptance names a path that another task's Writes covers, with no Depends path between them (it7 quant aao T04/T03).
   - As with every new check, the user decides whether to add it.
9. **Singles, 1 record each:**
   - `call_step` reads "as in" as a reuse, not a call (`dtrun.py:238`).
   - `interface_writes_symbols` includes classes and types.
   - `*` fake globs expand against the contract.
   - `spine_writes_problem` treats files inside a folder owner as the owner.
   - `dtrun.defined_in` accepts the constructor and mirror forms (2 mixed records).
10. **Boundary lines in the grader.** Fixes the dt-only mutation.
    - `interface_coverage` (or `types_in_contract`) also requires a Boundary line with Cases on every type that crosses step owners in any pipeline, mirroring dt's `type-cases`.
    - Low priority: `dt_lint_clean` already catches it.
11. **Evidence lists in `metrics`.** `grade.py` cuts evidence to 600 characters, so the corpus can only pin early items with `must_match` and `must_not_match`. Full lists in `metrics` would let it pin every item.

**dt follow-ups the mutations confirm** (iteration 8's dt list, still open):
- `dt roadmap --check` errors on a Depends cycle.
- A lint for a decision Accepted while its probe is open.
- `boundaries_unfrozen` reports a type in a milestone step's In → Out that the interface leaves out.
