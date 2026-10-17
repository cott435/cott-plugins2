---
name: build-setup
description: Turns the approved plans into an enforced quality bar before agents write code - CONSTRAINTS.md, tool config in pyproject.toml, check and hook scripts, and the tester, implementer and reviewer agent files. Use when tasks/plan.md is approved and the first build hasn't started, at kickoff when new packages or dependencies need the bar extended, at Advance to ratchet measured values, when a rule or exception should change, or to audit the bar for drift.
---

# Build Setup

This skill says what "good enough" means and makes it mechanical: `CONSTRAINTS.md` (the readable bar, `CR-NN` rules, `EX-NN` exceptions) and what enforces it: tool config, `scripts/check.sh` (modes `fast | collect | gate | full`), the floor guard, hook scripts and the three build agents. It is the last approval before agents write code. The tooling is **project-owned**: CI and people run it without the plugin. Loosening is loud; tightening is routine.

**Not for:** changing a rule mid-task so a gate goes green (stop the task and come here with the user); product code or tests (never writes `src/**`, `tests/intent/**` or `tests/unit/**`). It never starts a build, writes code or runs a task: `/build` does, run by the user.

**Needs:** an Approved `tasks/plan.md` from `build-planning`.

## What it writes

Only `CONSTRAINTS.md`, tool config in `pyproject.toml` (multi-package: the root's, plus each `packages/<id>/pyproject.toml`'s deptry section), `scripts/**`, `.claude/agents/**` and CI; plus `tests/conftest.py` with the Hypothesis profiles **only if it doesn't exist**, listed at the gate. Templates are in `templates/`, mapped to project files in `references/derive.md`. They carry the parallel build's rules: interface stubs (CR-02), the `Writes:` guard, red for the right reason. Load a tool's reference (`references/tools/<tool>.md`) **only when configuring or changing that tool**.

## Modes

Run `python3 ../../scripts/dt.py status --skill build-setup` first (path relative to this skill's folder, run from the project root). It reports the mode, the gap keys (`config_mismatches`, `protected_gaps`, `agents_missing`, …), `expired_exceptions`, `dependents` and `base`. Revise and Audit run when the user asks for them.

| Mode | When | Do |
|---|---|---|
| blocked | no Approved plan | Say which upstream skill is next. Stop |
| New | no `CONSTRAINTS.md` | `references/new.md` |
| Extend | kickoff, next plan approved | `references/extend.md` |
| Ratchet | Advance, after the exit checkpoint | `references/ratchet.md` |
| Revise | the user asks for a rule, threshold or exception change | `references/revise.md` |
| Audit | on request or at milestone exit; changes nothing | `references/audit.md` |
| current | the bar is in step | Report that; offer Audit. Stop |

## Review Gate

New, Extend, Ratchet and Revise end here. Rerun `dt status --skill build-setup`. Every gap key must be empty (`unknown` only where the input file doesn't exist yet) or explained under Open questions; the mode file names any extra key. Then present:
1. **What was written**, file by file (outside New, the diff of the bar), and the proof run (pass/fail, gate time vs budget).
2. **ASSUMPTIONS:** every derived value (`references/derive.md`), the coverage floor, vulture whitelist size, duplicate-code count, and the four answers.
3. **Loosenings**, each as before → after, or say there are none. A loosening is a higher limit, a removed rule, a new exception or a weaker type mode, and needs the user's explicit yes; a tightening is routine.
4. **Open questions** and anything uncovered (CI not requested, a non-Python part with no check).

Ask for approval and **stop the turn**.

| The user says | Do |
|---|---|
| An unambiguous yes | Set `**Status:** Approved` and `**Last reviewed:**`. Offer to commit the bar; commit only on a yes. **New or Extend:** after that commit, run `python3 ../../scripts/dt.py base` (sets the plan's `**Base:**` to HEAD, so guard-the-bar diffs and Audit start from a commit that holds the bar) and say the next step is `/build`, run by the user. Other modes: the mode file's last step. **Stop.** |
| A hedge on a loosening or exception ("fine I guess") | Not approval. Ask again about that item |
| Changes | Edit, keep Draft, repeat the gate |

No live user: write everything, list the confirmations needed under Open questions, leave Draft.
