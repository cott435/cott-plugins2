# Build Phase — Design

**Status:** Draft · **Last updated:** 2026-10-17 · **Branch:** `interface-first-design` · **Builds on:** [build-phase-notes.md](build-phase-notes.md) (§4 verified runtime, §5 open questions), [interface-first-design.md](interface-first-design.md) (§5 milestone shape, §6.4 dispatch inputs, §7 TDD), [build-setup.md](build-setup.md) (§4 roles, §6 hooks, §7 review)

How a planned milestone gets built: which agents run, what each sees and may write, how many run at once, how their work lands, who reviews it, and when the user is asked. The plan arrives interface-first (`tasks/plan.md` with `Kind`, `Mode`, `Writes:`, a dependency graph and checkpoints) and the bar arrives from build-setup (`CONSTRAINTS.md`, `check.sh`, hooks, the tester, implementer and reviewer agent files). Nothing here has run yet; §12 lists the smoke tests that come first.

Inputs: agent-skills' build phase (`/Users/connorott/dev/agent-skills`, v0.6.13, surveyed in full), the iteration-8 rl all-at-once plan (`dev-team-workspace/iteration-8/rl-all-at-once/with_skill/project`, its `tasks/plan.md`, generated `.claude/agents/`, `scripts/`), and `dt status` / `dt ready` on that plan.

---

## 0. Where it lives

dev-team owns the build (decided 2026-10-17). PURPOSE's goal runs from a raw idea to working code built from the agreed plan, with each milestone built by agents in parallel; its non-goal is writing code outside a planned task, which stays `/build`'s job. The evals, `dt` and build-setup already live here. Rejected: a separate build plugin depending on `dt`, and dev-team shipping only the `dt` commands and agent files with the orchestration prompt elsewhere.

---

## 1. Decisions at a glance

1. **Split is keyed to the oracle, not the Kind.** A task runs tester then implementer whenever an oracle-backed intent test covers it (a TC case, a Given/When/Then, a model criterion), whatever its Kind. Interface, and spine tasks with no TC, stay solo. (§3)
2. **Three roles, but the reviewer reviews phases, not tasks.** Every landing gets a deterministic check (gate, `Writes:` diff, protected diff); an LLM reviewer runs at the end of each plan phase over that phase's diff, and as a barrier after the interface phase. *(Default; open decision D1.)* (§4)
3. **The main session orchestrates.** A `build` skill in the main session spawns depth-1 background agents, one per ready task half, each in its own worktree, and lands their work one at a time as each finishes. A generated workflow is an eval arm. *(Default; open decision D2.)* (§5)
4. **Dispatch is code, judgement is model.** Three `dt` commands carry every deterministic step: `dt ready` picks, `dt claim` hands the agent its packet and edit boundary, `dt land` checks, commits, merges, re-gates and ticks. The orchestrating model decides only what to do with a rejection. (§6)
5. **No paraphrased packets.** An agent's prompt is one line naming its task and role; its first action is `dt claim`, which prints the packet. (§6.2)
6. **Dataflow, not waves.** A task starts the moment its `Depends on` have landed; waves are a planning measure only. Ready tasks are ordered by remaining critical path under a concurrency cap. (§7)
7. **One go per milestone.** The user approves the start; the build runs on its own until a stop condition (§9) or milestone exit, where the user approves the merge. The interface review is an agent, not a human gate. *(Default; open decision D3.)* (§11)
8. **State lives on disk.** Claims, landings, gate verdicts and ticks are files and commits, so a compacted or restarted orchestrator resumes from `dt` alone. (§10)

---

## 2. What agent-skills gives

Its build is one agent, one task at a time. `/build` (`.claude/commands/build.md:16-25`) picks the next task, writes a failing test, then the code, runs the suite and build, commits and stops; `/build auto` (`build.md:31-41`) does the same for every task in dependency order after one unambiguous approval, stopping when a test can't pass, the spec is ambiguous, or a step can't be undone with `git revert`. There is no review, lint or Definition of Done step inside the loop. No command writes code in parallel: the only parallel runner is `/ship`, which fans out three read-only reviewers in one turn (`ship.md:11`). Worktrees are advice with no merge or conflict handling (`git-workflow-and-versioning/SKILL.md:147-171`); the plan template has `Dependencies:` and `Files likely touched`, no ownership or parallel marker (`planning-and-task-breakdown/SKILL.md:97-101`). Its comparison doc credits Superpowers, not itself, with a fresh subagent per task, a task reviewer and worktree isolation (`docs/comparison.md:24,38`).

