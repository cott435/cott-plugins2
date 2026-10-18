# Iteration 8: the iteration-7 fixes, the api-probe skill, examples off the eval domains

## Run conditions

- **Skills:** branch `interface-first-design` at `3bfb11d`, staged into each run at 16:23. This covers:
  - the iteration-7 fix groups;
  - the `api-probe` skill;
  - examples rewritten into GridLoad and LeafLab.
- **Grader:** the checkout at grading time (18:47; harness last changed in `d9a759e`). Commits landed on the branch during the run (`d9a759e` to `01ccb79`: plan map, spec-writing, 0.4.0, build design). Of those, only the harness and plan-map changes affect these results.
- **Models:** Opus 5.5 agent, Sonnet simulated user, Opus 5.5 blind judge in both orders.
- **Scope:** n=1 per trajectory, no cost cap, run on 2026-10-17.
- **Where the runs are:** raw runs in `../../../../dev-team-workspace/iteration-8/`, packaged runs in `bench/` there.

**Before the run:** the one-turn smoke run cost $0.22. All nine `dev-team:*` skills were listed (`api-probe` included), and `evalperm` was connected.

**This is the last single-context iteration.** The driver resumed one agent session for every turn, so every skill ran in one growing context.
- Both quant runs reached the 1M window and auto-compacted (quant incremental before turn 42, quant all-at-once before its build-setup turn).
- Iteration 7 peaked at 323k–943k tokens.
- **Cost, and the incremental-vs-all-at-once deltas on cost and context, are confounded by carried history.** Re-priced with a fresh session per skill run, context tokens fall to 15–26% of actual (37–58% with a re-read allowance). See findings-flow F9.
- Iteration 9 runs a fresh session per skill run (fix plan, group 0).

