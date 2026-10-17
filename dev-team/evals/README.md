# dev-team evals

Multi-turn trajectories that plan two projects (`rl`, `quant`) from a raw idea to an approved build setup, in two modes:

- **incremental:** the simulated user reveals one stage at a time.
- **all-at-once:** every stage is in the first message.

Stages (from `harness/scenarios.json`): **rl** snake → fish → foraging; **quant** data → structure_portfolios → features_ml → forecasting_agents. Quant had six stages in the three-skill evals; statistics + classical portfolios and forecasting + agents are now merged, because each stage now runs through four more gates. The three-skill evals (iterations 1–4) are archived in [archive/three-skills/](archive/three-skills/README.md).

Each stage goes idea/brief → spec → architecture → pipelines → test plan (optional) → build plan. Build setup comes before the first build. Quant also exercises references and stage-level skill routing ([design/references.md](../design/references.md) §10): the user's three reference files arrive with the stage they serve and go through `reference-intake`, and the `data-analysis`, `null-hypothesis-testing` and `frontend-design` skills are routed per milestone (`frontend-design` to the data stage's viz app: a TypeScript + React frontend over a Python backend). Then the run is graded programmatically, mostly through `dt`, and the final docs can be compared by a blind judge. Design: [design/planning-stage.md §13](../design/planning-stage.md).

The plans are graded as interface-first plans ([design/interface-first-design.md](../design/interface-first-design.md) §9.1): the first milestone opens with an interface task that freezes every step boundary, then one spine per step, one wiring task per pipeline and the thicken tasks, with a `## Dependency graph` table and exclusive `Writes:`. The grader works out the task graph itself (waves, critical path, width) and checks it for parallelism, file ownership and edge mitigation, in both modes, so `modecmp.py` can compare incremental and all-at-once on the same metrics. Every run also exports its plan as it grew, turn by turn, for workflow-analyzer's plan map.

## Files (`harness/`)

