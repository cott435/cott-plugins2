---
name: build-setup
description: Turns the approved plans into an enforced quality bar before agents write code - CONSTRAINTS.md, tool config in pyproject.toml, check and hook scripts, and the tester, implementer and reviewer agent files. Use when tasks/plan.md is approved and the first build hasn't started, at kickoff when new packages or dependencies need the bar extended, at Advance to ratchet measured values, when a rule or exception should change, or to audit the bar for drift.
---

# Build Setup

## Overview

The plans say what to build; this skill says what "good enough" means and makes it mechanical. It writes `CONSTRAINTS.md` (the readable bar, with `CR-NN` rule IDs) and the files that enforce it: tool config in `pyproject.toml`, `scripts/check.sh` with fixed modes `fast | collect | gate | full`, the floor guard, the hook scripts, and the three build agents with their hooks. It is the last approval before agents write code.

The code tooling is **project-owned**: it is copied into the repo so CI and people can run it without the plugin, and because Claude Code ignores `hooks` in plugin-provided subagents. Loosening the bar is loud (shown explicitly, needs the user's yes). Tightening is routine.

Design: `design/build-setup.md`. Verified tool config: `design/tooling-verification.md`.

## When to Use

- `tasks/plan.md` is Approved and there is no `CONSTRAINTS.md` (New)
- Milestone kickoff after the next plan is approved: new packages, dependencies, stack or a Grow (Extend)
- Milestone Advance, after the exit checkpoint (Ratchet)
- The user wants a rule, threshold or exception changed (Revise)
- On request or at milestone exit: check the bar for loosening, drift and expired exceptions (Audit)

**Not for:**
- Changing a rule mid-task so a gate goes green. That is exactly what the bar exists to stop: stop the task and come here with the user.
- Writing or running product code or tests. This skill never writes `src/**`, `tests/intent/**` or `tests/unit/**`.
- A non-Python part's own tooling (a frontend). Use agent-skills `constraint-driven-development` for its rules; record them here with that part's path, and `check.sh` calls its check command.

## What It Writes

Only its write-matrix row: `CONSTRAINTS.md`, tool config in `pyproject.toml` (multi-package: the root's tool config, and each `packages/<id>/pyproject.toml`'s deptry section), `scripts/**`, `.claude/agents/**`, CI. One addition: `tests/conftest.py` with the Hypothesis profiles, **only if it doesn't exist**, listed at the gate. All templates are in `templates/` next to this file; every `{{placeholder}}` and how its value is derived is in `examples.md`.

| Project file | Template |
|---|---|
| `CONSTRAINTS.md` | `CONSTRAINTS.md` (≤ 2 pages) |
| `pyproject.toml` | single: `pyproject.toml` · multi: `pyproject.workspace.toml` at the root plus `package.pyproject.toml` per package |
| `scripts/check.sh`, `check_size.py`, `floor_guard.sh`, `floor_guard.py`, `vulture_whitelist.py` | `scripts/` |
| `scripts/hooks/{path_guard,post_edit,stop_gate,project_root}.sh` | `scripts/hooks/` |
| `.claude/agents/{tester,implementer,reviewer}.md` | `.claude/agents/` |
| `.github/workflows/check.yml` | only when the user asks for CI |
| `.gitignore` | append `gitignore.additions` (skip lines already present) |

Tool references (`references/tools/<tool>.md`: ruff_core, ruff_complexity, ruff_domain, mypy, pyright, pytest, deptry, import_linter, vulture, typos, pip_audit, pandera, hooks) are loaded **only when that tool is being configured or changed**.

## Modes

Run `python3 ../../scripts/dt.py status --skill build-setup` first (relative to this skill's folder; the project root is the current directory). It reports the mode and `constraints` (status), `config_mismatches`, `contract_mismatches` (import contracts vs the architecture), `optional_layers_existing`, `deptry_missing`, `protected_gaps` (`PROTECTED` vs CONSTRAINTS.md's list), `ignores_without_exception`, `agents_missing`, `hooks_missing`, `not_executable`, `expired_exceptions`, `tools_missing`, `dependents` (what `pkg_scope` must hold) and `base`.

| Mode | When | Does |
|---|---|---|
| **blocked** | No Approved plan | Say which upstream skill is next; stop |
| **New** | Plan approved, no `CONSTRAINTS.md` | The full process below |
| **Extend** | Kickoff, after the next plan is approved | Applies the milestone's deltas |
| **Ratchet** | `dt` reports `ratchet` (Advance; `**Ratcheted:**` is behind the finished milestone) | Records measured values, tightens what improved; hands back to `build-planning` Advance |
| **Revise** | The user asks for a rule, threshold or exception change | Edits CONSTRAINTS.md and config together |
| **Audit** | On request, or at milestone exit | Reports loosening, drift and expired exceptions; changes nothing |
| **current** | Nothing to do | Report the bar is in step; offer Audit |

## The Process (New Mode)

```
PRECHECK → DETECT → 4 QUESTIONS → GENERATE → [commit yes] → PROVE → REVIEW GATE
   → (next turn) [approved] → [commit yes] → dt base
```

The plan header's `**Base:**` stays `—` until the approved bar is committed; then `dt base` records it, so the guard-the-bar diff and Audit start from a commit that already holds the bar. Extend does the same at kickoff. `dt base` runs only after a New or Extend approval and commit; `dt status` then reports `current`. Ratchet, Revise and Audit never run it.

### Step 1: Precheck
- `command -v uv jq`. If either is missing, stop: "build-setup needs uv (check.sh runs every tool through `uv run --frozen`) and jq (the hooks read their input with it). Install them and run build-setup again."
- The plan is Approved and `CONSTRAINTS.md` doesn't exist. A `tasks/plan.md` from agent-skills `/plan` (no dev-team2 header) means stop and ask.

### Step 2: Detect, don't ask
Read, report in two lines, and infer: shape and package or component ids, `Depends on` / dependency rules and the tech stack ADs (`docs/architecture.md`); module layout and sizes (`docs/packages/*/pipelines.md`); test layout and fixtures (`tests.md`, `tests/fixtures/`); the milestone's dependencies (`tasks/plan.md`); Python version (`.python-version`, the language AD); existing `pyproject.toml`, linters, CI and `.claude/`. Use `dt section <ID>` for single sections.

### Step 3: Four questions, one at a time
Each has a guess and a default, so "I don't know" still produces a working bar (agent-skills `interview-me` style). Never more than four.
1. **Block or warn mid-task?** Default: block on the floor and the gate; `full` findings become review findings. ("Warn" adds `--warn` to the Stop hooks.)
2. **Type gate: mypy or pyright?** Default: mypy strict gates, pyright runs in `full`.
3. **Targets or measure-and-hold?** Default: measure and hold. Coverage `fail_under` = today's value (0 on an empty skeleton, recorded at the first Ratchet); vulture's whitelist holds today's findings.
4. **Slowest gate you'll tolerate?** Default: 90 s for `gate`; no limit for `full` and CI.

Don't ask about CI: write `.github/workflows/check.yml` only if the user asks (default). Mention once that it's available.

### Step 4: Generate
1. Derive every value per the placeholder table in `examples.md`. The ones that matter most:
   - **Protected list**: written once into `check.sh`'s `PROTECTED` (`path_guard.sh deny --protected` reads it from there) and copied into CONSTRAINTS.md: `tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `CONSTRAINTS.md`, `scripts/**`, `.claude/agents/**`, `.claude/settings.json`, `references/**`, `tests/contracts/**`. Multi-package adds `packages/*/pyproject.toml`.
   - **Frozen contracts** (CR-09): `check.sh` narrows `tests/contracts/**` to the contract folders that exist at `refs/checks/base`, so the Phase 0 contract task (`**Step:** contract`, run as the implementer) can write the new `tests/contracts/<pkg>.<symbol>/` it freezes, and from the next task's base nothing can change it. A frozen contract changes only through `architecture-design` Revise, then a new contract task re-freezes it in the main session (the implementer's guard blocks a folder frozen at the base); outside an open contract task naming the folder, the plugin's `dt guard` asks before any edit under `tests/contracts/`.
   - **Import contracts**: from the dependency rules (`references/tools/import_linter.md`). A module that doesn't exist yet is optional: `"(pkg.component)"`.
   - **`pkg_scope`** in `check.sh`: each package (single: component) and every package that depends on it, from the dependency graph.
   - **Domain rule families and stubs** from the tech stack ADs (`DTZ`, `NPY` + numpy, `PD` + `pandas-stubs`); pandera only when a DataFrame crosses a contract.
   - **Dependencies**: the milestone's, each with a `DEP002` exception expiring at milestone exit (below).
   - **References** (`design/references.md` §7): nothing to derive. The templates exclude `references/` from Ruff, mypy, pytest, coverage, deptry, vulture and typos; it is protected (so reference files are committed before a task starts); CR-08 forbids importing it or putting it on `sys.path`, and `floor_guard` checks the diff. Copying from a reference is the builder's call: there is no copy check, and copied code meets the normal bar.
