# Constraints
**Status:** Approved · **Last reviewed:** 2026-10-17 by @connor · **Ratcheted:** —

The standing quality bar. `pyproject.toml` and `scripts/check.sh` enforce it. Only `build-setup` changes this file, with the user: tightening is routine, loosening needs an explicit yes.

## Floor
- **CR-01** No new suppressions: `# noqa`, `# type: ignore`, `pragma: no cover` (`check.sh floor` on the diff)
- **CR-02** No stubs: `raise NotImplementedError` outside abstract methods, `pass`-only bodies, bare `except: pass`. One carve-out: an interface task's signature stub `raise NotImplementedError("<task id>")` while the task it names is open; `check.sh gate` fails on a stub naming a done task, and the milestone exit (`check.sh full --exit`) on any stub
- **CR-03** No skipped, deleted or assertion-free tests
- **CR-05** Oracle files (`tests/fixtures/**/expected.json`) change only with the user's approval
- **CR-06** The implementer never changes `tests/intent/**`
- **CR-07** This file, `pyproject.toml`, `scripts/` and `.claude/agents/` are not weakened to make a change pass
- **CR-08** Nothing imports from `references/` or adds it to `sys.path`
- **CR-09** A boundary contract or type sample (`tests/contracts/<pkg>.<symbol>/`) is frozen once its folder exists at the task's base. A frozen one changes only through `architecture-design` Revise and a new interface task, never to make a test pass

## Readability
- **CR-10** One entry function per pipeline; it reads top to bottom as its named steps (reviewer + `dt layout`)
- **CR-11** No registries, plugin dispatch or config-driven wiring without an AD
- **CR-12** New abstraction only with a second real implementation or a named seam

## Enforced with numbers
| ID | Dimension | Rule | Checked by | Config key | Runs at |
|---|---|---|---|---|---|
| CR-20 | Tests | every test passes (intent tests of open tasks other than this one excepted) | pytest | `tool.pytest.ini_options` | gate |
| CR-22 | Size | ≤ 500 lines/module, ≤ 60/function | check.sh sizes | — | edit, gate |

## Boundaries (generated from architecture — do not edit)
- `mdata` imports nothing internal; `risk` imports only `mdata.types` and `mdata.load_prices`

## Roles and protected paths
| Role | May edit | May not edit | Stop gate |
|---|---|---|---|
| tester | `tests/intent/**` | everything else; reads no source | `check.sh collect` |
| implementer / solo | `packages/*/src/**`, `tests/unit/**`, `tests/system/**`; an interface task also its new `tests/contracts/<pkg>.<symbol>/` | the protected list | `check.sh gate` + protected-path diff against `refs/checks/base` |
| reviewer, check | nothing | everything | runs `check.sh full` / `gate` by hand |

**Protected list** (`PROTECTED` in `scripts/check.sh`; `path_guard.sh deny --protected` reads the same list): `tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`, `pyproject.toml`, `CONSTRAINTS.md`, `scripts/**`, `.claude/agents/**`, `.claude/settings.json`, `references/**`, `tests/contracts/**`. `tests/contracts/**` covers the folders that exist at the task's base (CR-09). `tasks/**` is the orchestrator's: builders never tick `todo.md` or write findings.

## Review
Run by the reviewer agent at every checkpoint and at milestone exit, over the diff since the checkpoint's base.
1. **Five axes:** correctness, readability, architecture, security, performance.
2. **Pipelines:** each entry function matches its step table; step owners are respected.
3. **Guard the bar:** diff this file, `pyproject.toml`, `scripts/` and `.claude/agents/` against the milestone's Base. Any loosening is a Critical finding.
4. **Tests:** no assertion-free tests, no weakened intent tests, golden cases still loaded from fixtures.
5. **Docs:** `dt lint` clean, contracts fresh, no pre-build sections left after the wiring.

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
