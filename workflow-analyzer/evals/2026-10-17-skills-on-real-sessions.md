# Each skill triggers and does its job on a real interactive chat and a real dev-team2 eval run

**Tested against:** round 1 `8dd7264`, rounds 2–3 `2e94e6c` (`skills/*/SKILL.md`, `agents/run-reader.md`, `scripts/*.py`) · model: `claude-sonnet-5-5` executors (`claude -p --model sonnet --plugin-dir workflow-analyzer`); replays `claude-sonnet-5-5` · 2026-10-17
**Set:** none (ad hoc, first release) · **Baseline:** none · **Pass rate:** round 1 6/8 cases, rounds 2–3 3/3 re-runs of the failing or doubtful ones

## What was tested

Given a plain request naming a real session in `~/.claude/projects`, each skill triggers from
its description alone and does what its SKILL.md says, on one interactive chat and one
dev-team2 eval run each: `run-flow` builds and serves the page; `ask-run` answers with step
ids, and hands broad questions on big traces to `run-reader`; `run-to-eval` extracts a scenario
the original passes, and replays it on request; `compare-runs` builds and serves the page.

## Method

- Headless `claude -p` with the plugin loaded by `--plugin-dir`, `bypassPermissions`,
  `AskUserQuestion` disallowed, run from an empty directory, n=1 per case, eight in parallel.
  The runner script is `scratchpad/skilltest/run.sh` of session `9167272b`.
- Sessions: interactive chats `c9bf15e9` (dev-team2 worktree, 1 turn, 110 steps), `b5424b55`
  (V2, 1 turn) and `ce663432` (V2, 1 turn); dev-team2 iteration-6 eval runs `8e72d69e`
  (quant-incremental, 61 turns, 3 agents), `01ab6e91` (rl-incremental, 40 turns) and
  `95faec15` (rl-all-at-once, 19 turns).
- Two real replays with `replay.py`: `b5424b55`'s one turn (run by hand, not inside a skill
  run, before the skills were written), and `95faec15`'s first turn with `--isolate` and the
  eval's own staged dev-team2 plugin (started by the `eval-eval` skill run).
- Cost: about $1.0 in executors, plus $0.14 and $0.10 for the two replays.

## Results

| Case | Expected | Observed | Pass |
|---|---|---|---|
| run-flow · chat `c9bf15e9` | triggers; builds; serves; two-line close | `run-flow` invoked; page at `/dev-team2/c9bf15e9/flow.html`; title, turns, agents, tokens, URL | ✅ |
| run-flow · eval `01ab6e91` | same | page served; 40 turns, 0 agents, 377k output tokens | ✅ |
| ask-run · chat `b5424b55` | answers with step ids | six edits named with D4–D11, the read-back at D13; 5,679 output tokens; said the trace shows no test run | ✅ |
| ask-run · eval `8e72d69e`, two narrow questions | step ids; the slow cause | T07: `docs/spec.md` (D38, Bash), `architecture.md` (D48), `contract.md` (D49); T16: a 2m37s model gap after D152, not the command | ✅ |
| ask-run · eval `8e72d69e`, whole-run question (round 1 of it, `2e94e6c` minus the rule) | delegates to `run-reader` | answered correctly without delegating | ❌ rule too vague; reworded |
| ask-run · same question, round 3 | delegates; checks cited steps | spawned `run-reader` with the four-line prompt; re-checked D27 and D302 itself; T01/T05/T32 errors with causes and recovery | ✅ |
| run-to-eval · chat `c9bf15e9`, round 1 | extracts; original passes its checks | prompt began with `<system-reminder>`, so marked injected: 0 turns to replay; the executor patched `scenario.json` by hand | ❌ fixed in `to_eval.typed()` |
| run-to-eval · chat `c9bf15e9`, round 2 | same | 1 turn, 5 checks, original 5/5, both caveats reported, no replay | ✅ |
| run-to-eval · eval `95faec15` + 1-turn replay | extracts (original passes); replays on request | 19 turns, 29 checks, original 29/29; replay invoked `dev-team2:idea-refine`, $0.10. Graded 3/29 because the run-wide checks counted all 19 turns | ✅ after `--upto` (4/4, 25 not graded) |
| compare-runs · chats `b5424b55` vs `ce663432` | page; baseline first; says unrelated | page served; +1083% time, +188% tokens; "compares size and shape only" | ✅ |
| compare-runs · evals `8e72d69e` vs `01ab6e91` | same | page served; −34% turns, −22% tokens, 0 vs 3 agents | ✅ |

Mechanical, outside the skills: `trace.py view --agent Explore --sessions 8e72d69e,9167272b`
wrote the view page (3 + 0 units); dev-team2's `runviz.py --run` and `runviz.py iteration-6`
drew every run through the plugin's scripts (`WORKFLOW_ANALYZER_SCRIPTS`); `claude plugin
validate` passes (one warning: the root `CLAUDE.md` every plugin here keeps).

## Verdict

Holds for all four skills after three fixes, each re-run on the case that found it:
`<system-reminder>`-prefixed prompts are kept (stripped) rather than skipped; a replay cut
short is graded and compared on its own turns (`check.py --upto`, `compare.py --turns`); and
`ask-run`'s rule for spawning `run-reader` is now a decision from the overview. Not covered:
simulated-user replays (`--mode simulated`), which no case ran, and the interactive paths
(`AskUserQuestion` between matching chats, the browser pane), which headless runs can't
exercise.
