# Run

Read when `dt build status` shows no build for the active milestone. It starts one and drives it
until a stop or the milestone exit. The loop is `loop.md`; stops are `escalation.md`.

```
CHECK → [the user's go] → dt build start M<n> → loop.md → stop (escalation.md) or Exit
```

## Steps

**1. Check, then ask.** `dt status` shows the plan `Approved` with its `**Base:**` set, and
`dt status --skill build-setup` says `current`; the working tree is clean. Then ask for the go in
one message: the milestone, its task and half counts, the critical path and widest wave from
`dt status`, the concurrency cap (default 6), each `**Risk:** external` task (it waits for its own
yes), and that the build runs on its own from here until a stop or the exit. **Stop the turn.**

| The user says | Do |
|---|---|
| An unambiguous yes ("go", "build it") | Step 2 |
| A yes with a change (another cap, a task held back) | Make it, say so, step 2 |
| A hedge, or anything else | Not a go. Answer, ask again |

No live user: there is no go. Report what is ready and stop.

**2. Start.** `dt build start M<n>`. It refuses on a dirty tree; otherwise it creates and
switches to `build/M<n>`, the branch every worktree starts from and every landing commits to, and
commits the go there as `**Build:**` in `tasks/plan.md`. A refusal is reported as it stands; fix nothing yourself.

**3. Interface first.** The first `dt ready` lists only the interface task(s). After they land,
the interface review runs as a barrier, which `dt` adds when the plan has none, and the testers
run beside it: no implementer or solo half starts until the review is recorded as passed. A
Critical there is a stop like any other.

**4. Loop** (`loop.md`) until it ends: Exit when every task has landed and the exit review is
recorded, otherwise a stop reported per `escalation.md`.

## Example: gridload M1

```
Ready to build M1 Ingest & clean: 14 tasks, 19 halves (5 split), critical path 4, widest wave 11.
Cap 6 agents at a time. No task needs credentials. From your go it runs on its own until a stop
or the exit review, and the merge waits for you. Build M1?
```

User: "Go." Then:

```
$ dt build start M1
$ dt ready --reserve --cap 6 --json      → M1-T01 solo (implementer)
  spawn 1 agent
  … DONE M1-T01 solo → dt land → landed
$ dt ready --reserve --cap 6 --json      → M1-T01.gridload reviewer (barrier, lead), T11 tester, T12 tester, …
  … REVIEW M1-T01 gridload: 2 findings, 0 Critical → dt finding --from …/reviews/M1-T01.gridload.md
$ dt ready --reserve --cap 6 --json      → T05 solo, T02 solo, … (the free slots)
```

Each later turn is one completion and one landing, a few lines each.
