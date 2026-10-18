# The dispatch loop

Read with Run, Resume and Exit. Stops go to `escalation.md`.

Work is dataflow, not waves: a task half starts the moment what it needs has landed, and `dt`
decides what that is. The driver only spawns what `dt ready` lists and lands what finishes.

## Dispatch

```
python3 ../../scripts/dt.py ready --reserve --cap 6 --json
```

It prints one object: `rows` to spawn, `held` (halves waiting, each with its `why`), `holds`
(why nothing is released: a Critical or an escalation, `escalation.md`) and `all_landed`. Each row
is `{id, role, agent_type, title, kind, pkg, remaining_cp, prompt}`, already reserved and ordered
by remaining critical path. The cap counts reservations and live claims, so asking again
after every completion fills only the free slots. The user may set another cap; keep it for the run.

Spawn every row in **one message**, one Agent call each:

| Agent field | Value |
|---|---|
| `subagent_type` | the row's `agent_type` (`tester`, `implementer`, `reviewer`) |
| `isolation` | `worktree` |
| `run_in_background` | `true` |
| `description` | `<id> <role>` |
| `prompt` | the row's `prompt`, verbatim: one line naming the task, the role and the `dt` path |

Rows with `agent_type` `reviewer` are checkpoint reviews: `dt` lists them once a checkpoint's
tasks have all landed (each package with changes, one marked lead). Spawn them the same way; their
worktrees keep their mutations out of the main checkout.

Before spawning, nothing else: no reading the task, the packet or the plan. The agent runs
`dt claim`, which writes its packet, its edit list and its base in its own worktree.

## Landing

Each completion arrives on its own, as the agent's last message. Act on its status line
(`../SKILL.md`, Status lines), one landing at a time, in completion order:

| Line | Run | Then |
|---|---|---|
| `DONE <task> <role>` or `STOPPED <task> <role>: …` | `dt land <task> --role <role>` | branch on the JSON below |
| `REVIEW <checkpoint> <pkg>: …` | `dt finding --from <reviews>/<checkpoint>.<pkg>.md --checkpoint <checkpoint> --pkg <pkg>`, where `<reviews>` is `$(git rev-parse --git-common-dir)/dt-build/reviews` | a Critical count above 0 → `escalation.md`, Critical. No findings file (the reviewer couldn't write it) → `dt build release <checkpoint>.<pkg> reviewer` and dispatch again; a second time is a stop (`escalation.md`, harness) |
| anything else | `dt land <task> --role <role> --harness` | the half goes back to `dt ready` |

`dt land` prints `{landed, reject, kind, detail_file}`:

| Result | Do |
|---|---|
| `landed: true` | dispatch again |
| `reject` `gate`, `writes`, `conflict`, `integration` | dispatch again: a first rejection comes back as a ready half whose claim prints it to the new agent; a second one blocks the half (`escalation.md`) |
| `reject` `escalated` | `escalation.md`, by `kind` |
| `reject` `harness` | dispatch again; the third in a row on one half blocks it |

Never re-read the agent's message for more, never fix anything yourself, never retry a land by hand.

## Draining and stopping

A stop never interrupts an agent mid-task. While a stop is pending, keep landing the agents still
running and keep dispatching whatever `dt ready` still lists (it holds back what the stop
affects). When nothing is ready and nothing is running:
- **every task landed** and the exit review recorded → Exit (`exit.md`);
- otherwise, report the stop (`escalation.md`) and end the turn.

After a compaction in the same session, run `dt build status`: a claim not yet finished belongs
to a running agent; leave it and wait for its completion. A finished claim nobody landed gets
`dt land` now.

## The task list

Keep one item per running half (`<id> <role>`), ticked when it lands or blocks, so the user sees
the build move without reading the transcript.