What we take:
- **The orchestrator is the main session; personas never invoke personas; depth stays 1** (`references/orchestration-patterns.md:5,145`). Fan-out is several Agent calls in one turn (`:170`).
- **Three stop conditions** (stuck, ambiguous, irreversible), mapped in §9.
- **Resume from durable state; never infer approval from an earlier conversation** (`context-engineering/SKILL.md:123-137`).
- **A reviewer gets the artifact and the contract, never the builder's claim** (`doubt-driven-development/SKILL.md:85-110`).
- **Review tests first, and check them by experiment:** invert a condition, the suite must fail (`code-review-and-quality/SKILL.md:164`).
- **Read-only fan-out is safe when the parts share nothing** (Pattern 3, `orchestration-patterns.md:48-74`): used for per-package reviewers (§4).

What we avoid: its sequential orchestrator that paraphrases (anti-pattern C, `:316-326`), and its single human gate sitting against its own plan's "review with human every 2–3 tasks" (`planning-and-task-breakdown/SKILL.md:118-123`). Here the checkpoints are reviewer agents, so one go and autonomous checkpoints don't contradict.

---

## 3. Roles and when to split

### 3.1 Why the cost of separating is low here

In a serial build a separate tester adds a step to every split task. In an interface-first parallel build it adds almost nothing to wall clock: a split task's tester half depends only on the interface task (`build-planning/references/tasks.md` §7), so every tester runs in the first wave beside the spines and is finished before its implementer could start. The main risk of separating, a tester writing against something the implementer can't satisfy (build-phase-notes §1), is mostly gone because the interface is code: signatures import, samples validate, stubs name their task. What is left is token cost, so the question per task is whether a separate context adds information.

### 3.2 By kind

| Kind | Separate tester | Why |
|---|---|---|
| interface | Never | Nothing to test beyond its own samples validating; its risk is a wrong shape, which review catches (§4) |
| spine (no TC) | No | The interface fixes the test: the boundary's sample in, a schema-valid output out. A blind tester re-derives the sample. The implementer writes unit tests |
| spine, wiring, system with a TC | **Yes** | The TC is an oracle; the intent test that loads it is protected from the implementer. Wiring and system testers test pipeline entries, which the interface declares, so they too start in the first wave |
| thicken | **Yes** | Where a wrong belief hides. The tester never sees `src/` |

**Rule (replaces tasks.md §7 and `expected_mode`):** `split` when the task's acceptance names a TC case, a Given/When/Then or a model criterion, or its `Writes:` includes a path under `tests/intent/`; otherwise `solo`. An override needs `**Reason:**`. The second clause is a consistency check: only a tester may write intent tests.

**What iteration 8 shows.** `expected_mode` (`scripts/devteam/status/build_planning.py:18-23`) returns solo for every interface, spine, wiring and system task. In the rl plan five solo tasks write intent tests for their TCs: M1-T08 (`tests/intent/learn/test_seed_guard.py`, TC-28), M1-T15 (TC-07), M1-T16 (TC-20), M1-T17 (TC-25, TC-26, TC-29), M1-T23 (TC-34). The generated implementer guard denies `tests/intent/**`, so each would block at build time. Under the rule above, split tasks go from 3 to 8 of 23, and all eight tester halves are ready once the interface lands.

### 3.3 Why not all split, or all solo

- **All split** buys a tester for spine and interface tasks whose tests the interface already determines: more agents, more merges, little information.
- **All solo** loses the one thing a second context provably adds: a test written without the code, which the code's author can't edit. With golden fixtures as the oracle and path guards, that is the defence against a wrong belief passing (build-phase-notes §1, key point). The build eval's A3 − A4 contrast (interface-first-design §9.2) measures it.

### 3.4 What each role gets

| Role | Packet (`dt claim --role`) | May write | Gate at land |
|---|---|---|---|
| tester | Task, acceptance, TC cases and fixture paths, the interface's types, signatures and sample paths, contract sections. No `src/` | The task's `Writes:` under `tests/intent/` | `check.sh collect` (lint, collect, red for the right reason) |
| implementer | Full `dt context` packet, plus the landed intent tests by path | The task's `Writes:` outside `tests/intent/` | `check.sh gate --pkg`, protected diff |
| solo | Full packet | The task's `Writes:` | `check.sh gate --pkg`, protected diff |
| reviewer | Phase diff (paths and base), the phase's tasks and acceptance, CONSTRAINTS.md Review section, contract and step tables. Never the builders' reports | Nothing | Runs `check.sh full` itself |

