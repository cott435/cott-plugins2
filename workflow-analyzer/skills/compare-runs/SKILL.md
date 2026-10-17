---
name: compare-runs
description: Set two or more Claude Code sessions side by side on one page - turns, time, tokens, peak context, agents, tool calls, files changed, cost and eval checks, each with its change from the first, then per turn, skill, agent type and file. Use when someone wants to compare chats, runs, replays or eval iterations ("compare my last two chats", "how did the replay differ from the original?"). Not for one run on its own (run-flow) or a question about one (ask-run).
argument-hint: "<session-or-workspace> <session-or-workspace> [...] [LABEL=...] [--project TEXT]"
---

# Comparing runs

`C` is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compare.py`, `T` is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/trace.py`, `S` is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/serve.py`.

## 1. The runs

Each run is a session (an id or unique prefix, a `.jsonl` path, `latest`, or words from its
title) or a workspace a build already wrote (a directory holding `index.json`: a run-flow
workspace, a replay's `<run>/flow/`). Any of them may carry a label, `LABEL=<run>`; without
one a run is labelled by its eval iteration (when it has an `eval.json`) or its session's
first 8 characters. **The first run is the baseline**: every change is measured from it, so
put the original, the older version or the one the user called "before" first.

When the user's words don't pin the runs down ("my last two chats"), list candidates with
`T find --limit 8 [--project TEXT]` and, if it is still ambiguous, ask once with
`AskUserQuestion` (`multiSelect: true`, at most four options, the title as label, project and
span as description). "My last two chats" means the two newest other than this one.

Comparisons are most useful between runs of the same task: a replay and its original, two
eval iterations of one trajectory, the same prompt under two plugin versions. When the runs
are unrelated chats, say once that the page compares their size and shape only.

## 2. Build the page

`C <run> <run> [<run> …] [--project TEXT]` builds any session that isn't built yet (into
`~/.claude/run-flow/<project>/<id8>/`) and writes
`~/.claude/run-flow/compare/<id8>-vs-<id8>.html` (`--out` to put it elsewhere), printing its
path. The page:

- **Headline**: one row per measure, one column per run, the change from the baseline in
  green (better) or red (worse).
- **Checks**, when two or more runs have an `eval.json` (replays and graded evals do): the
  checks whose result differs, then the rest.
- **Per turn**: cumulative output tokens, wall time and peak context, one line per run.
  Turns line up by position, not by what they did.
- **Skills** and **agents**: per skill the turns that invoked it, per agent type its runs,
  with their tokens and time.
- **Files**: every file any run wrote or edited, and in which turns of each run.

## 3. Serve and tell

`S <page>` prints the URL; open it in the browser pane (or print it with no pane). Then say,
in three lines at most: which runs, the baseline, and the two or three biggest differences
the headline shows (with their numbers), and that each run's name links to its own run page.
Don't explain why the runs differ unless asked; `ask-run` on either run answers that, step
by step.

## What this skill never does

- Edit the projects or the transcripts, or commit anything.
- Write anywhere but `~/.claude/run-flow/` (or the `--out` the user gave).
