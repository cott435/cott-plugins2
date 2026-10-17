---
name: run-flow
description: Draw what any Claude Code session did, from its transcripts, as a local page opened in the browser pane - a timeline of the main thread and every agent, tokens and time per turn and per agent, a files-by-turns matrix, and a page per turn and agent with every step. With --agent, one agent type across sessions. Use when someone asks to see, draw or chart a chat or run ("draw my last chat", "what did the agents do in that eval run?"). Not for a question about a run (ask-run).
argument-hint: "[session-id | path.jsonl | latest | chat title words] [--project TEXT] [--plugin NAME] [--agent TYPE] [--sessions a,b | --branch GLOB]"
---

# Seeing a run

A run is what one chat did: the prompts the user typed (turns), every tool call the main thread
made, the agents it spawned (units) and what each of those did, step by step. This skill draws
one from its transcripts.

`T` is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/trace.py`; `S` is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/serve.py`.

## 1. The session

Everything in the arguments before the first flag names it:

- a path to a `.jsonl`, or a session id or a unique prefix of one: use it;
- `latest`: the newest session other than this chat;
- words from the chat's title, as the app's sidebar shows it: pass them as the session. `T`
  resolves them when exactly one chat matches; otherwise it prints the matches and exits 1;
- nothing: run `T find --limit 8` (add `--project <text>` when the user named a project or
  repo; `--all` includes headless eval runs in temp dirs) and, if the user's words point at
  exactly one, use it; otherwise ask as below.

`--project TEXT` narrows `latest`, title words and `find` to sessions whose working directory
contains TEXT. `--plugin NAME` is optional: with it, the main thread is also split into
segments at each `/NAME:<command>` and each agent is tied to its definition in that plugin.

When several chats match, ask once with `AskUserQuestion`: one option per session, at most
four, newest first. The label is the chat's title in quotes; the description is its project,
its span, its agent count and commands, and `fork of <id8>` when `find` says so. A forked or
resumed chat shares its history up to the split with the original, so two chats with the same
title are usually a chat and its fork. Never pick between them yourself.

With `--sessions a,b` or `--branch GLOB` there is no positional session: those list one agent
type across sessions, so they need `--agent`. Without it, say
`--sessions and --branch list one agent type across sessions: add --agent <type>` and stop.

## 2. Build

- One session: `T build <session> [--project TEXT] [--plugin NAME]`. It writes the workspace,
  `~/.claude/run-flow/<project>/<id8>/` (`$RUN_FLOW_HOME` overrides the root), and prints it.
  Rebuild on every call: it takes a second, and a running session gains turns and units
  with its step ids unchanged.
- Across sessions: `T view --agent TYPE (--sessions a,b | --branch GLOB) [--plugin NAME]`,
  one command that builds every session into its own workspace and then
  `~/.claude/run-flow/views/<type>-<date>.html`. Never stitch `T build` calls by hand.
  A `--branch` glob that matches nothing prints `no session … on a branch matching …`: say so
  and stop.

The workspace holds:

- `flow.html`: headline tiles (turns, wall and working time, tokens, peak context, agents and
  how many ran at once, tool calls and errors, files written and read); the **timeline**, wall
  clock left to right, the main thread on top and each agent below it, parallel agents in
  separate rows; **turns**, one column per prompt with its wall time and output tokens,
  split into main thread and agents and coloured by the skill it ran; the **files matrix**,
  every file read or changed against the turns that touched it; the agent wave chart; and
  tables of turns and units.
- `turns/T<nn>.html` and `units/U<nn>.html`: every step with its full input and output, each
  Write's content and each Edit's old and new text, commits, hooks, and what came back.
- `index.json`, `turns/T<nn>.json`, `units/U<nn>.json`, `run.md`: the same as data (what
  `ask-run` reads).

Step ids are stable: `D<n>` in the main thread, `U<nn>.S<n>` inside an agent, `T<nn>` a turn.

Print `T`'s summary lines. If the session has no turns, say it is empty and stop. With
`--agent` on one session, if no unit of that type ran, say so, name the types that did, and
open `flow.html` instead.

## 3. Serve and open

`S <page>` serves `~/.claude/run-flow/` on 127.0.0.1 (reusing the server it started before,
if it still answers) and prints the page's URL. The page is `<workspace>/flow.html`; with
`--agent` on one session `<workspace>/agents/<type>.html`; across sessions the `views/` page
`T view` printed. Open the URL in the browser pane. With no browser pane, print the URL and the
page's path.

Then tell the user, in two lines:

1. The run: its title, project, span, how many turns and agents, output tokens; and the URL.
2. That every box, bar and row opens that turn's or agent's page, and that `ask-run` answers
   questions about it, `run-to-eval` makes it a replayable eval, and `compare-runs` sets it
   beside another run.

When the question was about one agent or one turn, point at its page by its id
(`U03`, `T04`) rather than retelling its steps.

## What this skill never does

- Judge the run.
- Edit the project or the transcripts, or commit anything.
- Write anywhere but `~/.claude/run-flow/` (or `$RUN_FLOW_HOME`).
- Serve to anything but 127.0.0.1.
