# Ruff: complexity and size limits

Related: [ruff_core.md](ruff_core.md)

| | |
|---|---|
| **What it covers** | Cyclomatic complexity, function length, argument counts, branches, returns, nesting, locals |
| **Speed** | Instant, same as the rest of Ruff |
| **Config** | `[tool.ruff.lint.mccabe]` and `[tool.ruff.lint.pylint]` |
| **Hook tier** | End-of-work gate (Stop) for implementers, plus the reviewer. You can also run it per edit because it is instant |
| **Why it matters for agents** | Agents tend to grow functions instead of splitting them. These limits force splitting |

> **Verified** in `design/tooling-verification.md` (2026-10-16). `PLR0914`, `PLR1702` and `PLR0904` are still preview; `PLR0917` is stable.

## The rules at a glance

| Limit you want | Rule | Default | Setting (under `[tool.ruff.lint.…]`) | Status in ruff 0.17.1 |
|---|---|---|---|---|
| Cyclomatic complexity | **C901** | 10 | `mccabe` → `max-complexity` | stable |
| Function length (in **statements**) | **PLR0915** | 50 | `pylint` → `max-statements` | stable |
| Number of arguments | **PLR0913** | 5 | `pylint` → `max-args` | stable |
| Positional arguments | **PLR0917** | 5 | `pylint` → `max-positional-args` | stable |
| Branches | **PLR0912** | 12 | `pylint` → `max-branches` | stable |
| Return statements | **PLR0911** | 6 | `pylint` → `max-returns` | stable |
| Local variables | **PLR0914** | 15 | `pylint` → `max-locals` | **preview** |
| Nested blocks | **PLR1702** | 5 | `pylint` → `max-nested-blocks` | **preview** |
| Public methods per class | **PLR0904** | 20 | `pylint` → `max-public-methods` | **preview** |

**Preview rules.** To turn on only the preview rules you name (not all preview behavior), set:
```toml
[tool.ruff.lint]
preview = true
explicit-preview-rules = true
select = ["PLR0914", "PLR1702", "PLR0904"]   # plus your other selections
```
With preview on, also set `output-prefer-rule-codes = true` under `[tool.ruff]`, or the output shows rule names instead of codes.

**Statements, not lines.** `PLR0915` counts statements, so a long multi-line call counts as one. For physical length use the script at the bottom of this file.

---

## C901: cyclomatic complexity

The count is roughly 1 plus the number of decision points (`if`, `elif`, `for`, `while`, `except`, `case`). Each extra path needs its own test.

```python
# with max-complexity = 5
def tier(x):                      # complexity 6 -> C901
    if x < 0:
        return "neg"
    elif x == 0:
        return "zero"
    elif x < 10:
        return "small"
    elif x < 100:
        return "medium"
    elif x < 1000:
        return "large"
    return "huge"
```
Why: many paths means many hidden bugs and tests you need. Fix: a lookup table, `bisect`, or splitting the function.

## PLR0913: too many arguments

```python
# default max-args = 5
def backtest(df, start, end, fast, slow, fee, slippage):   # 7 args -> PLR0913
    ...
```
Why: long signatures are hard to call correctly and usually mean the function does too much or needs a config object. Fix: group related values into a dataclass.

## PLR0917: too many positional arguments

```python
# default max-positional-args = 5
def run(a, b, c, d, e, f): ...      # 6 positional -> PLR0917
def run(a, b, c, *, d, e, f): ...   # fine: d, e, f are keyword-only
```
Why: callers can swap arguments of the same type without noticing. Keyword-only arguments fix that cheaply.

## PLR0912: too many branches

```python
# with max-branches = 3
def handle(kind):                 # 4 branches -> PLR0912
    if kind == "a": ...
    elif kind == "b": ...
    elif kind == "c": ...
    else: ...
```
Why: similar to C901 but counts `if/elif/else`, `for`, `while`, `try` arms differently. Having both is fine, since they flag slightly different shapes.

## PLR0911: too many return statements

```python
# with max-returns = 3
def f(x):
    if x == 1: return "a"
    if x == 2: return "b"
    if x == 3: return "c"
    return "d"                    # 4 returns -> PLR0911
```
Why: many exits make it hard to tell what state the function leaves behind.

## PLR0915: too many statements (function length)

```python
# default max-statements = 50
def pipeline(df):
    a1 = ...
    a2 = ...
    ...                           # 51 simple statements -> PLR0915
```
Why: this is the closest Ruff gets to "function length". Long functions mix concerns and resist testing.

## PLR1702: too many nested blocks (preview)

```python
# with max-nested-blocks = 2
for a in xs:
    for b in ys:
        if a == b:                # third level -> PLR1702
            use(a)
```
Why: deep nesting is hard to read. Fix: early `continue`/`return` or extract a helper.

## PLR0914: too many locals (preview)

```python
# default max-locals = 15
def f():
    a = b = c = d = 0
    ...                           # 16+ local names -> PLR0914
```
Why: lots of live variables signals a function doing several jobs.

## PLR0904: too many public methods (preview)

```python
# default max-public-methods = 20
class Everything:
    def a(self): ...
    # ... 21 public methods -> PLR0904
```
Why: a "god class". Split by responsibility.

---

## What Ruff does NOT have

- **Function length in physical lines**: only statements (PLR0915).
- **Module / file length (min or max)**: I found no Ruff rule for this. Pylint has `too-many-lines` (C0302, default 1000), but Ruff does not implement it as far as I could confirm. It is not in the rule pages I read, so check `ruff rule --all | grep -i lines` on your machine.
- **Cognitive complexity** (different from cyclomatic): not in Ruff. Separate tools exist (for example `complexipy`), but I haven't verified them.

## Filling the gap: `scripts/check_size.py`

A small standard-library script (tested; needs Python 3.11+ for `tomllib`). It reads limits from your `pyproject.toml`:

```toml
[tool.size_limits]
max_module_lines = 500    # code lines per file
min_module_lines = 3      # skips __init__.py; catches empty placeholder files
max_function_lines = 60   # code lines per function or method
```

```bash
python scripts/check_size.py            # whole src/
python scripts/check_size.py src/a.py   # single file (used by the per-edit hook)
```

`SIZE003` also catches what `PLR0915` can't: a 62-line literal is one statement but 62 lines (verified).

Output looks like Ruff's:
```text
src/big.py:1: SIZE001 module has 14 code lines (max 10)
src/big.py:1: SIZE003 function `big` has 8 code lines (max 5)
src/tiny.py:1: SIZE002 module has 1 code lines (min 3)
```

"Code lines" are non-blank lines that aren't pure comments. Docstrings count. It exits 1 on any violation, so it works in hooks and CI. Source: [scripts/check_size.py](scripts/check_size.py).

If you'd rather use an existing tool, `pylint --disable=all --enable=too-many-lines --max-module-lines=500 src` does the max-length part. It is much slower than Ruff and has no minimum.

## Suggested starting values

These are tighter than the defaults on purpose, because agents drift toward big functions:

```toml
[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-positional-args = 4
max-branches = 10
max-returns = 5
max-statements = 40
max-locals = 12
max-nested-blocks = 4
```

Relax these for tests (long fixtures, many parametrized args) with a `per-file-ignores` entry. The full config is in [the pyproject template](../../templates/pyproject.toml). These numbers are CR-21 and CR-22 in CONSTRAINTS.md; change both together, through build-setup.
