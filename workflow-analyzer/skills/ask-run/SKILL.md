---
name: ask-run
description: Answer a question about what a Claude Code chat or eval run did, from its transcripts, citing the step ids it rests on (D12, U03.S7, T04) and linking the pages that show them - files a turn read or edited, why an agent took long, where the tokens went, what an agent was told and returned. Use when someone asks about a past or running session ("which files did turn 4 edit?", "why did the second agent take 6 minutes?"). Not for drawing a whole run (run-flow).
argument-hint: "<question> [session-id | path.jsonl | latest | chat title words] [--project TEXT]"
---

# Answering a question about a run

The answer comes from the trace, never from memory of the chat: every claim cites the step or
turn it rests on, and the reader can open that step's page to check it.

`T` is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/trace.py`, `Q` is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/query.py`, `S` is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/serve.py`.

## 1. The session

Resolve it exactly as `run-flow` does: a `.jsonl` path, an id or unique prefix, `latest` (the
newest session other than this chat), or words from the chat's title, optionally narrowed with
`--project TEXT`. When the question names none, use `T find --limit 8` and the question's own
words (a project, a title, "my last chat") to pick; when more than one fits, ask once with
`AskUserQuestion` (one option per session, at most four, newest first, the title as label).

## 2. Build

`T build <session> [--project TEXT]` (about a second; always rebuild, the session may have
grown). It prints the workspace, `W` below.

## 3. Find the answer

Start with `Q overview W`: the session, its tokens, one line per turn (steps, wall time,
calls, errors, output tokens, skills, agents, files changed, the prompt) and one per agent.
That alone answers most "which turn", "how many", "which agents" questions. Then narrow:

| Question about | Command |
|---|---|
| one turn: what it was asked, did, changed, cost | `Q turn W T04` (`--steps` lists every step) |
| one agent: its prompt, files, tokens, return | `Q unit W U02` (`--steps` lists every step) |
| one step's full input and output | `Q step W D31` or `Q step W U02.S7` (`--full` unclipped) |
| a file: who read, wrote or edited it, when | `Q files W <part of its path>` |
| where the time went | `Q slow W` (whole run), `Q slow W U02` or `Q slow W T04` |
| when something happened, or whether it did | `Q grep W <text>` |

Turn and agent numbers in the user's words map to ids: "turn 4" is `T04`; "the second agent"
is `U02` (agents are numbered by start time; check its type and description in the overview
when the user named it by what it did). A gap in `Q slow` is the time from one step to the
next: the tool's own run time plus the model deciding what to do next, so a long gap after a
Bash call is usually the command, and after a user message it is the model thinking.

File ops come from Read/Write/Edit calls, plus Bash commands that plainly read or write a
file (`cat`, `sed -n`, `>`, `tee`), marked `(Bash)`; a script that writes files itself is not
seen. Say so when the answer depends on it.

**Large traces.** Decide from the overview, before digging. If it shows more than 30 turns or
10 agents **and** the question is not about one named turn, agent, step or file (it asks
"which turns…", "across the run…", "why…" or "how…" over the whole session), don't dig
yourself: spawn one `workflow-analyzer:run-reader` agent in the foreground, which keeps the
step-by-step reading out of this conversation. A question about one named turn, agent, step or
file is answered here whatever the trace's size. Its prompt is four lines: `Workspace: <W>`, `Query: ${CLAUDE_PLUGIN_ROOT}/scripts/query.py`,
`Question: <the user's question>`, and `Leads: <ids the overview already points at>`. It is read-only and returns findings with step ids; check one or two of its cited steps
with `Q step` before relying on them.

## 4. Answer

Lead with the answer in one or two sentences, then the evidence as short lines, each ending
with the ids it rests on, for example:

> T04 edited two files: `docs/roadmap.md` (D23, via Bash) and `docs/brief.md` (D22).

Then link the pages: `S <W>/turns/T04.html` or `S <W>/units/U02.html` prints a URL (add
`#D23` to land on a step). Give the URL for the one or two pages that show the answer; open
it in the browser pane only when the user asked to see it.

When the trace cannot answer (the step's output was not recorded, the work happened in a
script the trace cannot see into, the session's files were deleted), say exactly that and
what it does show. Don't guess.

## What this skill never does

- Answer from anything but the trace and the project's files.
- Edit the project or the transcripts, or commit anything.
- Write anywhere but `~/.claude/run-flow/`.
