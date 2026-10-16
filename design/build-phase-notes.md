# Build Phase — Reading Notes

**Status:** Notes, not a design · **Last updated:** 2026-10-16 · **Purpose:** refresh memory and give the build-design chat its starting context.

Sources: agent-skills (`/Users/connorott/dev/agent-skills`), [build-setup.md](build-setup.md), [planning-stage.md](planning-stage.md).

---

## 1. Single agent vs multi-agent build

**Single agent:** one context writes the test, then the code (like agent-skills `/build`).

| | |
|---|---|
| + | Cheapest and fastest |
| + | Test and code can change together |
| + | Simple: `/build` and `/build auto` exist, and resume |
| + | Fine for plumbing, refactors and spine tasks |
| − | Grades its own work: a wrong belief (a wrong formula) goes into test and code, and passes |
| − | When stuck, the cheapest route to green is editing the test. Hooks can't fully stop it, because it owns both |
| − | Context builds up over a long task |
| − | Reviewing its own diff is weak |

**Multi-agent:** tester → implementer → reviewer, each with a fresh context.

| | |
|---|---|
| + | Independence: the tester sees only the contract, test cases and acceptance criteria, never `src/`, so tests encode the spec, not the implementation |
| + | Path guards make "edit the test to pass" impossible |
| + | Small fresh contexts mean less context rot |
| + | A diff-only reviewer is close to a real code review |
| − | Roughly 2–3× tokens and time per task (an estimate, not measured) |
| − | Handoff friction: the tester may write against an interface the implementer can't satisfy. Needs a precise contract and an escalation path |
| − | Errors still correlate (same model, same docs). Separate contexts fix context errors, not knowledge errors |
| − | More orchestration |

**Key point:** what catches *knowledge* hallucinations is an external oracle: the golden fixtures from test-planning (user data, paper tables, known-answer synthetic cases). The evidence-reader plugin uses the same blind-verifier idea.

**Decision (made): hybrid.**
- `Mode: split` (tester, then implementer) for behaviour tasks with a checkable outcome.
- `Mode: solo` for spine, refactor, glue and doc-sync tasks.
- A separate read-only reviewer at every checkpoint.
- `build-planning` sets Mode by rule.

---

## 2. How agent-skills does the build

Files read: `.claude/commands/{build,test,review}.md`; skills `incremental-implementation`, `test-driven-development`, `context-engineering`, `debugging-and-error-recovery`, `code-review-and-quality`, `git-workflow-and-versioning`, `doubt-driven-development`; `agents/{test-engineer,code-reviewer}.md`; `references/{definition-of-done,orchestration-patterns}.md`.

