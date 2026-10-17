# pip-audit: vulnerable dependencies

| | |
|---|---|
| **What it does** | Checks your installed or locked packages against a database of known vulnerabilities |
| **Speed** | A few seconds, but network-bound: it needs to reach a vulnerability database, so it can fail in offline or restricted sandboxes |
| **Config** | None needed. Options go on the command line |
| **Hook tier** | CI and the reviewer. **Not** per-edit, and not the implementer's gate: its result can change without any code change |

> **Verified** in `design/tooling-verification.md` (2026-10-16): pip-audit 2.10.1, 0.9 s warm, 3 s on its first run.

## What it catches

```text
Name      Version  ID              Fix Versions
requests  2.19.0   PYSEC-2018-28   2.20.0
```
Why: a pinned or old dependency with a known CVE. Ruff's `S` rules look for risky *code*; this looks at risky *packages*.

## Running it

```bash
pip-audit                       # audit the current environment
pip-audit -r requirements.txt   # audit a requirements file
```

The template runs `uv run --frozen pip-audit --skip-editable` in `full`: `--skip-editable` drops the "not on PyPI" row for the project itself. With no arguments it audits the whole venv, dev tools included.

Offline it fails, and `full` fails with it. That is correct: CONSTRAINTS.md's Review checklist needs at least one external check to have run.

Because the result depends on an outside database, run it on a schedule (the CI template runs nightly) as well as on pull requests. A new CVE can appear against code that did not change.
