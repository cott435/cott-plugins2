# Pipeline Design Examples

The template, two New rounds (a quant single package and an RL lab), then Revise and Grow rounds. Formats here are what `dt` parses: keep the header line, the `## PL-NN: Title` headings, the six step-table columns and the `(pre-build — removed by spine task)` headings exactly.

---

## Template

````markdown
# <pkg> — Pipelines

**Package:** <pkg> · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Contract:** [contract.md](contract.md)

## PL-NN: <Workflow name>
**Entry:** `src/<path>/pipeline.py::run_<workflow>` · **Trigger:** `python -m <module> <command>`
**Covers:** <spec IDs, ranges with an en dash>
**References:** <optional: RF-NN (step) for each reference that informs a step>

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `<function>` | <component[.module]> | <contract types> → <contract type> | <real, minimal baseline> | <spec IDs> |

### Entry sketch (pre-build — removed by spine task)
```python
def run_<workflow>(cfg: <Config>) -> <Result>:
    a = step_one(cfg.x)
    b = step_two(a)
    return step_three(b, cfg.out)
```

## Planned layout (pre-build — removed by spine task)
```
src/<pkg>/
  __init__.py   contract exports only
  pipeline.py   PL-NN entry
  <owner modules, one per step owner>
tests/intent/<pkg>/  tests/unit/<pkg>/
```

## Open questions
- <question> (assumed: <the default used>)

## Retired
- ~~PL-NN: <title>~~ Retired YYYY-MM-DD: <reason>
````

- Multi-package segment of a system pipeline: add `· **Part of:** PL-NN` to the pipeline's Entry/Trigger line.
- Appending PL IDs to an Approved `contract.md`'s `Used by:` lines leaves it Approved (`dt lint` ignores that edit); the commit offer includes it.
- A decision-backed exception to a readability rule goes in the row's Spine version or the pipeline's Covers line as a short note citing the `AD-NN`.
- After the spine task, `dt prebuild-clear` replaces each entry sketch with `Layout: \`dt layout <pkg>\`` and drops the planned layout.

---

## Example 1: Quant Lab, M1 (New, single package)

**Context:** the architecture is Approved, single package `quant`, components `data`, `stats`, `portfolio`. M1 covers DATA-01, DATA-02, STAT-01–STAT-04, QR-01, QR-02. `portfolio` is M2.

```
$ dt status --skill pipeline-design
skill: pipeline-design
mode: new
docs: brief Accepted · spec Approved · architecture Approved (Single package) · roadmap ok · plan missing · constraints missing
next ids: AD-04 PL-01 TC-01 M3
packages: quant=new
uncovered_ids: none
components_unowned: none
drift: none
retired_refs: none
misplaced: none
```

A package with no `pipelines.md` has nothing to check yet, so `uncovered_ids` and `components_unowned` stay empty in New mode; the scope comes from the architecture's Covers (M1's IDs above). They count at the gate's re-run.

**Interview** (one question per turn):

```
Q:       Which commands will you actually run in M1?
GUESS:   `load` to pull prices for a universe and date range, then `cov-report` to see PCA and cleaning on them.
DEFAULT: those two.
User:    Yes. And the report should be runnable on its own; it can load prices itself.

Q:       Should `cov-report` read prices saved by `load`, or call the loader directly?
GUESS:   call it directly; a separate cache step is more than M1 needs.
DEFAULT: call it directly.
User:    Directly.
```

Everything else (names, types, order, module split) is inferred and listed at the gate.

**`contract.md` after the write** (only the `Used by:` lines change; the consumer components were already there):

```markdown
### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** portfolio; PL-02
```

**Result — `docs/packages/quant/pipelines.md`:**

````markdown
# quant — Pipelines

**Package:** quant · **Status:** Draft · **Last updated:** 2026-10-16 · **Contract:** [contract.md](contract.md)

