# Test Planning Examples: New

Two New rounds. The template and fixture shapes are in `../examples.md`.

---

## Example 1: GridLoad, M1 (New)

**Context:** `docs/packages/gridload/pipelines.md` is Approved with PL-01 (Load meter readings) and PL-02 (Seasonality report).

```
$ dt status --skill test-planning
skill: test-planning
mode: new
next ids: AD-04 PL-03 TC-01 M2
packages: gridload=new
pipelines_no_smoke: PL-01, PL-02
pipelines_no_golden: PL-01, PL-02
cases_no_source: none  (and the other gap keys: none)
```

**Interview:**

```
Q:       Which workflow would hurt most if it were quietly wrong?
GUESS:   the meter load: dropping decommissioned meters would bias every regional total downstream.
DEFAULT: meter load first, then the seasonality report.

Q:       Do you have a real example of a decommissioned meter I can pin as a case?
GUESS:   an export from the utility's system with a meter that was retired.
DEFAULT: none; I'd use a synthetic registry with one planted decommissioning.

Q:       Any trusted output for the seasonality report, from a notebook or a paper?
GUESS:   no, so two synthetic known-answer cases: a flat spectrum on pure noise, and a planted daily sine.
DEFAULT: those two.

User:    The meter load. Yes, M-0417 was decommissioned 2018-06-29; here's the export
         [attaches decommissioned_2018.csv]. No trusted seasonality output, go with those two.
```

### A two-layer pair: TC-01

The user's export is in the utility's format, not the contract's, so it gets both layers.

```
tests/fixtures/gridload/TC-01/
  source/decommissioned_2018.csv
  readings.csv
  input.json
  expected.json
```

`source/decommissioned_2018.csv` (as given, never edited):
```
MeterID;Date;Reading kWh
M-0417;29/06/2018;10.50
M-0522;29/06/2018;19.80
M-0522;02/07/2018;20.00
```

