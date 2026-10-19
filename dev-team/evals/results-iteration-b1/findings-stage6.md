# Build eval iteration b1: stage 6 (rl9 projects, A3, n = 1)

Claude Code 2.1.302, every agent `claude-opus-5-5`, one run at a time. Each target is an iteration-9 rl planning project at "planning done", built from its own M1 plan with arm A3 (build skill, cap 6), its bar re-rendered by `port_bar.py` ([BUILD.md](../harness/BUILD.md), "Project targets"). Grading has no oracle: holdout, beliefs, mutants and the planted flaw are n/a. Runs: `dev-team-workspace/iteration-b1/<name>/`; pages here under the same names. Every run here predates the contract-gap fixes merged in 2a8b8e0.

## Runs

| Run | Plan | Tasks landed | Wall (s) | Cost ($) | Turns | Stop | Design checks |
|---|---|---|---|---|---|---|---|
| aborted-rl9-all-at-once-A3-r1-contracttest | all at once, 30 tasks | 1/30 | 4,409 | 36.17 | 7 | stalled | 14/17 |
| aborted-rl9-incremental-A3-r1-decision | incremental, 31 tasks | 0/31 | 886 | 5.37 | 7 | stalled | 12/16 |
| **rl9-incremental-A3-r1** | incremental, 31 → 32 tasks | **22/32** | 7,683 | 62.66 | 16 | max_turns | 15/17 |
| aborted-rl9-all-at-once-A3-r1-pkgscope | all at once, 30 tasks | 0/30 | 17,174 | 95.29+ | 11 (+1 killed) | stopped by the user | 12/16 |

The stage costs about $200. The last run was stopped in turn 12, in a loop that could land nothing (below); that turn's cost isn't counted.

## Go / no-go (interface-first-design.md §12, stage 6)

**No answer.** Stage 6 asks for a build-level answer to incremental vs all-at-once planning. Neither plan built M1, and what stopped them was mostly the bar port and the scripted persona, not the plans, so the two can't be compared. The incremental plan got furthest (22/32) once its contract problems were revised; the all-at-once plan landed its interface once, froze a contract test no builder could pass, and in the rerun never got past the gate.

## What stopped the builds (by cost)

1. **The gate couldn't run for either plan** (`pkg_scope`). Every rl9 task says `Package: rllab`; `dt claim` writes `.check_pkg=rllab`, and the re-rendered `check.sh`'s `pkg_scope` lists only the components, so `check.sh gate --pkg rllab` exits 64 and every interface attempt was rejected after building the whole interface (about 25 min each). The main session's way out is a build-setup Revise adding an `rllab` case: the first all-at-once run got there in turn 2 (4eb085c) and incremental in turn 8 (365ee31), after about 2,900 s of discarded builds. In the all-at-once rerun the persona answered the agents' escalation ("not a test: the gate itself can never pass") with "the test stands" and the main session's "Shall I run build-setup Revise?" with "continue", for 11 turns: 9 gate rejects, 5 TEST-WRONG escalations, 0 landed. `port_bar.py` missed it: its probe runs `check.sh gate` with no `--pkg`, and its `pkg_scope_vs_dependents` check compares against the architecture's components, not the plan's `Package:` values. The driver's stall stop missed it too: each failed attempt writes reject and escalate events, which count as progress.
2. **Scripted-persona gaps** decided both stalls and most lost turns. Stops it had no answer for: a TEST-WRONG blaming a frozen contract test (fixed, 267b68f); "pick one" options and "approved?" on a shown draft (fixed, b013817); and, still open, a TEST-WRONG or offer blaming the bar, a second escalation on the same claim (read as the finished contract change), several contract changes at once (one Revise asked per type, turns 9–12), a re-asked Revise for a type already revised (turn 16), and an approve pattern loose enough to approve a draft that didn't exist (turn 5). About 6 of incremental's 16 turns went to such answers; a perfect persona still needs 16–18 turns for that plan, so `max_turns` 16 is too small for a 31-task project.
3. **A contract test pinned the stubs** (all-at-once, first run). M1-T01 froze `tests/contracts/test_interface.py` with `test_step_stub_has_its_signature_and_names_its_task` and `test_step_class_has_its_constructor_and_names_its_task`: 36 rows asserting every step body still raises `NotImplementedError` naming its task, from the plan's acceptance "body `raise NotImplementedError("<its spine or wiring task>")`". No implementer could pass it; 19 escalated claims, about 1.45 of 1.97 agent-hours, were discarded. The incremental run's contract tests have no stub check but were rigid another way: `test_samples.py` requires the contract folders to match its list exactly, which blocked the re-freeze task M1-T32.
4. **The architecture didn't fit the bar** (incremental). M1-T01 couldn't freeze the contracts as written: `evaluate.evaluate` and `DQNAgent.__init__` took 7 parameters (CR-20 allows 5), and `compare.run_claims` took a `viz.Chart`, so compare imported viz against the layering (CR-24). Both were revised before the freeze (AD-17 4dbe063; AD-18 22791f7 with `EvalOptions`, an `ablation` literal and `Sequence[Path]` charts). An architecture-design check against CONSTRAINTS' limits would have caught them at planning.
5. **No review before the fan-out** (both plans have no barrier checkpoint). Incremental's six testers claimed 13 s after M1-T01 landed; four of them (T15, T20, T26, T29) found missing test seams within 30–150 s, which led to a post-freeze Revise (91bf90c) adding seams to TabularAgent, viz.Replay, DQNAgent and `reference`. Only `reference` got a re-freeze task (M1-T32, never landed); the M1-T15 and M1-T20 implementers grew the frozen TabularAgent and Replay classes in place, and DQNAgent was never re-frozen, which blocked T26. In all-at-once, nothing reviewed the stub-pinning test before six builders took it.
6. **`dt escalate` keeps one record per claim** (`scripts/devteam/commands/escalate.py:53`). Incremental's first M1-T01 agent escalated DQNAgent and then `evaluate` 6 s apart; the second overwrote the first, so turn 1 reported only `evaluate` and attempt 2 (413 s) rediscovered DQNAgent.

