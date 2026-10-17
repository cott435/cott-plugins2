# The eval's format

What `to_eval.py` writes to `~/.claude/run-flow/evals/<id>/`, and what `replay.py` and
`check.py` read.

- `scenario.json`:
  - `source`: the session, its transcript, project, branch, models and workspace.
  - `setup`: how a replay recreates the starting project. `git` clones the project's repo at
    the last commit before the session started and runs in the same subdirectory; `empty`
    (the project is gone or not a git repo) starts from an empty directory.
  - `turns`: one per prompt the user typed, verbatim, with what that turn did in the original
    (files changed and read, skills, agents, output tokens, seconds). Prompts the app injected
    (task notifications, interruptions) are kept with `replay: false` and skipped.
  - `checks`: files changed per turn and in all, skills invoked per turn and in all, agent
    types spawned, the final files present, and budgets of 1.5× the original's output tokens
    and wall time (`--budget-factor` changes it).
- `expected/final/`: the final content of every file the chat changed inside the project, as
  it is on disk now; `expected/file_ops.json`: every read and write per original turn.
