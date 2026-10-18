---
name: build
description: Builds the approved milestone with parallel agents - the main session drives dt, spawning tester, implementer and reviewer agents in worktrees with one-line prompts, landing each through dt land, stopping on escalations, Critical findings and the milestone exit. Use when the user says "build the milestone", "start the build", "resume the build" or "run M1-T04 alone", when the plan and bar are approved and the user gives the go, or when every task has landed and the exit review is due.
---

# Build

This skill builds one milestone from the approved plan and bar. The main session is the
**driver**: it holds no project content, reads only `dt` JSON and the agents' status lines, and
decides only what to do with a rejection, an escalation or a Critical finding. `dt` carries every
deterministic step (pick, claim, gate, merge, tick), and the agents do the work in their own
worktrees.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project
root. Run state lives under `$(git rev-parse --git-common-dir)/dt-build/`, never committed.

**Not for:** planning, the bar or code outside a planned task (`build-planning`, `build-setup`,
agent-skills' `/build`).

## Documents and IDs

- **Writes only through `dt`:** `**Build:**` in `tasks/plan.md` (`dt build start`), the
  `tasks/todo.md` ticks and landing commits on `build/M<n>` (`dt land`), the findings under each
  checkpoint block (`dt finding`, which creates the `M<n>-R<nn>` IDs) and the user's decisions
  (`dt build resolve`). It creates no IDs itself.
- **One command per Bash call:** every `dt` call on its own, never chained with `;`, `&&` or a
  variable, so each matches its allow rule.
- **Never:** writes code or edits `tests/`; edits `tasks/`, a doc or the bar by hand; runs git
  beyond what `dt` runs, except the merge after the user's yes (`references/exit.md`); reads a
  diff, a packet, a gate log, a findings file or an agent's report beyond its status line (except
  a `detail_file` the user asks to see in Task mode); writes an agent prompt other than the row's
  `prompt`, verbatim; paraphrases a report into the plan; re-freezes a contract itself (an
  interface task, run by an `implementer` agent, does).
- **The go is the user's**, once per milestone and plan version, said in this session or
  recorded by `dt build start`. Never infer it from an earlier conversation or an approval of the
  plan or bar.

## Status lines

Every agent ends with one status line, and the driver acts on that line alone: the last
non-empty line of the agent's final message; text above it is ignored, never read.

| Agent | Line |
|---|---|
| tester, implementer, solo | `DONE <task> <role>` or `STOPPED <task> <role>: see dt escalate` |
| reviewer | `REVIEW <checkpoint> <pkg>: <n> findings, <c> Critical` |

A final message whose last line is none of these (an API error, a report with no line) is a
harness failure: land it with `--harness` and read nothing more. Details live where `dt` reads them: escalation records,
recorded gate verdicts, findings files. The driver's own reports to the user are just as short:
what landed, what is blocked and why, the decision needed, and the `detail_file` path for anyone
who wants more.

## Modes

Run `dt build status` first. It reports the milestone, whether the go is recorded, landed,
reserved and claimed halves (each claim finished or not), ready and blocked halves with why,
reviews and findings by severity, and the next checkpoint.

| Mode | When | Do |
|---|---|---|
| blocked | the plan isn't Approved, or `dt status --skill build-setup` isn't `current` | Name the skill that comes first (`build-planning`, `build-setup`). Stop |
| Run | no build recorded for the active milestone, and the user gives the go | `references/run.md` |
| Resume | a build is recorded and this session has no agents running (a new session) | `references/resume.md` |
| Task | the user names one task (or half) to run in the foreground, to debug it | `references/task.md` |
| Exit | every task has landed and the exit review is due or done | `references/exit.md` |

Run, Resume and Exit drive the same loop, `references/loop.md`; every stop it hits is handled by
`references/escalation.md`. Load those two with the mode file, nothing else.
