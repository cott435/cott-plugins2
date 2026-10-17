# Ruff: core rules

Related: [ruff_complexity.md](ruff_complexity.md) · [ruff_domain.md](ruff_domain.md)

| | |
|---|---|
| **What it is** | Linter and formatter in one, written in Rust |
| **Speed** | Instant: a whole repo usually takes well under a few seconds, and more rules barely change that |
| **Config** | `[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml` |
| **Hook tier** | Per-edit (PostToolUse) **and** end-of-work gate (Stop): every agent type |
| **Check what a rule does** | `ruff rule B006` prints the docs and says whether it is preview-only |

> Template config verified against ruff 0.17.1 in `design/tooling-verification.md`. Check one example with `ruff check --select B006 t.py`.

Rules with a fix can be applied with `ruff check --fix`. The per-edit hook (`check.sh fast`) uses `--fix`, so many of these never reach the agent as errors.

**Template settings that matter** (`templates/pyproject.toml`):
- `output-prefer-rule-codes = true`: with `lint.preview = true`, Ruff prints rule *names* (`complex-structure`) unless this is set. CONSTRAINTS.md and `per-file-ignores` cite codes.
- `gate` and `full` run `ruff check --ignore-noqa`, so a used `# noqa` doesn't pass (CR-01). An exception is a `per-file-ignores` entry in protected config, with one row in CONSTRAINTS.md's Exceptions table. The standing entries (`tests/**`, `__init__.py`) are part of CR-20, not exceptions.
- Don't list `PD901`: Ruff removed it and warns on every run.

---

## F: Pyflakes (real bugs)

**F401 unused import**
```python
import os          # F401
```
Why: dead imports slow startup, hide real dependencies, and often mean a refactor left something behind.

**F841 unused variable**
```python
def f():
    result = compute()   # F841: assigned, never used
```
Why: usually a forgotten `return`, or a typo in the name you meant to use.

**F821 undefined name**
```python
def f():
    return totl + 1      # F821: typo for `total`
```
Why: would be a `NameError` at runtime, and only on the path that runs it.

## E: pycodestyle errors

**E711 / E712 comparison to None / True**
```python
if x == None: ...        # E711
if flag == True: ...     # E712
```
Why: `==` can be overloaded. NumPy and pandas return arrays here, not bools. Use `is None` and plain truthiness.

**E722 bare except**
```python
try:
    run()
except:                  # E722
    pass
```
Why: also swallows `KeyboardInterrupt` and `SystemExit`, so you can't Ctrl-C a hung job.

## I: isort

**I001 unsorted imports**
```python
import sys
import abc               # I001: wrong order / grouping
```
Why: consistent import blocks mean smaller diffs and no merge conflicts over import order. Auto-fixable.

## B: flake8-bugbear (likely bugs)

**B006 mutable default argument**
```python
def add(x, acc=[]):      # B006
    acc.append(x)
    return acc
```
Why: the default list is created once and shared across calls, so state leaks between them.

**B023 closure captures loop variable**
```python
fns = [lambda: i for i in range(3)]   # B023
print([f() for f in fns])             # [2, 2, 2], not [0, 1, 2]
```
Why: the lambda reads `i` when called, not when defined.

**B904 raise without `from` inside except**
```python
try:
    int(s)
except ValueError:
    raise RuntimeError("bad input")   # B904
```
Why: the traceback can't tell "caused by" from "a second error occurred while handling". Use `from e` or `from None`.

**B905 zip without `strict=`** (needs target Python 3.10+)
```python
for kwh, ts in zip(readings, timestamps):   # B905
    ...
```
Why: if the lists differ in length, `zip` silently truncates and your readings and timestamps misalign. `strict=True` raises instead.

**B007 unused loop variable**
```python
for i in range(3):       # B007: `i` never used -> use `_`
    do()
```
Why: tells readers the variable is intentionally ignored.

## UP: pyupgrade (modernize syntax)

**UP006 / UP045 old typing generics** (UP045 needs target 3.10+)
```python
from typing import List, Optional
def f(x: List[int]) -> Optional[str]: ...   # UP006, UP045
```
Why: use `list[int]` and `str | None`. Less import noise, same meaning.

**UP035 deprecated import**
```python
from typing import Callable   # UP035 -> collections.abc.Callable
```
Why: the `typing` aliases are deprecated and may be removed eventually.

## SIM: flake8-simplify

**SIM102 collapsible if**
```python
if a:
    if b:                # SIM102 -> if a and b:
        go()
```

**SIM115 file opened without context manager**
```python
f = open("x.txt")        # SIM115
data = f.read()
```
Why: if `read()` raises, the file handle leaks. Use `with open(...)`.

## C4: flake8-comprehensions

**C408 unnecessary `dict()` / `list()` call**
```python
d = dict(a=1, b=2)       # C408 -> {"a": 1, "b": 2}
```

**C419 comprehension inside `any` / `all`**
```python
any([x > 0 for x in xs]) # C419 -> any(x > 0 for x in xs)
```
Why: the list version builds the whole list first and can't short-circuit.