| Topic | What it says |
|---|---|
| `/build` loop | Next pending task → read acceptance → load context → RED → GREEN → full suite → build → commit → mark done → stop |
| `/build auto` | Needs a spec at `SPEC.md`, `docs/SPEC.md` or `spec/`, and a clean `git status` apart from planning files. Generates `tasks/plan.md` if missing. **One** approval ("approve/go/yes"; hedges don't count), then every task in dependency order with the same loop, one commit per task staging only that task's files |
| Stops and resume | Stops and asks when a test can't pass or the build breaks (→ debugging), the spec is ambiguous, or the task is high-risk or irreversible (→ doubt-driven + sign-off). User fixes it and re-runs `/build auto`; it resumes at the next pending task. No checkpoint step |
| Slicing | Vertical slices preferred; contract-first and risk-first too. >100 lines untested is a red flag. One logical change per increment, always compilable, simplicity first, "noticed but not touching" |
| TDD | RED must fail → GREEN minimum → REFACTOR. Prove-It for bugs. Test behaviour, not internals. Real > fake > stub > mock. A test that passes first time is suspect |
| Context | Load the spec section, the task's files, one example pattern; under ~2,000 lines; trim at 75%. Ask on conflicts or gaps, never invent. Restart fresh only at a completed-task boundary |
| Debugging | Stop the line: reproduce → localize → reduce → fix root cause → guard with a test → verify |
| Review | Five axes; review tests first and check by experiment (invert a condition, tests must fail). Critical / Required / Optional / Nit. Change size ~100 / 300 / 1000 lines |
| Git, done, doubt | Atomic commit per slice; failed change → revert. Worktrees for parallel agents. Definition of Done is a fixed bar. Doubt-driven: a fresh adversarial reviewer gets artifact + contract, never the claim; max 3 cycles; main session only |
| Orchestration | "The user or a slash command is the orchestrator; personas do not invoke personas" (Claude Code enforces it: subagents can't spawn subagents). Fan-out needs several Agent calls in one turn. Anti-patterns: router persona, persona-calls-persona, **sequential orchestrator that paraphrases** (loses context, ~2× tokens), deep trees. Plugin agents ignore `hooks` |

**Where it is single-agent**
- `/build` and `/test` run in the main session and spawn nothing. One context does RED and GREEN.
- `test-engineer` *reads the code under test first*, the opposite of a blind tester, and only runs via `/ship`. `code-reviewer` is likewise `/ship`-only; `/review` runs in the main session.
- The only split hint is in TDD: "spawn a subagent to write the reproduction test" so it's written without knowing the fix.

**What would need to change for the hybrid**
- New tester role (blind to `src/`). `test-engineer` can't be reused. Roles already drafted in build-setup.
- Orchestrator must be the main session: tester and implementer as depth-1 subagents. Pass `dt context` output verbatim, not a summary, to avoid the paraphrasing anti-pattern.
- `/build auto` preconditions assume agent-skills' layout: spec path (dev-team2's is `docs/spec.md`, lowercase, not in its list), the planning-file whitelist for the clean-`git status` check, and plan generation via `planning-and-task-breakdown` instead of `build-planning`.
- Debugging triage says "test outdated → update the test". The implementer can't touch intent tests, so that needs an escalation path.
- Commit and stop rules need a split variant (tester commit lands before the implementer starts).

---

## 3. Already decided for the build phase

**[build-setup.md](build-setup.md)**
- `CONSTRAINTS.md` is the readable bar, with floor, readability, numeric and measured rules, roles and review sections (§4). `pyproject.toml` and `check.sh` enforce it.
- `check.sh` modes `fast | collect | gate | full`, `--pkg <id>` (§3, §6). Instant tools on every edit; the rest once at Stop; `full` at checkpoints and CI.
- Roles and protected paths (§4, §6):
  - tester: edits `tests/intent/**` only; Stop → `collect`.
  - implementer: `src/**` and `tests/unit/**`; Stop → `gate` plus intent-tests-unchanged diff.
  - reviewer: read-only; runs `full` by hand.
  - Agent files live in the project's `.claude/agents/`, since plugin agents ignore hooks.
- Hooks (§6): path guard, post-edit check, stop gate with a 3-try loop guard, then a human. Two layers per protection: PreToolUse guard plus `git diff --exit-code` at Stop. Tester work is committed before the implementer starts.
- Review levels (§7): Edit (hook) → Task (hook) → Checkpoint (reviewer agent, findings need a disposition, Critical blocks the next checkpoint) → Milestone exit.
- Left explicitly for the build design (§1, §11): how the orchestrator runs each mode, and whether it wraps or replaces `/build`.

**[planning-stage.md](planning-stage.md)**
- Task template: `Package / Step / Covers / Size / Mode`, `Skills`, `Read`, `Acceptance`, `Verify`, `Depends on`, `Files likely` (§5.4).
- Mode rule: `split` if a TC case, Given/When/Then or model criterion covers it; otherwise `solo`. `dt status` flags violations; an override needs a one-line reason.
- `dt context <task>` assembles the builder's whole packet (warns over 2,000 lines). The orchestrator passes it as the subagent prompt; SessionStart doesn't fire for subagents (§9, §10).
- Checkpoints every 2–3 tasks plus milestone exit, reviewed by a separate agent (§5.4).
- Parallel groups are marked after the spine; kickoff check and Advance run at each milestone (§5.4); Replan, debug and rebuild flows (§8).
- Oracle files (`expected.json`) change only with user approval; the `dt guard` hook asks (§5.3, §10).

---

## 4. Open questions for the build design

1. **Wrap or replace `/build`?** A thin dev-team2 `/build` that calls `dt context` and delegates, or its own loop. Also decide what to do about the `/build auto` preconditions above.
2. **Who orchestrates each task?** Main session, per the orchestration rules. What it checks between tester and implementer (tests collect and fail for the right reason; tester work committed), and how it passes the packet unparaphrased.
3. **Escalation when an intent test is wrong or unsatisfiable.** Who decides, whether the tester is re-run, when it goes to the human (stop-gate's 3 tries?), and how a wrong `expected.json` is handled (the oracle ask path).
4. **What the tester writes against.** It never sees `src/`, so who supplies importable signatures (the contract, a stub from the spine task) so RED fails for the right reason?
5. **Parallel groups.** Worktrees or the same tree; shared files (`pyproject.toml`, contract exports); merge order; commit-per-task still holding.
6. **Checkpoint findings back into the plan.** Who writes the fix tasks and dispositions into `plan.md`; when a finding means Replan instead of a fix task.
7. **Resume and failure in split mode.** State lives in git and `todo.md`; what "tester done, implementer not" looks like on restart; commit conventions per mode.
8. **Stop conditions.** Map agent-skills' three (stuck, ambiguous spec, irreversible) to the stop gate, the doc Revise flows, and doubt-driven sign-off.
9. **Reviewer independence.** Same model or a different one (agent-skills' multi-model pattern); what it reads (see [planning-stage.md §9](planning-stage.md)).

**Eval:** test projects will exist by then, so the build design should ship with an eval comparing build modes on the same plan: all-solo vs the hybrid (optionally all-split). Things worth measuring: tokens and time per task (checks the 2–3× estimate), defects caught by golden fixtures, whether a planted wrong belief gets through, attempts to edit protected tests, escalations and human interventions, and checkpoint findings. The planning evals already have a harness and blind judge in `evals/harness/` to reuse.
