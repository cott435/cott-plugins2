# dev-team2 evals

Multi-turn trajectories that plan two projects (`rl`, `quant`) from a raw idea to an approved build setup, in two modes:

- **incremental:** the simulated user reveals one stage at a time.
- **all-at-once:** every stage is in the first message.

Stages (from `harness/scenarios.json`): **rl** snake → fish → foraging; **quant** data → structure_portfolios → features_ml → forecasting_agents. Quant had six stages in the three-skill evals; statistics + classical portfolios and forecasting + agents are now merged, because each stage now runs through four more gates. The three-skill evals (iterations 1–4) are archived in [archive/three-skills/](archive/three-skills/README.md).

Each stage goes idea/brief → spec → architecture → pipelines → test plan (optional) → build plan. Build setup comes before the first build. Then the run is graded programmatically, mostly through `dt`, and the final docs can be compared by a blind judge. Design: [design/planning-stage.md §13](../design/planning-stage.md).

## Files (`harness/`)

| File | What it does |
|---|---|
| `driver.py` | Runs one trajectory: an agent session (`claude -p`, resumed each turn) plus a simulated user (Sonnet, no tools). The whole plugin is staged into `<out>/plugin/` and loaded with `--plugin-dir`. Commits the project after every turn as `turn N`. |
| `plugin.py` | Stages the plugin the way a real install gets it: `.claude-plugin/`, `hooks/`, `scripts/` (without dt's tests), and `skills/`. Then checks that every skill's `../../scripts/dt.py` and every hook path resolves, and runs `claude plugin validate`. |
| `permission_mcp.py` | A stdio MCP server used as `--permission-prompt-tool`. It answers the plugin guard's "ask" on `tests/fixtures/**/expected.json` (headless runs have nobody to ask) and logs each prompt. |
| `grade.py` | Writes `grading.json` with a stable `id` per check. Uses the run's own `dt` snapshot. |
| `dtprobe.py`, `dtrun.py` | Call `dt` and its parser for facts the CLI doesn't print as JSON: live spec IDs, pipelines, tasks, derived roadmap status. |
| `simulate.py` | Replan and Advance simulation on a copy of the final project. No model calls. |
| `docstats.py` | Doc sizes and history residue, plus pipelines, tests, contract and plan lines against the §3 budgets. |
| `package.py` | Lays the runs out in the skill-creator benchmark format, including one `dt context` packet per task. |
| `judge_prompt.py`, `blind_judge_prompt.md` | Fill the blind-judge prompt for an A/B pair of packaged runs. |
| `dryrun.py`, `fake_claude.py` | Checks that cost nothing (below). |
| `run.sh` | Runs trajectories in parallel, then grades, measures and packages them. |
| `scenarios.json` | Persona, project facts, stages and turn budgets. |

## Checks that cost nothing (run these first)

```bash
python3 evals/harness/plugin.py /tmp/dt-plugin                  # stage and validate the plugin
python3 evals/harness/simulate.py scripts/tests/fixtures/quant   # Replan/Advance modes on dt's sample project
python3 evals/harness/dryrun.py                                 # replay that sample one layer per turn, then grade it
CLAUDE_BIN=$PWD/evals/harness/fake_claude.py \
  python3 evals/harness/driver.py quant-all-at-once /tmp/fake/quant-all-at-once/with_skill   # driver loop, fake CLI
```

On the dry run, 39 of 50 checks pass. The 11 failures are expected, because the sample is a two-milestone project that is mid-build, not a finished four-stage run:
- M2 has no plan.
- There is no features milestone, so no Grow.
- M1-T01's code is already in `src/`.
- The brief is already Accepted when the replay first shows it.
- The quant content checks fail (null-hypothesis-testing, classical portfolios, out-of-sample).

## Smoke run (one turn, about $0.30)

```bash
MAX_TURNS=1 python3 evals/harness/driver.py rl-all-at-once ../dev-team2-workspace/smoke/rl-all-at-once/with_skill
```

Check `turns.json` → `session_init`. It should list the `dev-team2:*` skills, and `mcp_servers` should show `evalperm` connected. The driver prints a warning if no dev-team2 skill is listed.

## Full run

```bash
evals/harness/run.sh iteration-5                      # all four trajectories, in parallel
evals/harness/run.sh iteration-5 quant-incremental    # or just some of them
```

- **Output:** `$EVAL_WS/<iteration>/<trajectory>/with_skill/`. `EVAL_WS` defaults to `../dev-team2-workspace`. Each run folder holds:
  - `project/` (a git repo, one commit per turn) and `plugin/` (the snapshot used)
  - `turns.json`, `summary.json` and `grading.json`
  - `agent_stream.jsonl`, `permission_prompts.jsonl` and `doc_history.txt`
- **Packaged runs:** `<iteration>/bench/`.
- **Re-grade a run:** `python3 evals/harness/grade.py <run>`.
- **Environment variables:**
  - `AGENT_MODEL` (default `claude-opus-5-5`), `USER_MODEL` (default `sonnet`)
  - `COST_CAP_USD` (per run, default 150)
  - `MAX_TURNS`
  - `PLUGIN_SRC`, or `SKILLS_SRC` to overlay an older skill snapshot for an A/B run
  - `PERMISSION_PROMPTS=0` to leave the oracle prompts unanswered
- **Prerequisites:** `claude`, `python3` ≥ 3.9, `uv` and `jq`. build-setup stops without `uv` and `jq`. It also runs `uv lock`/`uv sync`, so it needs network access.

## Cost and turns

Past runs that stopped at the architecture (iterations 2–4, Opus agent, quant in six stages; see [archive/three-skills/](archive/three-skills/README.md)):

| Run | Turns | Agent cost | Wall clock |
|---|---|---|---|
| rl incremental | 17 | $7 | 27 min |
| quant incremental | 30 | $21 | 71 min |
| rl all-at-once | 7 | $3 | 10 min |
| quant all-at-once | 7 | $3 | 10 min |

`total_cost_usd` is cumulative over a resumed session. Older `summary.json` files summed it per turn and overstated cost about 10×; `grading.json` was right.

Through build-setup, each stage adds 3–4 gates (pipelines, tests, plan, and setup once), and the context grows longer. Rough expectations:

| Run | Expected turns | Turn budget | Expected cost | Wall clock |
|---|---|---|---|---|
| rl incremental | 40–60 | 120 | $25–45 | about 1.5 h |
| quant incremental | 50–75 | 150 | $40–80 | 2–2.75 h |
| rl all-at-once | 15–25 | 50 | $8–20 | |
| quant all-at-once | 14–22 | 50 | $7–17 | |

Quant's four stages are roughly 4.4 six-stage-era stages of work: the two merged stages each take about 20% more turns (bigger spec and architecture rounds), but the per-stage gates (idea, spec, architecture, pipelines, tests, plan) are paid four times instead of six. A full four-run iteration costs about $80–160, plus a few dollars for the simulated user. Runs go in parallel, so wall clock is about the length of quant incremental. `COST_CAP_USD` stops a runaway.

## What `grade.py` checks

These are the §13 assertions. Each is a named check in `grading.json`.

| id | Check |
|---|---|
| `dt_lint_clean` | `dt lint` has no errors |
| `spec_on_pipeline_or_deferred` | Every live spec ID is on a pipeline step or its Covers, or is Deferred in a plan |
| `phase0_spine` | Every pipeline of a planned milestone has a Phase 0 spine task (active and queued plans) |
| `tasks_well_formed` | `Read:` IDs resolve (`dt context` exits 0), size is M or smaller, and Mode follows the rule or gives a Reason |
| `context_packets_small` | Every `dt context` packet is under 2,000 lines |
| `doc_budgets` | No `dt lint` budget warnings, and the brief is 500 words or fewer |
| `roadmap_rows` | One roadmap row per stage, and `dt roadmap --check` exits 0 |
| `incremental_all_planned` / `upfront_m1_planned` | Incremental: every milestone has a plan. All-at-once: M1 has a plan and every later milestone is at least Designed |
| `brief_goals_stage_neutral` | 5 goals or fewer, none worded per stage |
| `quant_grow_at_features` | Incremental: the shape first becomes multi-package in the features_ml stage. All-at-once: the final shape is multi-package |
| `no_code_during_planning` | Nothing under `src/`, `tests/intent/` or `tests/unit/` in any turn, beyond empty or docstring-only files |
| `gate_discipline` | No turn adds 12 or more lines to two layers. The layers are brief/idea, spec, architecture, pipelines, tests, plan and setup |
| `skills_invoked`, `test_planning_invoked`, `plan_docs_approved`, `approval_after_user` | Every planning skill ran, and the docs ended Approved only after the user said yes |
| `sim_replan_1..5`, `sim_advance_1..3` | The Replan and Advance simulations below |

The define and design checks from iterations 1–4 are kept, with the same text.

**Replan and Advance simulation.** `simulate.py` runs this on a copy of the final project:
- **Replan:**
  1. Edit a step of a pipeline in the active milestone and set its `pipelines.md` back to Draft. Expect pipeline-design `revise`.
  2. While it's Draft, expect build-planning `blocked` (waiting for approval).
  3. Re-approve it with a later Last updated. Expect `replan`, with the doc in `changed_since_plan`.
  4. Mark a task `Blocked` too. Expect `replan`, with the task listed.
  5. Restore both files. Expect build-planning back to its starting mode.
- **Advance:**
  1. `dt tick` every todo item. Expect not `advance`, because the exit checkpoint is still open.
  2. Tick the exit checkpoint. Expect `advance`.
  3. Run `dt archive`. Expect the plan stubbed, the milestone derived Done, and lint clean.

## Blind judge

```bash
python3 evals/harness/judge_prompt.py quant <bench/.../outputs A> <bench/.../outputs B> /tmp/blind-quant.json > /tmp/prompt.md
```

Hand the prompt to a fresh agent session. Shuffle A and B yourself, and keep the key.

The rubric adds three items:
- `pipeline_clarity`: pipelines read as clear call paths.
- `layout_sensibility`: the layouts make sense.
- `task_buildability`: each task can be built from its `context__<task>.md` packet alone. The judge reads at least three packets per set.

## Known gaps

- **No full trajectory has run yet.** The one-turn smoke run passed on 2026-10-16 (Claude Code 2.1.292, $0.34): the plugin loads via `--plugin-dir` alongside `--setting-sources project,local`, `session_init` lists all seven `dev-team2:*` skills, and `evalperm` is connected. A separate probe showed the guard's "ask" under `bypassPermissions` goes to `evalperm`, which allows and logs it. Without `--permission-prompt-tool` (or with `--permission-prompts none`) an "ask" is denied. Hook events other than SessionStart and Stop appear in stream-json only with `--include-hook-events`, which the driver now passes.
- **Agent frontmatter hooks don't fire in headless runs in an untrusted folder** (they are skipped silently) unless the agents are passed with `--agents`, installed user-level, or the folder was trusted beforehand ([build-setup.md §11](../design/build-setup.md)). That only matters once evals cover building. Planning never runs the tester, implementer or reviewer agents.
- **Skill names are namespaced.** Plugin skills show up as `dev-team2:<skill>`, and the grader strips the prefix.
