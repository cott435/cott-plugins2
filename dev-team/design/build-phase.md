# Build Phase — Design

**Status:** Draft, revised after a fresh-context review · **Last updated:** 2026-10-17 · **Branch:** `interface-first-design` · **Builds on:** [build-phase-notes.md](build-phase-notes.md) (§4 verified runtime, §5 open questions), [interface-first-design.md](interface-first-design.md) (§5 milestone shape, §6.4 dispatch inputs, §7 TDD), [build-setup.md](build-setup.md) (§4 roles, §6 hooks, §7 review)

How a planned milestone gets built: which agents run, what each sees and may write, how many run at once, how their work lands, who reviews it, and when the user is asked. The plan arrives interface-first (`tasks/plan.md` with `Kind`, `Mode`, `Writes:`, a dependency graph and checkpoints) and the bar arrives from build-setup (`CONSTRAINTS.md`, `check.sh`, hooks, the tester, implementer and reviewer agent files). None of the `dt` commands exist yet; §12 lists the runtime behaviour verified so far and the smoke tests still to run.

Inputs: agent-skills' build phase (`/Users/connorott/dev/agent-skills`, v0.6.13, surveyed in full), the iteration-8 rl all-at-once plan (`dev-team-workspace/iteration-8/rl-all-at-once/with_skill/project`, its `tasks/plan.md`, generated `.claude/agents/`, `scripts/`), `dt status` / `dt ready` on that plan, and an adversarial review of the first draft (38 findings; each is answered in the section it concerns).

---

## 0. Where it lives

dev-team owns the build (decided 2026-10-17). PURPOSE's goal runs from a raw idea to working code built from the agreed plan, with each milestone built by agents in parallel; its non-goal is writing code outside a planned task, which stays `/build`'s job. The evals, `dt` and build-setup already live here. Rejected: a separate build plugin depending on `dt`, and dev-team shipping only the `dt` commands and agent files with the orchestration prompt elsewhere.

---

## 1. Decisions at a glance

1. **Split is keyed to the oracle, not the Kind.** A task runs tester then implementer whenever an oracle-backed intent test covers it (a TC case, a Given/When/Then, a model criterion), whatever its Kind. Interface, and spine tasks with no TC, stay solo. (§3)
2. **Three roles, but the reviewer reviews phases, not tasks.** Every landing gets a deterministic check; an LLM reviewer runs at the end of each plan phase over that phase's landings, and as a barrier after the interface phase. (§4)
3. **The main session orchestrates, as a low-context driver.** A `build` skill in the main session spawns depth-1 background agents, one per ready task half, each in its own worktree, and lands their work one at a time. Every agent ends with one status line; details go to files `dt` reads. The driver branches only on `dt` JSON. A generated workflow is an eval arm. (§5)
4. **Dispatch is code, judgement is model.** `dt` carries every deterministic step: `dt ready --reserve` picks, `dt claim` hands the agent its packet and edit boundary, `dt land` checks, commits, merges, re-gates and ticks, `dt escalate` records why an agent stopped. The driver decides only what to do with a rejection or an escalation. (§6)
5. **No paraphrased packets.** An agent's prompt is one line naming its task, role and the `dt` path; `dt claim` writes the packet to a file the agent reads. (§6.2)
6. **Dataflow, not waves.** A task half starts the moment what it needs has landed; waves are a planning measure only. Ready halves are ordered by remaining critical path under a concurrency cap. (§7)
7. **The build branch stays green.** A tester's red tests land on a side branch and reach the build branch only with the implementer's code. (§6.3)
8. **One go per milestone.** The user approves the start; the build runs on its own until a stop (§9) or milestone exit, where the user approves the merge. The interface review is an agent, not a human gate. (§11)
9. **State lives in one place.** Reservations, claims, verdicts, escalations, reviews and an append-only log sit under the git common directory (`.git/dt-build/`), reachable from every worktree and never committed; landings are commits with a `Dt-Landed:` trailer. A compacted or restarted driver resumes from `dt` alone. (§10)

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

### 3.1 What separating costs here

In a serial build a separate tester adds a step to every split task. In an interface-first parallel build it mostly runs in parallel: a split task's tester half depends only on the interface tasks (`build-planning/references/tasks.md` §7), so testers run in the first wave beside the spines. For a split task whose implementer also waits on other tasks (a thicken after its spine, a wiring task after its steps), the tester is done before the implementer could start and costs no wall clock. For a split task that depends only on the interface (rl: T04, T08, T22), the tester is on that task's path: tester, then implementer. The main risk of separating, a tester writing against something the implementer can't satisfy (build-phase-notes §1), is mostly gone because the interface is code: signatures import, samples validate, stubs name their task. What is left is token cost and, for those few tasks, one extra step on their path.

### 3.2 By kind

