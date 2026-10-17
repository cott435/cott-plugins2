---
name: run-to-eval
description: Turn a real Claude Code chat into a replayable eval - its prompts as a scripted or simulated-user trajectory, the files each turn changed as expected evidence, and checks for files, skills, agents and budgets - then on request replay it in a fresh clone with claude -p, grade the replay and compare it with the original. Use when someone wants an eval or regression test from a chat ("turn this chat into an eval", "replay my last chat with sonnet and compare").
argument-hint: "[session-id | path.jsonl | latest | chat title words] [--project TEXT] [--simulated] [--replay] [--model M] [--plugin-dir DIR] [--max-turns N]"
---

# Turning a chat into an eval

An eval made here is a directory, `~/.claude/run-flow/evals/<id>/`, that says what to replay
and what a replay must show. Making it costs nothing; **replaying it runs a real agent**
(`claude -p`, full permissions, in a fresh clone) and costs money.

`T` is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/trace.py`, `E` is `…/to_eval.py`, `K` is
`…/check.py`, `R` is `…/replay.py`, `S` is `…/serve.py`, all under
`${CLAUDE_PLUGIN_ROOT}/scripts/`.

## 1. The session

Resolve and build it exactly as `run-flow` does: `T build <session> [--project TEXT]
[--plugin NAME]` prints its workspace, `W` below. Pass `--plugin NAME` when the chat ran a
plugin's commands, so the eval records which plugin it exercised.

## 2. Extract

`E W [--id NAME] [--mode simulated]` writes `~/.claude/run-flow/evals/<id>/` (the id defaults
to the chat's title words plus its id8) and prints a summary. `scenario.json` (the setup, the
turns and the checks) and `expected/` are described in `references/scenario.md`; read it
before editing a scenario.

Then check the eval is sound: `K <eval> W` grades the original against its own checks, and
every check but a budget must pass. One that fails means the extraction misread the run: say
which and fix the check in `scenario.json` before going on.

Read `E`'s warnings to the user, and review the scenario with them:

- **Setup `empty`, or files changed since the session ended**: a replay cannot start where
  the original did, or the final files are today's, not the session's. Say so.
- **Prompts that point outside the project** (absolute paths elsewhere, URLs, "push", "open a
  PR", "send", "deploy"): a replay would do that again. The replay rewrites the original
  project path to the clone's, removes the clone's git remote, and disallows
  `AskUserQuestion`, but it cannot undo a prompt that acts on the outside world. Name such
  turns and ask whether to drop them (set `replay: false`) or end the replay before them
  (`--max-turns`).
- **Prompts that depend on the user's own actions**, such as pasting an error from a command
  the user ran: a scripted replay sends the same paste whether or not this run hit that
  error. Simulated mode adapts better; suggest it.

**Simulated mode** (`--simulated`: pass `--mode simulated` to `E`, or set `"mode": "simulated"`
in `scenario.json`, or pass it to `R` for one replay): from turn 2
on, a separate tool-less `claude -p` rewrites each original prompt as a reply to what the
replay's assistant actually said. Fill `persona` (two or three sentences: who the user is,
how they answer and approve) and `facts` (what the user knows that the prompts reveal:
constraints, decisions, numbers) in `scenario.json` from the original prompts before the
first replay; the user should read them.

Tell the user, in three lines at most: the eval's path, how many turns and checks, the setup,
and anything from the review above. Stop there unless a replay was asked for.

## 3. Replay (only when asked)

Before running, say what it will do and what it may cost, and wait for a yes unless the
request already asked to replay: the turn count, the model (`--model`, default the CLI's),
the original's output tokens, and that it runs with `bypassPermissions` in
`<eval>/runs/<label>-<time>/project`.

`R <eval> [--model M] [--label NAME] [--max-turns N] [--plugin-dir DIR …] [--isolate]
[--mode simulated] [--user-model M]` in the background (`run_in_background`; a turn can take
many minutes). `--plugin-dir` loads a plugin version under test; `--isolate` keeps out the
user's own settings, plugins, CLAUDE.md and MCP servers, as dev-team's eval driver does.
Label each replay by what differs (`sonnet`, `plugin-0.4`), since the label names it on the
comparison page.

`R` prints one line per turn, a JSON summary (turns, seconds, cost, stop reason), then
PASS/FAIL per check, and the two pages: `<run>/flow/flow.html` and `<run>/compare.html`
(original vs replay). The run directory also holds `turns.json`, `summary.json`,
`grading.json` and `agent_stream.jsonl`, the layout dev-team's `evals/harness` reads, so its
`runviz.py --run <run>` and `package.py` work on it too.

## 4. Report

`S <run>/compare.html` prints the URL; open it in the browser pane. Then, in four lines at
most: checks passed out of total and which failed with their evidence; the two or three
biggest differences from the original (tokens, time, files); the cost; and that
`ask-run` on the replay (its session id is in `summary.json`) explains any difference step
by step. A failed check is a finding about the replay, not something to fix by editing the
checks, unless the user decides the check was wrong.

## What this skill never does

- Replay without a yes, or replay a turn the user chose to drop.
- Edit the original project, its repo or the transcripts; a replay works only in its clone.
- Commit or push anything outside the replay's clone.
- Loosen a check because a replay failed it, unless the user says so.
