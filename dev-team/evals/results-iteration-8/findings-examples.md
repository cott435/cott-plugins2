# Iteration 8: did moving the examples off the eval domains change quality?

Iteration 7's skill snapshot (`dev-team-workspace/iteration-7/*/with_skill/plugin`) still has the old examples, including a literal "RL Lab, Snake" pipeline example and a "quant M1" build plan. Iteration 8's snapshot has GridLoad/LeafLab and none of the banned terms. Each rewrite kept its lesson, shape and IDs. A few domain-neutral names survive in LeafLab (`RunDir`, `run_train`, `save_run`, `load_run`, `read_raw`, `write_report`), so they can't tell the two iterations apart.

## 1. Leakage

**Iteration 7 copied names from the old examples, mostly in rl.** Only names that appear in the old examples, not in the new ones and nowhere in iteration 8, are counted:

| Copied name | rl-inc | rl-all | quant-inc | quant-all |
|---|---|---|---|---|
| `make_env` | 19 | 3 | 0 | 0 |
| `make_agent` | 19 | 0 | 0 | 0 |
| `EnvSpec` | 0 | 10 | 0 | 0 |
| `CovMethod` | 0 | 0 | 0 | 6 |
| `mp_edge` | 0 | 0 | 2 | 2 |

- rl-incremental's PL-01 opens with the example's first two steps (`make_env` by name lookup).
- rl-all-at-once has a `core.EnvSpec` type section, which is the example's.
- quant-all-at-once has the example's `CovMethod` literal, and type sections mirroring its `data.Prices` / `stats.Returns` / `stats.Cov`.
- Iteration 8 has none of these.

**Some apparent copying isn't copying.** Iteration 8's quant-all-at-once never saw the quant example, yet still writes a `research.estimate_cov` heading, `n_obs` and `AgentConfig`, and the package name `rllab` appears in both iterations. These come from the domain, not the example. Golden-case titles and file layouts weren't copied in either iteration.

**Process wording is reused in both, which is intended.** "none: the smoke runs it" appears 62 times in iteration 7 and 138 in iteration 8.

**Iteration 8 has no GridLoad/LeafLab leakage.** A whole-word search of all docs and tasks found 0 hits for the domain terms (GridLoad, LeafLab, seasonality, Fourier, weather, meter, kWh, crop, CNN, confusion matrix, `core.Dataset`, `DatasetSpec`, `fit_batch`, `weights.pt`).

## 2. Quality on the patterns the examples teach

- **Interface task:** the same shape in both. Iteration 8 adds replay doubles, from the new `phase0.md` rule.
- **`**Boundary:**` lines rose:** rl-inc 15→27, rl-all 22→24, quant-inc 54→106, quant-all 35→55. `interface_coverage` went from 1/4 to 4/4. `types_in_contract` was 1/4 in both.
- **Spine/wiring/thicken shape:** `tasks_well_formed`, `step_tasks_small`, `frozen_interface_churn`, `sim_ready_3` and `dt_lint_clean` pass 4/4 in both iterations.
- **Dependency-graph tables:** `edge_table_consistent` passes 4/4 in both. The dominant edge kind changed from `code` to `order`, following the `tasks.md` rule change.
- **Across the 20 plan-shape checks:** 60/80 in iteration 7, 61/80 in iteration 8. Most of the movement has other causes: driver and `dt` fixes, probe checks that apply only in iteration 8, and the new rules.
- **One change may come from the examples:** rl-all-at-once went multi-package in iteration 8 (`rl_single_package` fails). Iteration 7 had a single-package RL example to follow. With n=1, that's a guess.

## 3. Verdict

**About the same quality, with the leakage gone.** The iteration-8 plans follow the interface-first patterns as well as iteration 7's did, without domain help. Confidence is low: there is one run per trajectory, and the domain change is confounded with rule, driver and probe changes in the same snapshot.