| Kind | Separate tester | Why |
|---|---|---|
| interface | Never | Nothing to test beyond its own samples validating; its risk is a wrong shape, which review catches (§4) |
| spine (no TC) | No | The interface fixes the test: the boundary's sample in, a schema-valid output out. A blind tester re-derives the sample. The implementer writes unit tests |
| spine, wiring, system with a TC | **Yes** | The TC is an oracle; the intent test that loads it is protected from the implementer. Wiring and system testers test pipeline entries, which the interface declares, so they too start in the first wave |
| thicken | **Yes** | Where a wrong belief hides. The tester never sees `src/` |

**Rule (replaces tasks.md §7 and `expected_mode`):** `split` when the task's acceptance names a TC case, a Given/When/Then or a model criterion, or its `Writes:` includes a path under `tests/intent/`; otherwise `solo`. The second clause is a consistency check: only a tester may write intent tests. An override needs `**Reason:** mode: <one line>`; `mode_violations` reads only a Reason starting `mode:`, so a task's unrelated Reason (rl T23's) no longer masks the rule.

**Unit tests have a home.** Every implementer and solo half writes unit tests (implementer.md), so its `Writes:` must name a `tests/unit/<pkg>/` path. A new `dt lint` rule, `writes-unit`, flags one that doesn't (rl: T21, T22, T23).

**What iteration 8 shows.** `expected_mode` (`scripts/devteam/status/build_planning.py:18-23`) returns solo for every interface, spine, wiring and system task. In the rl plan five solo tasks write intent tests for their TCs: M1-T08 (`tests/intent/learn/test_seed_guard.py`, TC-28), M1-T15 (TC-07), M1-T16 (TC-20), M1-T17 (TC-25, TC-26, TC-29), M1-T23 (TC-34). The generated implementer guard denies `tests/intent/**`, so each would block at build time. Under the rule above, split tasks go from 3 to 8 of 23, and all eight tester halves are ready once the interface lands.

### 3.3 Why not all split, or all solo

- **All split** buys a tester for spine and interface tasks whose tests the interface already determines: more agents, more merges, little information.
- **All solo** loses the one thing a second context provably adds: a test written without the code, which the code's author can't edit. With golden fixtures as the oracle and path guards, that is the defence against a wrong belief passing (build-phase-notes §1, key point). The build eval's A3 − A4 contrast (interface-first-design §9.2) measures it.

### 3.4 What each role gets

| Role (agent type) | Packet (`dt claim`, in `.claude/packet.md`) | May write | Gate at land |
|---|---|---|---|
| tester (`tester`) | Task, acceptance, TC cases and fixture paths, the interface's types, signatures and sample paths, contract sections. No `src/` | The task's `Writes:` under `tests/intent/` | `check.sh collect` (lint, collect, red for the right reason, every marker) |
| implementer (`implementer`) | Full `dt context` packet; its worktree already holds the tester's tests, merged by `dt claim` | The task's `Writes:` outside `tests/intent/` | `check.sh gate --pkg`, the task's own intent tests with every marker, protected diff |
| solo (`implementer`) | Full packet | The task's `Writes:` | `check.sh gate --pkg` (an interface task also `tests/contracts`), protected diff |
| reviewer (`reviewer`) | Prompt only: review kind, package, task IDs, base and end commits, paths, lead or not. It reads the diff, the tasks' acceptance, CONSTRAINTS.md's Review section, contract and step tables itself. Never builders' reports | Nothing that lands: mutations in its own worktree, restored after each; its findings in a gitignored `.dt/review.md`, handed in with `dt build submit-review` | Runs `check.sh full` itself |

There is no `solo` agent file: a solo half runs as `implementer`.

---

## 4. Review

| Level | When | Who | Blocks |
|---|---|---|---|
| Edit | Every Edit/Write | `post_edit.sh` hook | Feeds back |
| Land | Every task half | `dt land`: `Writes:` diff, protected diff, the role's gate, the gate on the merged tree | Rejects the landing (§6.3) |
| Interface | Phase 0 landed | Reviewer agent: the interface code is the contract, no more and no less | **Barrier**: `dt ready` releases nothing else until the review is recorded as passed. Critical → stop |
| Phase | Each plan phase's tasks all landed | Reviewer agent per package with changes, in parallel, over the phase's landings: interfaces followed, tests (mutation-checked), correctness, simplicity | Not a barrier: dispatch continues. Critical → `dt ready` stops releasing (§9) |
| Milestone exit | All tasks landed | Reviewer per package over the milestone diff, then the user | User approves the merge |

**Why phases, not tasks.** Per-task LLM review puts one more agent on the critical path of every XS task, and most of what it would check (bar, Writes, protected paths, stubs) `dt land` checks deterministically. Per-phase review keeps each diff bounded and runs beside the next phase. **Why not one checkpoint:** iteration 8's only mid-milestone checkpoint sits after M1-T22, which is every task but the system task, a diff far above agent-skills' ~1,000-line review limit (`code-review-and-quality/SKILL.md`, change sizing). **What the barrier costs:** the interface review (one reviewer run: venv, both type checkers, pip-audit) sits on the critical path once per milestone; it is the price of freezing the interface every other task builds on.

**What a phase review covers.** Under dataflow, a later phase can land work on a file an earlier phase wrote before the earlier phase finishes (rl: T21 thickens `qtable.py`, which T10 wrote, and may land before T14). So a phase is not a commit range: it is the set of its tasks' landing commits. `dt` lists them by their `Dt-Landed:` trailers; the reviewer gets those commits' first-parent diffs and the end SHA where the phase's last task landed, detaches its worktree there (`git switch --detach <end>`), and reviews. Each package gets its own reviewer; one is marked lead and alone reports repo-wide results (pip-audit, pylint `duplicate-code`, the bar diff), so they aren't reported once per package. A package diff over ~1,000 lines splits by task across two reviewers.

**What the reviewer looks for.** The checklist is CONSTRAINTS.md's Review section (template: `skills/build-setup/templates/CONSTRAINTS.md`); the procedure is the reviewer agent file. In outline:
- *Interface review:* types, signatures, stubs, samples, doubles and exports match `contract.md` exactly; every `Mitigated by` in the dependency graph exists; every split task's tester can write its tests from what is frozen.
- *Each phase:* interfaces followed (no frozen change, declared types used, no reaching into internals), tests that prove something, correctness to the spec, simplicity, pipeline shape, the bar, what the fakes hide, parallel hazards, and the five axes briefly.
- *Exit adds:* the Scope's Exit, every Covers ID tested, no stub, real providers in system tests, no drift between a provider and its double, and the slow and perf tests run (`-m slow`, `-m perf`) within the Bash time limit.

**Simplicity** has two failure directions, and the reviewer checks both:
- *Too much structure:* abstractions with one implementation, forwarding wrappers, one-method classes, parameters every caller sets the same, defensive `try/except` and type re-checks, loops the library provides (CR-11, CR-12).
- *Too little sharing:* near-copies of one concept. Parallel builders can't see each other's worktrees, so duplication across sibling tasks is structural, and the phase review is where all the copies are in view. A finding names the simpler form; its fix task (build-planning Replan) puts one function in the owning module. Tests may repeat for readability.
- CR-42 measures it: pylint `duplicate-code` on source, ≥ 8 similar lines, in `check.sh full`, must not grow; `floor_guard` catches the ways to silence it. The implementer prompt adds prevention: a function unless state persists, no parameter without a caller that varies it, grep for a helper before writing one.

**Mutation check.** The reviewer proves tests can fail by breaking the behaviour on purpose, in its own linked worktree (it checks `git rev-parse --git-dir` differs from `--git-common-dir`, else it skips the check and says so): per acceptance bullet or TC case, the smallest change that should break it (flip a comparison or boundary, drop a formula term, return the baseline, remove a guard, skip a side effect, unseed a generator, swap same-typed arguments), the covering tests run with every marker (`-m ""`, so a slow-marked test isn't silently deselected), the file restored. If no test ran, the finding is "untested", never "survived". At most 10 per review. Severity: Critical only when an intent test misses a mutation that changes its TC's expected output; any other survivor, including a possibly equivalent mutant, is Important with the mutant shown. Breadth comes later from `mutmut` on the changed lines at milestone exit, as a measured metric (§15).

**Findings.** A worktree agent's Write tool can't reach outside its worktree or into `.claude/` (verified, §12), so the reviewer writes its finding lines to a gitignored `.dt/review.md` in its worktree, runs `dt build submit-review <checkpoint>.<pkg> .dt/review.md` (dt copies it to `.git/dt-build/reviews/<checkpoint>.<pkg>.md`), and ends with one status line (`REVIEW <checkpoint> <pkg>: <n> findings, <c> Critical`). The driver runs `dt finding --from <file>`, which records each line under the checkpoint block in `plan.md`, commits that change on the build branch (the main checkout stays clean), and writes the review's outcome (`passed`, `critical`) to `.git/dt-build/reviews/<checkpoint>.<pkg>.json`. `dt ready` reads those outcomes: it holds everything behind an unpassed barrier and stops releasing while a Critical is unresolved; `dt build resolve <finding>` records the user's decision. Important findings get fix tasks through build-planning Replan at the next user gate (a stop or milestone exit), committed on the build branch before dispatch, and run before exit; Suggestions and Nits get one only if the user asks. After exit fix tasks land, the exit review runs again over their landings plus the Milestone exit list.

**Checkpoint placement (changes tasks.md §8).** `### Checkpoint after M<n>-T<nn>` closes each plan phase: after Phase 0, after Phase 1, after Phase 2, and the milestone exit. The Phase 0 block is written `### Checkpoint after M<n>-T<nn> (barrier)`. Each block names the phase's last task in plan order, as now.

---

## 5. The orchestrator

**The main session, running the `build` skill's Run mode, as a low-context driver.** It holds no project content. Each turn it reads `dt` JSON (`ready --reserve`, `land`, `finding --from`, `build status`), spawns agents with one-line prompts, and branches on a reject or escalation kind and on Critical. A background agent's whole final message enters the driver's context when it completes, so every agent is told to end with one status line: builders `DONE <task> <role>` or `STOPPED <task> <role>: see dt escalate` (details in their escalation record), reviewers the `REVIEW` line above. The driver never reads a diff, a packet, a gate log or a findings file itself. That keeps its context to a few lines per landing, so a milestone fits without compaction and a compaction loses nothing.

| | Main session | Generated workflow |
|---|---|---|
| Deterministic steps | Runs `dt` and `git` itself through Bash | No shell in the script; every `dt land` needs a land agent (build-phase-notes §4) |
| Scheduling | Each background agent's completion arrives separately, so halves start as their dependencies land | `pipeline()` can express the DAG, generated by `dt`; equally dataflow |
| Verdicts | `dt land` re-runs the gate and returns its result | Hook output never reaches the script; the land agent's last message carries it |
| Input mid-run | The user can interject; a stop asks in the same session | None; a stop ends the run and a new workflow resumes |
| Context | One short turn per landing (~35 for the rl M1); state on disk survives compaction | Script holds the state |
| Visibility | Transcript and task list | `/workflows` progress view |

The workflow form is kept as an eval arm: `dt build workflow M1` emits a script with one `pipeline()` per task chain and a low-effort land agent per landing.

**Finding `dt` from a subagent.** Agents have no plugin folder and `$CLAUDE_PROJECT_DIR` is empty in their Bash (build-phase-notes evidence, workflow-hooks 3b), so the one-line prompt carries the absolute path the `build` skill resolves from its own folder: *"You are the `<role>` for `<task>`. Run `python3 <abs>/dt.py claim <task> --role <role>`, then read the packet it names."* The reviewer's checklist needs `dt layout` and `dt lint`, so its prompt carries the same path.

**What the orchestrator never does:** write code, edit `tests/`, run git beyond what `dt` runs, write prompts beyond the one-line instruction, paraphrase a report into the plan, or merge by hand. A contract re-freeze (§9) is an interface task run by an `implementer` agent, never the main session; phase0.md's "runs in the main session" changes to match.

The plugin's existing Stop hook only lints and emits a message (`lint.py:1308-1320`); it needs no change for background agents.

---

## 6. `dt` commands

All state lives under `$(git rev-parse --git-common-dir)/dt-build/`: `reserved/`, `claims/`, `gates/`, `escalations/`, `reviews/`, and `log.jsonl`, an append-only event log (reserve, claim, land, reject, escalate, review, resolve) that the eval grader reads.

### 6.1 `dt ready --reserve [--cap N]` (extended)

Lists ready **task halves** and, with `--reserve`, writes a reservation for each before the driver spawns, so a half is never listed twice and the cap counts agents that haven't claimed yet. Row: `{"id", "role": "tester|implementer|solo", "agent_type", "title", "kind", "pkg", "remaining_cp", "prompt"}`; `prompt` is the one-line prompt, so the driver copies nothing by hand.
- A tester half is ready when every interface task among its ancestors has landed, or at once in a milestone with no interface task (matching `graph.tester_ready`).
- An implementer half is ready when its tester half has landed (on its tests branch, §6.3) and every `Depends on` task has landed.
- A solo task is ready when every `Depends on` has landed.
- Nothing is released behind an unpassed barrier checkpoint or while a Critical is unresolved (§4), or for a task marked `**Risk:** external` without the user's recorded yes (§9).
- `--cap N` returns at most N minus reservations and live claims. Sorted by remaining critical path in halves, size-weighted (XS=1, S=2, M=4), so the longest chain starts first when the cap bites. Default cap 6, revisited after the first build eval.

### 6.2 `dt claim <task> --role <role>` (new)

Run by the agent, inside its worktree, as its first action. It:
1. Turns the reservation into a claim; refuses with no reservation, or when the worktree's HEAD lacks a landing it depends on (a stale base fails here, not at merge).
2. For an implementer half, merges the task's tests branch (`dt/<task>-tests`) into the worktree, so the red tests are present and the build branch never held them.
3. Writes `.claude/.task_writes` (the role's share of `Writes:`: tester the `tests/intent/` paths, implementer the rest, solo all) and `.claude/.check_pkg` (the task's package, so the Stop gate runs `gate --pkg`, not every package).
4. Sets `refs/worktree/checks-base` to HEAD: per worktree, so parallel agents never share a base.
5. Links the gitignored inputs the project lists (`worktree-links` in CONSTRAINTS.md, written by build-setup: local data folders, never credentials) into the worktree, since a fresh worktree has none of them.
6. Records the claim (task, role, worktree path, branch, base SHA, time) and writes the packet to `.claude/packet.md`. It prints the packet's path, a few lines of summary, the role's done condition, and, on a re-dispatch, the previous rejection (§7). A packet can reach 2,000 lines, past what a Bash result shows in full, so it is never printed whole.

`.claude/packet.md`, `.claude/.task_writes` and `.claude/.check_pkg` are gitignored by build-setup and never staged.

### 6.3 `dt land <task> --role <role>` (new)

Run by the driver, in the main checkout. It takes a lock in `dt-build/` first, so two landings never interleave even if the driver issues them in parallel. Refuses if the main checkout isn't clean. From the claim record it:
1. **Writes.** Diffs the worktree against its base: committed, uncommitted and untracked. Any path outside the role's `Writes:` (re-derived from the plan, not `.task_writes`), or on the protected list minus the role's own allowance (the tester's intent paths; an interface task's new contract folders, narrowed as `frozen_contracts` does), → **reject `writes`**. An implementer's diff must leave the tester's files exactly as the tests branch has them.
2. **Gate.** Reuses the Stop gate's verdict when `gates/<claim>.json` matches the worktree's tree hash; otherwise runs the role's gate (§3.4) → **reject `gate`**. An escalation record for the claim → **reject `escalated`**, with its kind.
3. **Tester half:** squashes the worktree's diff into one commit on `dt/<task>-tests` (from the build branch head), trailer `Dt-Landed: <task> tester`. Nothing touches the build branch; the half is landed.
4. **Implementer or solo half:** `git merge --squash` into the build branch. A conflict means two tasks wrote one path, a lint gap → `git reset --hard HEAD` (safe: the checkout was clean and the change is dt's own) → **reject `conflict`**.
5. Sets the main checkout's `refs/worktree/checks-base` to the pre-merge HEAD and runs `check.sh gate --pkg <pkg>`. On failure it re-runs the failing tests once: a pass logs a flaky-test finding (Important) and continues; a second failure resets as in step 4 → **reject `integration`**.
6. Commits with the trailer `Dt-Landed: <task> <role>`, the `todo.md` tick, and for a wiring task `dt prebuild-clear` on its pipeline, in one commit.
7. On every outcome: appends to the log, releases the claim, removes the worktree. The branch is deleted after a landing; after a reject the worktree is discarded.

Output: one JSON object `{"landed": bool, "reject": "writes|gate|escalated|conflict|integration|harness|null", "kind": "<escalation kind or null>", "detail_file": "<path>"}`. `harness` means the agent ended without a status line or on an API error: re-dispatched without counting toward a block.

### 6.4 `dt escalate <kind> "<why>"` (new)

Run by an agent that can't finish: `TEST-WRONG` (implementer: an intent test is wrong), `CONTRACT-CHANGE` (tester or implementer: the interface can't express what the task needs), `NEEDS-DEP` (a dependency isn't declared). It writes `escalations/<claim>.json`. `stop_gate.sh` lets an agent with an escalation record stop without passing its gate; without this, the gate blocks it three times and the escalation arrives as `GATE FAILED`.

### 6.5 `dt build start | status | resolve | release` (new)

- `start M<n>`: refuses on a dirty tree; records `**Build:**` in `plan.md`; creates `build/M<n>` from HEAD (the plan's Base precedes the commit that records it).
- `status`: the run's state from `dt-build/` and the trailers: landed, reserved, claimed (with whether its agent finished, §10), ready, blocked (with why), reviews and findings by severity, the next checkpoint.
- `resolve <finding|task>`: records the user's decision on a Critical or a blocked task.
- `release <task> <role>`: drops a reservation or claim the driver has given up on.
- `submit-review <checkpoint>.<pkg> FILE`: run by a reviewer in its worktree; copies its findings file into `reviews/`, which the reviewer's Write tool can't reach.

---

## 7. The loop

```
start   user's go → dt build start M1
loop    rows = dt ready --reserve --cap N
        spawn one background agent per row (its agent_type, isolation: worktree, its prompt), all in one turn
        on each completion (one status line):
            r = dt land <task> --role <role>
            landed     → if a checkpoint's tasks are all landed: dt ready lists its reviewers; spawn them
            gate / writes / conflict / integration
                       → first time: re-dispatch the same half (dt claim prints the rejection)
                         second time: blocked (§9)
            escalated  → §9 by kind
            harness    → re-dispatch; three in a row on one half → blocked
        on a reviewer's completion: dt finding --from <file>
        nothing ready, nothing running → stop and report (all landed → exit)
exit    exit review → fix tasks (Replan, user) → exit review again over their landings → user approves → merge build/M1 → Advance
```

Reviewers are spawned with `isolation: worktree` like builders, so a mutation never touches the main checkout. On the rl M1 with the §3.2 rule: the 3 interface tasks run first; after the interface review, 17 halves are ready (9 solo: T05, T06, T07, T09, T10, T11, T12, T13, T14; 8 testers), dispatched 6 at a time by remaining critical path.

---

## 8. Worktrees and shared state

| Hazard | Rule |
|---|---|
| Shared base ref: `refs/checks/base` is one ref for every worktree (`scripts/check.sh:98-100`) | `refs/worktree/checks-base` everywhere: `dt claim` sets it in a worktree, `dt land` in the main checkout. `check.sh` reads it, else HEAD; the shared fallback goes |
| The `writes` guard fails open when `.claude/.task_writes` is missing (`path_guard.sh:32`) | Fails closed for `tester` and `implementer` agent types: "run `dt claim` first". The main session and other agent types are unaffected |
| Editable installs point at the checkout that installed them, so a shared venv tests the main checkout's code | Each worktree gets its own `.venv` (`uv run --frozen` creates it; the uv cache clones packages). Setup time is measured in the smoke test, torch included |
| Gitignored inputs (local data, `.env`) don't exist in a fresh worktree | `dt claim` links the `worktree-links` paths; credentials are never linked, and a task needing them is `**Risk:** external` (§9) |
| Fixed output paths collide between parallel smoke tests (`/tmp/x.mp4`, `runs/`) | Tests write under `tmp_path`; the reviewer flags a fixed path; Verify lines name a temp directory |
| `uv.lock`, `pyproject.toml`, `__init__.py`, `types.py` | Protected or interface-owned; a builder needing a change escalates (`NEEDS-DEP`, `CONTRACT-CHANGE`) |
| Chained git in one Bash call refused in worktrees (build-phase-notes §4) | Agent files say: one git command per call |
| Slow and perf tests deselected by `addopts` (rl: `-m 'not slow and not perf'`) | `red_check.py` and the reviewer's mutation runs pass `-m ""`; `dt land` runs the task's own intent tests with every marker; the exit review runs `-m slow` and `-m perf` |
| `tests/contracts` never runs (`check.sh` `test_dirs` covers `tests/intent` and `tests/unit` only) | `gate` and `full` run `tests/contracts` too, so samples, fakes and doubles are checked when the interface lands and after |
| Background agents' un-allowed commands are denied, and every worktree agent reads the main checkout's `.claude/settings.json` (verified, §12) | build-setup writes allow rules there for `uv run`, `git`, `scripts/check.sh` and the `dt` path; the build runs in `acceptEdits`. The main checkout's copy is the one that must stay protected. The rules apply only in a trusted folder: headless runs and evals pass them with `--allowedTools` |
| A worktree agent's Write tool can't write outside its worktree, nor into `.claude/` (verified, §12) | Anything an agent hands to `dt` sits in a gitignored `.dt/` in its worktree; `dt`, a process, moves it (`submit-review`) |
| Worktree base | Agent-tool worktrees branch from the main checkout's HEAD (verified, §12). `dt claim` still checks the base |

---

## 9. Stopping and escalation

Independent work **drains, never stops mid-task**: when a half blocks, its dependents aren't released, in-flight agents finish and land, and the driver stops and reports once nothing else is ready or running.

| Condition | How it arrives | What happens |
|---|---|---|
| A test can't pass / the build breaks | `reject gate` or `integration` twice | Blocked; user. The detail file has both outputs and the dependents |
| An intent test is wrong | `escalated` `TEST-WRONG` | Blocked; the user decides. On their yes, `dt build resolve` reopens the tester half, a fresh tester rewrites the test, never a fixture or expected value (`dt guard` handles any `expected.json` change). No intent test changes without the user |
| The interface can't express what the task needs | `escalated` `CONTRACT-CHANGE` | Every half reading that interface stops; architecture-design Revise, then a re-freeze interface task (run by an `implementer` agent) through build-planning Replan; user approves both |
| A dependency isn't declared | `escalated` `NEEDS-DEP` | Drain everything in flight; build-setup Extend on the build branch at a user gate (`pyproject.toml`, `uv.lock`); new worktrees start from the new head |
| High-risk or irreversible | `**Risk:** external` on the task (credentials, network writes, anything outside the repo) | Not released on the go alone; the user's yes is recorded with `dt build resolve` |
| Writes or conflict | `reject writes` or `conflict` | Re-dispatched once with the rejected paths; a `conflict` is also logged as a plan-lint gap; a second time → blocked |
| Critical finding | A reviewer's file | User; `dt ready` stops releasing, in-flight work drains |
| Harness failure | `reject harness` | Re-dispatched; not counted, unless it repeats three times on one half |

---

## 10. Resume

Everything the driver knows is under `dt-build/` or in the build branch's `Dt-Landed:` trailers (never commit subjects, which an agent could imitate), `todo.md` ticks, findings in `plan.md`, and the go (`**Build:**`).

**Liveness.** A `SubagentStop` hook in the plugin's `hooks.json` (it sees `agent_type` and the worktree as `cwd`) marks the claim in that worktree `finished`. So after a compaction, a claim not yet finished belongs to a running agent and is left alone.

On restart (Resume mode, a new session, so no agent of the old one is running), `dt build status` and:
- **Claim finished:** `dt land` it. The gate re-runs, so finished work isn't lost.
- **Claim not finished, or a reservation:** the agent died with the old session: `dt release` and re-dispatch (tasks are XS or S).
- **Tester landed, implementer not:** the implementer half is simply ready.
- **Barrier, Critical, blocked:** as recorded in `reviews/` and `escalations/`; stays until resolved.
- **Approval:** the recorded go stands for this milestone and this plan version; a Replan since the go needs a new one.

---

## 11. User gates

1. **Go**, once per milestone, after `dt status` shows the plan Approved and build-setup's bar current.
2. **Interface review** by an agent. Its Critical findings, like every stop in §9, come to the user.
3. **Stops** (§9), each recorded with `dt build resolve`.
4. **Milestone exit:** the exit review's findings, their fix tasks and the second exit review, the Definition of Done, the Scope's Exit line, and the user's yes before `build/M1` merges.

---

## 12. Before building: smoke tests

**Verified** (build-phase-notes §4; [evidence/2026-10-17-build-smoke.md](evidence/2026-10-17-build-smoke.md), Claude Code 2.1.296, $0.97):
- Hook `cwd` is the worktree and `$CLAUDE_PROJECT_DIR` the main checkout; plugin and agent-file hooks fire in worktree and background agents; chained git is refused in worktrees; a `schema` agent skips its gate; per-worktree refs (`refs/worktree/*`, git 2.48).
- Worktree agents load the **main checkout's** `.claude/settings.json` from disk, not the worktree's copy.
- Agent-tool worktrees branch from the main checkout's HEAD (the build branch, not the default branch).
- A worktree holding only new, untracked files is kept; an unchanged one is removed. A kept worktree's path and branch come back with the agent's result.
- A subagent runs `dt` by absolute path and reads a 2,100-line packet file in full.
- In `-p`, a background agent's command with no allow rule is denied, not asked; `--allowedTools` rules reach subagents; `acceptEdits` accepts writes inside the worktree; a guard's `ask` becomes a denial.
- With the sandbox on, a worktree agent writes under the git common dir (the session's cwd, the repo root, contains it).
- SubagentStart and SubagentStop carry the agent's worktree as `cwd`, so the liveness hook finds its claim.
- A per-worktree venv takes 0.35–0.9 s from a warm uv cache, torch included; the first torch import ~6 s.
- `claude -p` waits for background agents and resumes the main agent on each completion, with one `result` event per main turn.

**Verified by a live build** ([evidence/2026-10-17-live-build.md](evidence/2026-10-17-live-build.md), buildmini M1, five runs, $2.85): a split task end to end with the build branch never red (the tester's tests reach `build/M1` only in the implementer's landing); two worktree agents in parallel, landed one after the other under the lock; the merged-tree gate catching a real integration error; retries on `writes` and `integration` rejects; the Stop gate's verdict reused at land; the interface and exit reviews recorded through `submit-review`. The runs also showed that project allow rules apply only in a trusted folder, and that worktree agents can't Write outside their worktree or into `.claude/`.

**Still to verify:** in the interactive app, how a background agent's permission prompt, or a guard's `ask`, surfaces.

---

## 13. What iteration 8 shows about the plan

`dt status` on the rl M1: 23 tasks, 7 waves, width 12, parallelism 3.29, critical path M1-T02 → T10 → T17 → T18 → T19 → T20 → T23 (7). Plan-side causes:

| Cause | Fix | Effect |
|---|---|---|
| T18, T19, T20 (wire PL-15, PL-16, PL-17) all write lab `pipeline.py`, so they chain by `file` edges; T15 and T16 do the same on worlds `pipeline.py` and `__main__.py` | Each pipeline's wiring writes its own entry module; the package's `__main__.py` dispatch is written by the interface task (phase0.md) | The wiring tasks run side by side |
| T18 waits on T17 because `learn.train` has no fake, though phase0.md already asks for fakes on cross-package calls | A `dt lint` rule: a `call` edge marked `none` where the callee is a contract symbol needs a fake or a reason | Lab wiring leaves the learn chain |
| The Mode rule (§3.2) | As above | 5 tasks no longer blocked; 8 testers in the first wave |

With the first two, T23 reaches T17 only through T18, so T23's `Depends on` must name T17 directly (it runs the real chain). The critical path then counts 4 in whole tasks, and 5 in the halves that are actually dispatched, since T04, T08 and T22 run tester then implementer: T01 → T04t → T04i → T15 → T23, and T02 → T08t → T08i → T17 → T23. `dt status` reports it in halves and gains a warning for `file` edges on the critical path, since each is a planning choice.

---

## 14. Answers to build-phase-notes §5

| # | Question | Answer |
|---|---|---|
| 1 | Wrap or replace `/build` | Replace, for planned milestones: a dev-team `build` skill (§0). agent-skills `/build` stays for unplanned work |
| 2 | Who orchestrates | Main session as a low-context driver (§5); packets unparaphrased through `dt claim` (§6.2); between tester and implementer the tests land on a side branch, red for the right reason, and the implementer's claim merges them (§6.3) |
| 3 | Wrong or unsatisfiable intent test | `dt escalate TEST-WRONG` → the user decides → a reopened tester half; oracle files only through `dt guard` (§9) |
| 4 | What the tester writes against | The frozen interface (interface-first-design §4.3, §7) |
| 5 | Parallel groups | Dataflow from `dt ready`, worktree per half, landed one at a time under a lock, in completion order rather than interface-first-design §6.4's plan order, since `Writes:` are disjoint (§6–§8) |
| 6 | Findings into the plan | `dt finding --from`; fix tasks through build-planning Replan at the next user gate; Critical stops (§4) |
| 7 | Resume in split mode | From `dt-build/`, `Dt-Landed:` trailers and the liveness marker (§10) |
| 8 | Stop conditions | §9 |
| 9 | Reviewer independence | Fresh context, reads the diff and the contract, never the builders' reports; same model by default, a different model is an eval arm |
| 10 | Guard ownership | The plugin's `hooks.json` keyed by `agent_type` (build-phase-notes §4 rec. 1), with the agent files' frontmatter hooks as backup |

---

## 15. Decisions and follow-ups

**Decided (2026-10-17):** the review runs per phase, plus a barrier interface review (§4); the main session is the orchestrator, as a low-context driver (§5); the interface review is a reviewer agent that checks the interface code against the approved contract, and later phases check that interfaces were followed (§4); the reviewer mutation-checks tests in its own worktree; simplicity is a review item with a duplicate-code metric (CR-42).

**Decided:** PURPOSE says "reviewers that land nothing", since the mutation check edits files in the reviewer's worktree.

**Defaults to revisit after the first build eval:** the concurrency cap (6); one retry before blocking; three harness failures; Important findings waiting for the next user gate; the mutation cap (10 per review); the ~1,000-line reviewer split.

**Eval arms** (interface-first-design §9.2 plus): per-task review vs per phase (defects found, tokens, wall clock); a generated workflow vs the main-session driver (wall clock, harness failures, lost verdicts). The grader reads `dt-build/log.jsonl` and maps work to tasks by `Dt-Landed:` trailers, not by `worktree-*` branch names or `M1-Tnn:` subjects (which changes interface-first-design §9.2's integration metrics).

**Follow-up:** `mutmut` on the changed lines at milestone exit as a measured metric beside CR-40–CR-42.

---

## 16. Changes by file

| Where | Change |
|---|---|
| `PURPOSE.md` | Done: reviewer wording (§15) |
| `skills/build` (new) | `SKILL.md`: the orchestrator's role, the docs it writes (`todo.md` ticks, findings, `**Build:**`, through `dt`), what it never does, mode table. `references/run.md` (a milestone, §7), `task.md` (one task in the foreground, for debugging), `resume.md` (§10), `exit.md` (exit review, fix tasks, the merge); topic reference `escalation.md` (§9) |
| `skills/build-planning/references/tasks.md` | §7 Mode rule and `mode:` Reason (§3.2); §8 checkpoints at phase ends, `(barrier)` on Phase 0 (§4); `**Risk:** external`; unit-test path in every implementer and solo `Writes:` |
| `skills/build-planning/references/phase0.md` | Per-pipeline entry modules; `__main__` dispatch owned by the interface task; the re-freeze runs as an interface task by an `implementer` agent, not in the main session |
| `scripts/devteam/status/build_planning.py`, `commands/lint.py` | `expected_mode` per §3.2 with `mode:` Reasons; `writes-unit`; `call` edges marked `none` on a contract symbol; warning for `file` edges on the critical path; critical path in halves |
| `scripts/devteam/commands/ready.py` | Task halves, `--reserve`, `--cap`, remaining-critical-path order, barrier, Critical and Risk holds, the `prompt` field (§6.1) |
| `scripts/devteam/commands/` `claim.py`, `land.py`, `escalate.py`, `build.py` (new); `finding.py` | §6.2–§6.5; `dt finding --from <file>` commits on the build branch and records the review outcome; `dt build workflow` (eval arm) |
| `hooks/hooks.json` | Role guard keyed by `agent_type` (§14 row 10); `SubagentStop` liveness marker (§10) |
| `skills/build-setup/templates/scripts/` | `check.sh`: `refs/worktree/checks-base` only, `tests/contracts` in `gate` and `full`. `path_guard.sh writes` fails closed for builder agent types. `stop_gate.sh` lets an agent with an escalation record stop, and writes its verdict with the tree hash. Done: `red_check.py` judges every marker |
| `skills/build-setup/templates/` agent files | Tester and implementer: the one-line prompt contract (`dt claim`, read the packet file), `dt escalate`, one status line at the end, one git command per call. Reviewer: findings to the file the prompt names, one `REVIEW` status line. Done: the reviewer's slice, lead flag, worktree check, mutation rules and severity; the implementer's simplicity rules |
| `skills/build-setup/templates/CONSTRAINTS.md` | `worktree-links`; the Roles text that still says the orchestrator writes `.claude/.task_writes` and sets `refs/checks/base` (now `dt claim`); the Review intro's `dt land` once it exists. Done: the Review section (§4), CR-42 |
| `skills/build-setup/templates/` other | `.claude/settings.json` allow rules for background agents; `gitignore.additions`: `.claude/packet.md`, `.claude/.task_writes`, `.claude/.check_pkg`. Done: pylint in `pyproject*.toml`, `check.sh full`, `floor_guard.py`'s pylint loopholes, `references/tools/pylint.md`, new/extend/ratchet/SKILL notes |
| `skills/build-setup/references/new.md`, `design/build-setup.md` §4, §6, §7 | `refs/checks/base` → per-worktree; reviewer wording; checkpoints per phase rather than every 2–3 tasks; Critical stops the build rather than blocking the next checkpoint |
| `evals/harness/` | Build-eval arms of interface-first-design §9.2, plus the §15 arms; `grade_build.py` reads `dt-build/log.jsonl` and `Dt-Landed:` trailers |
