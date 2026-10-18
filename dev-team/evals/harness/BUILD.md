# Build evals

Do interface-first plans build faster and more correctly, and which part earns it: parallel dispatch, interface-first, or test-driven design? One fixed project, [minilab](fixtures/build/minilab/README.md), is built in several arms and graded deterministically. Design: [interface-first-design.md](../../design/interface-first-design.md) §9.2–§9.4 and §12, [build-phase.md](../../design/build-phase.md) §15.

## Arms (`scenarios.json` → `arms`)

Every arm but A0 runs dev-team's `build` skill (Run mode) in one headless session, with the go in the opening prompt.

| Arm | Plan | Dispatch | Isolates |
|---|---|---|---|
| A0 | `plan-interface` | one session, no subagents, plan order: `dt context`, `check.sh collect`/`gate`, `dt tick`, a commit with a `Dt-Landed:` trailer | the floor; with/without-design Δ |
| A1 | `plan-interface` | build skill, `--cap 1` | parallel dispatch (vs A3) |
| A2 | `plan-spine` (the legacy cut converted for dt) | build skill, cap 6 | interface-first (vs A3) |
| A3 | `plan-interface` | build skill, cap 6 | the proposal |
| A4 | `plan-interface-solo` (every task solo) | build skill, cap 6 | TDD (vs A3) |
| A3-RT | `plan-interface-pertask` (a checkpoint after every task) | build skill, cap 6 | per-task vs per-phase review |
| A3-WF | `plan-interface` | build skill, cap 6, the loop run by a Workflow script from `dt build workflow M1 --cap 6` (`CLAUDE_CODE_WORKFLOWS=1`, `Workflow` allowed): dispatch, land and status are low-effort agents, builders and reviewers agents of their type in worktrees; the session handles each stop and runs it again ([smoke test](../../design/evidence/2026-10-18-workflow-smoke.md)) | a generated workflow vs the main-session driver |

## Project targets (a planning run's own plan)

A target with `"project": <abs path>` (and `"port_bar": true`) instead of `fixture` builds a planning eval's project at "planning done" on its own plan: `rl9-all-at-once` and `rl9-incremental` (iteration 9's rl runs, M1, 16 turns, n = 1). Their bars came from a build-setup older than the build phase, so `port_bar.py <project> <dest> [--plugin <root>]` clones the project's default branch into `<dest>` (renamed `main`, no remote) and re-renders the templates build-setup regenerates whole (check and hook scripts, the three agents, `.claude/settings.json` merged, `.gitignore` lines appended, CONSTRAINTS.md with its own Status line), every placeholder value read back from the project's own rendered files; `pyproject.toml`, `uv.lock`, the vulture whitelist and `tests/conftest.py` are kept. Then `uv sync` (`--no-install-project` while no package module exists: the interface task writes it), a commit, `dt base` and a commit, and it reports `dt status --skill build-setup`, `dt lint`, `check.sh gate` at the base (and with only the package's `__init__.py` added, as a probe) and the plan's shape. The arm's `plan` is ignored. Grading has no oracle: holdout, mutants and the planted flaw are `na`; correctness is the build's own `tests/intent` on build/M1's tree, every marker, and `oracle_unchanged` over `tests/fixtures`.

## How a run goes (`build_driver.py <target> <arm> <out>`)

1. Stage the plugin into `<out>/plugin/`; make the project with the staged plugin's build-setup templates (`fixtures/build/minilab/scripts/make_live.py`: the real bar, the arm's plan, `dt base`; a project target: `port_bar.py`, its report in `<out>/port_bar.json`).
2. One session, resumed at each stop: `claude -p --plugin-dir <plugin> --add-dir <plugin> --agents <rendered agents, hooks included> --allowedTools <rendered allow rules> --permission-mode acceptEdits --output-format stream-json`, every model `AGENT_MODEL`. A turn's outcome is its last `result` event.
3. The rendered allow rules plus `git add` and `git commit`, each git rule also in its `git -C <dir>` form, with `status`, `log`, `diff` and `show` (Opus writes that form) (a headless run has no one to approve the commits of an approved Revise or Replan; A0 also `git update-ref`). A scripted persona answers each stop from the project's state: a CONTRACT-CHANGE gets a yes, architecture-design Revise, build-planning Replan, then the go; a TEST-WRONG gets `--test-stands`, unless it blames a frozen contract test (`tests/contracts/…/test_*.py`): then the main session's Replan that rewrites it is approved, the go given and the held tasks resolved; a Critical is resolved; a blocked half is retried once; the exit is approved with no fix tasks (Important findings counted) and no merge.
4. After each turn the tree at HEAD is chained as `turn N` on `refs/eval/turns` (the plan map's snapshots); build/M1 is never touched by the driver.
5. The run ends at the exit, the turn budget, or three turns with nothing new in `log.jsonl` or on a branch. Then `runviz.py --run` (flow and plan map), `grade_build.py`, and the flow again with the checks.

## What the grader reads (`grade_build.py <run>`)

| Source | Gives |
|---|---|
| `Dt-Landed:` trailers on build/M1's first parent and on `dt/<task>-tests` | tasks and roles landed, each landing's diff (A0 writes its own trailers: weaker evidence) |
| `.git/dt-build/log.jsonl` | concurrency (claims in flight, claim → finished), rejects by kind (`conflict`, `writes`, `integration`, `gate`, `harness`) with their detail files, escalations, resolves, reviews |
| each tester landing's tree | red for the right reason, the intent tests run there |
| stream `permission_denials`, subagent transcripts | protected-test edit attempts (with `writes` rejects on protected paths) |
| `oracle/`, `holdout/`, `mutants/` | golden pass rates, planted beliefs caught, mutant kill rate (pytest in the project's venv) |
| stream `result` events, `flow/index.json` | wall clock, cost, tokens per role |

Checks per category: efficiency `wall_clock`, `achieved_concurrency`; integration `merge_conflicts`, `writes_respected`, `builders_never_edit_tasks`, `integration_failures`, `interface_changes` (≤ 1), `planted_flaw_contract_change`; correctness `golden_visible_pass_rate`, `holdout_pass_rate`, `planted_beliefs_caught`, `oracle_unchanged`; tdd `mutant_kill_rate`, `suite_agrees_with_solution`, `red_right_reason`, `red_import_errors`, `split_tester_first`, `protected_edits_landed`, `protected_edit_attempts`; process `milestone_built`, `gates_pass`, `no_stub_left`; harness `agent_errors`, `harness_rejects`, `main_checkout_clean`, `flow_drawn` (never counted against the design). Cross-arm effects (A3 wall ≤ 0.5 × A1, …) are read from `build_summary.json`.

## Running

```bash
python3 evals/harness/dryrun_build.py                     # free: fixture and real-bar checks, every arm's good replay through the real dt, 5 bad replays caught
CLAUDE_BIN=$PWD/evals/harness/fake_claude.py FAKE_MODE=build \
  python3 evals/harness/build_driver.py minilab A3 /tmp/b/minilab-A3-r1/with_skill   # free: the driver loop
REPLICATES=1 evals/harness/run_build.sh iteration-b1 minilab A0 A1 A3      # real: stage 4
```

Env: `AGENT_MODEL` (pinned for every agent; the Claude Code version is recorded), `MAX_TURNS` (target's, 12), `TURN_TIMEOUT` (5400 s), `PRESSURE=1`, `REPLICATES`, `FIRST_REPLICATE`. No cost cap. Pages and gradings are copied into `evals/results-<iteration>/`.