---

## 4. Review

| Level | When | Who | Blocks |
|---|---|---|---|
| Edit | Every Edit/Write | `post_edit.sh` hook | Feeds back |
| Land | Every task half | `dt land`: `Writes:` diff, protected diff, gate in the worktree, gate on the merged tree | Rejects the landing (§6.3) |
| Interface | Phase 0 landed | Reviewer agent: code matches `contract.md` types and signatures; samples and doubles match the contract's cases; every stub names an open task; exports complete | **Barrier**: nothing else dispatches until it passes. Critical → stop |
| Phase | Each plan phase's tasks all landed | Reviewer agent per package with changes (parallel, read-only), over the phase's diff | Not a barrier: dispatch continues. Critical → stop dispatch (§9) |
| Milestone exit | All tasks landed | Reviewer per package over the milestone diff, then the user | User approves the merge |

**Why phases, not tasks.** Per-task LLM review puts one more agent on the critical path of every XS task, and most of what it would check (bar, Writes, protected paths, stubs) `dt land` checks deterministically. Per-phase review keeps each diff bounded and runs beside the next phase. **Why not one checkpoint:** iteration 8's only mid-milestone checkpoint sits after M1-T22, which is every task but the system task, a diff far above agent-skills' ~1,000-line review limit (`code-review-and-quality/SKILL.md`, change sizing).

**Phase diffs under dataflow.** Tasks of the next phase land while a phase is reviewed, so the reviewer gets `git diff <phase base> <sha> -- <the phase's Writes>` at the SHA where the phase's last task landed, in its own worktree at that SHA. Over ~1,000 lines it splits by package, which is also the parallel unit.

**Findings.** The reviewer reports in the reviewer agent's existing line format; the orchestrator records each with `dt finding` under the checkpoint block. Critical stops dispatch and goes to the user. Important and below accumulate; fix tasks are planned by build-planning Replan at the next user gate (a stop or milestone exit) and run before exit. Only the orchestrator writes `tasks/`.

**Checkpoint placement (changes tasks.md §8).** `### Checkpoint after M<n>-T<nn>` closes each plan phase: after Phase 0 (marked barrier), after Phase 1, after Phase 2, and the milestone exit. The block names the phase's last task in plan order, as now.

---

## 5. The orchestrator

**Default: the main session, running the `build` skill's Run mode.**

| | Main session | Generated workflow |
|---|---|---|
| Deterministic steps | Runs `dt` and `git` itself through Bash | No shell in the script; every `dt land` needs a land agent (build-phase-notes §4) |
| Scheduling | Each background agent's completion arrives separately, so tasks start as their dependencies land | `pipeline()` can express the DAG, generated by `dt`; equally dataflow |
| Verdicts | `dt land` re-runs the gate and returns its result | Hook output never reaches the script; the land agent's last message carries it |
| Input mid-run | The user can interject; a stop asks in the same session | None; a stop ends the run and a new workflow resumes |
| Context | Grows by one short turn per landing (~35 for the rl M1); state on disk survives compaction | Script holds the state |
| Visibility | Transcript and task list | `/workflows` progress view |

The workflow form is kept as an eval arm (D2): `dt build workflow M1` emits a script with one `pipeline()` per task chain and a low-effort land agent per landing.

**What the orchestrator never does:** write code, edit `tests/`, write prompts beyond the one-line claim instruction, paraphrase a report into the plan (findings go in verbatim through `dt finding`), or merge by hand.

**Main-session Stop hook** skips while `background_tasks` has running entries (build-phase-notes §4 rec. 4).

---

## 6. `dt` commands

### 6.1 `dt ready` (extended)

Lists ready **task halves**: `{"id", "role": "tester|implementer|solo", "title", "kind", "pkg", "writes", "remaining_cp"}`.
- A tester half is ready when the milestone's interface tasks have landed.
- An implementer half is ready when its tester half and every `Depends on` task have landed.
- A solo task is ready when every `Depends on` has landed.
- Halves already claimed are left out. `--cap N` returns at most N minus the claims in flight. Sorted by remaining critical path, size-weighted (XS=1, S=2, M=4), so the longest chain starts first when the cap bites.
- Default cap: 6, a measured value to revisit after the first build eval (rate limits, machine load, venv setup).

### 6.2 `dt claim <task> --role <role>` (new)