## PL-01: Load prices
**Entry:** `src/quant/data/pipeline.py::run_load_prices` · **Trigger:** `python -m quant.data load`
**Covers:** DATA-01, DATA-02, QR-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `read_raw` | data.raw | dates → raw rows | read a synthetic CSV | DATA-01 |
| 2 | `apply_universe` | data.universe | raw rows, dates → Prices | static universe, no delistings | DATA-02 |
| 3 | `save_prices` | data.store | Prices → path | one Parquet file per run | DATA-01 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_load_prices(cfg: LoadConfig) -> Path:
    rows = read_raw(cfg.start, cfg.end)
    prices = apply_universe(rows, cfg.start, cfg.end)
    return save_prices(prices, cfg.out)
```

## PL-02: Covariance report
**Entry:** `src/quant/stats/pipeline.py::run_cov_report` · **Trigger:** `python -m quant.stats cov-report`
**Covers:** STAT-01–STAT-04, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_prices` | data | universe, dates → Prices | PL-01 as built | DATA-01 |
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
| 4 | `pca` | stats.pca | Cov → Factors | full eigendecomposition | STAT-01 |
| 5 | `write_report` | stats.report | Factors → CovReport | print table | STAT-04 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_cov_report(cfg: CovConfig) -> CovReport:
    prices = load_prices(cfg.universe, cfg.start, cfg.end)
    cov = estimate_cov(prices.returns())
    cov = clean_eigen(cov, n_obs=len(prices))
    factors = pca(cov)
    return write_report(factors, cfg.out)
```

## Planned layout (pre-build — removed by spine task)
```
src/quant/
  data/
    __init__.py   contract exports only (load_prices, Prices)
    __main__.py   CLI: load
    pipeline.py   PL-01 entry
    raw.py  universe.py  store.py
  stats/
    __init__.py   contract exports only (estimate_cov, clean_eigen)
    __main__.py   CLI: cov-report
    pipeline.py   PL-02 entry
    cov.py  rmt.py  pca.py  report.py
tests/intent/quant/  tests/unit/quant/
```

## Open questions
- Should `clean_eigen` take T from Returns instead of a parameter? (assumed: parameter)

## Retired
````

**Review gate message:**

```
Wrote docs/packages/quant/pipelines.md (Draft).
- PL-01 Load prices · `python -m quant.data load` · read_raw → apply_universe → save_prices
- PL-02 Covariance report · `python -m quant.stats cov-report` · load_prices → estimate_cov → clean_eigen → pca → write_report
- Layout: data/ and stats/ subfolders, one module per step owner; contracts exported from each __init__.

ASSUMPTIONS: function and module names above; `save_prices` writes one Parquet file per run (AD-03);
returns are computed by `Prices.returns()`, not a separate step; `clean_eigen` takes T as a parameter.
contract.md: appended PL IDs to Used by — data.load_prices (PL-01, PL-02), stats.estimate_cov (PL-02),
stats.clean_eigen (PL-02). No other contract edits.
Open questions: the clean_eigen parameter (above).
Uncovered: none. `portfolio` owns no step yet: it's M2.

Approve, or tell me what to change.
```

The turn ends there.

---

## Example 2: RL Lab, Snake (New, single package, non-quant)

**Context:** a learning lab of small 2D environments with a shared core. Architecture: single package `rllab`, components `core` (env interface, training loop, evaluation, run storage), `snake`, `agents`, `baselines`, `viewer`. AD-03 lets the CLI pick an environment by name from one dict in `core/envs.py`. Spec: ENV-01–ENV-04, AGT-01, TRN-01, EVAL-01, VIEW-01, QR-01 (under an hour on a laptop CPU), QR-02 (same seed, same run).

**Interview:**

```
Q:       Which things will you actually run for Snake?
GUESS:   `train snake` to train a DQN agent and save the run, and `replay <run>` to watch it.
DEFAULT: those two.
User:    Yes. Training should also show it beats random and the scripted snake.

