# Build Setup — Design (constraints and code review)

**Status:** Ready to build (after planning skills) · **Last updated:** 2026-10-16 · **Verified by:** [tooling-verification.md](tooling-verification.md) · **Companion to:** [planning-stage.md](planning-stage.md)

Covers the step between planning and building: turning the approved docs into an enforced quality bar (CONSTRAINTS.md, tool config, check scripts, agent roles, hooks) and defining code review. Building itself, meaning how tasks are executed, is a later design.

Inputs: `python_tooling` (README, `check.sh`, `check_size.py`, `hooks/*.sh`, `hooks.md`), verified and fixed in [tooling-verification.md](tooling-verification.md), agent-skills `constraint-driven-development` and `code-review-and-quality`, and [planning-stage.md](planning-stage.md).

---

## 1. Decisions at a glance

1. **New skill `build-setup`, run after `build-planning` and before the first `/build`.** It's the last approval before agents write code. It runs again at every milestone kickoff to apply deltas.
2. **Two tooling layers with different owners:**
   - **Doc tooling** (`dt`): plugin-owned. Planning records, ID checks, context packets.
   - **Code tooling** (`check.sh`, Ruff, mypy…): project-owned and copied into the repo. CI and humans need it without the plugin, and Claude Code ignores `hooks` in plugin-provided subagents, so agent files must live in the project's `.claude/agents/`.
3. **CONSTRAINTS.md is the readable bar; `pyproject.toml` and `check.sh` enforce it.** Every numeric rule names its config key, and `dt status` fails if the two disagree.
4. **The review plan is a section of CONSTRAINTS.md**, not a separate file. Review findings are recorded in the plan under the checkpoint that produced them.
5. **Boundaries are generated, not hand-written.** import-linter contracts come from the architecture's dependency rules (components in a single package, packages in multi). Grow then changes the granularity of the contracts, not the rules.
6. **Hybrid build, three roles**, from the tooling: tester (intent tests), implementer (code + unit tests), reviewer (read-only). Behaviour tasks run tester then implementer (`Mode: split`). Spine, refactor and glue tasks run one agent with the implementer's guards and gate (`Mode: solo`). Every checkpoint gets a separate reviewer. Protected paths keep any of them from moving the goalposts.
7. **Loosening is loud, tightening is routine.** Only `build-setup` (with the user) edits the bar. Builders can't touch it, and a diff check at Stop catches edits made through Bash.

---

## 2. Where it sits

```
architecture-design → pipeline-design → test-planning (opt) → build-planning → build-setup → /build
                                                                                   ↑
                    Advance: Ratchet [gate] → archive → kickoff → next plan [gate] → build-setup Extend [gate]
```

**Why after `build-planning`:**
- Every input is known by then: language and stack (architecture ADs), packages and dependency direction (architecture), file paths and module sizes (pipelines), test layout and fixture types (test plan), dependencies each milestone brings (plan).
- The plan doesn't depend on the bar. Its `Verify:` lines and checkpoints use the fixed mode names `check.sh fast|gate|full`, which `build-setup` guarantees exist.
- It gives one "ready to build" approval with the whole picture in view.

**What earlier steps use before the bar exists:** `pipeline-design` plans layouts against the same default limits the bar will enforce (500 code lines per module, 60 per function), read from the skill's defaults file, so it never plans a layout the bar would reject. The readability rules are written by `pipeline-design` and recorded in CONSTRAINTS.md by `build-setup`.

---

## 3. What it writes into the project

```
CONSTRAINTS.md                       readable bar (§4), ≤ 2 pages
pyproject.toml                       [tool.*] sections; multi-package: root workspace + per-package deps
scripts/check.sh                     modes fast | collect | gate | full; --pkg <id> scopes to package + dependents
scripts/check_size.py                module/function length limits
scripts/floor_guard.sh               diff-scoped floor checks (adapted from agent-skills floor-guard)
scripts/hooks/path_guard.sh          PreToolUse allow/deny globs
scripts/hooks/post_edit.sh           PostToolUse → check.sh fast <file>
scripts/hooks/stop_gate.sh           Stop/SubagentStop → check.sh <mode>, 3-try loop guard; blocks with JSON decision
scripts/hooks/project_root.sh        resolves the project root from the hook input's cwd (worktree-safe)
.claude/agents/tester.md             role + hooks in frontmatter
.claude/agents/implementer.md
.claude/agents/reviewer.md           tools: Read, Grep, Glob, Bash (no Edit/Write)
.github/workflows/check.yml          optional: check.sh full
.gitignore                           + .claude/.stop_attempts_*, .hypothesis/, .import_linter_cache/, .coverage
```

