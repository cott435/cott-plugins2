# Revise

Read when the user asks for a rule, threshold or exception change. Exceptions and numbers follow `derive.md`; the run ends at the Review Gate in `../SKILL.md`.

## Steps

Edit `CONSTRAINTS.md` and its config key together. A request to raise a limit "just this once" to unblock a task is a loosening like any other: an expiring exception with the user's yes, or the code gets fixed. A raised global limit (`max-complexity = 12`) is a bigger loosening than a file-scoped exception; offer the exception first.

## Example: a loosening

```
You asked to allow complexity 12 in profile/holidays.py.
Loosening: CR-21 ≤ 10 per function → unchanged; new exception
  EX-03 · CR-21 C901 · `src/gridload/profile/holidays.py` · observed-holiday rules follow the tariff's 12-branch case split · @connor · 2026-12-31
  pyproject: [tool.ruff.lint.per-file-ignores] "src/gridload/profile/holidays.py" = ["C901"]
This needs your explicit yes.
```
