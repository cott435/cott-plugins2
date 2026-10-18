# New: worked examples

Two New rounds, each from `dt status` to the gate. The format is `template.md`.

## Example 1: GridLoad, M1 (New, single package)

**Context:** the architecture is Approved, single package `gridload`, components `data`, `profile`, `forecast`. M1 covers DATA-01, DATA-02, PROF-01–PROF-04, QR-01, QR-02. `forecast` is M2.

```
$ dt status --skill pipeline-design
skill: pipeline-design
mode: new
next ids: AD-04 PL-01 TC-01 M3
packages: gridload=new
uncovered_ids: none  (and the other lists: none)
```

In New mode the lists stay empty until the gate's re-run; the scope comes from the architecture's Covers.

**Interview:**

```
Candidates for M1 (nothing is written until you confirm):
1. `load` — pull hourly readings for the meter registry and a date range   M1
2. `season-report` — daily and weekly Fourier fit on loaded demand          M1
3. `holdout` — seasonal-naive forecast scored on held-out weeks             M2 (later)
Q:       Which will you actually run in M1?   (multi-select; recommended: 1, 2)
User:    1 and 2. And the report should be runnable on its own; it can load readings itself.

Q:       Should `season-report` read readings saved by `load`, or call the loader directly?
GUESS:   call it directly; a separate cache step is more than M1 needs.
DEFAULT: call it directly.
User:    Directly.
```

**`contract.md` after the write** (only `Used by:` changes; each step-table type already has its `type` section):

```markdown
### profile.fit_seasonality: Seasonal profile fit
`def fit_seasonality(demand: Demand, *, terms: Terms = "daily+weekly") -> Profile`
- **Invariants:** one sine/cosine pair per harmonic; `residuals` has the input's length and mean zero
- **Errors:** `ValueError` if there are fewer than 168 hours or the input contains NaN
- **Used by:** forecast; PL-02
```

**Result — `docs/packages/gridload/pipelines.md`:**

````markdown
# gridload — Pipelines

**Package:** gridload · **Status:** Draft · **Last updated:** 2026-10-16 · **Contract:** [contract.md](contract.md)

## PL-01: Load readings
**Entry:** `src/gridload/data/pipeline.py::run_load_readings` · **Trigger:** `python -m gridload.data load`
**Covers:** DATA-01, DATA-02, QR-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `read_raw` | data.raw | dates → RawReadings | read a synthetic CSV | DATA-01 |
| 2 | `apply_registry` | data.registry | RawReadings, dates → Readings | static registry, no decommissioned meters | DATA-02 |
| 3 | `save_readings` | data.store | Readings → path | one Parquet file per run | DATA-01 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_load_readings(cfg: LoadConfig) -> Path:
    rows = read_raw(cfg.start, cfg.end)
    readings = apply_registry(rows, cfg.start, cfg.end)
    return save_readings(readings, cfg.out)
```

## PL-02: Seasonality report
**Entry:** `src/gridload/profile/pipeline.py::run_season_report` · **Trigger:** `python -m gridload.profile season-report`
**Covers:** PROF-01–PROF-04, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_readings` | data | regions, dates → Readings | PL-01 as built | DATA-01 |
| 2 | `fit_seasonality` | profile.fit | Demand → Profile | daily and weekly Fourier terms | PROF-02 |
| 3 | `trim_terms` | profile.terms | Profile, n_hours → Profile | keep every term (baseline) | PROF-03 |
| 4 | `residual_spectrum` | profile.spectrum | Profile → Spectrum | full periodogram of the residuals | PROF-01 |
| 5 | `write_report` | profile.report | Spectrum → SeasonalityReport | print table | PROF-04 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_season_report(cfg: SeasonConfig) -> SeasonalityReport:
    readings = load_readings(cfg.regions, cfg.start, cfg.end)
    profile = fit_seasonality(readings.demand())
    profile = trim_terms(profile, n_hours=len(readings))
    spectrum = residual_spectrum(profile)
    return write_report(spectrum, cfg.out)
```

## Planned layout (pre-build — removed by spine task)
```
src/gridload/
  data/
    __init__.py   contract exports only (load_readings, Readings)
    __main__.py   CLI: load
    pipeline.py   PL-01 entry
    raw.py  registry.py  store.py
  profile/
    __init__.py   contract exports only (fit_seasonality, trim_terms)
    __main__.py   CLI: season-report
    pipeline.py   PL-02 entry
    fit.py  terms.py  spectrum.py  report.py
tests/intent/gridload/  tests/unit/gridload/
```

## Open questions
- Should `trim_terms` take the hour count from Profile instead of a parameter? (assumed: parameter)

## Retired
````

**Review gate message:**

```
Wrote docs/packages/gridload/pipelines.md (Draft).
- PL-01 Load readings · `python -m gridload.data load` · read_raw → apply_registry → save_readings
- PL-02 Seasonality report · `python -m gridload.profile season-report` · load_readings → fit_seasonality → trim_terms → residual_spectrum → write_report
- Layout: data/ and profile/ subfolders, one entry module per pipeline, one module per step owner; contracts exported from each __init__.

