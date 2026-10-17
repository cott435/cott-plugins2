# mypy: static type checking

Related: [pyright.md](pyright.md) (the alternative)

| | |
|---|---|
| **What it does** | Reads your type annotations and reports calls and values that don't match them. Ruff can't do this because it doesn't resolve types |
| **Speed** | Slowest of the checkers on a cold run. Much faster once its cache (`.mypy_cache`) is warm, and faster still with the daemon (`dmypy`) |
| **Config** | `[tool.mypy]` in `pyproject.toml` |
| **Hook tier** | Stop gate for implementers; reviewer. Per-edit only if you use `dmypy` |
| **mypy or pyright?** | Pick **one** as the hard gate. Running both gives duplicate and sometimes conflicting messages that agents try to satisfy both ways |

> **Verified** in `design/tooling-verification.md` (2026-10-16): mypy 2.4.0, strict, 0.16 s warm and 1.75 s cold on a 7-file package.

## Config

```toml
[tool.mypy]
python_version = "3.11"
files = ["src"]
strict = true                 # turns on the checks below and more
show_error_codes = true
pretty = true

[[tool.mypy.overrides]]   # an exception: needs a row in CONSTRAINTS.md's Exceptions table
module = ["some_untyped_lib.*"]
ignore_missing_imports = true
```

`files = ["src"]` means mypy never sees tests, so a `tests.*` override is dead config; the template has none. Multi-package lists every `packages/<id>/src`.

**Stubs.** strict fails with `import-untyped` on a library without types. Add its stubs to the dev group in New and Extend: `pandas-stubs` for pandas (verified), `types-requests`, `types-PyYAML` and so on.

Starting on an existing codebase? Drop `strict = true`, begin with `disallow_untyped_defs = true` on new modules only, and widen from there.

## Errors it catches

**`union-attr`: using a value that might be None**
```python
import re
m = re.match(r"\d+", s)
print(m.group(0))   # error: Item "None" of "Match[str] | None" has no attribute "group"  [union-attr]
```
Why: `re.match` returns `None` when there's no match, and this crashes with `AttributeError` on that input. Fix: `if m is not None:`.

**`arg-type`: wrong argument type**
```python
def sma(prices: list[float], n: int) -> float: ...
sma([1.0, 2.0], "20")     # error: Argument 2 has incompatible type "str"; expected "int"  [arg-type]
```
Why: fails later and further away, usually as a `TypeError` inside the function.

**`return-value`: return doesn't match the signature**
```python
def count() -> int:
    return "3"            # error: Incompatible return value type (got "str", expected "int")  [return-value]
```

**`assignment`: incompatible assignment**
```python
x: int = "a"              # error: Incompatible types in assignment  [assignment]
```

**`attr-defined`: attribute that doesn't exist**
```python
"abc".foo()               # error: "str" has no attribute "foo"  [attr-defined]
```
Why: catches typos and use of renamed methods.

**`call-arg`: wrong number of arguments**
```python
def f(a: int) -> None: ...
f(1, 2)                   # error: Too many arguments for "f"  [call-arg]
```

**`no-untyped-def` (strict): missing annotations**
```python
def f(x):                 # error: Function is missing a type annotation  [no-untyped-def]
    return x
```
Why: unannotated functions are skipped by the checker, so bugs inside them go unseen.

**`var-annotated`: empty container needs a type**
```python
items = []                # error: Need type annotation for "items"  [var-annotated]
```

**`import-untyped`: library has no type stubs**
```python
import yaml              # error: Library stubs not installed for "yaml"  [import-untyped]
```
Fix: install the stubs package (`types-PyYAML`) or add an override.

**`unused-ignore`: stale ignore comment**
```python
x: int = 1  # type: ignore    # error: Unused "type: ignore" comment  [unused-ignore]
```
Why: with `warn_unused_ignores` (part of strict), agents can't leave dead ignores behind.

**A used `# type: ignore[code]` passes mypy and every other gate tool** (verified). mypy can't be told to ignore its own ignores. `floor_guard.sh` catches it on the diff (CR-01), and pyright with `enableTypeIgnoreComments = false` catches it in `full`.

**`override`: subclass breaks the parent's signature**
```python
class A:
    def run(self, n: int) -> int: ...
class B(A):
    def run(self, n: str) -> int: ...   # error: Argument 1 of "run" is incompatible with supertype "A"  [override]
```

## Making it fast enough for hooks

```bash
mypy                       # reads files = ["src"]; uses .mypy_cache
dmypy run -- src           # starts a daemon on first call; later calls are quick
dmypy stop                 # when finished
```

For the implementer's Stop gate, plain `mypy` with a warm cache is usually fine. If it is slow in your repo, switch the gate to `dmypy run -- src`.

## Habits to enforce with agents

- Never add `# type: ignore` at all. Ruff's `PGH003` rejects a blanket one, mypy flags an unused one, and `floor_guard.sh` flags a used one.
- Don't let agents loosen `[tool.mypy]`. `pyproject.toml` is on the protected list (see [hooks.md](hooks.md)).