Q:       Should the baseline comparison run inside `train`, or as its own command?
GUESS:   inside `train`, so every saved run carries its learning curve and baseline scores.
DEFAULT: inside `train`.
User:    Inside train.
```

**First draft caught at Step 2:** the entry sketch looped over episodes (`for ep in range(cfg.episodes): …`). That loop is logic, so it became the step `train`, owned by `core.train`. The entry now only calls steps.

**Result — `docs/packages/rllab/pipelines.md`** (excerpt):

````markdown
## PL-01: Train an agent
**Entry:** `src/rllab/core/pipeline.py::run_train` · **Trigger:** `python -m rllab train snake --agent dqn`
**Covers:** ENV-01–ENV-04, AGT-01, TRN-01, EVAL-01, QR-01, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `make_env` | core.envs | env name, seed → Env | 10×10 Snake, fixed food sequence; lookup by name (AD-03) | ENV-01–ENV-04 |
| 2 | `make_agent` | agents.dqn | EnvSpec, AgentConfig → Agent | uniform random policy | AGT-01 |
| 3 | `train` | core.train | Env, Agent, episodes → Agent, Log | episode loop calling act/update; CSV log | TRN-01 |
| 4 | `run_baselines` | baselines | Env, seeds → Scores | random policy only | EVAL-01 |
| 5 | `evaluate` | core.evaluate | Agent, Env, Scores → Curve | mean return over 20 episodes | EVAL-01 |
| 6 | `save_run` | core.runs | Agent, Log, Curve → RunDir | folder with config.json, weights.npz, log.csv | QR-02 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_train(cfg: TrainConfig) -> RunDir:
    env = make_env(cfg.env, seed=cfg.seed)
    agent = make_agent(env.spec, cfg.agent)
    agent, log = train(env, agent, episodes=cfg.episodes)
    scores = run_baselines(env, seeds=cfg.eval_seeds)
    curve = evaluate(agent, env, scores)
    return save_run(agent, log, curve, cfg.out)
```

## PL-02: Watch a replay
**Entry:** `src/rllab/viewer/pipeline.py::run_replay` · **Trigger:** `python -m rllab replay runs/<id>`
**Covers:** VIEW-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_run` | core.runs | RunDir → Run | read the run folder | VIEW-01 |
| 2 | `rollout` | core.rollout | Run, seed → Episode | one greedy episode | QR-02 |
| 3 | `render` | viewer.render | Episode → frames | ASCII grid printed per step | VIEW-01 |

## Planned layout (pre-build — removed by spine task)
```
src/rllab/
  __main__.py     CLI: train, replay
  core/
    __init__.py   contract exports only (Env, Agent, Run)
    pipeline.py   PL-01 entry
    envs.py       name → env constructor (AD-03)
    train.py  evaluate.py  runs.py  rollout.py
  snake/      __init__.py  env.py
  agents/     __init__.py  dqn.py
  baselines/  __init__.py  random.py
  viewer/     __init__.py  pipeline.py (PL-02 entry)  render.py
