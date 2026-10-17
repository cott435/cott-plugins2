---
name: build-setup
description: Turns the approved plans into an enforced quality bar before agents write code - CONSTRAINTS.md, tool config in pyproject.toml, check and hook scripts, and the tester, implementer and reviewer agent files. Use when tasks/plan.md is approved and the first build hasn't started, at kickoff when new packages or dependencies need the bar extended, at Advance to ratchet measured values, when a rule or exception should change, or to audit the bar for drift.
---

# Build Setup

This skill says what "good enough" means and makes it mechanical: `CONSTRAINTS.md` (the readable bar, `CR-NN` rules) and what enforces it: tool config, `scripts/check.sh` (modes `fast | collect | gate | full`), the floor guard, hook scripts and the three build agents. It is the last approval before agents write code. The tooling is **project-owned**: CI and people run it without the plugin. Loosening is loud; tightening is routine.

**Not for:** changing a rule mid-task so a gate goes green (stop the task and come here with the user); product code or tests (never writes `src/**`, `tests/intent/**` or `tests/unit/**`).

## What it writes

Only `CONSTRAINTS.md`, tool config in `pyproject.toml` (multi-package: the root's, plus each `packages/<id>/pyproject.toml`'s deptry section), `scripts/**`, `.claude/agents/**` and CI; plus `tests/conftest.py` with the Hypothesis profiles **only if it doesn't exist**, listed at the gate. Templates are in `templates/`, mapped to project files in `references/derive.md`. They carry the parallel build's rules: interface stubs (CR-02), the `Writes:` guard, red for the right reason. Load a tool's reference (`references/tools/<tool>.md`) **only when configuring or changing that tool**.

## Modes

Run `python3 ../../scripts/dt.py status --skill build-setup` first (path relative to this skill's folder, run from the project root). It reports the mode, the gap keys (`config_mismatches`, `protected_gaps`, `agents_missing`, …), `expired_exceptions`, `dependents` and `base`.

- **blocked** (no Approved plan): say which upstream skill is next; stop.
- **New** (no `CONSTRAINTS.md`): the process below.
- **Extend** (kickoff, next plan approved), **Ratchet** (Advance), **Revise** (the user asks for a rule, threshold or exception change), **Audit** (on request or at milestone exit; changes nothing): read `references/modes.md`.
- **current**: report the bar is in step; offer Audit.

## Process (New)

```
PRECHECK → DETECT → 4 QUESTIONS → GENERATE → [commit yes] → PROVE → REVIEW GATE
   → (next turn) [approved] → [commit yes] → dt base
```

**1. Precheck.** `command -v uv jq`; if either is missing, stop and ask the user to install it (check.sh and the hooks need both). A `tasks/plan.md` without a dev-team header (agent-skills `/plan`) means stop and ask.

**2. Detect, don't ask.** Read, and report in two lines: shape, ids, dependency rules and stack ADs (`docs/architecture.md`); module layout (`pipelines.md`); tests and fixtures; the milestone's dependencies (`tasks/plan.md`); Python version; existing config, CI and `.claude/`.

**3. Four questions**, one at a time, with these defaults: **block or warn mid-task?** (block on the floor and gate; `full` findings become review findings; "warn" adds `--warn` to the Stop hooks); **type gate?** (mypy strict gates, pyright in `full`); **targets or measure-and-hold?** (measure and hold); **slowest gate tolerated?** (90 s; no limit for `full`). Mention CI once; write it only if asked.

**4. Generate.** Derive every value per `references/derive.md` and `examples.md`, and fill the templates; `grep -rn '{{[a-z_]*}}'` over the written files must print nothing. `chmod +x scripts/*.sh scripts/hooks/*.sh`; append the `.gitignore` lines. `uv lock && uv sync`, then write the vulture whitelist: the template header plus `uv run --frozen vulture --make-whitelist`. Never edit `check.sh` steps or hook commands by hand.

**5. Prove.** Ask to commit the bar skeleton (default yes): the protected-path diff needs a commit. On a yes, commit and `git update-ref refs/checks/base HEAD`. Run `uv run --frozen ruff check --show-settings >/dev/null` and `time bash scripts/check.sh gate`; fix the config, never the check, until it passes within budget. Headless: don't commit; run the gate, report the protected-path step as expected to fail, leave Draft.

## Review Gate

Rerun `dt status --skill build-setup`. Every gap key must be empty (`unknown` only where the input file doesn't exist yet) or explained under Open questions; after a Ratchet, `expired_exceptions` too. Then present:
1. **What was written**, file by file, and the proof run (pass/fail, gate time vs budget).
2. **ASSUMPTIONS:** every derived value (`references/derive.md`), the coverage floor, vulture whitelist size, and the four answers.
3. **Loosenings** (Extend, Ratchet, Revise), each as before → after, or say there are none.
4. **Open questions** and anything uncovered (CI not requested, a non-Python part with no check).

Ask for approval and **stop the turn**.

| The user says | Do |
|---|---|
| An unambiguous yes | Set `**Status:** Approved` and `**Last reviewed:**`. Offer to commit the bar; commit only on a yes. **New or Extend:** after that commit, run `python3 ../../scripts/dt.py base` (sets the plan's `**Base:**` to HEAD, so guard-the-bar diffs and Audit start from a commit that holds the bar) and say the next step is `/build`, run by the user. **Ratchet:** no `dt base`; next is `build-planning` Advance. **Stop.** |
| A hedge on a loosening or exception ("fine I guess") | Not approval. Ask again about that item |
| Changes | Edit, keep Draft, repeat the gate |

No live user: write everything, list the confirmations needed under Open questions, leave Draft. This skill never starts a build, writes code or runs a task.
