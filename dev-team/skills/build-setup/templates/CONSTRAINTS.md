# Constraints
**Status:** Draft · **Last reviewed:** {{date}} by {{owner}} · **Ratcheted:** —

The standing quality bar. `pyproject.toml` and `scripts/check.sh` enforce it; every number here names its config key, and `dt status` fails if the two disagree. Only `build-setup` changes this file, with the user: tightening is routine, loosening needs an explicit yes.

## Floor
- **CR-01** No new suppressions. Ruff runs with `--ignore-noqa` in gate and full, so a Ruff exception is a `per-file-ignores` entry in protected config with a row in Exceptions. `floor_guard.sh` catches the other suppressions on the diff
- **CR-02** No stubs: `raise NotImplementedError` outside abstract methods, `pass`-only bodies, bare `except: pass`. One carve-out: the interface task's step signatures, whose body is only `raise NotImplementedError("<task id>")` naming the open task that replaces it. `check.sh gate` fails on one naming a task that isn't open in `tasks/todo.md`, and on a test that expects one (`stub-pinned`); `check.sh full --exit` fails on any
- **CR-03** No skipped, deleted or assertion-free tests, unless a row in Exceptions names the test file
- **CR-04** No secrets in source
- **CR-05** Oracle files (`tests/fixtures/**/expected.json`) change only with the user's approval
- **CR-06** The implementer never changes `tests/intent/**`
- **CR-07** This file, `pyproject.toml` tool config, `scripts/` and `.claude/agents/` are not weakened to make a change pass
- **CR-08** Nothing imports from `references/` or `probes/`, or adds either to `sys.path` (or `PYTHONPATH`, pytest `pythonpath`). `floor_guard.sh` checks the diff for both. Code copied from either is project code and meets the same bar
- **CR-09** A frozen interface (`tests/contracts/<id>.<symbol>/`: schema, samples, fake; and the types, signatures and exports the interface task wrote) is frozen once it exists at the task's base. Only the interface task freezing it (`**Kind:** interface`) writes a new folder, and no other task's `Writes:` names its `types.py` or `__init__.py`; a frozen interface changes only through `architecture-design` Revise, never to make a test pass

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
| CR-41 | vulture findings at `min_confidence = 60` (`scripts/vulture_whitelist.py`) | {{vulture_today}} | must not grow by `full --exit` (earlier `full` runs report) |
| CR-42 | Duplicate blocks of ≥ 8 similar source lines (pylint `duplicate-code`, `[tool.pylint.similarities]` in pyproject.toml) | {{duplicates_today}} | must not grow |

## Boundaries (generated from architecture — do not edit)
{{boundary_rules}}

## Roles and protected paths
| Role | May edit | May not edit | Stop gate |
|---|---|---|---|
| tester | `tests/intent/**`, within the task's `Writes:` | everything else; reads no source | `check.sh collect` (lint, collect, red for the right reason) |
| implementer / solo | `src/**`, `tests/unit/**`, within the task's `Writes:`; an interface task also `tests/support/**` and the `tests/contracts/<id>.<symbol>/` its `Writes:` names | the protected list; `tasks/` | `check.sh gate` + protected-path diff against the worktree's base |
| reviewer | its worktree, for the mutation check, and its findings file; nothing lands (the orchestrator records findings with `dt finding`) | everything else | runs `check.sh full` by hand |

**Protected list** (`PROTECTED` in `scripts/check.sh`; `path_guard.sh deny --protected` reads the same list): {{protected_globs_md}}. `tests/contracts/**` covers the contract folders that exist at the task's base (CR-09). **`Writes:`**: `dt claim` writes the role's share of the task's `Writes:` to `.claude/.task_writes` and sets the worktree's base; `path_guard.sh writes` blocks edits outside it, and builder edits before the claim. Only the orchestrator writes `tasks/` (`dt land`, `dt finding`).

**Worktree links:** {{worktree_links}}