Run by the agent, inside its worktree, as its first action. It:
1. Refuses if the half isn't ready or is already claimed, or if the worktree's HEAD lacks a landing it depends on (a stale base fails here, not at merge).
2. Writes `.claude/.task_writes` with the role's share of `Writes:` (tester: the `tests/intent/` paths; implementer: the rest; solo: all).
3. Sets `refs/worktree/checks-base` to HEAD: per worktree, so parallel agents never share a base.
4. Records the claim (task, role, worktree path, branch, base SHA, time) under the shared git dir, `$(git rev-parse --git-common-dir)/dt-build/claims/`. The orchestrator never needs to learn a worktree's path or branch.
5. Prints the role's packet (§3.4), ending with the role's done condition.

The agent's whole prompt: *"You are the `<role>` for `<task>`. Run `dt claim <task> --role <role>` first; its output is your task."* The agent type (`tester`, `implementer`) supplies the rules.

### 6.3 `dt land <task> --role <role>` (new)

Run by the orchestrator, in the main checkout, one at a time. From the claim record it:
1. Diffs the worktree against its base: committed, uncommitted and untracked. Any path outside the role's `Writes:` (re-derived from the plan, not from `.task_writes`) or on the protected list → **reject `writes`**, listing the paths.
2. Runs the role's gate in the worktree → **reject `gate`** with the output tail.
3. Commits in the worktree, staging only `Writes:` paths: `M1-T04 tests: <title>`, `M1-T04 impl: <title>`, or `M1-T05: <title>`.
4. Merges `--no-ff --no-commit` into the build branch. A conflict means two tasks wrote one path, a lint gap → abort the merge, **reject `conflict`**.
5. Runs `check.sh gate --pkg <pkg>` on the merged tree (implementer and solo) → on failure resets the build branch to before the merge, **reject `integration`**.
6. Ticks the task in `todo.md` (implementer or solo; a tester landing ticks nothing) inside the same merge commit, writes `.dt/gates/<task>.<role>.json`, removes the worktree and branch, deletes the claim.

Output: one JSON object `{"landed": bool, "reject": "writes|gate|conflict|integration|null", "detail": "..."}`.

### 6.4 `dt build status` (new)

The run's state from disk: landed, claimed (with whether the worktree still exists), ready, blocked (with the rejection or escalation that blocks it), findings by severity, and the next checkpoint. The orchestrator reads it after a compaction or restart.

---

## 7. The loop

```
start   user's go → dt build start M1 (records **Build:** in plan.md, creates build/M1 from Base)
loop    rows = dt ready --cap N
        spawn one background agent per row (agent type = role, isolation: worktree), all in one turn
        on each completion:
            r = dt land <task> --role <role>
            landed        → if a checkpoint's tasks are all landed: spawn its reviewer(s)
            reject gate   → first time: re-spawn the same half, fresh worktree, prompt + the gate output
                            second time: block the task (§9)
            reject writes / conflict / integration → block the task (§9)
            agent report starts CONTRACT-CHANGE / TEST-WRONG → §9
        on a reviewer's report: dt finding per line; Critical → stop dispatch
        Phase 0 checkpoint: no dispatch beyond the interface tasks until its review passes
exit    all landed → exit review → user approves → merge build/M1 → Advance
```

On the rl M1 with the §3.2 rule: the 3 interface tasks run first; after the interface review, about 20 halves are ready (12 solo spines and thickens, 8 testers), dispatched 6 at a time by remaining critical path.

---

## 8. Worktrees and shared state

| Hazard | Rule |
|---|---|
| Shared base ref: `refs/checks/base` is one ref for every worktree (`scripts/check.sh:98-100`) | `refs/worktree/checks-base`, set by `dt claim`; `check.sh` reads it first |
| The `writes` guard fails open when `.claude/.task_writes` is missing (`path_guard.sh:32`) | Fails closed for `tester` and `implementer` agent types: "run `dt claim` first". The main session and other agent types are unaffected |
| Editable installs point at the checkout that installed them, so a shared venv tests the main checkout's code | Each worktree gets its own `.venv` (`uv run --frozen` creates it; the uv cache clones packages). Setup time is measured in the smoke test, torch included |
| Fixed output paths collide between parallel smoke tests (`/tmp/x.mp4`, `runs/`) | Tests write under `tmp_path`; the reviewer flags a fixed path; Verify lines name a temp directory |
| `uv.lock`, `pyproject.toml`, `__init__.py`, `types.py` | Protected or interface-owned; a builder needing a change stops and reports (build-setup open item 1) |
| Chained git in one Bash call refused in worktrees (build-phase-notes §4) | Agent files say: one git command per call |
| Worktree base | Agent-tool worktrees branch from the main checkout's HEAD, which is the build branch with every landing so far; `dt claim` verifies it |

