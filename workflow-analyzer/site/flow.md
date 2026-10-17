# The flow

Who does what in `workflow-analyzer`: which skill reads which file, and which agent it hands
large traces to.

## Which route

| You want to | Ask for | |
|---|---|---|
| See what a session did | `run-flow` | a page per run, turn and agent |
| Ask a question about a session | `ask-run` | answers citing step ids |
| Make a replayable eval from a chat | `run-to-eval` | `scenario.json` and `expected/`, and a graded replay on request |
| Compare runs | `compare-runs` | one page, each run against the first |

Every skill first builds the session with `trace.py`, so they all read the same workspace.

## Agents and skills

<!-- flow:agents-skills -->

## Who writes what

<!-- flow:writes -->

## Who reads what

<!-- flow:reads -->

<!-- flow:documents -->