`readings.csv` (transcribed into the contract's Readings columns, shown to the user for approval):
```
date,meter_id,kwh
2018-06-29,M-0417,10.5
2018-06-29,M-0522,19.8
2018-07-02,M-0522,20.0
```

`input.json`:
```json
{"meters": ["M-0417", "M-0522"], "readings": "readings.csv", "start": "2018-06-01", "end": "2018-12-31"}
```

`expected.json` (the user's statement, not derived from the rows):
```json
{"last_date": {"M-0417": "2018-06-29"}, "tol": 0}
```

- **Parse test** (tester, later): `read_raw("source/decommissioned_2018.csv")` returns exactly the rows of `readings.csv`.
- **Pipeline test:** PL-01 on `input.json` keeps M-0417 through 2018-06-29 and drops it after.

### Result — `docs/packages/gridload/tests.md`

````markdown
# gridload — Tests

**Package:** gridload · **Status:** Draft · **Last updated:** 2026-10-16 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m gridload.data load --smoke` | read_raw, apply_registry | TC-01 (RawReadings → apply_registry → Readings) | — |
| PL-02 | `python -m gridload.profile seasonality-report --smoke` | fit_seasonality, spectrum, deseason | TC-02 (Load → spectrum → Spectrum), TC-03 (Load → fit_seasonality → Profile) | — |

### TC-01: Decommissioned meter drops out
**Pipeline:** PL-01 · **Covers:** DATA-02 · **Kind:** user example · **Fixture:** tests/fixtures/gridload/TC-01/
**Source:** user file `decommissioned_2018.csv` and the user's decommissioning date for M-0417 (given 2026-10-15)
**Expected:** meter M-0417 present through 2018-06-29, absent after · **Tolerance:** exact, dates are discrete
**Parse:** read_raw(source/decommissioned_2018.csv) == readings.csv

### TC-02: Flat spectrum on pure noise
**Pipeline:** PL-02 · **Covers:** STAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/gridload/TC-02/
**Source:** generator `noise(T=2016, seed=7)`; closed form for a sinusoid's least-squares amplitude on white noise, edge a+ = 4σ√(2/T)
**Expected:** every fitted Fourier amplitude ≤ a+ · **Tolerance:** 5% of a+, for finite-sample fluctuation

### TC-03: Planted daily sine is recovered
**Pipeline:** PL-02 · **Covers:** STAT-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/gridload/TC-03/
**Source:** generator `daily_sine(T=1000, amplitude=1.0, seed=3)`
**Expected:** the daily term explains ≥ 40% of variance · **Tolerance:** property; the planted sine carries well over 40% by construction

## Open questions

## Retired
````

The synthetic fixtures hold only the generator and the property:

```
TC-02/input.json     {"generator": "noise", "T": 2016, "seed": 7}
TC-02/expected.json  {"property": "max_fourier_amp <= amp_edge", "tol_frac": 0.05}
TC-03/input.json     {"generator": "daily_sine", "T": 1000, "amplitude": 1.0, "seed": 3}
TC-03/expected.json  {"property": "explained['daily'] >= 0.40"}
```

### Review gate message

```
Wrote docs/packages/gridload/tests.md (Draft) and fixtures TC-01..TC-03.

Strategy: one smoke per pipeline (above).
Oracles — please approve each:
- TC-01 (PL-01, your file): M-0417 present through 2018-06-29, absent after · exact, dates are discrete
- TC-02 (PL-02, noise T=2016 seed 7): every fitted Fourier amplitude ≤ a+ · 5% of a+, finite-sample fluctuation
- TC-03 (PL-02, daily sine T=1000 seed 3): daily term explains ≥ 40% · property

Transcription: readings.csv from your export (shown above). Check the dates: DD/MM in the raw.
ASSUMPTIONS: seeds 7 and 3; sizes; the 5% edge tolerance; case names; each case's step span.
Open questions: none.
Uncovered: STAT-02 and STAT-04 have step unit tests but no golden case (no trusted output exists).

Do you approve these expected outputs?
```

---

## Example 2: LeafLab, single-crop set (New, synthetic only)

**Context:** PL-01 Train a model (`make_dataset` → `make_model` → `train` → `run_baselines` → `evaluate` → `save_run`) and PL-02 View predictions (prediction gallery and confusion matrix) are Approved. The user has no trained models yet, so there are no real pairs. Spec: MOD-01, TRN-01, EVAL-01 (held-out accuracy beats the majority-class and logistic baselines), QR-02 (same seed, same run). No installed skill owns "beats a baseline".

````markdown
## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m leaflab train single-crop --model cnn --smoke` | datasets, train, evaluate, runs | TC-01 (Dataset, Model → train → Model), TC-02 (whole pipeline) | TC-03 |
| PL-02 | `python -m leaflab gallery runs/<id> --smoke` | predict, render | TC-02 (whole pipeline) | — |

### TC-01: Separable set solved by construction
**Pipeline:** PL-01 · **Covers:** MOD-01, TRN-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/leaflab/TC-01/
**Source:** generator `separable(n=40, classes=2, seed=0)`: the two classes' pixel means differ by a fixed margin, so a linear boundary separates them by construction
**Expected:** after 50 training epochs the model classifies all 40 training images correctly, on each of 5 eval seeds · **Tolerance:** exact, a count of correct images is discrete

### TC-02: Same seed, same run
**Pipeline:** PL-01 · **Covers:** QR-02 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/leaflab/TC-02/
**Source:** generator `single_crop(size=32, seed=42)`, 5 epochs, run twice
**Expected:** both runs write byte-identical log.csv and weights.npz; the gallery for either shows the same predictions · **Tolerance:** exact, determinism is the requirement

### TC-03: CNN beats the baselines on the single-crop set
**Pipeline:** PL-01 · **Covers:** EVAL-01 · **Kind:** model evaluation · **Fixture:** tests/fixtures/leaflab/TC-03/
**Source:** spec EVAL-01
**Expected:** accuracy on the held-out test split (never used in training) is above the majority-class and the logistic baseline's, for each of training seeds 0, 1, 2 · **Tolerance:** none, a strict comparison per training seed; seeds are fixed so the result reproduces
````

`TC-01/input.json` is `{"generator": "separable", "n": 40, "classes": 2, "seed": 0, "epochs": 50, "eval_seeds": [0, 1, 2, 3, 4]}` and `expected.json` is `{"property": "train_accuracy == 1.0", "tol": 0}`.

Under **Open questions:** "EVAL-01 says 'beats'. No installed skill owns that claim, so TC-03 uses a strict per-seed comparison on 3 training seeds. Is that the bar you want, or should it be a statistical test?"
