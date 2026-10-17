# pyright: static type checking

Related: [mypy.md](mypy.md) (the alternative)

| | |
|---|---|
| **What it does** | Same job as mypy: checks annotations against how values are used |
| **Speed** | Generally faster than a cold mypy run, and it re-checks incrementally in editors and `--watch` |
| **Config** | `[tool.pyright]` in `pyproject.toml` |
| **Hook tier** | Reviewer and CI; or the implementer's Stop gate if you pick pyright instead of mypy |
| **Install note** | The PyPI `pyright` wheel bundles the JS and runs on the system `node`. With no Node installed it downloads one through `nodeenv` on first run; use `pyright[nodejs]` to avoid that |

> **Verified** in `design/tooling-verification.md` (2026-10-16): pyright 1.1.414, 0.88 s warm. `enableTypeIgnoreComments = false` made it report the error a used `type: ignore[return-value]` hid.

**Pick one hard gate (mypy or pyright).** The two disagree on edge cases, and an agent will waste turns satisfying both. A common split is mypy as the gate and pyright left to your editor.

## Config

```toml
[tool.pyright]
include = ["src"]
pythonVersion = "3.11"
typeCheckingMode = "standard"   # "basic" < "standard" < "strict"
strict = ["src/core"]           # strict mode just for these paths
reportUnnecessaryTypeIgnoreComment = true
enableTypeIgnoreComments = false   # template default: a used `type: ignore[code]` still fails in full
```

The template gates on mypy and runs pyright in `full` only (CONSTRAINTS.md CR-23). If the user picks pyright as the gate, `TYPE_GATE=pyright` in `check.sh` and CR-23's key becomes `tool.pyright.typeCheckingMode`; `full` then runs mypy.

## Errors it catches

**`reportOptionalMemberAccess`: value might be None**
```python
import re
m = re.match(r"\d+", s)
print(m.group(0))   # error: "group" is not a known attribute of "None"
```
Why: the crash happens only on inputs that don't match.

**`reportArgumentType`: wrong argument type**
```python
def rolling_mean(loads: list[float], n: int) -> float: ...
rolling_mean([1.0], "20")    # error: Argument of type "Literal['20']" cannot be assigned to parameter "n" of type "int"
```

**`reportReturnType`: return doesn't match the signature**
```python
def count() -> int:
    return "3"      # error: Type "Literal['3']" is not assignable to return type "int"
```

**`reportAttributeAccessIssue`: attribute doesn't exist**
```python
"abc".foo()         # error: Cannot access attribute "foo" for class "str"
```

**`reportCallIssue`: wrong number or names of arguments**
```python
def f(a: int) -> None: ...
f(1, 2)             # error: Expected 1 positional argument
```

**`reportPossiblyUnbound`: variable may not be assigned**
```python
if cond:
    value = 1
print(value)        # error: "value" is possibly unbound
```
Why: a real `UnboundLocalError` on the other branch. Pyright flags this clearly.

**`reportIndexIssue`: indexing something that can't be indexed**
```python
x = None
x[0]                # error: Object of type "None" is not subscriptable
```

**`reportMissingImports`: import can't be resolved**
```python
import not_installed   # error: Import "not_installed" could not be resolved
```
Why: usually a missing dependency or wrong environment. Pairs with [deptry.md](deptry.md).

**`reportUnnecessaryTypeIgnoreComment`: stale ignore**
```python
x: int = 1  # type: ignore    # error: Unnecessary "# type: ignore" comment
```
Why: stops agents from leaving dead ignores around. Needs the setting turned on (shown in the config).

## Habits to enforce with agents

- `# pyright: ignore[...]` still works under `enableTypeIgnoreComments = false` (verified), so `floor_guard.sh` flags every new `pyright:` comment (CR-01).
- `pyproject.toml` is protected, so agents can't lower `typeCheckingMode` (see [hooks.md](hooks.md)).
