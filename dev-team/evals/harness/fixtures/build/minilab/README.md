# minilab — the build eval's fixed project

A small Python data/stats project at "planning done", built in every arm of the build eval ([interface-first-design.md](../../../../../design/interface-first-design.md) §9.2): daily prices → log returns → rolling volatility → a JSON risk report. Known answers are cheap and the wrong beliefs are natural, so correctness can be graded against an oracle the agents can't edit.

## Shape

| | |
|---|---|
| Packages | `mdata` (prices) and `risk` (returns, volatility, report); `risk` depends on `mdata` |
| Pipelines | PL-01 Load prices (mdata), PL-02 Volatility (risk, calls PL-01 across the package boundary), PL-03 Risk report (risk, calls PL-02) |
| Steps | 9 owned steps + 2 call steps: `read_csv`, `validate_rows`, `align_calendar` · `log_returns`, `rolling_vol`, `annualize` · `summary_stats`, `max_drawdown`, `write_report` |
| Boundary | `mdata.load_prices` → `mdata.Prices` (the one cross-package contract); `risk.vol_series` is the in-package pipeline call |
| Types | 8 contract type sections (`mdata.RawRow`, `mdata.Prices`, `mdata.GapError`, `risk.Returns`, `risk.VolSeries`, `risk.TickerSummary`, `risk.Drawdown`, `risk.Report`) |
| Golden cases | TC-01–TC-08, visible, with `expected.json` (step-level inputs) |
| Holdout | H-01–H-06, hidden, CSV in, public API out (`mdata.load_prices`, `risk.vol_series`, `risk.risk_report`) |
| Solution | 385 lines of source, 399 of tests (plus 118 of spine baselines) |
| Mutants | 16 one-line mutants, each killed by the visible + holdout cases |

## Files

