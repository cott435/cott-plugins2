# Build evals

Do interface-first plans build faster and more correctly, and which part earns it: parallel dispatch, interface-first, or test-driven design? One fixed project, [minilab](fixtures/build/minilab/README.md), is built in several arms and graded deterministically. Design: [interface-first-design.md](../../design/interface-first-design.md) §9.2–§9.4. Nothing here has been run against a real model yet.

## Arms (`scenarios.json` → `arms`)

| Arm | Plan | Dispatch | TDD | Isolates |
|---|---|---|---|---|
| A0 | interface | serial, one agent, no subagents | solo | floor; with/without-design Δ |
| A1 | interface | serial orchestrator, one builder at a time | split | parallel dispatch (vs A3) |
| A2 | spine (today) | `Parallel:` groups, worktrees + merge + check agent | split | interface-first (vs A3) |
| A3 | interface | waves from `dt ready`, worktrees + merge + check agent | split | the proposal |
| A4 | interface | as A3 | solo (Mode overridden) | TDD (vs A3) |
| A5 (optional) | spine | serial | split | plan × dispatch interaction |

Each arm's prompt is `build_common_prompt` (commit convention, gates, who writes `tasks/`, oracle and contract-change rules, checkpoints) plus the arm's own text. Parallel arms run one workflow per checkpoint segment (`CLAUDE_CODE_WORKFLOWS=1`); serial arms set `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`.

## Files

| File | What it does |
|---|---|
| `build_driver.py <target> <arm> <out>` | Copies the fixture's `project/` and the arm's plan, stages the plugin, re-renders tester/implementer/reviewer from the staged build-setup templates, passes all agents with `--agents`, runs the orchestrator session turn by turn with the deterministic build persona, commits `turn N`, then draws the flow, grades and redraws |
| `grade_build.py <run>` | Every §9.2 metric into `grading.json` (expectations with a `category`, `summary` over design checks, `harness_summary` apart) |
| `dryrun_build.py [out]` | Fixture checks, a good replay of every arm from `solution/`, and five bad replays the grader must catch |
| `run_build.sh <iteration> [target] [arm …]` | Arms one at a time, order rotated per replicate (`REPLICATES`, default 3); writes `build_summary.json` |
| `permission_mcp.py` | `EVALPERM_POLICY=deny-oracle`: denies writes under `tests/fixtures/` and logs each decision (default `allow` keeps planning as it was) |
| `fake_claude.py` | `FAKE_MODE=build`: each turn replays the next checkpoint segment, so the whole loop runs for free |

## Conventions the grader reads

- **Commits:** `M1-T05 tester: …`, `M1-T05 implementer: …`, `M1-T05 solo: …`, `M1-T22 interface: …` for builders; `dt: …` (ticks, replans, findings) and `merge M1-T05: <branch>` for the orchestrator. Builder branches are `worktree-*`.
- **Gates:** `scripts/check.sh collect|gate --task <id>` appends a verdict to `.dt/gates/<id>.json` in the main checkout.
- **Plan at turn 0** is the plan graded for graph facts and claims; the final plan adds replanned tasks (the contract change).

## Checks (`grading.json` ids)

| Category | Checks |
|---|---|
| efficiency | `wall_clock`, `achieved_concurrency` (units' time overlap, else git commit spans); `extra.efficiency`: agent time, per-role units and tokens, parallel efficiency, planned vs achieved rounds |
| integration | `merge_conflicts` (`git merge-tree --write-tree` per recorded branch), `writes_respected` (advisory for `Files likely` plans), `builders_never_edit_tasks`, `no_rework`, `integration_failures` (failed wiring/system gates), `interface_changes` (≤ 1, classed missing field / wrong type / wrong boundary), `planted_flaw_contract_change` |
| correctness | `golden_visible_pass_rate`, `holdout_pass_rate` (the grader's own runs), `planted_beliefs_caught` (0–3), `oracle_unchanged` |
| tdd | `mutant_kill_rate` (final suite on `solution/` + each mutant), `suite_agrees_with_solution`, `red_right_reason` (each tester commit run on its own tree: AssertionError, NotImplementedError or DID NOT RAISE), `red_import_errors`, `split_tester_first`, `protected_edits_landed`, `protected_edit_attempts` |
| process | `gates_pass`, `milestone_built`, `no_stub_left`; `extra.process`: escalations, human interventions, checkpoint findings |
| harness | `agent_errors`, `worktrees_merged`, `gates_recorded`, `work_committed_by_agents`, `flow_drawn` (never counted against the design) |

Cross-arm effects (A3 wall ≤ 0.5 × A1, …) are read from `build_summary.json`, not graded per run.

## Running

```bash
python3 evals/harness/dryrun_build.py                     # free: fixture, 6 good replays, 5 bad replays caught
CLAUDE_BIN=$PWD/evals/harness/fake_claude.py FAKE_MODE=build \
  python3 evals/harness/build_driver.py minilab A3 /tmp/b/minilab-A3-r1/with_skill   # free: the driver loop
evals/harness/run_build.sh iteration-b1 minilab A0 A3      # real: stage 4 (n=3 unless REPLICATES=1)
```

Env: `AGENT_MODEL` (pinned; the Claude Code version is recorded), `COST_CAP_USD` (60 per run), `MAX_TURNS` (target's, 12), `TURN_TIMEOUT` (5400 s), `PRESSURE=1`.
