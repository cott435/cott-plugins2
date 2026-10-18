# Resume

Read when a build is recorded and this session has started no agents: a new session after a
stop, a crash or a closed terminal. No agent of the old session is still running, so every claim
is either finished work to land or a dead agent's to release. The loop is `loop.md`; stops are
`escalation.md`.

Everything the driver needs is on disk: `dt-build/` under the git common directory, the
`Dt-Landed:` trailers on `build/M<n>` (never commit subjects, which an agent could imitate), the
`tasks/todo.md` ticks, the findings in `tasks/plan.md` and the recorded go. Nothing from an
earlier conversation counts, approvals least of all.

## Steps

**1. Read the state.** `dt build status`. The main checkout must be on `build/M<n>` and clean; if
not, report it and stop (never stash, reset or switch yourself).

**2. Check the go.** It stands for this milestone and this plan version. If the plan's
`**Last updated:**` is later than the go (`go` in `dt build status`), a Replan came since: ask for
a new go (what changed, the halves left) and stop the turn until it comes.

**3. Reconcile, one row at a time:**

| `dt build status` shows | Do |
|---|---|
| a claim marked finished | `dt land <task> --role <role>`: the gate re-runs if no verdict matches, so finished work isn't lost. Branch on the result as `loop.md` says |
| a claim not finished, or a reservation | its agent died with the old session: `dt build release <task> <role>`; the half comes back through `dt ready` (tasks are XS or S, so redoing is cheap) |
| a tester half landed, its implementer not | nothing: the implementer half is ready |
| a review reserved but not recorded | `dt build release <checkpoint>.<pkg> reviewer`; `dt ready` lists the review again |
| a barrier unpassed, a Critical open, a half blocked | stays until the user decides (`escalation.md`); report it with the rest |

**4. Report, then continue.** One message: what landed before, what was re-landed or released
now, what is blocked and the decision it needs. With a decision pending and nothing ready, end the
turn there. Otherwise run the loop (`loop.md`).

## Example

```
$ dt build status
M1 · go recorded 2026-10-18 (plan unchanged) · landed 9/19 halves
claims: M1-T11 implementer finished · M1-T12 tester not finished · M1-T13 tester reserved
blocked: none · reviews: M1-T01.gridload passed · next checkpoint: after M1-T07

$ dt land M1-T11 --role implementer      → landed
$ dt build release M1-T12 tester
$ dt build release M1-T13 tester
```

> Resumed M1: 10/19 halves landed (M1-T11 implementer just now); M1-T12 and M1-T13 testers
> released, their agents died with the last session. Nothing blocked. Dispatching.
