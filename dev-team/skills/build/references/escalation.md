# Stops and escalations

Read with every mode that drives the loop. A stop drains, never interrupts: in-flight agents
finish and land, `dt ready` holds back what the stop affects, and the driver reports once nothing
is ready or running (`loop.md`, Draining and stopping). Every user decision is recorded with
`dt build resolve <finding|task> --note "<the user's words>"`; a decision said in chat and not
recorded doesn't exist for a resumed build.

## By condition

| Condition | Arrives as | Do |
|---|---|---|
| A test can't pass, or the build breaks | `reject` `gate` or `integration` a second time on one half | Blocked. Report the task, its dependents held back and the `detail_file` (both outputs). The user decides: a Replan, a bar change through `build-setup` Revise, or a retry (`dt build resolve <task>`) |
| Writes outside the task, or a merge conflict | `reject` `writes` or `conflict` a second time | Blocked, as above. A `conflict` means two tasks claim one path: a plan gap for `build-planning` Replan, whatever the user decides |
| An intent test is wrong | `escalated`, `kind` `TEST-WRONG` | Blocked. Give the user the implementer's one-line reason from `dt build status` and the `detail_file` path; never judge it yourself. On their yes, `dt build resolve <task>` reopens the tester half and a fresh tester rewrites the test, never a fixture or expected value (oracle changes go through `test-planning` and `dt guard`). A no means the test stands: `dt build resolve <task> --test-stands --note "<their words>"` keeps the tests and retries the implementer, whose claim prints the decision |
| The interface can't express what a task needs | `escalated`, `CONTRACT-CHANGE` | Every half reading that interface is held. After the drain: `architecture-design` Revise, then `build-planning` Replan adds a re-freeze interface task (run by an `implementer` agent, its `Writes:` naming the frozen folders); the user approves both, each committed on the build branch, then the loop resumes |
| A dependency isn't declared | `escalated`, `NEEDS-DEP` | Drain everything in flight. `build-setup` Extend adds it on the build branch (`pyproject.toml`, `uv.lock`) with the user's yes; new worktrees start from the new head |
| High risk or irreversible | a `**Risk:** external` task `dt ready` never lists | At the go or when it is next, ask; on a yes, `dt build resolve <task>` |
| Critical finding | a `REVIEW` line with Critical above 0 | `dt ready` stops releasing. After the drain, show the Critical lines (`dt build status`) and ask: a fix task through `build-planning` Replan, or the user's override, recorded with `dt build resolve <finding>` |
| Harness failure | `reject` `harness` three times in a row on one half | Blocked: report it as a harness problem (permissions, API), not the task's |

Important findings wait for the next user gate (a stop or Exit), where `build-planning` Replan
turns them into fix tasks, committed on the build branch before dispatch. Suggestions and Nits get
one only if the user asks.

## Reporting a stop

One message, then end the turn:

```
Build M1 stopped: nothing else can start until you decide.
Landed 12/19 halves. Running: none.
Blocked: M1-T17 implementer: TEST-WRONG (details: .git/dt-build/escalations/M1-T17.json).
  Held back: M1-T18, M1-T23.
Decide: rewrite the intent test (a fresh tester), or keep it and retry the implementer?
```

The user's answer is recorded first (`dt build resolve`), then the skills it calls for run, each
through its own gate, and the loop resumes with `dt ready`. The go covers one plan version: after a
Replan, `dt ready` holds everything (`go:`) until the user's new go, recorded with
`dt build go --note "<their words>"`. Never resume on a hedge.

## Never

- Edit a test, a fixture, the bar or the contract to get past a stop.
- Re-dispatch a blocked half without a recorded decision.
- Read a gate log, a diff or a findings file to decide for the user: show the `detail_file` path
  and the status lines, and let `dt build status` summarise.