- **Templates:** the fixed, verified scripts and `pyproject.toml` in `evals/tooling-check/` become `skills/build-setup/templates/`, not the original bundle. The tool reference files (`ruff_core.md`, `mypy.md`…) become `skills/build-setup/references/tools/`, loaded only when a tool is being configured.
- **Prerequisites:** New mode checks `command -v uv jq` first and stops with a clear message if either is missing. The hooks need jq and `check.sh` needs uv.
- **`check.sh` runs every tool through `uv run --frozen`**, because hooks don't activate the venv; bare `ruff` picked up a different install in verification.
- **`pyproject.toml` template rules:**
  - always a `[build-system]` (src layout)
  - `output-prefer-rule-codes = true` whenever Ruff preview is on, so output uses codes like `C901` that CONSTRAINTS.md and `noqa` cite
  - no `PD901`, which Ruff has removed
  - type stubs per stack in New mode too (`pandas-stubs` for pandas)
- **Generated import contracts** mark not-yet-existing modules as optional layers, `"(pkg.component)"`, so the gate passes on a fresh skeleton. `dt status` flags the parentheses once the module exists.

**Generated, not hand-edited:**
| Output | Source |
|---|---|
| import-linter contracts | Architecture dependency rules (component `Depends on`, or the package dependency rules) |
| `known-first-party`, `root_package` | Package ids |
| Protected-path globs | Role table (§6) plus the test layout |
| deptry config per package | Package manifests |
| Domain rule families (`DTZ`, `NPY`, `PD`), pandera | Tech stack ADs; pandera only when a DataFrame crosses a contract |
| `--pkg` dependents | Architecture dependency graph, via `dt` |

---

## 4. CONSTRAINTS.md

agent-skills format, so its `/review`, `/build` and `/ship` read it unchanged, plus four sections: Readability, Roles, Review and Boundaries. Rules carry IDs (`CR-NN`) so exceptions and review findings can cite them, and a rule that enforces a spec quality requirement cites it (`QR-02`).

````markdown
# Constraints
**Last reviewed:** 2026-10-15 by @connor · **Status:** Approved

## Floor
- **CR-01** No new suppressions. Ruff runs with `--ignore-noqa` in gate and full, so a Ruff exception must be a `per-file-ignores` entry, which sits in protected config and maps one-to-one to the Exceptions table. `# type: ignore`, `pyright: ignore` and `pragma: no cover` are caught by `floor_guard.sh` on the diff
- **CR-02** No stubs: `raise NotImplementedError` outside abstract methods, `pass`-only bodies, bare `except: pass`
- **CR-03** No skipped, deleted or assertion-free tests without a reason in the commit message
- **CR-04** No secrets in source
- **CR-05** Oracle files (`tests/fixtures/**/expected.json`) change only with user approval
- **CR-06** The implementer never changes `tests/intent/**`
- **CR-07** This file, `pyproject.toml` tool config, `scripts/` and `.claude/agents/` are not weakened to make a change pass

## Readability
- **CR-10** One entry function per pipeline; it reads top to bottom as its named steps (reviewer + `dt layout`)
- **CR-11** No registries, plugin dispatch or config-driven wiring without an AD
- **CR-12** New abstraction only with a second real implementation or a named seam