ASSUMPTIONS: names above; one Parquet file per run (AD-03); demand via `Readings.demand()`.
contract.md: PL IDs appended to Used by for data.load_readings, profile.fit_seasonality, profile.trim_terms.
Open questions: the trim_terms parameter (above).
Uncovered: none. `forecast` owns no step yet: it's M2.

Approve, or tell me what to change.
```

---

## Example 2: LeafLab, single-crop set (New, single package, another domain)

**Context:** single package `leaflab`, components `core` (Dataset and Model protocols, training loop, evaluation, run storage), `singlecrop`, `models`, `baselines`, `viewer`. AD-03 lets the CLI pick a dataset by name from one dict in `core/datasets.py`. Spec: DS-01–DS-04, MOD-01, TRN-01, EVAL-01, VIEW-01, QR-01 (under an hour on a laptop CPU), QR-02 (same seed, same run).

**Interview:**

```
Candidates for the single-crop set (nothing is written until you confirm):
1. `train singlecrop` — train a small CNN and save the run
2. `gallery <run>` — browse a saved run's predictions
3. `compare <run>` — learning curve against majority-class and logistic baselines
Q:       Which will you actually run?   (multi-select; recommended: 1, 2, 3)
User:    1 and 2. Training should show it beats majority-class and the logistic baseline, inside `train`.
```

**Caught at Step 2:** the first entry sketch looped over epochs; that loop is logic, so it became the step `train` (`core.train`).

**Result — `docs/packages/leaflab/pipelines.md`** (excerpt):

````markdown
## PL-01: Train a model
**Entry:** `src/leaflab/core/pipeline.py::run_train` · **Trigger:** `python -m leaflab train singlecrop --model cnn`
**Covers:** DS-01–DS-04, MOD-01, TRN-01, EVAL-01, QR-01, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `make_dataset` | core.datasets | dataset name, seed → Dataset | lookup by name (AD-03) | DS-01 |
| 2 | `SingleCropSet` | singlecrop.dataset | seed → Dataset | 200 synthetic leaves, fixed split | DS-02–DS-04 |
| 3 | `make_model` | models.factory | DatasetSpec, ModelConfig → Model | always the CNN | MOD-01 |
| 4 | `SmallCnn` | models.cnn | DatasetSpec → Model | uniform random guess | MOD-01 |
| 5 | `train` | core.train | Dataset, Model, epochs → Model, Log | epoch loop calling fit_batch; CSV log | TRN-01 |
| 6 | `run_baselines` | baselines | Dataset, seeds → Scores | majority class only | EVAL-01 |
| 7 | `evaluate` | core.evaluate | Model, Dataset, Scores → Curve | held-out accuracy over 5 seeds | EVAL-01 |
| 8 | `save_run` | core.runs | Model, Log, Curve → RunDir | folder with config.json, weights.pt, log.csv | QR-02 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_train(cfg: TrainConfig) -> RunDir:
    dataset = make_dataset(cfg.dataset, seed=cfg.seed)
    model = make_model(dataset.spec, cfg.model)
    model, log = train(dataset, model, epochs=cfg.epochs)
    scores = run_baselines(dataset, seeds=cfg.eval_seeds)
    curve = evaluate(model, dataset, scores)
    return save_run(model, log, curve, cfg.out)
```

## PL-02: Browse predictions
**Entry:** `src/leaflab/viewer/pipeline.py::run_gallery` · **Trigger:** `python -m leaflab gallery runs/<id>`
**Covers:** VIEW-01

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_run` | core.runs | RunDir → Run | read the run folder | VIEW-01 |
| 2 | `predict` | core.predict | Run, seed → Predictions | predict the held-out split | QR-02 |
| 3 | `render` | viewer.render | Predictions → pages | text table of label vs prediction | VIEW-01 |

## Planned layout (pre-build — removed by spine task)
```
src/leaflab/
  __main__.py     CLI: train, gallery
  core/
    __init__.py   contract exports only (Dataset, Model, Run)
    pipeline.py   PL-01 entry
    datasets.py   name → dataset constructor (AD-03)
    train/        core.train's folder: its private helpers (batches.py, checkpoint.py)
    evaluate.py  runs.py  predict.py
  singlecrop/ __init__.py  dataset.py
  models/     __init__.py  factory.py  cnn.py
  baselines/  __init__.py  majority.py
  viewer/     __init__.py  pipeline.py (PL-02 entry)  render.py
tests/intent/leaflab/  tests/unit/leaflab/
```
````

Notes:
- `SingleCropSet` and `SmallCnn` are rows of their own: the factories return them and `train` drives them through `Dataset` and `Model`, so each gets its own spine, and wiring waits on those spines, never on the real CNN.
- The random-guess model and the text table are real spines: the floor the CNN and the image gallery must beat.
- Each pipeline has its own entry module (`core/pipeline.py`, `viewer/pipeline.py`), so their wiring tasks never share a file; `__main__.py` dispatches both triggers.
- The dataset lookup is a registry, allowed only because AD-03 names it on the row.
- The logistic baseline is a later step upgrade of `run_baselines` (a task), not a new step.
