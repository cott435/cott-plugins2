# workflow-analyzer

See, question and replay what any Claude Code session did. Point it at a chat (by id, path,
`latest`, or words from its title) and it rebuilds the run from the transcripts in
`~/.claude/projects/`: every prompt, every tool call, every agent spawned and what each one
did, with tokens, time and file reads and writes per turn and per agent. It works on any
session, interactive or headless, with or without a plugin.

## Install

```
/plugin marketplace add cott435/cott-plugins2
/plugin install workflow-analyzer@cott-plugins2
```

Needs only Python 3.10+ (standard library) and, for replays, the `claude` CLI.

## Skills

| Skill | What it does |
|---|---|
| `run-flow` | Draws a session as a local page opened in the browser pane: a wall-clock timeline of the main thread and every agent (parallel agents side by side), tokens and time per turn and per agent, a files × turns matrix, and a page per turn and per agent with every step's full input and output. When the run's workspace holds a `plan.json`, a **Plan** section opens the plan map: how the plan grew turn by turn, the plan as of each turn, and per milestone what would be built in parallel and what in series. With `--agent TYPE`, every run of one agent type across sessions. |
| `ask-run` | Answers a question about what a chat did ("which files did turn 4 edit?", "why did the second agent take 6 minutes?") from the trace, citing step ids (`D12`, `U03.S7`, `T04`) and linking the pages that show them. Hands large traces to the read-only `run-reader` agent. |
| `run-to-eval` | Turns a chat into a replayable eval: the user's prompts as a scripted or simulated-user trajectory, the files each turn changed and the final files as expected evidence, and checks (files per turn, skills, agents, token and time budgets). On request, replays it with `claude -p` in a fresh clone of the project, grades the replay and compares it with the original. |
| `compare-runs` | Sets two or more sessions (or built runs, or replays) side by side: headline measures with their change from the first, eval checks, per-turn curves, per skill, per agent type and per file. |

## Agent

| Agent | What it does |
|---|---|
| `run-reader` | Read-only. Answers one question from a large trace with `query.py`, every finding citing its step ids. Spawned by `ask-run`. |

## Scripts

All in `scripts/`, standard library only, each runnable on its own (`--help`):

| Script | What it does |
|---|---|
| `trace.py` | `find` sessions; `build` one into a workspace (`index.json`, `turns/`, `units/`, `flow.html`); `view` one agent type across sessions; `ws` prints a session's workspace. |
| `flow.py`, `charts.py` | Draw the run page, the turn and unit pages, the timeline, the per-turn bars and the files matrix. |
| `planmap.py` | Draws a workspace's `plan.json` (schema `plan-map/1`, written by a producer such as dev-team's eval harness) as `plan/`: `index.html` (growth per turn, a node × turn matrix, a change ledger), `T<nn>.html` (the plan as of that turn) and `M<n>.html` (a milestone's build waves, critical path and metrics). Sample and tests: `tests/`. |
| `query.py` | Compact answers from a built run: `overview`, `turn`, `unit`, `step`, `files`, `slow`, `grep`. |
| `compare.py` | The comparison page for two or more runs or sessions. |
| `to_eval.py` | A built run → `scenario.json` + `expected/`. |
| `replay.py` | Replays an eval in a fresh clone, then builds, grades and compares the replay. |
| `check.py` | Grades any built run against an eval's checks. |
| `serve.py` | Serves the pages on 127.0.0.1, reusing one server. |

## Where things go

Everything is written under `~/.claude/run-flow/` (set `$RUN_FLOW_HOME` to move it):

```
~/.claude/run-flow/
├── <project>/<id8>/           one session's workspace: flow.html, index.json, turns/, units/, and plan/ beside a plan.json
├── views/<type>-<date>.html   one agent type across sessions (run-flow --agent)
├── compare/<a>-vs-<b>.html    comparisons (compare-runs)
└── evals/<id>/                an eval: scenario.json, expected/, runs/<label>-<time>/ per replay
```

Workspaces hold the project's file contents as the transcripts recorded them. They live in
your home directory, outside any repo, and nothing here is ever committed. Pages are served
only to 127.0.0.1.

## Limits

- File reads and writes come from Read/Write/Edit calls, plus Bash commands and
  `python - <<EOF` scripts that name a file plainly. A file written by a script that builds
  its path at run time is not seen. Replays don't depend on this: each replayed turn is
  committed, and the commit's files count.
- A replay starts from the project's last commit before the session. Uncommitted changes the
  project had then are not reproduced.
- A replay runs a real agent with `bypassPermissions` in its clone. The clone has no git
  remote, but a prompt that acts on the outside world (a URL, a deploy, a message) would act
  again. `run-to-eval` asks you to review such turns first.

## Used by

dev-team's eval harness (`dev-team/evals/harness/runviz.py`) ends every eval run by drawing it with
`trace.py`, `flow.py`, `charts.py` and `compare.py`, and saves the flow in the run's folder. Its
`planexport.py` writes the run's `plan.json` there first, and `planmap.py` draws it.

## Working on it

Read `CLAUDE.md` first. Versioning, contract checks and the site builder are shared across all
plugins and live in the `plugin-dev` plugin.
