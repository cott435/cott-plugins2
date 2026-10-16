# Constraints

**Last reviewed:** 2026-10-16 by @connor · **Status:** Approved

## Floor
- **CR-01** No new suppressions
- **CR-05** Oracle files (`tests/fixtures/**/expected.json`) change only with user approval

## Readability
- **CR-10** One entry function per pipeline; it reads top to bottom as its named steps

## Enforced with numbers
| ID | Dimension | Rule | Checked by | Config key | Runs at |
|---|---|---|---|---|---|
| CR-21 | Complexity | ≤ 10 per function | ruff C901 | `tool.ruff.lint.mccabe.max-complexity` | gate |
| CR-22 | Size | ≤ 500 lines/module, ≤ 60/function | check_size.py | `tool.size_limits` | edit, gate |

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
