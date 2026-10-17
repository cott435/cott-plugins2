# dev-team evals

Multi-turn trajectories that plan two projects (`rl`, `quant`) from a raw idea to an approved build setup, in two modes:

- **incremental:** the simulated user reveals one stage at a time.
- **all-at-once:** every stage is in the first message.

Stages (from `harness/scenarios.json`): **rl** snake → fish → foraging; **quant** data → structure_portfolios → features_ml → forecasting_agents. Quant had six stages in the three-skill evals; statistics + classical portfolios and forecasting + agents are now merged, because each stage now runs through four more gates. The three-skill evals (iterations 1–4) are archived in [archive/three-skills/](archive/three-skills/README.md).

Each stage goes idea/brief → spec → architecture → pipelines → test plan (optional) → build plan. Build setup comes before the first build. Quant also exercises references and stage-level skill routing ([design/references.md](../design/references.md) §10): the user's three reference files arrive with the stage they serve and go through `reference-intake`, and the `data-analysis` and `null-hypothesis-testing` project skills are routed per milestone. Then the run is graded programmatically, mostly through `dt`, and the final docs can be compared by a blind judge. Design: [design/planning-stage.md §13](../design/planning-stage.md).

## Files (`harness/`)

| File | What it does |
|---|---|
| `driver.py` | Runs one trajectory: an agent session (`claude -p`, resumed each turn) plus a simulated user (Sonnet, no tools). The whole plugin is staged into `<out>/plugin/` and loaded with `--plugin-dir`. Commits the project after every turn as `turn N`. Records each turn's top-level Agent launches (`agents` in `turns.json`). |
| `plugin.py` | Stages the plugin the way a real install gets it: `.claude-plugin/`, `hooks/`, `scripts/` (without dt's tests), and `skills/`. Then checks that every skill's `../../scripts/dt.py` and every hook path resolves, and runs `claude plugin validate`. |
| `permission_mcp.py` | A stdio MCP server used as `--permission-prompt-tool`. It answers the plugin guard's "ask" on `tests/fixtures/**/expected.json` (headless runs have nobody to ask) and logs each prompt. |
| `grade.py` | Writes `grading.json` with a stable `id` per check. Uses the run's own `dt` snapshot. |
| `dtprobe.py`, `dtrun.py` | Call `dt` and its parser for facts the CLI doesn't print as JSON: live spec IDs, pipelines, tasks (with Skills), derived roadmap status and milestone Skills, reference entries. |
| `simulate.py` | Replan and Advance simulation on a copy of the final project. No model calls. |
| `docstats.py` | Doc sizes and history residue, plus pipelines, tests, contract and plan lines against the §3 budgets. |
| `package.py` | Lays the runs out in the skill-creator benchmark format, including one `dt context` packet per task. |
| `judge_prompt.py`, `blind_judge_prompt.md` | Fill the blind-judge prompt for an A/B pair of packaged runs. |
| `dryrun.py`, `fake_claude.py` | Checks that cost nothing (below). |
| `run.sh` | Runs trajectories in parallel, then grades, measures and packages them. |
| `scenarios.json` | Persona, project facts, stages, turn budgets, and per project the skill stubs (`project_skills`) and reference files per stage (`references`). |
| `stub_*_SKILL.md` | Project skill stubs installed in the run's `.claude/skills/`: `null-hypothesis-testing` (both projects), `data-analysis` (quant). |
| `references/quant/` | The user's reference code (never run): `market_decomposition.py` (PCA market removal, fit on the full sample: a deliberate look-ahead caveat) for structure_portfolios; `tft_dataset.py` and `tft_targets.py` for forecasting_agents. The driver copies them into the project's `references/` when that stage is revealed (all at the start in all-at-once) and says so in the user's message. |

## Checks that cost nothing (run these first)

```bash
python3 evals/harness/plugin.py /tmp/dt-plugin                  # stage and validate the plugin
python3 evals/harness/simulate.py scripts/tests/fixtures/quant   # Replan/Advance modes on dt's sample project
python3 evals/harness/dryrun.py                                 # replay that sample one layer per turn, then grade it
CLAUDE_BIN=$PWD/evals/harness/fake_claude.py \
  python3 evals/harness/driver.py quant-all-at-once /tmp/fake/quant-all-at-once/with_skill   # driver loop, fake CLI
```

The dry run replays the fixture's `references/` and `docs/references.md` as a reference-intake turn (with one fake Agent launch per file) before the M2 idea. To exercise the driver's reference copying and Agent parsing, run the fake loop on `quant-all-at-once` with `MAX_TURNS=5`: turn 4 is the intake layer and should record one launch per file.

On the dry run, 46 of 58 checks pass. The 12 failures are expected, because the sample is a two-milestone project that is mid-build, not a finished four-stage run:
- There is no features milestone, so no Grow.
- M1-T01's code is already in `src/`.
- The brief is already Accepted when the replay first shows it.
- The quant content checks fail (null-hypothesis-testing, classical portfolios, out-of-sample).
- The sample's PCA reference serves its M1 (data + stats), not the structure_portfolios milestone, and its M2 has no `**Skills:**` line (`refs_milestones`, `skills_on_structure_tasks`).

## Smoke run (one turn, about $0.30)

```bash
MAX_TURNS=1 python3 evals/harness/driver.py rl-all-at-once ../../dev-team-workspace/smoke/rl-all-at-once/with_skill
```

Check `turns.json` → `session_init`. It should list the `dev-team:*` skills, and `mcp_servers` should show `evalperm` connected. The driver prints a warning if no dev-team skill is listed.

## Full run

```bash
evals/harness/run.sh iteration-5                      # all four trajectories, in parallel
evals/harness/run.sh iteration-5 quant-incremental    # or just some of them
```

- **Output:** `$EVAL_WS/<iteration>/<trajectory>/with_skill/`. `EVAL_WS` defaults to `../../dev-team-workspace`. Each run folder holds:
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
| quant incremental | 55–85 | 150 | $45–90 | 2.25–3 h |
| rl all-at-once | 15–25 | 50 | $8–20 | |
| quant all-at-once | 16–26 | 50 | $9–20 | |

Reference intake adds about 2 turns each time files arrive (draft with milestone questions, then approval): twice in quant incremental (structure_portfolios, forecasting_agents), once in all-at-once. idea-refine's skill-routing question and offering unassigned references add about one more per quant stage when they can't ride on an existing answer. The intake subagents read 85–105-line files, so they cost cents; the extra cost is mostly the longer resumed context. Budgets stay at 150 and 50.

Quant's four stages are roughly 4.4 six-stage-era stages of work: the two merged stages each take about 20% more turns (bigger spec and architecture rounds), but the per-stage gates (idea, spec, architecture, pipelines, tests, plan) are paid four times instead of six. A full four-run iteration costs about $85–175, plus a few dollars for the simulated user. Runs go in parallel, so wall clock is about the length of quant incremental. `COST_CAP_USD` stops a runaway.

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
| `roadmap_rows` | Every stage has at least one roadmap row, every row maps to a stage, and `dt roadmap --check` exits 0. A stage may split into several milestones. Rows map by Source (incremental: `brief` is stage 1, and an idea file belongs to the stage that was current when it first appeared). In all-at-once, where every row cites the brief, they map by the stage `keywords` in `scenarios.json` matched against the row's name and outline |
| `milestone_depends` | Every milestone after the first has a Depends line naming existing milestones, with no cycles |
| `first_planned_rest_designed` | Both modes: the first milestone has a plan and every later milestone is at least Designed (task plans are written for the next milestone only), so the final roadmaps of the two modes compare like for like |
| `brief_goals_stage_neutral` | 5 goals or fewer, none worded per stage |
| `quant_grow_at_features` | Incremental: the shape first becomes multi-package in the features_ml stage. All-at-once: the final shape is multi-package |
| `no_code_during_planning` | Nothing under `src/`, `tests/intent/` or `tests/unit/` in any turn, beyond empty or docstring-only files |
| `gate_discipline` | No turn adds 12 or more lines to two layers. The layers are brief/idea, references (`docs/references.md`), spec, architecture, pipelines, tests, plan and setup |
| `skills_invoked`, `test_planning_invoked`, `plan_docs_approved`, `approval_after_user` | Every planning skill ran, and the docs ended Approved only after the user said yes |
| `sim_replan_1..5`, `sim_advance_1..3` | The Replan and Advance simulations below |

Quant only (projects with reference files), all through `dt`:

| id | Check |
|---|---|
| `refs_indexed_approved` | Every file in `references/` has an RF entry, `references_unindexed`/`_changed`/`_missing` are empty, and `docs/references.md` is Approved |
| `refs_milestones` | By file name: `market_decomposition.py` on at least one structure_portfolios milestone, and both TFT files on at least one of forecasting_agents's. Later milestones that reuse a file may list it too (`—` while that stage has no roadmap row) |
| `refs_skills_routed` | For every planned milestone, each of its references is in a task's `Read:` and each roadmap `**Skills:**` entry is on a task, unless the plan's Open questions names it; the same for dt's `references_unrouted` and `skills_unrouted` (active and queued plans) |
| `skills_on_structure_tasks` | The structure_portfolios milestones' `**Skills:**` lines name data-analysis and null-hypothesis-testing, and each is on at least one of their tasks (no plan for them yet: the lines only) |
| `reference_intake_invoked`, `intake_subagent_per_file` | reference-intake ran, and its turns launched one Agent per reference file (each launch names exactly one file; none batched) |
| `no_reference_imports` | Nothing under `src/` or `tests/` imports `references` or adds it to `sys.path` (CR-08; matters once evals cover building) |

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

The rubric adds four items:
- `milestone_quality`: each milestone is one runnable capability with its outcome stated, splits follow dependency lines (no leftover milestones carved off for size), sizes are balanced, Depends are right, and planned milestones have checkable Exit criteria.
- `pipeline_clarity`: pipelines read as clear call paths.
- `layout_sensibility`: the layouts make sense.
- `task_buildability`: each task can be built from its `context__<task>.md` packet alone. The judge reads at least three packets per set.

## Known gaps

- **Iteration 5 was the first full run** (2026-10-16, about $104): results and findings in [results-iteration-5/findings.md](results-iteration-5/findings.md). It found three driver bugs, now fixed. A stage change blocked by `readiness()` is re-asked instead of sending a message that already introduces the next stage. The simulated user moves to the next stage instead of ending at stage 1's build setup. After 4 blocked moves in a row with no doc change, the run stops as `stalled: …`. `gate_discipline` no longer counts `Used by:` appends to `contract.md`.
- **Smoke run.** The one-turn smoke run passed on 2026-10-16 (Claude Code 2.1.292, $0.34): the plugin loads via `--plugin-dir` alongside `--setting-sources project,local`, `session_init` lists all seven `dev-team:*` skills, and `evalperm` is connected. A separate probe showed the guard's "ask" under `bypassPermissions` goes to `evalperm`, which allows and logs it. Without `--permission-prompt-tool` (or with `--permission-prompts none`) an "ask" is denied. Hook events other than SessionStart and Stop appear in stream-json only with `--include-hook-events`, which the driver now passes.
- **Agent frontmatter hooks don't fire in headless runs in an untrusted folder** (they are skipped silently) unless the agents are passed with `--agents`, installed user-level, or the folder was trusted beforehand ([build-setup.md §11](../design/build-setup.md)). That only matters once evals cover building. Planning never runs the tester, implementer or reviewer agents.
- **Skill names are namespaced.** Plugin skills show up as `dev-team:<skill>`, and the grader strips the prefix.