| File | What it does |
|---|---|
| `driver.py` | Runs one trajectory: an agent session (`claude -p`, resumed each turn) plus a simulated user (Sonnet, no tools). The whole plugin is staged into `<out>/plugin/` and loaded with `--plugin-dir`. Commits the project after every turn as `turn N` and keeps that turn's plan snapshot in `<out>/plans/T<nnn>.json`. Records each turn's top-level Agent launches (`agents` in `turns.json`). |
| `plugin.py` | Stages the plugin the way a real install gets it: `.claude-plugin/`, `hooks/`, `scripts/` (without dt's tests), and `skills/`. Then checks that every skill's `../../scripts/dt.py` and every hook path resolves, and runs `claude plugin validate`. |
| `permission_mcp.py` | A stdio MCP server used as `--permission-prompt-tool`. It answers the plugin guard's "ask" on `tests/fixtures/**/expected.json` (headless runs have nobody to ask) and logs each prompt. |
| `grade.py` | Writes `grading.json` with a stable `id` per check, and the numbers behind the graph checks as each check's `metrics`. Uses the run's own `dt` snapshot. |
| `dtprobe.py`, `dtrun.py` | Call `dt` and its parser for facts the CLI doesn't print as JSON: live spec IDs, pipelines and steps (with In and Out types), tasks (Kind, Writes, Depends on, Read symbols, Skills, acceptance), each plan's dependency-graph rows and the symbols its interface task declares, contract symbols and type sections, test cases, derived roadmap status and milestone Skills, reference entries. They read the interface-first parser fields when dt has them and the raw task fields and tables otherwise. `dtrun.py` also holds the harness's own graph functions (waves, critical path, ancestors, ready set). |
| `simulate.py` | Replan, Advance, Ready and contract-change simulations on copies of the final project. No model calls. |
| `planexport.py` | Writes `<run>/flow/plan.json` (schema `plan-map/1`): the plan as of every turn that changed `docs/` or `tasks/`, from the run's turn commits. |
| `modecmp.py` | Compares incremental and all-at-once for one project on the interface-first metrics and writes `<iteration>/mode_delta.json` (below). |
| `docstats.py` | Doc sizes and history residue, plus pipelines, tests, contract and plan lines against their per-unit budgets. |
| `package.py` | Lays the runs out in the skill-creator benchmark format, including one `dt context` packet per task and the final plan snapshot. |
| `judge_prompt.py`, `blind_judge_prompt.md` | Fill the blind-judge prompt for a pair of packaged runs, in both orders, and average the two verdicts. |
| `dryrun.py`, `fake_claude.py` | Checks that cost nothing (below). |
| `selftest/quant-interface-first/` | An interface-first M1 for dt's quant sample (the §5.3 plan: interface task, six step spines, two wiring tasks, four split thicken tasks, a system task) with its contract types and typed pipelines. The dry run lays it over the sample for its interface-first replays, so their pinned results don't depend on the sample's own plan. |
| `runviz.py` | The workflow analysis that ends every run: exports the run's plan (`planexport.py`), draws what the run did from its session transcripts and saves it in `<run>/flow/`, then draws the plan map when workflow-analyzer has `planmap.write` (below). Uses the `workflow-analyzer` plugin's scripts (`trace.py`, `flow.py`, `charts.py`, `compare.py`), found at `$WORKFLOW_ANALYZER_SCRIPTS`, in this marketplace's `workflow-analyzer/scripts`, or in the installed plugin. |
| `run.sh` | Runs trajectories in parallel, then grades, measures, packages and draws them. |
| `scenarios.json` | Persona, project facts, stages, turn budgets, and per project the skill stubs (`project_skills`) and reference files per stage (`references`). |
| `stub_*_SKILL.md` | Project skill stubs installed in the run's `.claude/skills/`: `null-hypothesis-testing` (both projects), `data-analysis` and `frontend-design` (quant; the latter stands in for Anthropic's plugin skill, which the isolated run can't load). |
| `references/quant/` | The user's reference code (never run): `market_decomposition.py` (PCA market removal, fit on the full sample: a deliberate look-ahead caveat) for structure_portfolios; `tft_dataset.py` and `tft_targets.py` for forecasting_agents. The driver copies them into the project's `references/` when that stage is revealed (all at the start in all-at-once) and says so in the user's message. |

## Checks that cost nothing (run these first)

```bash
python3 evals/harness/plugin.py /tmp/dt-plugin                  # stage and validate the plugin
python3 evals/harness/simulate.py scripts/tests/fixtures/quant   # Replan/Advance modes on dt's sample project
python3 evals/harness/dryrun.py                                 # replay that sample one layer per turn, then grade it
CLAUDE_BIN=$PWD/evals/harness/fake_claude.py \
  python3 evals/harness/driver.py quant-all-at-once /tmp/fake/quant-all-at-once/with_skill   # driver loop, fake CLI
```

On dt's sample, `simulate.py` passes every Replan and Advance check and fails the one Ready check while the sample's plan has no interface task; on the dry run's interface-first replay, the Ready and contract-change checks wait on `dt ready` (below).

The dry run replays the fixture's `references/` and `docs/references.md` as a reference-intake turn (with one fake Agent launch per file) before the M2 idea. To exercise the driver's reference copying and Agent parsing, run the fake loop on `quant-all-at-once` with `MAX_TURNS=5`: turn 4 is the intake layer and should record one launch per file. The fake loop also writes one plan snapshot per turn to `plans/`.

The dry run is also the grader's self-test. It grades four replays, exports each one's `plan.json`, and compares every check with the result pinned in `dryrun.py`, exiting 1 on anything unexpected:

| Replay | What it is | Checks passing |
|---|---|---|
| `quant-incremental` | The sample as it is (old-format plan), then its M1 code as a build turn | 51 of 77 |
| `quant-incremental-ifd` | The sample with the interface-first M1 from `selftest/`; no code | 62 of 80 |
| `quant-incremental-ifdbad` | That plan broken once per check, plus a `types.py` written in a planning turn and a frozen type revised after the plan | 46 of 80 |
| `quant-incremental-ifdserial` | The spines chained one after another and the testers solo | 57 of 80 |

Expected failures in every replay, because the sample is a two-milestone project, not a finished four-stage run:
- The sample is single-package, not multi-package from the data stage (`quant_multi_from_data`).
- The brief is already Accepted when the replay first shows it.
- The quant content checks fail (null-hypothesis-testing, classical portfolios, out-of-sample, the viz app's boundary).
- The sample has no viz app, so its M1 has no frontend-design (`skills_on_data_tasks`).
- The sample's PCA reference serves its M1 (data + stats), not the structure_portfolios milestone, and its M2 has no `**Skills:**` line (`refs_milestones`, `skills_on_structure_tasks`).

Beyond those, the old-format replay fails `no_code_during_planning` (M1-T01's code) and every interface-first check its plan has no fields for. The bad replay fails each of `graph_metrics` (a cycle), `writes_disjoint`, `edges_mitigated`, `unmitigated_reasoned`, `no_edge_to_code_when_interface`, `edge_table_consistent`, `phase0_split`, `step_tasks_small`, `tester_starts_early`, `fakes_only_cross_pipeline`, `tasks_not_editing_plan`, `interface_coverage`, `types_in_contract`, `tasks_well_formed`, `no_code_during_planning` and `doc_budgets`, and reports one `frozen_interface_churn` revision where the good replay reports none. The serial replay fails `plan_parallelism` and `wave_width`.

Five checks depend on the dt being staged and are pinned as pending: `sim_ready_1`–`3` and `sim_contract_1` need `dt ready` (with tester halves) and `interfaces_changed`, and the interface-first replays need `task-size` to count `Writes:`. With the interface-first dt they pass on the good replay. The dry run stages the plugin at `PLUGIN_SRC` and replays that checkout's sample, so it checks the harness against another branch's dt without merging it:

```bash
PLUGIN_SRC=<worktree>/dev-team python3 evals/harness/dryrun.py
```

When the sample's own plan is interface-first, the first replay grades it, and the interface-first checks on it are reported, not pinned.

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
  - `plans/T<nnn>.json`, the plan snapshot after each turn
  - `agent_stream.jsonl`, `permission_prompts.jsonl` and `doc_history.txt`
  - `flow/`, the workflow analysis and the plan map (below)
- **Packaged runs:** `<iteration>/bench/`.
- **Re-grade a run:** `python3 evals/harness/grade.py <run>`.
- **Environment variables:**
  - `AGENT_MODEL` (default `claude-opus-5-5`), `USER_MODEL` (default `sonnet`)
  - `COST_CAP_USD` (per run, default 150)
  - `MAX_TURNS`
  - `PLUGIN_SRC`, or `SKILLS_SRC` to overlay an older skill snapshot for an A/B run
  - `PERMISSION_PROMPTS=0` to leave the oracle prompts unanswered
- **Prerequisites:** `claude`, `python3` ≥ 3.9, `uv` and `jq`. build-setup stops without `uv` and `jq`. It also runs `uv lock`/`uv sync`, so it needs network access.

## Seeing what a run did

Every eval run ends with its workflow analysis. `driver.py` builds `<run>/flow/` from the session transcripts when the trajectory ends, and `run.sh` rebuilds it with the grade after grading, plus the comparison with the previous iteration. A failure to draw is printed and never fails the eval. To view, serve the workspace (the pages link across iterations):

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory ../../dev-team-workspace
```

Then open `http://127.0.0.1:8765/<iteration>/runflow/index.html`.

- **`<iteration>/runflow/index.html`:** every trajectory with its checks, turns, working time, output tokens, peak context, agents, files changed and cost, each with its change from the previous iteration.
- **`<run>/flow/flow.html`, one run:** stat tiles and failed checks; a timeline against wall time, one bar per main-thread turn and one per agent, stacked when agents ran at once; per turn the skill, time, tokens, peak context, cost and files read and written; a files × turns matrix; one page per turn (`turns/T<nn>.html`) and per agent (`units/U<nn>.html`) with every step in full. `eval.json` beside it holds the trajectory, its checks and per-turn cost.
- **`<iteration>/runflow/<trajectory>-vs-<previous>.html`:** headline deltas, every check whose result changed, per-turn curves, and tokens and time per skill and per agent type.
- **`<run>/flow/plan.json` and `<run>/flow/plan/`:** the plan map. `planexport.py` walks the run's `turn N` commits; a turn that left `docs/` and `tasks/` unchanged, or produced the same plan, is recorded as `same_as` the last turn that changed it. Each other turn's snapshot is the one the driver kept after that turn, or else is rebuilt from that commit, extracted with `git archive` into a temp dir (the run's project is never checked out), with the run's own dt: `dt plan --json` when that dt has it, else built from dtprobe facts. A snapshot has nodes for stages, milestones, tasks (kind, size, mode, acceptance, reads, writes), pipelines, steps (In and Out types), test cases, contract types and symbols; edges for `Depends on`, task → step, test → pipeline and every dependency-graph row with its mitigation; and per planned milestone its waves and critical path. workflow-analyzer's `planmap.write` draws `plan/index.html` (how the plan grew), one page per changed turn, and one build view per milestone (waves by task kind, the critical path, mitigated edges). Old runs get a plan map too: `python3 evals/harness/planexport.py <run-dir>`.

Other forms:

```bash
python3 evals/harness/runviz.py iteration-6 --against iteration-4    # another baseline
python3 evals/harness/runviz.py --run ../../dev-team-workspace/iteration-6/rl-incremental/with_skill
python3 evals/harness/runviz.py --compare <run-dir> <run-dir> --out cmp.html
```

With `workflow-analyzer` installed, its skills work on these runs too: `ask-run` answers questions about one with step ids, and `compare-runs` compares any sessions.

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
| `phase0_split` | Every pipeline of the planned milestone has the types of its steps declared by an interface task, one spine task per step (or a fold rule applied: a split thicken task that keeps the baseline selectable, or a trivial step done by the wiring task), and one wiring task whose `Writes:` holds the entry module and a smoke test. Calls into another pipeline are faked, not spined. `phase0_spine`, which it replaces, stays in `grading.json` as not applicable so older iterations line up |
| `tasks_well_formed` | Every task declares `Kind:` (interface, spine, wiring, thicken or system) and `Writes:`, its `Read:` IDs resolve (`dt context` exits 0), size is M or smaller, and Mode follows the rule or gives a Reason. Split is also allowed for a task whose `Read:` symbols the interface task declares |
| `context_packets_small` | Every `dt context` packet is under 2,000 lines |
| `doc_budgets` | Plans within 12 lines per task, plus one per dependency-graph row, plus 40 (and no task section over 15 lines); contracts within 8 lines per symbol, types included, plus 12; no other `dt lint` budget warnings; the brief 500 words or fewer |
| `milestone_size` | Every planned milestone's critical path, as the grader works it out, is at most 15 tasks |
| `roadmap_rows` | Every stage has at least one roadmap row, every row maps to a stage, and `dt roadmap --check` exits 0. A stage may split into several milestones. Rows map by Source (incremental: `brief` is stage 1, and an idea file belongs to the stage that was current when it first appeared). In all-at-once, where every row cites the brief, they map by the stage `keywords` in `scenarios.json` matched against the row's name and outline |
| `milestone_depends` | Every milestone after the first has a Depends line naming existing milestones, with no cycles |
| `first_planned_rest_designed` | Both modes: the first milestone has a plan and every later milestone is at least Designed (task plans are written for the next milestone only), so the final roadmaps of the two modes compare like for like |
| `brief_goals_stage_neutral` | 5 goals or fewer, none worded per stage |
| `quant_multi_from_data` | No turn's architecture is single-package (the data stage's TypeScript frontend is a runtime boundary), and the final shape has two or more packages |
| `no_code_during_planning` | Nothing under `src/`, `tests/intent/` or `tests/unit/`, no code under `tests/contracts/` and no `types.py` anywhere, in any turn, beyond empty or docstring-only files. Types, signatures, schemas and fakes are the build's interface task's work; sample payloads under `tests/contracts/` are data and may be planned |
| `gate_discipline` | No turn adds 12 or more lines to two layers. The layers are brief/idea, references (`docs/references.md`), spec, architecture, pipelines, tests, plan and setup. Its evidence also lists contract type sections added in pipeline-design turns, the sign of pipeline-design finding missing types and revising the architecture itself |
| `skills_invoked`, `test_planning_invoked`, `plan_docs_approved`, `approval_after_user` | Every planning skill ran, and the docs ended Approved only after the user said yes |
| `sim_replan_1..5`, `sim_advance_1..3`, `sim_ready_1..3`, `sim_contract_1` | The simulations below |

Quant only (projects with reference files), all through `dt`:

| id | Check |
|---|---|
| `refs_indexed_approved` | Every file in `references/` has an RF entry, `references_unindexed`/`_changed`/`_missing` are empty, and `docs/references.md` is Approved |
| `refs_milestones` | By file name: `market_decomposition.py` on at least one structure_portfolios milestone, and both TFT files on at least one of forecasting_agents's. Later milestones that reuse a file may list it too (`—` while that stage has no roadmap row) |
| `refs_skills_routed` | For every planned milestone, each of its references is in a task's `Read:` and each roadmap `**Skills:**` entry is on a task, unless the plan's Open questions names it; the same for dt's `references_unrouted` and `skills_unrouted` (active and queued plans) |
| `skills_on_data_tasks`, `skills_on_structure_tasks` | The data milestones' `**Skills:**` lines name frontend-design; the structure_portfolios milestones' lines name data-analysis and null-hypothesis-testing. A planned milestone whose line names a skill puts it on a task (unplanned: the lines only) |
| `reference_intake_invoked`, `intake_subagent_per_file` | reference-intake ran, and its turns launched one Agent per reference file (each launch names exactly one file; none batched) |
| `no_reference_imports` | Nothing under `src/` or `tests/` imports `references` or adds it to `sys.path` (CR-08; matters once evals cover building) |

The define and design checks from iterations 1–4 are kept, with the same text.

**Interface-first checks.** The grader works out every graph fact itself from dt's parser facts (each task's `Depends on`, `Writes:`, `Kind:` and `Read:`, and the plan's `## Dependency graph` rows) and uses dt's own numbers (`devteam.graph`, the graph fields of `dt status --json`) only as a cross-check, so a dt bug can't grade itself. Only `Depends on` orders tasks; a mitigated row is documentation. Planned scope is the active milestone's plan:

| id | Check | Threshold |
|---|---|---|
| `graph_metrics` | Tasks, critical path (plain and size-weighted, XS=1 S=2 M=4), waves, width per wave and N/CP, with no Depends-on cycle. Fails only when dt's numbers exist and disagree | Agree exactly |
| `plan_parallelism` | Tasks ÷ critical path | ≥ 2.5 when there are 10 or more tasks |
| `wave_width` | Tasks ready right after the interface task (whose only Depends on is the interface task) plus split tasks' tester halves, against the milestone's steps (steps that call another pipeline excluded) | ≥ 0.8 × steps |
| `writes_disjoint` | No two tasks without a Depends-on path between them share a `Writes:` path (a `dir/**` entry covers what is under it); a spine writes only one module, its owner's, and its unit test; `__init__.py`, `types.py`, `pipeline.py` and entry modules only by interface, wiring or system tasks | 0 conflicts |
| `edges_mitigated` | `data` and `call` rows whose mitigation names symbols the interface task declares | ≥ 90% |
| `unmitigated_reasoned` | Every `none:` row has a reason of an allowed kind: same module (thickens), an unsplittable shared or entry file, a real side-effect order (the smoke test runs the real code, swapping a fake), or a contract change | 100% |
| `no_edge_to_code_when_interface` | No Depends on whose row says it is mitigated, and none from a step task to another step's task when the type between them is declared, or from one wiring task to another whose pipeline it calls through a declared fake | 0 |
| `edge_table_consistent` | Every Depends on other than the interface task has a row; every row names two tasks of the plan and a known kind; every unmitigated row is in Depends on | 100% |
| `phase0_split` | Above | 100% |
| `step_tasks_small` | Spine and thicken tasks are XS or S | 100% |
| `tester_starts_early` | Split tasks whose `Read:` symbols are all declared by the interface task | ≥ 80% |
| `fakes_only_cross_pipeline` | A fake (in a row's mitigation or the interface task's acceptance) only on a `call` row, for a step that calls another pipeline or a symbol another package uses | 0 violations |
| `tasks_not_editing_plan` | No `Writes:` under `tasks/` (only the orchestrator writes the plan) | 0 |

Designed scope is every pipeline and the contract:

| id | Check | Threshold |
|---|---|---|
| `interface_coverage` | Every step boundary between two owners has its Out type as a contract type section (`### <component>.<Type>: type`); for the planned milestone's pipelines the section also names a sample under `tests/contracts/` (a `Sample:` field) or the folder exists | 100% |
| `types_in_contract` | Every type named in a step table's In → Out cell (a CapWords name) resolves to a contract type section | 100% |
| `frozen_interface_churn` | Revisions to a type section or `tests/contracts/` file after the first plan was approved, walked over the turn commits (`Used by:` edits ignored) | Reported; compared by `modecmp.py` |

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
- **Ready** (a plan without an interface task gets one failing check instead):
  1. With every todo item unticked, expect `dt ready --json` to list only the interface task.
  2. With the interface task ticked, expect every spine and every split task whose `Read:` symbols the interface task declares (its tester half).
  3. With everything ticked except one pipeline's wiring task, that pipeline's last spine and what follows them, expect the wiring task not ready; tick the spine, expect it ready.
- **Contract change:** add an invariant to a type the interface task froze and re-approve the contract with a later Last updated. Expect build-planning `replan`, with the tasks that read the type named in `dt status --skill build-planning --json` or as a `contract-change` edge in `dt plan --json`.

## Mode comparison

```bash
python3 evals/harness/modecmp.py iteration-7 quant [--judge <averaged judge json>]
```

`modecmp.py` reads both quant (or rl) trajectories' `grading.json` and writes `<iteration>/mode_delta.json`, keyed by project: every interface-first metric for both modes, their deltas, and the band. Without `--judge` it uses `<iteration>/judge-<project>.json` when that file is an averaged judge result.

| Band item | Holds when |
|---|---|
| `parallelism_within_20pct` | The two modes' N/CP differ by at most 20% of the larger |
| `max_width_within_1` | Their widest waves differ by at most one task |
| `both_pass_coverage_types_writes` | Both pass `interface_coverage`, `types_in_contract` and `writes_disjoint` |
| `judge_within_1` | The averaged judge scores differ by at most 1 on `interface_quality` and `dependency_graph_soundness` |

`frozen_interface_churn` is reported beside the band with the expectation that all-at-once revises frozen interfaces no more than incremental does. Anything outside the band is listed under `findings`; it is a finding to read, not a failure, because each mode is one run.

## Blind judge

```bash
python3 evals/harness/judge_prompt.py quant <bench/eval-1-quant/incremental/run-1/outputs> \
  <bench/eval-1-quant/all_at_once/run-1/outputs> <iteration>/judge-quant.json \
  --both /tmp/judge-quant --labels incremental all_at_once
python3 evals/harness/judge_prompt.py average <iteration>/judge-quant.json
```

The first command writes two prompts, `prompt-AB.md` and `prompt-BA.md`, the same pair in both orders, and the key (`judge-quant.key.json`; the labels stay there, never in a prompt). Hand each prompt to its own fresh agent session; each writes `judge-quant.AB.json` or `judge-quant.BA.json`. `average` then writes `judge-quant.json`: each run's scores averaged over the two orders and keyed by label, the winner in each order, and any item whose two scores differ by more than 1. Without `--both`, the command prints one prompt in the given order.

Each packaged run holds `plan_snapshot.json`, the final plan as one graph, with nothing that names the mode. The rubric adds six items:
- `milestone_quality`: each milestone is one runnable capability with its outcome stated, splits follow dependency lines (no leftover milestones carved off for size), sizes are balanced, Depends are right, and planned milestones have checkable Exit criteria.
- `pipeline_clarity`: pipelines read as clear call paths.
- `layout_sensibility`: the layouts make sense.
- `task_buildability`: each task can be built from its `context__<task>.md` packet alone; a spine's packet suffices without its sibling steps' code. The judge reads at least three packets per set, one of them a spine's.
- `interface_quality`: the boundary types are code shapes, minimal and complete for their boundary; helpers aren't frozen; one sample per boundary; fakes only for calls into another pipeline or package.
- `dependency_graph_soundness`: edges are real, with no false serialization; `none:` reasons are valid; every spine could start the moment the interface task lands; tasks that can run at once never write the same file.

## Known gaps

- **Iteration 5 was the first full run** (2026-10-16, about $104): results and findings in [results-iteration-5/findings.md](results-iteration-5/findings.md). It found three driver bugs, now fixed. A stage change blocked by `readiness()` is re-asked instead of sending a message that already introduces the next stage. The simulated user moves to the next stage instead of ending at stage 1's build setup. After 4 blocked moves in a row with no doc change, the run stops as `stalled: …`. `gate_discipline` no longer counts `Used by:` appends to `contract.md`.
- **Smoke run.** The one-turn smoke run passed on 2026-10-16 (Claude Code 2.1.292, $0.34): the plugin loads via `--plugin-dir` alongside `--setting-sources project,local`, `session_init` lists all seven `dev-team:*` skills, and `evalperm` is connected. A separate probe showed the guard's "ask" under `bypassPermissions` goes to `evalperm`, which allows and logs it. Without `--permission-prompt-tool` (or with `--permission-prompts none`) an "ask" is denied. Hook events other than SessionStart and Stop appear in stream-json only with `--include-hook-events`, which the driver now passes.
- **Agent frontmatter hooks don't fire in headless runs in an untrusted folder** (they are skipped silently) unless the agents are passed with `--agents`, installed user-level, or the folder was trusted beforehand ([build-setup.md §11](../design/build-setup.md)). That only matters once evals cover building. Planning never runs the tester, implementer or reviewer agents.
- **The interface-first checks have run only on replays.** Their thresholds are the design's proposals. `sim_ready_*`, `sim_contract_1` and the `graph_metrics` cross-check need the interface-first dt in the staged plugin; until then the cross-check reports that dt has no graph numbers.
- **Skill names are namespaced.** Plugin skills show up as `dev-team:<skill>`, and the grader strips the prefix.