## Enforced with numbers
| ID | Dimension | Rule | Checked by | Config key | Runs at |
|---|---|---|---|---|---|
| CR-20 | Lint | zero errors | ruff | `tool.ruff.lint.select` | edit, gate |
| CR-21 | Complexity | ≤ 10 per function | ruff C901 | `tool.ruff.lint.mccabe.max-complexity` | gate |
| CR-22 | Size | ≤ 500 lines/module, ≤ 60/function | check_size.py | `tool.size_limits` | edit, gate |
| CR-23 | Types | zero errors, strict | mypy | `tool.mypy.strict` | gate |
| CR-24 | Boundaries | import contracts hold | import-linter | `tool.importlinter.contracts` | gate |
| CR-25 | Dependencies | none missing/unused | deptry | `tool.deptry` | gate |
| CR-26 | Deps security | nothing known-vulnerable | pip-audit | — | full (scheduled) |
| CR-27 | Reproducibility | same seed → same result (QR-02) | pytest tests marked `repro` (marker declared in `markers`) | `tool.pytest.ini_options.markers` | gate |

## Measured, not yet enforced
| ID | Metric | Today | Direction |
|---|---|---|---|
| CR-40 | Coverage (branch) | 71.2% (`tool.coverage.report.fail_under`, raised by Ratchet) | must not fall |
| CR-41 | vulture findings at `min_confidence = 60`, with a whitelist file | 3 | must not grow |

## Boundaries (generated from architecture — do not edit)
- `quant.data` imports nothing first-party · `quant.stats` → data · `quant.portfolio` → stats, data

## Roles and protected paths
| Role | May edit | May not edit | Stop gate |
|---|---|---|---|
| tester | `tests/intent/**` | everything else | `check.sh collect` |
| implementer / solo | `src/**`, `tests/unit/**` | the protected list | `check.sh gate` + protected-path diff against `refs/checks/base` |
| reviewer | nothing (the orchestrator records findings with `dt finding`) | everything | runs `check.sh full` by hand |

