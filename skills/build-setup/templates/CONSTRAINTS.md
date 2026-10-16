# Constraints
**Status:** Draft · **Last reviewed:** {{date}} by {{owner}} · **Ratcheted:** —

The standing quality bar. `pyproject.toml` and `scripts/check.sh` enforce it; every number here names its config key, and `dt status` fails if the two disagree. Only `build-setup` changes this file, with the user: tightening is routine, loosening needs an explicit yes.

## Floor
- **CR-01** No new suppressions. Ruff runs with `--ignore-noqa` in gate and full, so a Ruff exception is a `per-file-ignores` entry in protected config with a row in Exceptions. `# type: ignore`, `pyright:` comments and `pragma: no cover` are caught by `floor_guard.sh` on the diff
- **CR-02** No stubs: `raise NotImplementedError` outside abstract methods, `pass`-only bodies, bare `except: pass`
- **CR-03** No skipped, deleted or assertion-free tests, unless a row in Exceptions names the test file
- **CR-04** No secrets in source
- **CR-05** Oracle files (`tests/fixtures/**/expected.json`) change only with the user's approval
- **CR-06** The implementer never changes `tests/intent/**`
- **CR-07** This file, `pyproject.toml` tool config, `scripts/` and `.claude/agents/` are not weakened to make a change pass
- **CR-08** Nothing imports from `references/` or adds it to `sys.path` (or `PYTHONPATH`, pytest `pythonpath`). References are outside the tooling, so imported code would bypass the bar; `floor_guard.sh` checks the diff for both. Code copied from a reference is project code and meets the same bar

## Readability
- **CR-10** One entry function per pipeline; it reads top to bottom as its named steps (reviewer + `dt layout`)
- **CR-11** No registries, plugin dispatch or config-driven wiring without an AD
- **CR-12** New abstraction only with a second real implementation or a named seam
{{readability_rules}}

## Enforced with numbers
| ID | Dimension | Rule | Checked by | Config key | Runs at |
|---|---|---|---|---|---|
| CR-20 | Lint | zero errors; standing per-file-ignores only for `tests/**` and `__init__.py` | ruff | `tool.ruff.lint.select` | edit, gate |
| CR-21 | Complexity | ≤ 10 per function | ruff C901 | `tool.ruff.lint.mccabe.max-complexity` | gate |
| CR-22 | Size | ≤ 500 lines/module, ≤ 60/function | check_size.py | `tool.size_limits` | edit, gate |
| CR-23 | Types | zero errors, strict | {{type_gate}} | `{{type_gate_key}}` | gate |
| CR-24 | Boundaries | import contracts hold | import-linter | `tool.importlinter.contracts` | gate |
| CR-25 | Dependencies | none missing or unused | deptry | `tool.deptry` | gate |
| CR-26 | Deps security | nothing known-vulnerable | pip-audit | — | full, CI nightly |
{{extra_enforced_rows}}

## Measured, not yet enforced
| ID | Metric | Today | Direction |
|---|---|---|---|
| CR-40 | Coverage (branch) | {{coverage_today}} (`tool.coverage.report.fail_under`, raised by Ratchet) | must not fall |
| CR-41 | vulture findings at `min_confidence = 60` (`scripts/vulture_whitelist.py`) | {{vulture_today}} | must not grow |

## Boundaries (generated from architecture — do not edit)
{{boundary_rules}}

## Roles and protected paths
| Role | May edit | May not edit | Stop gate |
|---|---|---|---|
| tester | `tests/intent/**` | everything else; reads no source | `check.sh collect` |
| implementer / solo | `src/**`, `tests/unit/**` | the protected list | `check.sh gate` + protected-path diff against `refs/checks/base` |
| reviewer | nothing (the orchestrator records findings with `dt finding`) | everything | runs `check.sh full` by hand |

**Protected list** (`PROTECTED` in `scripts/check.sh`; `path_guard.sh deny --protected` reads the same list): {{protected_globs_md}}.

## Review
Run by the reviewer agent at every checkpoint and at milestone exit, over the diff since the checkpoint's base.
1. **Five axes:** correctness, readability, architecture, security, performance.
2. **Pipelines:** each entry function matches its step table (`dt layout`); step owners are respected; spine baselines are still selectable.
3. **Guard the bar:** diff this file, `pyproject.toml`, `scripts/` and `.claude/agents/` against the milestone's Base. Any loosening is a Critical finding. New exceptions need an owner and expiry.
4. **Tests:** no assertion-free tests, no weakened intent tests, golden cases still loaded from fixtures, Hypothesis on the `ci` profile.
5. **Docs:** `dt lint` clean, contracts fresh, no pre-build sections left after the spine.
6. **External check:** pip-audit ran, so the bar isn't made entirely of the agent's own tests.
7. **References:** where reference code was reused, its Caveats (`docs/references.md`) were handled (e.g. a full-sample fit became per-window), and it fits the contract and step table rather than the reference's own structure.

Findings go under the checkpoint block in `tasks/plan.md` (`dt finding`), each with a fix task or a reason. Critical findings block the next checkpoint.

## Done
agent-skills `references/definition-of-done.md`, tailored once:
- **Correctness and Quality:** checked per task by the gate.
- **Integration and Documentation:** checked at each checkpoint.
- **The full list:** checked at milestone exit.

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
{{exception_rows}}
