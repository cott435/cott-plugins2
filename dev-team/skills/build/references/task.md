# Task

Read when the user asks to run one task, or one half of it, in the foreground: to watch it, or to
debug a half that keeps being rejected. It uses the same `dt` steps as the loop, one agent at a
time, and never edits anything itself. Stops are `escalation.md`.

## Steps

**1. Check.** `dt build status`: a build must be recorded for the milestone (the go); without
one, this is Run's question first (`run.md`'s message, for one task). The half must be ready or
blocked: one still waiting on a dependency or behind the barrier can't run, so say what it waits
for and stop. A blocked half runs only after the user's decision is recorded
(`dt build resolve <task>`).

**2. Reserve.** `dt ready --reserve --cap 1 --json` and find the row for that task and role. If
`dt ready` lists another half first, release it (`dt build release <task> <role>`) and ask again;
never write a prompt by hand.

**3. Run in the foreground.** One Agent call: the row's `agent_type`, `isolation: worktree`,
`run_in_background: false`, its `prompt` verbatim. The user watches the agent's work in the
transcript; the driver still acts on its status line alone.

**4. Land.** `dt land <task> --role <role>` (with `--harness` when the agent ended without a
status line). Report the JSON as it stands: landed, or the rejection with its `kind` and
`detail_file`. When the user wants to see why, read the `detail_file` to them; this is the one
mode where the driver opens one, and only on that request.

**5. Stop.** One task per request. A split task's other half is a second request, and a full
build is Run or Resume. A rejection or escalation is handled as `escalation.md` says, with the
user deciding now.

## Example

> User: "Run M1-T11's implementer alone, I want to see why it keeps failing the merged gate."

```
$ dt build status                          → M1-T11 implementer: blocked (integration ×2)
```

> M1-T11 implementer is blocked after two integration rejections. Retry it once in the
> foreground? That records your decision with `dt build resolve M1-T11`.

User: "Yes." Then `dt build resolve M1-T11`, reserve, one foreground implementer, `dt land`:

```
{"landed": false, "reject": "integration", "kind": null, "detail_file": ".git/dt-build/gates/M1-T11.implementer.log"}
```

> Rejected again: the merged-tree gate fails (details in `.git/dt-build/gates/M1-T11.implementer.log`).
> Want me to read it to you?