**Protected list** (one generated list feeds both the `path_guard.sh deny` globs and `check.sh`'s `PROTECTED`): `tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`, `pyproject.toml`, `CONSTRAINTS.md`, `scripts/**`, `.claude/agents/**`.

## Review
(checkpoint checklist, §7)

## Done
agent-skills `references/definition-of-done.md`, tailored once:
- **Correctness and Quality:** checked per task by the gate.
- **Integration and Documentation:** checked at each checkpoint.
- **The full list:** checked at milestone exit.

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
````

---

## 5. Single vs multi-package

| | Single package | Multi-package |
|---|---|---|
| `pyproject.toml` | One, with all tool config | uv workspace: root holds shared tool config (ruff, mypy, typos, size); each package holds its own dependencies |
| import-linter | Contracts between component subfolders (`quant.data`, `quant.stats`) | Contracts between packages; optional internal contracts per package |
| deptry | Whole project | Per package, so each declares only what it imports |
| `check.sh gate` | Whole repo | `--pkg <id>`: the package plus its dependents' tests (from the dependency graph) |
| Grow | — | `build-setup` Extend turns component contracts into package contracts. The rules don't change, so code already passing keeps passing |

Enforcing component boundaries inside a single package is what makes Grow cheap: by the time a component becomes a package, its imports are already clean.

---

## 6. Hooks: who owns which

| Source | Fires | Hooks |
|---|---|---|
| Plugin `hooks/hooks.json` (dev-team2) | Every session, **including tool calls inside subagents** (confirmed in the docs). So the oracle guard and `dt lint` also cover the tester and implementer | SessionStart `dt status --summary` (doesn't reach subagents; use `SubagentStart` if they need it); PreToolUse oracle guard (`expected.json` → ask); PostToolUse `dt lint` on `docs/**`, `tasks/**` |
| Project `.claude/agents/*.md` frontmatter | Only while that agent runs, and only in a trusted workspace (`claude -p` doesn't count) | tester: allow `tests/intent/*`, post_edit, Stop → collect. implementer: deny the protected list, post_edit, Stop → gate. Stop becomes SubagentStop automatically. Commands are `bash "$CLAUDE_PROJECT_DIR"/scripts/hooks/<x>.sh`, never relative: a missing script is a non-blocking error, so a broken relative path would silently switch the guard off |
| Project `.claude/settings.json` | Main session | Optional Stop → `check.sh gate` as a last safety net |

**Cost rule (from the tooling):** instant tools (ruff, typos, size) run on every edit; everything else runs once, when an agent tries to finish. `full` runs at checkpoints, milestone exit and in CI.

**Two layers for every protection:**
- A PreToolUse guard stops the normal route.
- At Stop, a check catches writes made through Bash. It diffs the whole protected list against a recorded base ref (`refs/checks/base`) and also lists untracked files.
- The orchestrator sets that ref when it commits the tester's work, and at each task start.
- The scripts take the project root from the hook input's `cwd`, because `CLAUDE_PROJECT_DIR` stays on the main checkout in worktrees.

**Stop-hook behaviour (verified):**
- A Stop hook blocks with JSON `decision: "block"`.
- After 3 failed tries, `stop_gate.sh` lets the agent stop and leaves a `systemMessage`, which the main view doesn't show for a subagent (live check, 2.1.292). So the third block tells the agent to start its report with `GATE FAILED: scripts/check.sh <mode>`, and the orchestrator still re-runs `check.sh gate` after every subagent returns (or adds a PostToolUse hook on the `Agent` tool).

---

## 7. Code review

| Level | When | Who | What runs | Blocks? |
|---|---|---|---|---|
| Edit | Every Edit/Write | hook | `check.sh fast` on the file | Feeds back (PostToolUse) |
| Task | Implementer tries to finish | hook | `check.sh gate --pkg`, `floor_guard.sh` on the diff, protected-path diff | Yes (SubagentStop, 3 tries, then a `systemMessage` to you; the orchestrator re-runs the gate) |
| Checkpoint | Every 2–3 tasks | reviewer agent (read-only) | `check.sh full` + the Review checklist below | Findings become tasks |
| Milestone exit | All tasks done | reviewer agent, then you | Checkpoint review over the milestone diff + ratchet update + doc Sync | You approve |

**Review checklist** (the Review section of CONSTRAINTS.md):
1. **Five axes** (agent-skills `code-review-and-quality`): correctness, readability, architecture, security, performance.
2. **Pipelines:** each entry function matches its step table (`dt layout`); step owners are respected; spine baselines are still selectable.
3. **Guard the bar:** diff CONSTRAINTS.md, `pyproject.toml`, `scripts/`, `.claude/agents/` against the milestone's starting commit; any loosening is a Critical finding. New exceptions need an owner and expiry.
4. **Tests:** no assertion-free tests, no weakened intent tests, golden cases still loaded from fixtures, Hypothesis on the `ci` profile.
5. **Docs:** `dt lint` clean, contracts fresh, no pre-build sections left after the spine.
6. **At least one external check** ran (pip-audit), so the bar isn't made entirely of the agent's own tests.

**Recording findings** (deterministic, no separate file): the reviewer reports, and the orchestrator writes each finding under the checkpoint block in `tasks/plan.md` with `dt finding`.
```markdown
### Checkpoint after M2-T04 — reviewed 2026-11-03
- [x] … checklist …
**Findings:**
- M2-R01 Critical · CR-21 · `stats/rmt.py::clean_eigen` complexity 14 → fix task M2-T09
- M2-R02 Nit · readability · report column names → won't fix: matches paper notation
```
Every finding needs a disposition: a fix task or a reason. `dt lint` flags any finding without one. Critical findings block the next checkpoint.

---

## 8. Modes

| Mode | When | Does |
|---|---|---|
| New | First bar, before M1's first `/build` | Check `uv` and `jq`. Detect the stack, then ask four questions with defaults (below). Generate the files in §3 and commit the skeleton (with your yes). Then run `ruff check --show-settings` and `check.sh gate` once to prove the config, and stop at the review gate |
| Extend | Milestone kickoff, after the next plan is approved | Applies deltas: new packages → contracts and deptry; new dependency stack → type stubs and rule families; Grow → package-level contracts; the milestone's dependencies (see §11, open item 1) |
| Ratchet | Milestone Advance | Records new measured values; a metric that improved tightens; you can promote a measured metric to enforced |
| Revise | You want a rule or threshold changed, or an exception added | Edits CONSTRAINTS.md and config together; a loosening is shown explicitly and needs your yes |
| Audit | On demand, or at milestone exit | Guard-the-bar diff, expired exceptions, config vs CONSTRAINTS.md mismatches |

**New-mode questions** (agent-skills style: at most four, each with a default, so "I don't know" still produces a working bar):
1. Block or warn mid-task? Default: block on the floor and gate; warn on `full`.
2. Type gate: mypy or pyright? Default: mypy strict as the gate, pyright in `full`.
3. Targets or measure-and-hold? Default: measure and hold (ratchets).
4. Slowest gate you'll tolerate? Default: 90 s for `gate`; unlimited for `full`/CI.

---

## 9. Deterministic checks

`dt status --skill build-setup` reports:
- CONSTRAINTS.md missing or Draft (blocks `/build`).
- Numbers in CONSTRAINTS.md that differ from their config keys.
- import-linter contracts that differ from the architecture's dependency rules.
- Expired exceptions.
- Missing agent files or hook scripts, or scripts that aren't executable.
- Packages with no deptry config.
- Protected-path globs that don't cover the test layout, or that differ between `path_guard` and `check.sh`.
- Ruff `per-file-ignores` entries with no matching row in Exceptions.
- Optional `"(pkg.component)"` import layers whose module now exists.
- `uv` or `jq` missing.

---

## 10. Changes this implies for planning-stage.md (applied 2026-10-16)

- **Test layout:** `tests/intent/<pkg>/` (tester; written from TC cases and acceptance criteria), `tests/unit/<pkg>/` (implementer), `tests/fixtures/<pkg>/TC-NN/` (test-planning).
- **Flow:** `build-planning → build-setup → /build`. Kickoff check gains "build-setup Extend"; Advance gains "build-setup Ratchet".
- **Checkpoint block:** run by the reviewer agent against CONSTRAINTS.md's Review section; findings recorded as above.
- **"Nothing copied into the project"** applies to doc tooling only. Code tooling is project-owned.

## 11. Decisions and open questions

**Decided (2026-10-16)**
- Skill name: `build-setup`.
- Python is the primary stack and gets the full tooling. A non-Python part (e.g. a frontend) falls back to agent-skills `constraint-driven-development` for its rules and tools, recorded in the same CONSTRAINTS.md with that part's path in each rule. `check.sh` calls the frontend's own check commands for those paths.
- Build model is hybrid: `split` for behaviour tasks, `solo` for spine/refactor/glue, a separate reviewer at every checkpoint. How the orchestrator runs each mode, and whether it wraps or replaces agent-skills `/build`, is for the build-phase design.
- The tooling was installed and run (`tooling-verification.md`). Tool choice and rule config hold up; the 8 config/script fixes and the hook fail-open fixes are folded in above. Timing: `gate` takes 2–3 s warm and about 14 s on a fresh venv for a 7-file package, well inside the 90 s default.

**Open**
1. **How dependencies arrive.** The implementer can't edit `pyproject.toml`, and deptry fails on a declared but unimported dependency (`DEP002`). Choose:
   - **(a), recommended:** Extend adds the milestone's dependencies at kickoff, each with a `DEP002` exception that expires at milestone exit. A dependency nobody planned blocks the task and goes to `build-setup` Revise.
   - **(b):** the implementer may change `[project.dependencies]` only, and the protected diff skips those lines.
2. **CI.** Generate `.github/workflows/check.yml` by default, or only on request?

**Follow-ups before `build-setup` ships:**
- ~~A live smoke test in a real Claude Code session~~ done 2026-10-16; results in `skills/build-setup/references/tools/hooks.md` (Verified live). It changed `stop_gate.sh` (GATE FAILED report) and `gitignore.additions` (`.claude/worktrees/`).
- Write and test `floor_guard.sh` and `check.sh --pkg`, neither of which exists yet.
- Eval runs through the headless harness won't fire agent frontmatter hooks unless the agents are passed with `--agents`, installed user-level, or the project folder is trusted first (verified: an untrusted `-p` run skips them silently).