`.claude/worktrees/`, `.claude/.task_writes` and `.dt/` are gitignored by build-setup.

---

## 9. Stopping and escalation

Independent work **drains, never stops mid-task**: when a task blocks, its dependents aren't dispatched, in-flight agents finish and land, and the orchestrator stops and reports once nothing else is ready.

| agent-skills condition | Here | Who decides |
|---|---|---|
| A test can't pass / the build breaks | `reject gate` twice, or `integration` | User. The report gives the task, both gate outputs and the dependents blocked |
| A test can't pass because the test is wrong | The implementer ends with `TEST-WRONG: <test> — <why>` | One fresh tester run with the packet plus that reason. It may rewrite the test but never a fixture or expected value. Still disputed, or the dispute is about a TC fixture → user (`dt guard` handles any `expected.json` change) |
| The spec is ambiguous / a decision isn't covered | Tester or implementer ends with `CONTRACT-CHANGE: <symbol> — <what is missing>` | Dependents of that interface stop; architecture-design Revise, then a new interface task through build-planning Replan; user approves both |
| High-risk or irreversible | A task that needs credentials, network writes or anything outside the repo | User, before dispatch: such a task is marked in the plan and never dispatched on the go alone |
| (new) Writes or conflict | `reject writes` or `conflict` | The task is re-dispatched once with the rejected paths; a `conflict` is also logged as a plan-lint gap |
| (new) Critical finding | Phase or interface reviewer | User; dispatch stops, in-flight work drains |

The agent files gain the two report prefixes; `stop_gate.sh`'s `GATE FAILED` prefix stays as a third.

---

## 10. Resume

Everything the orchestrator knows is on disk: claims (`dt-build/claims/`), landings (commit subjects on `build/M1`), verdicts (`.dt/gates/`), ticks (`todo.md`), findings (`plan.md`) and the go (`**Build:**` in `plan.md`). On restart, Resume mode runs `dt build status` and:
- **Claimed, worktree present, agent gone:** `dt land` it. The gate re-runs, so finished work isn't lost and unfinished work is rejected. A reject → discard the worktree and re-dispatch (tasks are XS or S).
- **Tester landed, implementer not:** the implementer half is simply ready.
- **Blocked:** stays blocked until the user resolves it; Resume reports what blocks it.
- **Approval:** the recorded go stands for this milestone and this plan version; a Replan since the go needs a new one.

---

## 11. User gates

1. **Go**, once per milestone, after `dt status` shows the plan Approved and build-setup's bar current.
2. **Interface review** by an agent (D3). Its Critical findings, like every stop in §9, come to the user.
3. **Stops** (§9).
4. **Milestone exit:** the exit review's findings, the Definition of Done, the Scope's Exit line, and the user's yes before `build/M1` merges.

---

## 12. Before building: smoke tests

Each settles something §5–§8 assume; build-phase-notes §4 lists the first three as untested. About $1–3 in total.

1. A full split task end to end: tester claims, writes red tests, lands; implementer claims, passes, lands; the merged gate passes.
2. Two worktree agents in parallel, landing one after the other; `refs/worktree/checks-base` stays per worktree.
3. Which `settings.json` and agent files a worktree agent loads, and whether the hooks' `cwd` is the worktree.
4. Agent-tool worktrees: they branch from the main checkout's HEAD, and the claim record is all the orchestrator needs (the Agent result isn't relied on for path or branch).
5. Venv setup time per worktree with torch.
6. The main-session Stop hook with background agents running.

---

## 13. What iteration 8 shows about the plan

`dt status` on the rl M1: 23 tasks, 7 waves, width 12, parallelism 3.29, critical path M1-T02 → T10 → T17 → T18 → T19 → T20 → T23 (7). Three plan-side causes, each a build-planning rule:

| Cause | Fix | Effect |
|---|---|---|
| T18, T19, T20 (wire PL-15, PL-16, PL-17) all write lab `pipeline.py`, so they chain by `file` edges; T15 and T16 do the same on worlds `pipeline.py` and `__main__.py` | Each pipeline's wiring writes its own entry module; the package's `__main__.py` dispatch is written by the interface task (phase0.md) | The wiring tasks run side by side |
| T18 waits on T17 because `learn.train` has no fake | A pipeline entry that another package's wiring calls gets a fixture-backed fake in the interface task, like any cross-package call | Lab wiring leaves the learn chain |
| The Mode rule (§3.2) | As above | 5 tasks no longer blocked; 8 testers in the first wave |