## rl9-incremental-A3-r1 in detail

| Phase | s | |
|---|---|---|
| Setup → first claim | 37 | |
| Interface M1-T01, claim → land | 6,109 | 8 attempts: 3 contract changes, 2 pkg_scope gate rejects (≈2,900 s of whole-interface builds thrown away) |
| Barrier review | 13 | none: T01 landed at 6,120, six testers claimed by 6,147 |
| Parallel phase 1 | 783 | 17 tasks and 2 tester halves landed; 5 escalations; peak 6 in flight |
| Post-freeze Revise, Replan, go | 387 | turns 9–14 |
| Parallel phase 2 | 312 | 4 tasks landed; 4 escalations |

16 rejects: escalated 14 (CONTRACT-CHANGE 10, NEEDS-DEP 3, TEST-WRONG 1), gate 2 (both rc 64); no harness, conflict, integration or writes rejects. The 10 tasks not landed: T21, T23, T24, T25 held by T28's NEEDS-DEP (its acceptance was already delivered by M1-T06); T26 blocked (DQNAgent not re-frozen); T27 and T32 escalated on files missing from their Writes; T29 waits on T32; T31 never reached. Tokens: 121 M cache read, 0.96 M output; M1-T01's 8 attempts alone used 54.7 M, more than the main session (47.5 M).

## The defects known before the runs

| Defect | Shown? | Cost |
|---|---|---|
| No barrier checkpoint in either plan | yes, both | the stub-pinning test reached six builders (all-at-once); four seam gaps found after the freeze (incremental) |
| 4 tasks per plan without a tests/unit path | incremental only: the turn-13 Replan fixed T28–T31 because `dt lint` flagged them | none |
| incremental's `pkg_scope` narrower than its architecture | yes, and all-at-once has the same gap for `rllab` | the costliest defect of the stage (above) |

## Grading notes

- `interface_changes` reports "none" for incremental, a false negative: `INTERFACE_PATHS` (`grade_build.py:50`) covers only `types.py`, `protocols.py` and `tests/contracts`, so it misses the frozen classes' modules. The real count is 4 contract revisions after the freeze and 2 classes grown in place.
- `golden_visible_pass_rate` 89/89 for incremental covers only the 22 of 71 golden cases an intent test names; the rest belong to unlanded tasks.
- `red_right_reason` 98/99 (one T30 test passed at the base); `no_stub_left` fails on the stubs of the unlanded wiring tasks.

## Harness changes

Made during the stage: the persona answers a TEST-WRONG that blames a frozen contract test with the main session's Replan, the go and a resolve (267b68f); it approves a draft shown for approval and takes a stated recommendation (b013817).

Needed before rl9 runs again:
- `port_bar.py` runs the gate once per plan `Package` at the base and fails setup on an unknown package.
- The driver stops when nothing lands for 3 turns, or when one task is rejected for the same reason 3 times running; `progress()` alone counts reject events as progress.
- Persona: a TEST-WRONG or offer that blames the bar (build-setup, `check.sh`, `pkg_scope`, CONSTRAINTS) gets "yes, run build-setup Revise"; escalations keyed on claim and time; all open contract changes taken together; an already-revised type goes straight to the re-freeze Replan; `APPROVE_ASK` limited to "do you approve …?".
- `max_turns` for an rl9 target of at least 24.
- The grader's `INTERFACE_PATHS` take the modules of every type the interface task froze.

dev-team: `dt escalate` should keep every escalation on a claim, not the last; build-planning's interface-task wording and the barrier checkpoint are in [contract-gap-proposals.md](../../design/contract-gap-proposals.md).

## Validity

- **n = 1 per plan, and no run finished.** The outcomes say more about the harness and the persona than about the two planning modes.
- **Runs before the merged fixes.** Shape-only contract tests, the interface review before building on it and the other contract-gap fixes (2a8b8e0) came after these runs. With them, the stub-pinning test is refused at the floor and an interface review runs before the fan-out, which would have changed both all-at-once runs.
- **The bar was re-rendered, not planned.** Both projects' bars came from a build-setup older than the build phase, whose `pkg_scope` names components only; `port_bar.py` kept those cases, and the build phase's `dt claim` passes the plan's package. So the `rllab` gap is the old bar meeting the new build, caught by neither port_bar nor the driver, not a planning-skill defect.