**Flow pages** (workflow-analyzer, drawn at the end of `run.sh` and copied here in the workspace's layout):
- all runs: [runflow/index.html](runflow/index.html), and each run against iteration 7, e.g. [quant-all-at-once-vs-iteration-7.html](runflow/quant-all-at-once-vs-iteration-7.html)
- one run: [rl-incremental](rl-incremental/with_skill/flow/flow.html), [rl-all-at-once](rl-all-at-once/with_skill/flow/flow.html), [quant-incremental](quant-incremental/with_skill/flow/flow.html), [quant-all-at-once](quant-all-at-once/with_skill/flow/flow.html)
- the plan map's M1 build view: `<trajectory>/with_skill/flow/plan/M1.html`, e.g. [rl incremental M1](rl-incremental/with_skill/flow/plan/M1.html)

**Detail reports:**
- [findings-interface.md](findings-interface.md): the interface-first checks, F1–F14, plus R6–R8. Cited here as interface-F#.
- [findings-flow.md](findings-flow.md): run flow, probes, secrets, the older checks, cost and context. Cited as flow-F#.
- [findings-judge.md](findings-judge.md): blind judge and mode comparison, J1–J4.
- [findings-examples.md](findings-examples.md): the effect of moving the examples off the eval domains.

## Results

| Run | Checks | Turns | Agent cost | Wall clock | Milestones | Stop | Judge (both orders) |
|---|---|---|---|---|---|---|---|
| rl incremental | 61/67 | 41 | $25.19 | 63 min | 6 | finished | **7.7** |
| rl all-at-once | 59/67 | 20 | $15.44 | 42 min | 6 | finished | 7.25 |
| quant incremental | 69/89 | 68 | $58.44 | 143 min | 14 (5 stages) | finished | **7.8** |
| quant all-at-once | 80/90 | 41 | $39.97 | 87 min | 8 | finished | 7.45 |

- **Against the baseline** (iteration 7 re-graded, `../results-iteration-7/regraded/`): 58, 64, 71 and 67. Rough estimates with the grader false positives below removed: 62/67, 61/67, 73/89 and 83/90.
- **Total:** $139.04 for the agents, +35% on iteration 7. quant all-at-once doubled: about 16 extra turns and $12.80 went to a probe loop caused by a driver bug (flow-F2).
- **M1:**

  | Run | Critical path (iteration 7) | Widest wave (iteration 7) | N/CP |
  |---|---|---|---|
  | rl incremental | 8 (6) | 18 (8) | 3.38 |
  | rl all-at-once | 7 (5) | 12 (16) | 3.29 |
  | quant incremental | 6 (6) | 26 (21) | 6.33 |
  | quant all-at-once | 5 (8) | 17 (19) | 5.0 |

- **Judge:** incremental wins both projects in both orders (margins 0.45 and 0.35, above the ~0.3 position bias). In iteration 7 both projects were ties.
- **Examples off the eval domains:** quality about the same. The iteration-7 leakage (`make_env`, `make_agent`, `EnvSpec`, `CovMethod`) is gone, and there are 0 GridLoad/LeafLab hits in any plan.

## Re-graded with iteration 9's grader

[regraded/](regraded/) holds the four runs graded by the self-tested grader (commit `7fc015d`: fixes 1–6 from [grader-selftest.md](grader-selftest.md)). `../results-iteration-7/regraded/` is refreshed with the same grader, so both are iteration 9's baselines.

| Run | Original | Re-graded | Iteration 7, re-graded |
|---|---|---|---|
| rl incremental | 61/67 | 60/67 | 59/67 |
| rl all-at-once | 59/67 | 61/67 | 64/67 |
| quant incremental | 69/89 | 78/91 | 71/81 |
| quant all-at-once | 80/90 | 85/92 | 67/81 |

- **The false positives are gone.** `no_secret_seen`, `runner_split`, `phase0_split` (all four runs), `wave_width`, `tester_starts_early`, `plan_blocked_while_open`, the probe-precision checks, `spec_no_vendors` and `spec_pca_mp` now pass where they were ruled grader faults.
- **New fails are real.** rl incremental's `unmitigated_reasoned` was a false pass and now fails: wiring waits on library thickens (interface-F3).
- **Three grader-reason failures remain** (fix 9 in grader-selftest.md): quant inc `no_edge_to_code_when_interface` ("as in PL-06"), rl inc `tester_starts_early` (contract classes) and quant aao `fakes_only_cross_pipeline` (the `data.load_*` glob). With those, iteration 8 still doesn't meet its "no grader-reason failure" bar.
- **Two quant checks are new and don't apply to the iteration 7 and 8 runs.** `data_sources_suggested` (both iterations) and `crosscheck_facts_reached_design` (iteration 8) fail on runs whose user never named yahooquery or asked for sources. Leave them out when comparing with iteration 9.

## Iteration 8 against its bar

| Criterion | Result |
|---|---|
| All four trajectories finish, no `stalled` | **Met.** All four `finished`, including rl incremental, which stalled in iteration 7 |
| Every stage has milestone rows in both modes | **Met.** All-at-once designed every stage: every `pipelines.md` Approved, `uncovered_ids: none` |
| No interface-first check fails for a grader reason | **Not met.** 10 check-runs fail for grader reasons only (interface-F4–F9). The probe family also has false positives: `no_secret_seen` in both quant runs, `runner_split`, `plan_blocked_while_open`, `docs_before_probe`, `probe_checks_cover`, and part of `probe_not_guess` (flow-F5, F6) |
| rl incremental M1 critical path ≤ 4, widest wave ≥ 12 | **Width met (18), critical path missed (8).** Without the wiring→wiring edges it would be 4 (interface-F1) |
| quant all-at-once critical path ≤ 5 | **Met (5)**, down from 8 |
| Mode delta in band, or each miss explained as a mode effect | **Not met.** Max width is out in both projects and N/CP in quant (21%). The misses come from defects (rl all-at-once's multi-package split, interface-F14; quant all-at-once's Stage 1 cut by layer, J1), not acceptable mode effects. The must-pass checks fail for real defects in both modes (interface-F10, F11). Cost and context deltas are confounded (above) |

## Findings by owner

### Fixed since iteration 7

- **Object boundaries** (iteration-7 interface F1): replay doubles are in every run.
  - rl incremental's wave 1 went from 8 to 18 tasks, and its `no_edge_to_code` violations from 10 to 0.
- **Shared thicken modules** (F2): no thicken→thicken chains are left, and quant all-at-once's critical path went from 8 to 5.
- **Also fixed:** cross-runtime types (F5), interface_coverage (F8, 4/4), fakes across packages (F10), milestone_depends parsing (F12) and no_edge_to_code (F13).
- **Run flow:** rl incremental no longer stalls; all-at-once designs every stage (flow-F3); stages get cut (flow-F1).
- **Plan map:** R1–R5 landed.

### Design (`design/interface-first-design.md`)

- **The new critical-path setter (interface-F1).** Every wiring task of a package writes the same `pipeline.py` and `__main__.py`, so the wiring tasks chain. That adds +4, +3, +1 and +1 to the critical path.
  - §4.1 and §5.1 must make the entry modules and `__main__.py` shared modules written by the interface task.
  - Two wiring tasks never share an entry module.
- **§11.2 (interface-F3): decide how library classes behind a factory step are handled.** Either they become their own steps with spines, or the interface task writes trivial real implementations. In rl incremental, wiring waited on 9 library thickens.
- **Probes (interface-F11):** a step blocked on a probe gets a milestone stand-in behind its Protocol. quant incremental invented `sources/synthetic.py`.

### Skills (`skills/**`)

- **pipeline-design and build-planning:**
  - one entry module per pipeline; the interface task writes `__main__.py` (interface-F1);
  - wiring depends on spines and folds only (F3);
  - a fold is Kind thicken (F11);
  - the interface declares every type in a milestone step's In → Out (F12).
- **architecture-design:**
  - a function used by another package or pipeline gets a Boundary line and a fake (interface-F2, rl all-at-once's unfaked `learn.train`);
  - nested field types are defined (F10);
  - contract size and in-package dependency direction aren't reasons to split packages (F14, rl all-at-once's 4 packages);
  - at approval, a decision whose probe isn't Answered or Waived stays Proposed. quant incremental Accepted AD-04 and AD-05 with their probes Ready (flow-F6).
- **build-planning:**
  - Depends holds only needed milestones, never build-order notes. quant incremental's notes made a dt cycle (interface-F13, flow-F8).
  - Test-command fixes go to test-planning (flow-F7).
  - While blocked on probes, offer one queued plan, not one per milestone ($6 on M4–M8, flow-F2).
- **api-probe:**
  - A missing or unknown step writes evidence with error kind `usage`.
  - The README states cross-probe order.
  - After two "ran it" with unchanged evidence, offer to waive or pause.
  - When the user gives test facts, one check covers them (flow-F2, §2).
- **idea-refine Extend:** a new stage never adds a goal. quant incremental's brief reached 8 goals and 514 words (flow-F8).
- **test-planning:** cap web verification of user-given facts (132 web calls, $7.22 in one turn, flow-F9).
- **Data sources:** both quant plans suggest only price sources, never a fundamentals source. quant incremental put fundamentals out of scope. The new `data_sources_suggested` check (on the plan-driver branch) fails both runs. Whether a skill should prompt for fundamentals is open: wait for iteration 9's result before changing a skill.

### dt (`scripts/**`)

- Lints:
  - two wiring tasks writing one entry module or `__main__.py` (interface-F1);
  - a contract function used across packages with no Boundary line (F2);
  - a decision Accepted while its probe is open (flow-F6);
  - a brief budget of 500 words and 5 goals (flow-F8).
- `dt roadmap --check` errors on a Depends cycle; `Milestone.depends` reads only IDs outside parentheses (interface-F13, flow-F8).
- `model.spine_pipeline` counts a system task for the pipelines it names; `boundaries_unfrozen` reports milestone In → Out types missing from the interface (interface-F4, F12).

### Harness: driver (`evals/harness/driver.py`)

- **The plan-driver branch covers:**
  - a fresh session per skill run, chosen by `dt next` (flow-F9, F7);
  - probe steps run from the README (flow-F2);
  - keys mapped only to the vendor they name (flow-F4);
  - yahooquery named as the cross-check, with a fake Yahoo behind an HTTPS proxy (both modes picked different, unfaked cross-check vendors);
  - `data_sources_suggested`.
- **Still to do:**
  - Detect "ran it" from a structured field, not a regex (flow-F3).
  - Tell the simulated user each step's rc (flow-F3).
  - Ask to run a Ready probe that blocks a revealed stage (flow-F3; quant incremental never ran its probes).
  - Route `sharadar.com` through the proxy too: public.py hit the live vendors, and the fake Sharadar got 0 requests (flow-F4).
  - A closing turn that only approves (flow-F8: `CONSTRAINTS.md` ended Draft).
  - No re-ask for a doc the user's current message approves (flow-F1).
  - A per-turn marker in `agent_stream.jsonl` (flow-F6 turn drift).

### Harness: grader (`grade.py`, `dtrun.py`, `probefacts.py`, `probegrade.py`, `simulate.py`)

- **Interface family:**

  | Fix | Finding |
  |---|---|
  | Units by spine Writes or Reason; call steps kept; spines matched by unit | interface-F4 |
  | `interface_writes_symbols` includes classes and types | F5 |
  | Skip graph rows to an interface task | F6 |
  | Only "PL-NN as built" counts as a call | F7 |
  | Expand `*` globs | F8 |
  | Accept constructor and "mirrors" type forms | F10 |
  | Owner-folder Writes | F11 |
  | Tighten the `order` and `same_step_unit` leniencies; check wiring `file` rows for a missing fake | F1–F3 |
  | Print full evidence lists | Smaller |

- **Probe and secret family:**
  - `secret_reads` and `runs_user_script` skip heredoc bodies, quoted strings and non-reading commands (flow-F5, interface-F9). **The canary was never seen.**
  - Turn numbering from driver markers (flow-F6).
  - `probe_code_in_probe_turns` by `turn_skill_map`.
  - `plan_blocked_while_open` also sets aside `tasks/queued/`.
  - `probe_checks_cover` counts only the source-delivery requirement.
  - `docs_before_probe` uses each probe's own vendor domain.
  - `probe_not_guess` counts only source-choice decisions.
- **Older checks:** `spec_no_vendors` exempts vendors the user names (Sharadar, and yahooquery once it's in the facts). `spec_pca_mp` accepts "eigenvalues" and "components above the edge" (flow-F8).
- **Judge:** run judges read-only (`claude -p`, Read/Glob/Grep), with the key out of their reach (J4).

### workflow-analyzer (`workflow-analyzer/scripts/planmap.py`)

- `reason_class` tests `file` and integration before `order`. rl incremental's tile swaps 18 and 4 and hides the interface-F1 chain (R6).
- Draw every tied critical path (R8).
- The widest-wave tile shows boxes and whole tasks (R7).
- Mark wiring→wiring shared-entry edges.

## Fix plan for iteration 9

Each group writes disjoint files, so groups 1–5 run in parallel once group 0 has merged.

0. **Merge the plan-driver work first:**
   - `refs/heads/claude/plan-driver-26137f`: `dt next`/`dt route`, fresh session per skill run, `/dev-team:plan`, PURPOSE.md, yahooquery and the Yahoo proxy fake, README probe steps, `vendor_env`, `data_sources_suggested`;
   - `refs/heads/claude/tool-calls-turn-split`: turn attribution.

   Its PURPOSE.md edit conflicts with `e52929b` on this branch. Then re-grade iteration 8 with the fixed grader (group 4), so iteration 9 compares like for like.
1. **Design:** entry modules and `__main__.py` as shared modules (F1), §11.2 library classes (F3), probe stand-ins (F11), and §9.1 type forms (F10).
2. **Skills:** the skill items above.
3. **dt:** the dt items above.
4. **Harness:** the remaining driver items and every grader item above, plus judge blinding.
5. **workflow-analyzer:** R6–R8 and the shared-entry edges.

## Iteration 9 is done when

- All four trajectories finish and every stage has milestone rows in both modes, with a fresh session per skill run.
- No check fails for a grader reason, in the interface family or the probe family. `no_secret_seen` fails only on a real read.
- rl incremental's M1 critical path is ≤ 4 with widest wave ≥ 12. quant all-at-once's critical path stays ≤ 5. No wiring→wiring chain sets a critical path.
- Each quant run's Sharadar and Yahoo probes run through the fakes, and at least one planted fact reaches the design.
- The mode delta is in band, or each miss is explained as a mode effect. Cost and context deltas can be compared because no history is carried between skills.
