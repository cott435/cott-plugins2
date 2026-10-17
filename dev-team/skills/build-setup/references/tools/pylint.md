# pylint duplicate-code: copied blocks

| | |
|---|---|
| **What it does** | Finds blocks of similar lines repeated across source files (R0801) |
| **Speed** | Seconds on a small codebase; it parses every file |
| **Config** | `[tool.pylint.similarities]` |
| **Hook tier** | `full` only (checkpoints, CI). Ruff does every other lint; pylint runs this one check |

> **Verified** 2026-10-17 with pylint 3.3.8 on a two-file sample: a 9-line episode loop copied under a new function name is reported, and pylint exits 8 (non-zero), so `check.sh full` fails. In config, `fail-under = 0`, `exit-zero = true` and `ignore-patterns` each turn that exit into 0.

## What it catches

```text
src/pkg/b.py:1:0: R0801: Similar lines in 2 files
==pkg.a:[1:10]
==pkg.b:[1:10]
    total = 0.0
    for s in seeds:
        ...
```
Why: builders in parallel worktrees can't see each other's code, so two tasks that need the same loop each write it. The reviewer turns each block into a finding (CR-42); the fix is one function in the owning module.

## Config

```toml
[tool.pylint.similarities]
min-similarity-lines = 8
ignore-imports = true
ignore-signatures = true
ignore-docstrings = true
ignore-comments = true
```

- 8 lines with imports, signatures, docstrings and comments ignored keeps import blocks, dataclass headers and stub signatures out.
- pylint has no whitelist. A block found on existing code is an Exceptions row plus its file in `[tool.pylint.main] ignore-paths`; Ratchet removes the entry once the block is gone.
- Multi-package: the config, and any `[tool.pylint.main] ignore-paths`, live in the root `pyproject.toml`; pylint reads it from where `check.sh` runs.
- `--fail-under=10` on the command line beats a lowered `fail-under` in config. `floor_guard` flags the other ways to silence it: a `# pylint: disable` or `skip-file` comment, `exit-zero = true`, a longer `ignore`, `ignore-patterns` or `ignore-paths`, and a `pylintrc`. Removing `min-similarity-lines` also counts as a loosening, though pylint's default (4) is stricter.
- Tests aren't scanned: they may repeat for readability.

Run: `pylint --disable=all --enable=duplicate-code --recursive=y --score=n --fail-under=10 <src dirs>` (`check.sh full`).
