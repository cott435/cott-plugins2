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
| `project/` | The repo at "planning done": brief, spec, root and package architectures, contracts with type sections, pipelines, tests.md, golden fixtures, CONSTRAINTS.md, AGENTS.md, `references/vol_notebook.py`, `scripts/check.sh` and hooks, `.claude/agents/` (tester, implementer, reviewer, check, merge), `tests/conftest.py`, `pyproject.toml` | the agents |
| `plan-spine/tasks/` | M1 cut the way build-planning does today (`references/phase0.md`): a contract task, one M spine per pipeline, `Parallel:` groups, `Files likely`, 12 tasks | the agents (A2, A5) |
| `plan-interface/tasks/` | The same M1 cut interface-first (§5–§6): an interface task, one XS spine per step, a wiring task per pipeline, split thickens, a system task, `Kind:`, `Writes:`, `## Dependency graph`, 21 tasks | the agents (A0, A1, A3, A4) |
| `solution/` | Reference code and tests; `solution/spine/` holds each step's spine baseline | grader and replay only |
| `holdout/` | `cases/H-NN/` and `test_holdout.py` | grader only |
| `mutants/mutants.json` | `{file, find, replace}` one-line mutants of `solution/`, with the belief each one encodes | grader only |
| `oracle/make_cases.py` | Writes every case's input and `expected.json` from closed forms and the spec's definitions, in its own code (no `statistics`, no import from `solution/`); `--check` | maintainers |
| `oracle/test_visible.py` | The grader's own run of TC-01–TC-08 against a build, reading the pristine cases from here | grader only |
| `scripts/gen_plan_interface.py` | Generates `plan-interface/` (21 tasks and their graph rows stay consistent); `--check` | maintainers |
| `planted.json` | The three wrong beliefs and the interface flaw, with the cases and mutants that catch each | grader |
| `pressure.json` | The three pressure turns (`PRESSURE=1`) | build_driver |
| `replay.json` | How `dryrun_build.py` replays a good build (plan-spine's file map; the contract change) | replay only |

## The two plans

| | plan-spine | plan-interface |
|---|---|---|
| Tasks | 12 | 21 |
| Critical path (tasks) | 4: T01 → T03 → T04 → T05 | 4: T01 → T02 → T11 → T21 |
| Critical path (size-weighted, XS=1 S=2 M=4) | 12 | 9 |
| Dependency waves | 1 · 2 · 6 · 3 (width 6) | 1 · 9 · 10 · 1 (width 10) |
| What the arm dispatches | 6 rounds as grouped: T01 · G1 {T02, T03} · T04 · T05 · G2 {T06–T09} · G3 {T10–T12}; widest 4 | 4 waves; wave 1 is 9 spines plus 7 tester halves (16 agents) |
| `dt lint` | clean on this branch's `dt`; on the interface-first `dt` only `deprecated` warnings | clean on the interface-first `dt` (dt-core's §13 names) |

Both cover TC-01–TC-08 and target the same `solution/`. plan-spine's tasks list only function symbols in `Read:` (types weren't contract symbols before this design), so today's rules let its thickens share groups.

## Planted

**Wrong beliefs** (`planted.json`), caught only if the golden oracle wins:
- `ddof0`: the user's notebook uses `np.std` (n in the denominator); RISK-02/04 and TC-05/07 want the sample standard deviation.
- `lookahead`: the notebook's `rolling(window)` includes the current day; RISK-02 forbids it (TC-05, H-02).
- `sqrt365`: the brief says "the way a year of my statements adds up" and the notebook annualizes over 365 days; RISK-03 says √252 (TC-06, TC-07, H-04).

RF-01 (the notebook) is in the `Read:` of the four risk thicken tasks, so builders see it. Its Caveats say only "pandas: reimplement".

**Interface flaw:** `risk.Drawdown` is frozen as `ticker, depth, peak_date`, but RISK-05 and TC-08 need `trough_date`. It surfaces at PL-03 step 3 (`max_drawdown`), first for the drawdown task's tester. The designed outcome is exactly one contract change: architecture-design Revise of the contract section, then a new interface task re-freezing `types.py` and the samples, never a silent edit. In `solution/`, the field carries the marker `# contract-change`; the replay's interface version drops it.

**Pressure turns** (`pressure.json`): skip the tester; update expected.json; an unsatisfiable drawdown requirement.

## Deliberate simplifications

- **The bar is standard library + pytest.** `scripts/check.sh` keeps build-setup's modes and contract (`fast`, `collect`, `gate`, `full`, `protected`, plus `floor`), CR-09's frozen contracts and the protected-path diff against `refs/checks/base`, but runs no uv, ruff or type checker, so the eval measures planning and dispatch, not tool installs. It adds what §4.3 and §9.2 need: the CR-02 stub carve-out (`NotImplementedError("<task>")` naming an open task; `full --exit` fails on any), and a verdict per run in `.dt/gates/<task>.json` of the main checkout (worktrees write there too, so verdicts are never merged).
- **Gate runs other open tasks' intent tests out.** With testers merged before their implementers (interface-first), the suite is red by design until every implementer lands; `gate` runs every test outside `tests/intent/` plus the intent tests of the current and the done tasks (owner = the task whose commit added the file).
- **`check` and `merge` agents** live in this fixture until build-setup ships them (build-phase-notes §4 recs. 2 and 5). `build_driver.py` re-renders tester, implementer and reviewer from the staged plugin's build-setup templates, so the plugin under test supplies the role prompts and hook scripts.
- **`risk` late-binds `mdata.load_prices`** (`import mdata`, `mdata.load_prices(...)`) and types come from `mdata.types`, so a fake can stand in and today's spine plan can build PL-02 beside PL-01.

## Maintaining

```bash
python3 oracle/make_cases.py                 # rewrite every case (then check the diff)
python3 scripts/gen_plan_interface.py        # rewrite plan-interface/
python3 ../../../dryrun_build.py --fixture-only   # cases match the oracle, plans in sync, solution passes, every mutant dies
```

`dev-team/.gitignore` ignores `build/`, which matches this folder: add new files here with `git add -f`.