## RET: flake8-return

**RET504 needless assignment before return**
```python
def f():
    x = compute()
    return x             # RET504
```

**RET505 `else` after `return`**
```python
if a:
    return 1
else:                    # RET505
    return 2
```
Why: less nesting for the same logic.

## A: flake8-builtins

**A001 / A002 shadowing a builtin**
```python
max = 10                 # A001
def f(list): ...         # A002
```
Why: later `max(...)` or `list(...)` calls break with confusing errors. `id`, `type` and `input` are common victims.

## PTH: use pathlib

**PTH123 / PTH118**
```python
open("a.csv")                 # PTH123 -> Path("a.csv").open()
os.path.join("data", "a.csv") # PTH118 -> Path("data") / "a.csv"
```
Why: cross-platform paths and a cleaner API.

## PERF: performance anti-patterns

**PERF401 manual list building**
```python
out = []
for x in xs:
    out.append(x * 2)    # PERF401 -> [x * 2 for x in xs]
```

**PERF203 try/except in a loop**
```python
for x in xs:
    try:                 # PERF203
        parse(x)
    except ValueError:
        pass
```
Why: costs time before Python 3.11 (Ruff skips the rule for 3.11+ targets), and usually means validation belongs outside the loop.

## PL (selected): Pylint "likely error" and warning groups

Enable only `PLE` and `PLW` from the core list. The size and complexity rules (`PLR09xx`) are in [ruff_complexity.md](ruff_complexity.md).

**PLW2901 loop variable overwritten**
```python
for line in lines:
    line = line.strip()  # PLW2901
```
Why: reassigning the loop variable is confusing and error-prone. Use a new name.

**PLW0603 `global` statement**
```python
cache = {}
def f():
    global cache         # PLW0603
    cache = {}
```
Why: hidden mutable state makes code hard to test.

## TRY: tryceratops (exception hygiene)

**TRY300 return inside `try`**
```python
try:
    x = parse(s)
    return x             # TRY300 -> move to `else:`
except ValueError:
    return None
```

**TRY400 `logging.error` in except**
```python
except Exception as e:
    logging.error("failed: %s", e)   # TRY400 -> logging.exception(...)
```
Why: `logging.exception` includes the traceback, `logging.error` doesn't.

> Ignore **TRY003** (long messages in exception constructors). It is noisy.

## G: logging format

**G004 f-string in a logging call**
```python
logging.info(f"loaded {n} rows")     # G004 -> logging.info("loaded %d rows", n)
```
Why: the f-string is formatted even when INFO is disabled. Lazy `%` formatting skips that work.

## PGH: pygrep-hooks

**PGH003 blanket `# type: ignore`**
```python
x: int = foo()  # type: ignore      # PGH003 -> # type: ignore[assignment]
```
Why: a blanket ignore hides every future error on that line. This matters for agents, which reach for `# type: ignore` to make a checker go quiet.

## S: flake8-bandit (security)

**S101 `assert` in non-test code**
```python
assert user.is_admin     # S101
```
Why: `python -O` strips asserts, so the check disappears. Allow it in tests.

**S307 `eval`**
```python
eval(user_input)         # S307
```

**S301 pickle**
```python
pickle.load(f)           # S301
```
Why: loading a pickle can run arbitrary code. Be careful with pickled models and datasets you didn't create.

**S608 SQL built from strings**
```python
cur.execute(f"SELECT * FROM t WHERE sym = '{sym}'")   # S608
```
Why: SQL injection. Use parameters: `cur.execute("... WHERE sym = ?", (sym,))`.

**S105 hardcoded password / key**
```python
API_KEY = "sk-abc123"    # S105 (name looks like a secret)
```
Why: secrets end up in git history.

## PT: flake8-pytest-style

More on running tests in [pytest.md](pytest.md).

**PT011 `pytest.raises` too broad**
```python
with pytest.raises(ValueError):    # PT011 -> add match="..."
    f()
```
Why: any unrelated `ValueError` would make the test pass.

**PT018 composite assertion**
```python
assert a and b           # PT018 -> two asserts
```
Why: when it fails, you can't tell which half was false.

## RUF: Ruff-specific

**RUF012 mutable class attribute**
```python
class A:
    items = []           # RUF012 -> ClassVar or set in __init__
```
Why: the list is shared by every instance.

**RUF013 implicit Optional**
```python
def f(x: int = None): ... # RUF013 -> x: int | None = None
```
Why: type checkers no longer accept this, and it lies about the type.

**RUF015 materialise just to take one**
```python
first = list(it)[0]      # RUF015 -> next(iter(it))
```
Why: builds the entire list to read one element.

**RUF100 unused `noqa`**
```python
x = 1  # noqa: F401      # RUF100: nothing to suppress
```
Why: stale suppressions rot, and agents leave behind `noqa` comments that no longer do anything.

---

## Rules to skip (low value, high noise)

`D` (docstrings), `ANN` (the type checker does it better), `COM`, `ERA`, `FBT`, `CPY`, and `PLR2004` (magic numbers) unless you specifically want them.
