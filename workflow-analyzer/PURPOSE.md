# Purpose: `workflow-analyzer`

## Goal

Anyone can see, question and replay what a Claude Code session actually did, from its
transcripts alone: every turn, agent, tool call, token, second and file, as pages and as
answers that cite the step they rest on.

## Who uses it, and when

A developer after a chat or an eval run who wants to know where the time and tokens went,
why an agent did something, or whether a change made a workflow better. They name a session;
the rest is read from `~/.claude/projects/`. dev-team's eval harness calls its scripts at the
end of every run.

## What it does

- Draws a session as local pages: a timeline of the main thread and every agent, tokens and
  time per turn and per agent, the files each turn touched, and every step in full.
- Answers a question about a session with step ids and links.
- Turns a session into a replayable eval, replays it and grades the replay.
- Compares two or more runs side by side.

## Non-goals

- Changing the session or project it reads.
- Writing anywhere but its own home, or serving pages beyond 127.0.0.1.
- Dependencies beyond the Python standard library.

## Done well means

A question about a run is answered from its trace in seconds, with ids a reader can follow.
Two runs of the same workflow can be told apart at a glance.