2. Fill the templates; then `grep -rn '{{[a-z_]*}}'` over the written files must print nothing. `chmod +x scripts/*.sh scripts/hooks/*.sh`. Append the `.gitignore` lines.
3. `uv lock && uv sync`, then write the vulture whitelist: the template header plus `uv run --frozen vulture --make-whitelist`.
4. Keep the numbers in `CONSTRAINTS.md` and their config keys identical.

### Step 5: Prove the config
1. Ask: "Commit the bar skeleton so the gate can run against it? (default: yes)". The protected-path diff needs a commit. Commit only on a yes; then `git update-ref refs/checks/base HEAD`.
2. Run `uv run --frozen ruff check --show-settings >/dev/null` (Ruff accepts every option) and `time bash scripts/check.sh gate`. Fix the config, never the check, until it passes; note the time against the budget from question 4.
3. No live user (headless): don't commit. Run the gate anyway and report the protected-path step as expected to fail; leave Status at Draft.

Then the Review Gate.

## Extend Mode
At kickoff, after the next plan is approved. Run `dt status`, then apply only the deltas:
- **Dependencies (default, design open item 1 option a):** add the milestone's dependencies, each with a `[tool.deptry.per_rule_ignores] DEP002` entry and an Exceptions row expiring `M<n> exit`. A dependency nobody planned blocks its task and comes back through Revise. (Option b, letting the implementer edit `[project.dependencies]`, is not used.)
- **New packages or components:** contracts, `pkg_scope`, deptry config, `known-first-party`, test dirs in the protected list.
- **Frozen contracts**, on a bar written before them (`protected_gaps` names `tests/contracts/**` once the project is multi-package or has `tests/contracts/`): copy the template's `frozen_contracts` and `protected_globs` functions into `check.sh` and its `protected` and `gate` lines, `tests/contracts/**` in both protected lists, CR-09 and the role-table row. A tightening.
- **New stack:** stubs and rule families.
- **Grow:** rewrite component contracts as package contracts; the rules don't change.
- Remove parentheses from optional layers whose module now exists.
- **References**, on a bar written before them: the `references/` excludes, `references/**` in both protected lists, CR-08 and Review item 7. A tightening; the floor guard doesn't count the `references` excludes as loosening.