tests/intent/rllab/  tests/unit/rllab/
```
````

Notes:
- The spine agent is a random policy and the spine renderer prints ASCII. Both are real, both run in seconds, and both stay as the floor DQN and the 2D viewer must beat.
- The env lookup is a registry, allowed only because AD-03 names it; the row says so.
- The scripted-snake baseline is a later step upgrade of `run_baselines` (a task), not a new step.

---

## Example 3: Revise (shrinkage before cleaning)

**Context:** during M1 the build found MP cleaning of a raw sample covariance is unstable at T/N ≈ 2. `architecture-design` Revise added AD-07: shrink to a Ledoit–Wolf target before cleaning. PL-02's spine is built, so its entry sketch is already gone.

**Before:**
```markdown
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
```

**After** (`Status: Draft`):
```markdown
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `shrink` | stats.shrink | Cov, T → Cov | no shrinkage (baseline; AD-07) | STAT-02 |
| 4 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
```

Rows below shift down a number; step names and the PL ID don't change. `shrink` isn't a contract symbol (it's internal to `stats`), so `contract.md` is untouched; had it been, its `Used by:` line would gain PL-02. The new step's spine is "no shrinkage": `shrink` returns its input until a task upgrades it, which is a real baseline, not a mock. No entry sketch is recreated: the code now calls four steps where the table has five, so `dt layout quant` reports drift until the task lands.

**Gate message (excerpt):**

```
Revised PL-02: new step `shrink` (stats.shrink) between estimate_cov and clean_eigen, per AD-07.
Affected tasks: M1-T04 (Step: PL-02.clean_eigen; Read: PL-02). They pause until this is approved:
while pipelines.md is Draft, build-planning's dt status says blocked (waiting for approval).
After approval: build-planning Replan (its dt status says replan, changed_since_plan lists
docs/packages/quant/pipelines.md) adds the `shrink` task. TC-02's expected output is unchanged
(the MP-edge property holds either way), so no test-planning Revise.
```

---

## Example 4: Grow (quant M3 splits into packages)

**Context:** at the end of M2, `quant/pipelines.md` holds PL-01 Load prices, PL-02 Covariance report, PL-03 Min-variance backtest (`estimate_cov` → `min_variance` → `compare`) and the retired line for PL-04. M3 brings feature engineering with torch. `architecture-design` Grow made the repo Multi-package (`data`, `stats`, `portfolio`, `features`, under `packages/<pkg>/src/<pkg>/`) and added one system pipeline, with a new ID from `dt next-id PL`, grown from PL-03:

```markdown
## System pipelines
### PL-05: Research run
**Trigger:** `python -m portfolio backtest` (PL-03's entry) · **Covers:** FEAT-01, PORT-01, PORT-02
1. `data` → `stats`: `data.load_prices`
2. `stats` → `features`: `stats.estimate_cov`
3. `features` → `portfolio`: `features.screen`
```

`dt status --skill pipeline-design` reports the four new packages as `new`, but `quant/pipelines.md` still holds their pipelines and the architecture's Grow is approved, so this is Grow, not New. (Once a moved section's Entry points into another package's folder, `dt` reports `grow` itself, with the pipeline under `misplaced`.)

**Moves:**

| Section in `quant/pipelines.md` | Goes to | Why |
|---|---|---|
| PL-01 Load prices | `docs/packages/data/pipelines.md` | entry `run_load_prices` is owned by data |
| PL-02 Covariance report | `docs/packages/stats/pipelines.md` | entry in stats; step `load_prices` stays a call to data's contract (stats → data is allowed) |
| PL-03 Min-variance backtest | `docs/packages/portfolio/pipelines.md`, as PL-05's portfolio segment | entry in portfolio; keeps its ID, step table and Entry, and gains `· **Part of:** PL-05` |
| `~~PL-04: Raw eigen dump~~` | `stats` Retired list | it was folded into PL-02 |

Each moved section keeps its ID, title, table and Covers. Only the Entry path and the Trigger's module change, to the new source folder:

```markdown
## PL-03: Min-variance backtest
**Entry:** `packages/portfolio/src/portfolio/pipeline.py::run_backtest` · **Trigger:** `python -m portfolio backtest` · **Part of:** PL-05
```

PL-03 is not deleted or merged into the root: TC-04 and M2's tasks cite it, and the root's PL-05 is a different ID, so no two live sections share one.

**Other segments of PL-05:** data and stats each hand over one contract call (`data.load_prices`, `stats.estimate_cov`), so they need no segment pipeline. `features` has no pipeline yet, so the gate lists it as uncovered and the next round (Extend) asks the user about the feature-screening workflow and adds PL-06 with `**Part of:** PL-05`, plus a planned layout for it (it's new and unbuilt). The same round adds a `screen` row (owner features) to PL-03, so the portfolio segment calls `features.screen`; that new step needs no planned layout, since PL-03 is built.

**Gate message (excerpt):**

```
Grow: moved PL-01 → data, PL-02 → stats, PL-03 → portfolio (now PL-05's portfolio segment,
marked Part of: PL-05); PL-04's retired line moved to stats. Deleted docs/packages/quant/pipelines.md (empty).
All three pipelines.md files are Draft.
Drift until the code moves: every Entry path now points under packages/<pkg>/src/ (a build-planning task).
Uncovered: features owns no pipeline; the feature-screening workflow needs your input (next: Extend).
```
