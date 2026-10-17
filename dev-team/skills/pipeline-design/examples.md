# Pipeline Design Examples

Formats here are what `dt` parses: keep the header line, the `## PL-NN: Title` headings, the six step-table columns and the `(pre-build — removed by spine task)` headings exactly. Revise is in `references/modes.md`, Grow in `references/grow.md`.

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
- After the wiring task, `dt prebuild-clear` replaces each entry sketch with `Layout: \`dt layout <pkg>\`` and drops the planned layout.

---

## Example 1: Quant Lab, M1 (New, single package)

**Context:** the architecture is Approved, single package `quant`, components `data`, `stats`, `portfolio`. M1 covers DATA-01, DATA-02, STAT-01–STAT-04, QR-01, QR-02. `portfolio` is M2.

```
$ dt status --skill pipeline-design
skill: pipeline-design
mode: new
next ids: AD-04 PL-01 TC-01 M3
packages: quant=new
uncovered_ids: none  (and the other lists: none)
```

In New mode the lists stay empty until the gate's re-run; the scope comes from the architecture's Covers.

**Interview:**

```
Candidates for M1 (nothing is written until you confirm):
1. `load` — pull prices for a universe and date range                 M1
2. `cov-report` — PCA and MP cleaning on loaded returns                M1
3. `backtest` — min-variance vs equal weight out of sample             M2 (later)
Q:       Which will you actually run in M1?   (multi-select; recommended: 1, 2)
User:    1 and 2. And the report should be runnable on its own; it can load prices itself.

Q:       Should `cov-report` read prices saved by `load`, or call the loader directly?
GUESS:   call it directly; a separate cache step is more than M1 needs.
DEFAULT: call it directly.
User:    Directly.
```

**`contract.md` after the write** (only `Used by:` changes; each step-table type already has its `type` section):

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
| 1 | `read_raw` | data.raw | dates → RawPrices | read a synthetic CSV | DATA-01 |
| 2 | `apply_universe` | data.universe | RawPrices, dates → Prices | static universe, no delistings | DATA-02 |
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

ASSUMPTIONS: names above; one Parquet file per run (AD-03); returns via `Prices.returns()`.
contract.md: PL IDs appended to Used by for data.load_prices, stats.estimate_cov, stats.clean_eigen.
Open questions: the clean_eigen parameter (above).
Uncovered: none. `portfolio` owns no step yet: it's M2.

Approve, or tell me what to change.
```

---

## Example 2: RL Lab, Snake (New, single package, non-quant)

**Context:** single package `rllab`, components `core` (env interface, training loop, evaluation, run storage), `snake`, `agents`, `baselines`, `viewer`. AD-03 lets the CLI pick an environment by name from one dict in `core/envs.py`. Spec: ENV-01–ENV-04, AGT-01, TRN-01, EVAL-01, VIEW-01, QR-01 (under an hour on a laptop CPU), QR-02 (same seed, same run).

**Interview:**

```
Candidates for Snake (nothing is written until you confirm):
1. `train snake` — train a DQN agent and save the run
2. `replay <run>` — watch a saved run
3. `compare <run>` — learning curve against random and scripted baselines
Q:       Which will you actually run?   (multi-select; recommended: 1, 2, 3)
User:    1 and 2. Training should show it beats random and the scripted snake, inside `train`.
```

**Caught at Step 2:** the first entry sketch looped over episodes; that loop is logic, so it became the step `train` (`core.train`).

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
- The random policy and ASCII renderer are real spines: the floor DQN and the 2D viewer must beat.
- The env lookup is a registry, allowed only because AD-03 names it on the row.
- The scripted-snake baseline is a later step upgrade of `run_baselines` (a task), not a new step.