Then the Review Gate, showing the diff of the bar.

## Ratchet Mode
At Advance, after the exit checkpoint. Run `check.sh full`; record measured values in "Measured, not yet enforced". A metric that improved tightens (`fail_under` up, a shorter vulture whitelist). Drop expired `DEP002` entries the code now imports. Offer once to promote a measured metric to enforced. Set `**Ratcheted:** M<n>` in the header. Review Gate. After approval and the commit offer, hand back to `build-planning` Advance, whose next step is `dt archive`. Never run `dt base` and never say `/build` is next: the next milestone isn't planned yet.

## Revise Mode
The user asks for a change. Edit `CONSTRAINTS.md` and its config key together. A loosening (a higher limit, a removed rule, a new exception, a weaker type mode) is shown as a before → after line and needs the user's explicit yes. Every exception gets an `EX-NN` row with a rule, path, reason, owner and expiry (a date, or `M<n> exit`); a Ruff exception is also a `per-file-ignores` entry. Review Gate.

## Audit Mode
Changes nothing. Run `bash scripts/floor_guard.sh --base <plan Base>` (it reports a loosened `pyproject.toml`, new config files, removed rules and new exceptions) and `dt status`. Report each loosening since the milestone's Base and whether a build-setup commit recorded the user's yes, plus expired exceptions and config mismatches. Offer Revise for anything to fix.

## Review Gate

