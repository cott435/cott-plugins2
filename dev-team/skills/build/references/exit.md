# Exit

Read when every task of the milestone has landed. The exit review, its fix tasks, a second exit
review over them, the user's yes, the merge. Each user gate ends a turn; run `dt build status` at
the start of each turn to see where you are. The loop is `loop.md`; stops are `escalation.md`.

```
exit review → findings → [fix tasks: build-planning Replan, the user] → loop → exit review again
  → [the user's yes] → merge build/M<n> → build-planning Advance
```

## Steps

**1. Exit review.** Once the last task lands, `dt ready` lists the exit reviewers (one per
package with changes over the milestone diff, one lead; code a checkpoint already reviewed isn't
reviewed again), which run the Milestone exit list too:
the Scope's Exit, every Covers ID tested, no stub left (`check.sh full --exit`), real providers in
system tests, the slow and perf tests. Spawn and record them as `loop.md` says. A Critical is a
stop (`escalation.md`).

**2. Fix tasks.** With the review recorded, show `dt build status`'s findings by severity and
point to the checkpoint blocks in `tasks/plan.md`. Important findings get fix tasks; Suggestions
and Nits only if the user asks. The tasks come from `build-planning` Replan, through its own gate;
on its approval it commits the plan on the build branch. The go covers one plan version, so ask
for it again for the fix tasks and record it with `dt build go`, then run the loop until they land. No findings needing a task:
step 4.

**3. Exit review again.** After the fix tasks land, `dt ready` lists the exit reviewers again,
over the fix tasks' landings plus the Milestone exit list. Record them as before. New Important
findings go back to step 2; repeat only with the user's yes, and say how many rounds have run.

**4. The user's yes.** One message, then **stop the turn**:
- the exit review's findings and each one's disposition (fix task landed, or won't fix and why);
- the Definition of Done (CONSTRAINTS.md, Done: the full list) and the Scope's `**Exit:**` line,
  each held or not, from the reviewers' lines;
- what merges: `build/M<n>` into the branch the build started from, with the landing count.

| The user says | Do |
|---|---|
| An unambiguous yes ("merge it") | Step 5 |
| A change, or a hedge ("looks fine I guess") | Not a yes. Ask what to change; a fix is a Replan (step 2) |

**5. Merge.** The one git the driver runs itself, only after that yes, from a clean main
checkout: `git switch <the branch the build started from>`, then `git merge --no-ff build/M<n>`,
each in its own Bash call. A conflict: `git merge --abort`, report it, stop. Never push. Then
`dt build prune`: it deletes the tests branches and the rejected halves' branches and worktrees.

**6. Hand on.** Say the milestone is built and merged, and that the next step is
`build-planning` Advance (exit checkpoint, archive), which offers `build-setup` Ratchet. Stop.

## Example: the gate message

```
M1 is built: all 14 tasks and fix task M1-T15 landed; the exit review ran twice.
Findings: M1-R04 Important (duplicate window loop in profile/fourier.py and profile/spectrum.py)
  → fix task M1-T15, landed; M1-R05 Nit (column names) → won't fix: matches the utility's notation.
Definition of Done: held. Exit: "the Fourier profile and the residual spectrum run on 10y of hourly
  load; TC-01–TC-03 pass": held (exit review).
Merge build/M1 (15 task landings) into main?
```
