# pytest (with pytest-cov and Hypothesis)

Related: [ruff_core.md](ruff_core.md#pt-flake8-pytest-style) (the `PT` lint rules)

| | |
|---|---|
| **What it does** | Runs your tests. `pytest-cov` shows which lines no test ran. Hypothesis generates edge-case inputs for property tests |
| **Speed** | Depends entirely on your suite. `pytest-cov` usually adds roughly 10–30% (less on Python 3.12+ with the `sysmon` core). Each Hypothesis test runs about 100 examples by default |
| **Config** | `[tool.pytest.ini_options]`, `[tool.coverage.*]` |
| **Hook tier** | Implementer Stop gate (`--no-cov`, fast); reviewer and CI (with coverage and a bigger Hypothesis profile) |

> **Verified** in `design/tooling-verification.md` (2026-10-16): pytest 9.1.1, pytest-cov 7.1.0, Hypothesis 6.170.0. The `dev` profile stops at 20 examples and `ci` at 500 (`--hypothesis-show-statistics`).

---

## Who owns which tests

This is the contract your three agents rely on.

```text
tests/
  conftest.py        human-owned (Hypothesis profiles). Protected. build-setup writes it only if missing.
  intent/<pkg>/      TESTER writes these first, from TC cases and acceptance criteria. Protected from the implementer.
  unit/<pkg>/        IMPLEMENTER writes these.
  fixtures/<pkg>/TC-NN/   test-planning writes these. expected.json changes only with the user's yes.
```

- **Tester** writes `tests/intent/`: tests of *what the code should do*, written before the implementation. They should fail at first, for the right reason.
- **Implementer** makes them pass, and writes `tests/unit/` for its own code.
- **Reviewer** runs everything, with coverage, and reads for gaps.

The "implementer can't edit intent tests" rule is enforced by hooks plus a git check. See [hooks.md](hooks.md#two-layers). `check.sh --pkg <id>` runs `tests/{intent,unit}/<id>` plus the dirs of every package that depends on it.

## Config

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config --import-mode=importlib"
xfail_strict = true            # an xfail test that unexpectedly passes is a failure
markers = [
    "intent: tester-written specification tests",
    "unit: implementer-written unit tests",
    "repro: same seed, same result",
    "slow: skipped in the fast loop",
]
# filterwarnings = ["error"]   # turn warnings into failures once the suite is clean

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
skip_covered = true
show_missing = true
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
fail_under = 80               # CR-40: the measured value; Ratchet raises it
```

`repro` is declared so `--strict-markers` accepts it. It labels the reproducibility tests behind a QR; `gate` runs every test anyway, so `-m repro` is only for running them alone.

pytest exits 5 when it collects nothing. `check.sh` treats that as a pass in `gate` and `full` (a fresh skeleton has no tests), and as a failure in `collect` (the tester wrote nothing).

Coverage is not in `addopts` on purpose: gates pass `--no-cov` or `--cov` explicitly, so the fast loop stays fast. The threshold lives in `fail_under`, not a `check.sh` flag, so `dt status` can compare it with CONSTRAINTS.md.

## Failures you will see (and why they are useful)

**A failing assertion**
```python
def test_rolling_mean():
    assert rolling_mean([1, 2, 3], 2) == 2.0
# E  assert 2.5 == 2.0
```
Why: pytest rewrites asserts so you see both values without writing a message.

**`DID NOT RAISE`**
```python
def test_rejects_zero_window():
    with pytest.raises(ValueError):
        rolling_mean([1, 2, 3], 0)
# Failed: DID NOT RAISE <class 'ValueError'>
```
Why: the code didn't validate input. Add `match="window"` too, or any `ValueError` passes (that's Ruff's `PT011`).

**Typo in a marker (with `--strict-markers`)**
```python
@pytest.mark.slwo
def test_x(): ...
# 'slwo' not found in `markers` configuration option
```
Why: without strict markers, a typo silently means "no marker", and the test runs when you thought it was excluded.

**Unexpected pass (with `xfail_strict`)**
```python
@pytest.mark.xfail
def test_known_bug(): ...   # now passes
# [XPASS(strict)] test_known_bug
```
Why: a fixed bug leaves a stale xfail otherwise, and agents can't hide a failing test by marking it xfail and forgetting.

**Collection error**
```python
from mypkg.missing import thing     # ModuleNotFoundError
# ERROR collecting tests/intent/test_a.py
```
Why: one broken import stops the whole file from running. This is what the tester's gate checks with `--collect-only`.

**Fixture not found**
```python
def test_x(load_df): ...            # fixture not defined anywhere
# E  fixture 'load_df' not found
```

## Parametrize: many cases, one test

```python
@pytest.mark.parametrize(
    ("window", "expected"),
    [(1, 3.0), (2, 2.5), (3, 2.0)],
)
def test_rolling_mean(window, expected):
    assert rolling_mean([1, 2, 3], window) == pytest.approx(expected)
```
Why: each case is reported separately. Use `pytest.approx` for floats, never `==`.

## pytest-cov: what no test touched

```bash
pytest --cov --cov-report=term-missing
```
```text
Name              Stmts   Miss Branch BrPart  Cover   Missing
src/signals.py       42      7     10      2    83%   18-24, 31->33
```
`Missing` lists line ranges never executed; `31->33` means a branch from line 31 to 33 never ran. Use it to find missing tests, not to chase a score. Agents can write tests that execute lines without asserting anything, so the reviewer should read the tests too.

## Hypothesis: let the library find edge cases

```python
from hypothesis import given, strategies as st
import statistics

@given(st.lists(st.floats()))
def test_mean_in_range(xs):
    assert min(xs) <= statistics.mean(xs) <= max(xs)
# Falsifying example: test_mean_in_range(xs=[])
# (it also finds nan and inf)
```
Why: it tries many inputs and shrinks a failure to the smallest example. It suits numeric, parsing and round-trip code (`parse(format(x)) == x`).

Control the cost with profiles in `tests/conftest.py` (human-owned):
```python
import os
from hypothesis import settings
settings.register_profile("dev", max_examples=20)
settings.register_profile("ci", max_examples=500)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
```
Gates use `dev`; the reviewer or CI sets `HYPOTHESIS_PROFILE=ci`.

## Commands by situation

```bash
pytest tests/intent --collect-only -q --no-cov   # tester gate: do the tests import and collect?
pytest tests/intent -x -q --no-cov               # intent tests only, stop at first failure
pytest tests/unit tests/intent --no-cov -q       # implementer gate
pytest -m "not slow" --no-cov                    # fast loop
pytest --lf --no-cov                             # only what failed last time
HYPOTHESIS_PROFILE=ci pytest --cov -q            # reviewer / CI
```

`pytest-xdist` (`pytest -n auto`) runs tests in parallel and helps big suites. It is a separate install and a good optional extra.
