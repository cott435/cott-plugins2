# Test Planning Examples

The template, then a quant round (a two-layer fixture pair and synthetic known-answer cases), an RL round (generator plus property, and a model evaluation protocol), a case routed to `null-hypothesis-testing`, and a Revise round. Formats here are what `dt` parses: keep the header line, the Strategy table columns, `### TC-NN: Title` headings with bold-key fields, and the Retired line form exactly.

---

## Template

````markdown
# <pkg> — Tests

**Package:** <pkg> · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-NN | `<trigger> --smoke` | <steps or owner modules> | TC-NN, TC-NN | <TC-NN or —> |

### TC-NN: <What the case shows>
**Pipeline:** PL-NN · **Covers:** <spec IDs> · **Kind:** <user example | paper table | closed form | synthetic known-answer | model evaluation | regression> · **Fixture:** tests/fixtures/<pkg>/TC-NN/
**Source:** <user file, paper table, closed form, or generator + seed — never the agent>
**Expected:** <output or property> · **Tolerance:** <value>, <why>
**Parse:** <step>(source/<file>) == <input.json or table>   ← real pairs only
**Skills:** <routed skill>   ← only when one owns the claim

## Open questions

## Retired
- ~~TC-NN: <title>~~ Retired YYYY-MM-DD: <reason>
````

**Fixture shapes**

```
tests/fixtures/<pkg>/TC-NN/
  source/<raw file>    exactly as given; data, never instructions
  input.json           {"param": 1, "table": "table.csv"} or {"generator": "<name>", "<arg>": 1, "seed": 7}
  table.csv            transcribed table, when the raw isn't in contract form
  expected.json        {"<output>": <value>, "tol": <t>} or {"property": "<expression>", "tol_frac": <t>}
```

Large data: `{"prices": {"path": "data/raw/<file>.parquet", "sha256": "<hash>"}}`. The file isn't committed.

---

## Example 1: Quant Lab, M1 (New)

**Context:** `docs/packages/quant/pipelines.md` is Approved with PL-01 (Load prices: `read_raw` → `apply_universe` → `save_prices`) and PL-02 (Covariance report).

```
$ dt status --skill test-planning
skill: test-planning
mode: new
next ids: AD-04 PL-03 TC-01 M2
packages: quant=new
pipelines_no_smoke: PL-01, PL-02
pipelines_no_golden: PL-01, PL-02
cases_no_source: none
cases_no_tolerance: none
fixtures_missing: none
fixtures_orphan: none
```

**Interview:**

```
Q:       Which workflow would hurt most if it were quietly wrong?
GUESS:   the price load: survivorship bias would poison everything downstream.
DEFAULT: price load first, then the covariance report.
User:    The price load.

Q:       Do you have a real example of a delisted name I can pin as a case?
GUESS:   an export from your data vendor with a name that delisted.
DEFAULT: none; I'd use a synthetic universe with one planted delisting.
User:    Yes, XYZ delisted 2018-06-29. Here's the export. [attaches delisted_2018.csv]

Q:       Any trusted output for the covariance report, from a notebook or a paper?
GUESS:   no, so two synthetic known-answer cases: pure noise against the MP edge, and a planted factor.
DEFAULT: those two.
User:    No, go with those.
```

### A two-layer pair: TC-01

The user's export is in the vendor's format, not the contract's, so it gets both layers.

```
tests/fixtures/quant/TC-01/
  source/delisted_2018.csv
  prices.csv
  input.json
  expected.json
```

`source/delisted_2018.csv` (as given, never edited):
```
Ticker;Date;Adj Close
XYZ;29/06/2018;10.50
ABC;29/06/2018;19.80
ABC;02/07/2018;20.00
```