Run `dt status --skill build-setup` again. `config_mismatches`, `contract_mismatches`, `optional_layers_existing`, `deptry_missing`, `protected_gaps`, `ignores_without_exception`, `agents_missing`, `hooks_missing`, `not_executable` and `tools_missing` must be empty (`unknown` only where the input file doesn't exist yet), or each is explained under Open questions; after a Ratchet, `expired_exceptions` too. `pkg_scope` in `check.sh` must match `dependents`.

Then present:
1. **What was written**, file by file, and the proof run (pass/fail, gate time vs budget).
2. **ASSUMPTIONS:** every derived value: shape and ids, protected list, contracts and optional layers, `pkg_scope`, rule families, stubs, dependencies and their exceptions, coverage floor, vulture whitelist size, and the four answers (or defaults).
3. **Loosenings** (Extend, Ratchet, Revise), each as before → after. Empty is fine; say so.
4. **Open questions** and anything left uncovered (a non-Python part with no check command, CI not requested).

Then ask for approval and **stop the turn**.

| The user says | Do |
|---|---|
| An unambiguous yes ("approved", "yes, ship it") | Set `**Status:** Approved` and `**Last reviewed:**`. Offer to commit the bar; commit only on a yes. **New or Extend:** after that commit, record the base with `python3 ../../scripts/dt.py base` (sets the plan header's `**Base:**` to HEAD, so guard-the-bar diffs start from a commit that holds the bar; `dt status` then reports `current`), and tell the user the next step is `/build`. **Ratchet:** no `dt base`; the next step is `build-planning` Advance (`dt archive`). **Stop.** |
| A hedge on a loosening or exception ("fine I guess") | Not approval. Ask again about that item |
| Changes | Edit, keep Draft, repeat the gate |

No live user: write everything, list the confirmations needed under open questions, leave Draft. After approval this skill is done: it never starts a build, writes code or runs a task.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll add constraints once the code settles" | Code settles around whatever was allowed while it was moving |
| "The tests are the constraints" | Tests the agent wrote prove it agrees with itself. pip-audit and import contracts are opinions it can't argue with |
| "We can't hit 80% coverage" | Then don't set 80. Measure today's value and hold it |
| "This will slow the agent down" | Only if slow checks sit in the edit loop. `fast` is instant; everything else runs once, at Stop |
| "Raising the limit just this once unblocks the task" | That's a loosening: explicit, with the user's yes, as an expiring exception. Otherwise fix the code |
| "The gate fails on the fresh skeleton, so drop that check" | Fix the config: optional layers, `DEP002` exceptions, a commit before the proof run |
| "I'll hand-write the contracts and the protected list" | They are generated from the architecture and role table, so `dt` can check them |
| "Approved, go ahead — I'll start the build" | Approval ends this skill. `/build` is the next step, run by the user |

## Red Flags

- More than four questions, or a config the user can't explain
- A number in CONSTRAINTS.md that differs from its config key, or a rule with no tool behind it
- A threshold the codebase fails today, with no plan to reach it
- An exception with no owner or expiry, or a `per-file-ignores` / `per_rule_ignores` entry with no Exceptions row
- `check.sh` steps or hook commands edited by hand, a relative hook command, or a check removed to get green
- Protected list missing a test directory, or `check.sh` and the agent files disagreeing about it
- A frozen contract under `tests/contracts/` edited to make a test pass, or `tests/contracts/**` left off the protected list of a multi-package bar
- A loosening approved by a hedge, or committed without the user's yes
- Anything written under `src/**`, `tests/intent/**` or `tests/unit/**`
- Every constraint judged by the project's own tests (no external check)

## Verification

- [ ] `dt status --skill build-setup` shows empty (or explained) `config_mismatches`, `contract_mismatches`, `optional_layers_existing`, `deptry_missing`, `protected_gaps`, `ignores_without_exception`, `agents_missing`, `hooks_missing`, `not_executable` and `tools_missing`; `pkg_scope` matches `dependents`
- [ ] No `{{placeholder}}` left in any written file
- [ ] Every CR rule with a number names its config key, and the two agree
- [ ] `PROTECTED` and CONSTRAINTS.md's protected list are the same eleven globs (Step 4), plus `packages/*/pyproject.toml` in multi-package
- [ ] Contracts match the architecture's dependency rules; missing modules are optional layers
- [ ] Every exception has an owner and an expiry; every config ignore has a row
- [ ] `check.sh gate` passed once on the committed skeleton, inside the time budget
- [ ] At least one external check (pip-audit) is in `full`
- [ ] The turn stopped at the gate; after a New or Extend approval and the commit, `dt base` recorded the Base (never after Ratchet); nothing was built