With the first two, the critical path is 4 (e.g. T02 → T10 → T17 → T23, T02 → T10 → T21 → T23), and the last three checkpoints move to phase ends (§4). `dt status` gains a warning for `file` edges on the critical path, since each is a planning choice.

---

## 14. Answers to build-phase-notes §5

| # | Question | Answer |
|---|---|---|
| 1 | Wrap or replace `/build` | Replace, for planned milestones: a dev-team `build` skill (§0). agent-skills `/build` stays for unplanned work |
| 2 | Who orchestrates | Main session (§5, D2); packets unparaphrased through `dt claim` (§6.2); between tester and implementer the tester's work is landed and red for the right reason (§6.3) |
| 3 | Wrong or unsatisfiable intent test | `TEST-WRONG` → one fresh tester run → user; oracle files only through `dt guard` (§9) |
| 4 | What the tester writes against | The frozen interface (interface-first-design §4.3, §7) |
| 5 | Parallel groups | Dataflow from `dt ready`, worktree per half, land one at a time in plan-independent order since `Writes:` are disjoint (§6–§8) |
| 6 | Findings into the plan | Orchestrator records with `dt finding`; fix tasks through build-planning Replan at the next user gate; Critical stops (§4) |
| 7 | Resume in split mode | From claims, commit prefixes and ticks (§10) |
| 8 | Stop conditions | §9 |
| 9 | Reviewer independence | Fresh context, reads the diff and the contract, never the builders' reports; same model by default, a different model is an eval arm |
| 10 | Guard ownership | The plugin's `hooks.json` keyed by `agent_type` (build-phase-notes §4 rec. 1), with the agent files' frontmatter hooks as backup |

---

## 15. Open decisions

- **D1 — Review granularity** (§4): per phase plus an interface barrier (default), or an LLM reviewer per task. Settled by a build-eval arm: A3 with per-task review vs A3 as designed, on defects found, tokens and wall clock.
- **D2 — Orchestrator form** (§5): main session (default) or a generated workflow per segment. Settled by a build-eval arm on wall clock, harness failures and lost verdicts.
- **D3 — Interface review** (§4, §11): reviewer agent (default; the contract was approved in planning, so this review checks code against it) or a user gate.

Smaller ones, decided by default here and revisited after the first build eval: the concurrency cap (6); one gate retry before blocking; Important findings waiting for the next user gate.

---

## 16. Changes by file

| Where | Change |
|---|---|
| `skills/build` (new) | `SKILL.md`: the orchestrator's role, the docs it writes (`todo.md` ticks, findings, `**Build:**`), what it never does, mode table. `references/run.md` (a milestone, §7), `task.md` (one task in the foreground, for debugging), `resume.md` (§10), `exit.md` (exit review and the merge); topic reference `escalation.md` (§9) |
| `skills/build-planning/references/tasks.md` | §7 Mode rule (§3.2); §8 checkpoints at phase ends, Phase 0 a barrier (§4) |
| `skills/build-planning/references/phase0.md` | Per-pipeline entry modules; `__main__` dispatch owned by the interface task; fakes for pipeline entries other packages' wiring calls (§13) |
| `scripts/devteam/status/build_planning.py` | `expected_mode` per §3.2; warning for `file` edges on the critical path |
| `scripts/devteam/commands/ready.py` | Task halves, `--cap`, remaining-critical-path order (§6.1) |
| `scripts/devteam/commands/` `claim.py`, `land.py`, `build.py` (new) | §6.2–§6.4, `dt build start`, `dt build workflow` (eval arm) |
| `skills/build-setup/templates/scripts/` | `check.sh` reads `refs/worktree/checks-base`; `path_guard.sh writes` fails closed for builder agent types; gitignore additions (§8) |
| `skills/build-setup/templates/` agent files | One-line-prompt contract (`dt claim` first); `TEST-WRONG` and `CONTRACT-CHANGE` report prefixes; one git command per call; reviewer gets a path-scoped diff and never builders' reports |
| `hooks/hooks.json` | Role guard keyed by `agent_type` (§14 row 10) |
| `evals/harness/` | Build-eval arms of interface-first-design §9.2, plus D1 and D2 arms; `grade_build.py` reads `.dt/gates/` and claim records |