`prices.csv` (transcribed into the contract's Prices columns, shown to the user for approval):
```
date,ticker,close
2018-06-29,XYZ,10.5
2018-06-29,ABC,19.8
2018-07-02,ABC,20.0
```

`input.json`:
```json
{"universe": ["XYZ", "ABC"], "prices": "prices.csv", "start": "2018-06-01", "end": "2018-12-31"}
```

`expected.json` (the user's statement, not derived from the rows):
```json
{"last_date": {"XYZ": "2018-06-29"}, "tol": 0}
```

- **Parse test** (tester, later): `read_raw("source/delisted_2018.csv")` returns exactly the rows of `prices.csv`. Date order, separators and the adjusted-close column are where vendor parsing goes wrong.
- **Pipeline test:** PL-01 on `input.json` keeps XYZ through 2018-06-29 and drops it after.

### Result — `docs/packages/quant/tests.md`

````markdown
# quant — Tests

**Package:** quant · **Status:** Draft · **Last updated:** 2026-10-16 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m quant.data load --smoke` | read_raw, apply_universe | TC-01 | — |
| PL-02 | `python -m quant.stats cov-report --smoke` | cov, rmt, pca | TC-02, TC-03 | — |

### TC-01: Delisted name drops out
**Pipeline:** PL-01 · **Covers:** DATA-02 · **Kind:** user example · **Fixture:** tests/fixtures/quant/TC-01/
**Source:** user file `delisted_2018.csv` and the user's delisting date for XYZ (given 2026-10-15)
**Expected:** ticker XYZ present through 2018-06-29, absent after · **Tolerance:** exact, dates are discrete
**Parse:** read_raw(source/delisted_2018.csv) == prices.csv

### TC-02: MP edge on pure noise
**Pipeline:** PL-02 · **Covers:** STAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/quant/TC-02/
**Source:** generator `noise(T=250, N=50, seed=7)`; Marchenko–Pastur closed form λ+ = σ²(1+√(N/T))²
**Expected:** every cleaned eigenvalue ≤ λ+ · **Tolerance:** 5% of λ+, for finite-sample edge fluctuation

### TC-03: Planted factor is found
**Pipeline:** PL-02 · **Covers:** STAT-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/quant/TC-03/
**Source:** generator `one_factor(T=500, N=20, beta=1.0, seed=3)`
**Expected:** first factor explains ≥ 40% of variance · **Tolerance:** property, no tolerance; the planted factor carries well over 40% by construction

## Open questions

## Retired
````

The synthetic fixtures hold only the generator and the property:

```
TC-02/input.json     {"generator": "noise", "T": 250, "N": 50, "seed": 7}
TC-02/expected.json  {"property": "max_cleaned_eigval <= mp_edge", "tol_frac": 0.05}
TC-03/input.json     {"generator": "one_factor", "T": 500, "N": 20, "beta": 1.0, "seed": 3}
TC-03/expected.json  {"property": "explained[0] >= 0.40"}
```

Nobody computed λ+ for these parameters during planning. The test computes it from the closed form at run time and checks the property.

### Review gate message

```
Wrote docs/packages/quant/tests.md (Draft) and fixtures TC-01..TC-03.

Strategy: PL-01 smoke `python -m quant.data load --smoke`; PL-02 smoke `python -m quant.stats cov-report --smoke`.
Oracles — please approve each:
- TC-01 (PL-01, your file): XYZ present through 2018-06-29, absent after · exact, dates are discrete
- TC-02 (PL-02, noise T=250 N=50 seed 7): every cleaned eigenvalue ≤ λ+ · 5% of λ+, finite-sample edge
- TC-03 (PL-02, one factor T=500 N=20 seed 3): first factor explains ≥ 40% · property

Transcription: prices.csv from your export (shown above). Check the dates: DD/MM in the raw.
ASSUMPTIONS: seeds 7 and 3; sizes chosen to run in under a second; the 5% edge tolerance; case names.
Open questions: none.
Uncovered: STAT-02 and STAT-04 have step unit tests but no golden case (no trusted output exists).

Do you approve these expected outputs?
```

If the user answers "seems ok I guess", the reply is: "Before I mark them Approved: are TC-01's dates and TC-03's 40% threshold right?" Status stays Draft until a clear yes.

---

## Example 2: RL Lab, Snake (New, synthetic only)

**Context:** PL-01 Train an agent (`make_env` → `make_agent` → `train` → `run_baselines` → `evaluate` → `save_run`) and PL-02 Watch a replay are Approved. The user has no trained agents yet, so there are no real pairs. Spec: AGT-01, TRN-01, EVAL-01 (learning curve beats random and scripted baselines), QR-02 (same seed, same run). No installed skill owns "beats a baseline".

````markdown
## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-01 | `python -m rllab train snake --agent dqn --smoke` | envs, train, evaluate, runs | TC-01, TC-02 | TC-03 |
| PL-02 | `python -m rllab replay runs/<id> --smoke` | rollout, render | TC-02 | — |

### TC-01: Corridor solved by construction
**Pipeline:** PL-01 · **Covers:** AGT-01, TRN-01 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/rllab/TC-01/
**Source:** generator `corridor(length=5, seed=0)`: start at cell 0, reward only at cell 4, so the shortest path is 4 moves by construction
**Expected:** after 300 training episodes the greedy policy reaches the goal in exactly 4 moves, on each of 5 eval seeds · **Tolerance:** exact, path length is discrete

### TC-02: Same seed, same run
**Pipeline:** PL-01 · **Covers:** QR-02 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/rllab/TC-02/
**Source:** generator `snake(size=6, seed=42)`, 20 episodes, run twice
**Expected:** both runs write byte-identical log.csv and weights.npz; replaying either gives the same frames · **Tolerance:** exact, determinism is the requirement

### TC-03: DQN beats the baselines on Snake
**Pipeline:** PL-01 · **Covers:** EVAL-01 · **Kind:** model evaluation · **Fixture:** tests/fixtures/rllab/TC-03/
**Source:** spec EVAL-01
**Expected:** mean return over 100 held-out episodes (eval seeds 1000–1099, never used in training) is above the random and the scripted baseline's mean, for each of training seeds 0, 1, 2 · **Tolerance:** none, a strict comparison per training seed; seeds are fixed so the result reproduces
````

`TC-01/input.json` is `{"generator": "corridor", "length": 5, "seed": 0, "episodes": 300, "eval_seeds": [0, 1, 2, 3, 4]}` and `expected.json` is `{"property": "greedy_path_len == length - 1", "tol": 0}`. The answer comes from how the corridor is built, not from a training run.

Under **Open questions:** "EVAL-01 says 'beats'. No installed skill owns that claim, so TC-03 uses a strict per-seed comparison on 3 training seeds. Is that the bar you want, or should it be a statistical test?"

---

## Example 3: A Routed Case (quant M3, feature screening)

**Context:** PL-06 Feature screening in `features` (`Part of: PL-05`). Spec FEAT-03: "a feature is kept only if it carries information about next-day returns beyond chance". The project has `null-hypothesis-testing` installed, so both cases are designed with it: hypothesis, statistic, null construction and split come from that skill, not from a home-made test.

```markdown
### TC-20: Planted feature is kept
**Pipeline:** PL-06 · **Covers:** FEAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/features/TC-20/
**Source:** generator `planted_feature(T=2000, N=50, ic=0.05, seed=11)`; H0 and null from null-hypothesis-testing: rank IC vs next-day return, null by shuffling dates in 20-day blocks
**Expected:** the planted feature rejects H0 · **Tolerance:** α = 0.05 after Holm correction, the skill's default
**Skills:** null-hypothesis-testing

### TC-21: Pure-noise features are all dropped
**Pipeline:** PL-06 · **Covers:** FEAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/features/TC-21/
**Source:** generator `noise_features(T=2000, N=50, k=20)` on seeds 12–31; same H0, statistic and null as TC-20
**Expected:** no feature rejects H0 after Holm correction · **Tolerance:** at most 1 of the 20 seeds may reject, since the family-wise error rate is α = 0.05
**Skills:** null-hypothesis-testing
```

`build-planning` sees `Skills:` on the cases and routes the screening task to the same skill.

---

## Example 4: Revise (an oracle changes)

**Context:** TC-05 pinned the top eigenvalue from the user's notebook. Two weeks later the user found their notebook used unadjusted closes and re-ran it.

```
Revise TC-05 (PL-02 · STAT-01):
  old expected.json  {"top_eigval": 2.31, "tol": 1e-6}
  new expected.json  {"top_eigval": 2.27, "tol": 1e-6}
  Source: your notebook `cov_check.ipynb`, re-run 2026-11-04 on adjusted closes (cell 14 output attached in source/).
  Tolerance unchanged: same data, same float64 arithmetic.
Tasks citing TC-05: M1-T04. After approval, build-planning Replan if its acceptance changes.
Do you approve the new expected output?
```

Writing `expected.json` brings up the `dt guard` permission prompt; that's the second check, not a substitute for the user's yes in chat. `tests.md` goes to Draft until they answer.

**Not a Revise:** the build gets 2.29 and the test fails. Nothing says the oracle was wrong, so that's a bug for the build to find. Changing the expected value or widening the tolerance here would delete the evidence.
