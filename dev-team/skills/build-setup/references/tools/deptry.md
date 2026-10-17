# deptry: dependency hygiene

| | |
|---|---|
| **What it does** | Compares what your code imports against what `pyproject.toml` declares |
| **Speed** | Fast: a few seconds |
| **Config** | `[tool.deptry]` |
| **Hook tier** | Implementer Stop gate and reviewer. Not per-edit (it needs the whole project) |

> **Verified** in `design/tooling-verification.md` (2026-10-16): deptry 0.25.1. It caught `DEP002` (`uv add six`) and `DEP003` (`from dateutil import parser`) in the sample.

## What it catches

**DEP001: imported but not declared**
```python
import requests        # DEP001: `requests` is not in pyproject.toml dependencies
```
Why: works on your machine because it happens to be installed, then fails on a clean install. Agents do this often: they `import` something that happens to be in the environment.

**DEP002: declared but never imported**
```toml
dependencies = ["pandas", "requests"]   # DEP002 if nothing imports requests
```
Why: dead weight, and each extra dependency is more attack surface.

**DEP003: relies on a transitive dependency**
```python
import urllib3         # DEP003 if you only declared `requests`, which pulls urllib3 in
```
Why: if `requests` drops `urllib3` later, your code breaks without warning.

**DEP004: dev dependency used in source code**
```python
import pytest          # DEP004 in src/ if pytest is only in the dev group
```

## Config

```toml
[tool.deptry]
known_first_party = ["yourpackage"]
# Packages whose import name differs from the install name:
# [tool.deptry.package_module_name_map]
# scikit-learn = "sklearn"
```

Run: `deptry . --no-ansi` (single package). Multi-package: `check.sh` runs it in each `packages/<id>/`, against that package's own `pyproject.toml`, so each declares only what it imports. A sibling package is a declared dependency (`{ workspace = true }`).

## Dependencies that arrive before the code (DEP002)

A dependency the milestone needs but no code imports yet fails `DEP002`. build-setup's default (design open item 1, option a): Extend adds the milestone's dependencies at kickoff, each with an exception that expires at milestone exit:

```toml
[tool.deptry.per_rule_ignores]
DEP002 = ["numpy", "pandas"]
```
```markdown
| EX-03 | CR-25 DEP002 | `numpy`, `pandas` | M2 dependencies, first imported by M2-T03 | @owner | M2 exit |
```

Remove the entry once the code imports the package (Ratchet does it at the latest). A dependency nobody planned blocks the task and goes to build-setup Revise; the implementer can't `uv add` (pyproject.toml and uv.lock are protected).