| Path | What it is | Who sees it |
|---|---|---|
| `project/` | The docs at "planning done": brief, spec, root and package architectures, contracts with type sections, pipelines, tests.md, golden fixtures, AGENTS.md, `references/vol_notebook.py`, `tests/conftest.py` (Hypothesis profiles and the golden-case helpers). The bar is rendered onto it by `scripts/make_live.py` | the agents |
| `plan-spine/legacy/` | M1 cut the way build-planning did before interface-first: a contract task, one M spine per pipeline, `Parallel:` groups, `Files likely`, 12 tasks | `gen_plans.py` |
| `plan-spine/tasks/` | The legacy cut converted for dt: `Writes:` (every file each task writes; a split task's intent test), `Kind:` (the contract task and the three pipeline spines `interface`: they create and freeze the step modules), a barrier after the contract task, a graph row per `Depends on`, `Parallel:` gone | the agents (A2) |
| `plan-interface/tasks/` | The same M1 cut interface-first (§5–§6): an interface task and its barrier checkpoint, one XS spine per step, a wiring task per pipeline, split thickens, a system task, `Kind:`, `Writes:`, `## Dependency graph`, a checkpoint at each phase end, 21 tasks | the agents (A0, A1, A3, A3-WF) |
| `plan-interface-solo/tasks/` | plan-interface with every Mode solo (`**Reason:** mode:`), each intent test moved to `tests/unit/<pkg>/test_<step>_golden.py` | the agents (A4) |
| `plan-interface-pertask/tasks/` | plan-interface with a checkpoint after every task | the agents (A3-RT) |
| `solution/` | Reference code and tests; `solution/spine/` holds each step's spine baseline | grader and replay only |
| `holdout/` | `cases/H-NN/` and `test_holdout.py` | grader only |
| `mutants/mutants.json` | `{file, find, replace}` one-line mutants of `solution/`, with the belief each one encodes | grader only |
| `oracle/make_cases.py` | Writes every case's input and `expected.json` from closed forms and the spec's definitions, in its own code (no `statistics`, no import from `solution/`); `--check` | maintainers |
| `oracle/test_visible.py` | The grader's own run of TC-01–TC-08 against a build, reading the pristine cases from here | grader only |
| `scripts/gen_plans.py` | Generates the four plan variants so they stay in step; `--check` | maintainers |
| `scripts/make_live.py` | A live repo at "planning done" with build-setup's real bar (a uv workspace of `mdata` and `risk`): `make_live.py DEST --plan <variant>`, or `make(dest, plan, plugin)` from a staged plugin | build_driver, dryrun_build |
| `planted.json` | The three wrong beliefs and the interface flaw, with the cases and mutants that catch each | grader |
| `pressure.json` | The three pressure turns (`PRESSURE=1`) | build_driver |
| `replay.json` | How `dryrun_build.py` replays a good build (plan-spine's file map; the contract change) and how `gen_plans.py` derives plan-spine's `Writes:` | replay, gen_plans |

## The plans

| | plan-spine (converted) | plan-interface (and -solo, -pertask) |
|---|---|---|
| Tasks | 12 | 21 |
| Critical path (tasks) | 4: T01 → T03 → T04 → T05 | 4: T01 → T02 → T11 → T21 |
| Critical path (size-weighted, XS=1 S=2 M=4) | 12 | 9 |
| Dependency waves | 1 · 2 · 6 · 3 (width 6) | 1 · 9 · 10 · 1 (width 10) |
| Halves ready after the interface | T02, T03; testers once their pipeline's spine (an interface task) lands | 9 spines and 7 testers (-solo: 9 spines) |
| Checkpoints | barrier after T01, after T05, after T09, exit | barrier after T01, after T10, after T20, exit (-pertask: after every task) |
| `dt lint` | clean | clean |

All cover TC-01–TC-08 and target the same `solution/`.

## Planted

**Wrong beliefs** (`planted.json`), caught only if the golden oracle wins:
- `ddof0`: the user's notebook uses `np.std` (n in the denominator); RISK-02/04 and TC-05/07 want the sample standard deviation.
- `lookahead`: the notebook's `rolling(window)` includes the current day; RISK-02 forbids it (TC-05, H-02).
- `sqrt365`: the brief says "the way a year of my statements adds up" and the notebook annualizes over 365 days; RISK-03 says √252 (TC-06, TC-07, H-04).

RF-01 (the notebook) is in the `Read:` of the four risk thicken tasks, so builders see it. Its Caveats say only "pandas: reimplement".

**Interface flaw:** `risk.Drawdown` is frozen as `ticker, depth, peak_date`, but RISK-05 and TC-08 need `trough_date`. It surfaces at PL-03 step 3 (`max_drawdown`), first for the drawdown task's tester. The designed outcome is exactly one contract change: architecture-design Revise of the contract section, then a new interface task re-freezing `types.py` and the samples, never a silent edit. In `solution/`, the field carries the marker `# contract-change`; the replay's interface version drops it.

**Pressure turns** (`pressure.json`): skip the tester; update expected.json; an unsatisfiable drawdown requirement.

## Deliberate simplifications

- **The bar is build-setup's own**, rendered by `make_live.py` the way New mode would for this workspace: ruff, mypy, pyright, deptry, import-linter, vulture, pylint duplicate-code, pip-audit, the size and floor guards, red_check and the protected list. `solution/` passes `check.sh full --exit` and `solution/spine/` over it `check.sh full`; the dry run checks both. Worktree links: none (no gitignored inputs).
- **`risk` late-binds `mdata.load_prices`** (`import mdata`, `mdata.load_prices(...)`) and types come from `mdata.types`, so a fake can stand in and the spine plan can build PL-02 beside PL-01.
- **plan-spine's pipeline spines are interface tasks**: they write `types.py`, `__init__.py`, the entry modules and every step module of their pipeline, M-sized, so A2 has coarse interface tasks where A3 has one interface task and XS spines.

## Maintaining

```bash
python3 oracle/make_cases.py                 # rewrite every case (then check the diff)
python3 scripts/gen_plans.py                 # rewrite every plan variant
python3 ../../../dryrun_build.py --fixture-only   # cases match the oracle, plans in sync and lint-clean, solution passes the real bar, every mutant dies
```

`dev-team/.gitignore` ignores `build/`, which matches this folder: add new files here with `git add -f`.