## Review
Run by the reviewer agent, per package, at each checkpoint and the milestone exit. `dt land` already checked each landing's `Writes:`, protected paths and gates; review judges what tools can't.

**Interface** (after Phase 0): the code is the contract, no more and no less.
1. Types match `contract.md`: fields, types, invariants. Nothing a step's In → Out needs is missing; no helper is frozen.
2. Signatures match the step tables, in their owner modules. Each stub names the open task that owns its step; no logic beyond types and validation.
3. One sample per case the contract names, valid and realistic, never holding a TC's expected value. Replay doubles replay an interaction the Protocol allows. Each fake passes its contract's cases; anything it does beyond echoing a fixture (filtering, ordering, an error) is a case the real provider must pass too. Contract tests check shape only, never a stub or other state a later task changes.
4. `__init__.py` exports exactly the contract; each `Mitigated by` in the plan's dependency graph exists; each frozen concrete class instantiates.
5. **What later tasks need** (`dt build needs <checkpoint>`): every type, method, attribute and state each task's acceptance and golden cases make its tests use is public in the frozen surface.

**Each phase**, per package, tests before code:
1. **Interfaces followed** (CR-09): no frozen type, signature or contract folder changed outside a Revise. Consumers use the declared types: no dict for a dataclass, no reaching into a provider's internals, no local redefinition. A stub is replaced only by the task it names; no cross-package import outside the contract; spine tests run on samples and doubles, not another step's code.
2. **Tests prove something:** each intent test asserts its TC case or acceptance bullet, loading expected values and tolerances from fixtures; none is assertion-free or weakened; Hypothesis runs the `ci` profile. Unit tests are specific, never computing the expected value with the code under test or testing only a mock. **Mutation check** per acceptance bullet (`.claude/agents/reviewer.md`).
3. **Correct to the spec:** each acceptance bullet truly met, not special-cased to the sample; the error paths the requirement names; seeding and determinism; numerical edge cases.
4. **Simple** (CR-11, CR-12, CR-42): no abstraction with one implementation outside the contract or an AD; no forwarding wrapper, one-method class, or class where a function does; no parameter, flag or config key every caller sets the same; no `try/except` that only re-raises or swallows, no checks the types already guarantee; no loop the library already provides. No near-copies within or across the phase's tasks: one concept is one function in its owner module (tests may repeat for readability). Each finding names the simpler form, with the same tests passing.
5. **Pipelines** (CR-10): entry functions read as their step tables (`dt layout`); step owners respected; spine baselines still selectable.
6. **The bar** (CR-07): diff this file, `pyproject.toml`, `scripts/` and `.claude/agents/` against the milestone's Base. Any loosening is Critical; new exceptions need an owner and expiry.
7. **Hidden and parallel risks:** where a real provider could act differently from its double; fixed output paths, global state, test-order dependence.
8. **The rest:** readability, security, performance where a QR sets a number; reused reference or probe code has its Caveats handled and fits the contract; `dt lint` clean, pre-build sections replaced by `dt layout` pointers.

**Milestone exit**, over the whole diff, adds: the Scope's Exit holds; every Covers ID has a test; `check.sh full --exit` finds no stub; system tests use real providers; the same sample through a real provider and its double agrees; deferred requirements untouched; pip-audit ran.

**Severity:** Critical: a frozen interface changed, a seam a later task needs missing from the interface, a contract test pinning a transient state, a weakened test, an intent test that misses a mutation changing its TC's expected output, a wrong answer, a loosened bar, a security hole, lost data; it stops the build. Important: a consumer bypassing a type, any other surviving mutation, an unneeded abstraction, a duplicate across tasks. Suggestion and Nit: local. Each finding gets a fix task or a reason.

## Done
agent-skills `references/definition-of-done.md`, tailored once:
- **Correctness and Quality:** checked per task by the gate.
- **Integration and Documentation:** checked at each checkpoint.
- **The full list:** checked at milestone exit.

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
{{exception_rows}}
