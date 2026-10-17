# The scripts build, query, extract, replay, grade and compare real sessions

**Tested against:** `2e94e6c` (`scripts/*.py`) · model: none for the scripts; `claude-sonnet-5-5` for the two replays · 2026-10-17
**Set:** none · **Baseline:** none · **Pass rate:** 9/9 after fixes

## What was tested

That the scripts moved from dev-team2's `evals/harness/runflow/` work on any session, not
only dev-team2 evals, and that the new ones (`query.py`, `to_eval.py`, `replay.py`,
`check.py`, `serve.py`) do what their docstrings say on real transcripts.

## Method

Direct runs from the shell against sessions in `~/.claude/projects` (ids as in
`2026-10-17-skills-on-real-sessions.md`), checking output by hand and pages in the browser
pane.

## Results

| Case | Expected | Observed | Pass |
|---|---|---|---|
| `trace.py find` without `--plugin` | every session, newest first, this chat marked | 2.5s over 534 MB of transcripts; `← this chat` shown | ✅ |
| `trace.py build` on a chat and an eval run | workspace under `~/.claude/run-flow/<project>/<id8>/` | `dev-team2/c9bf15e9` (0.2s), `quant-incremental-with_skill-project/8e72d69e` (0.5s); page renders | ✅ |
| `serve.py` twice | one server reused, 200 | same port both calls; HTTP 200 | ✅ |
| `query.py` overview/turn/unit/step/files/slow/grep on `8e72d69e` | ids on every line | all seven print ids and pages | ✅ |
| `to_eval.py` + `check.py` on the original, `8e72d69e` | original passes its own checks | 42/42 after excluding `/dev/null)` and out-of-project paths from file ops | ✅ after fix |
| `replay.py` on `b5424b55`, Sonnet, 1 turn | turn runs in a clone; graded; compared | ran (41s, $0.14); graded 2/4: the edit was made in a `python - <<EOF` script the trace didn't see | ❌ → fixed two ways: Python-heredoc file-op detection in `trace.py`, and each turn's git commit recorded as `files_changed`; regraded 4/4 |
| `compare.py` with session ids | builds missing workspaces; default path | `compare/e441ef3d-vs-b5424b55.html` | ✅ |
| `replay.py --max-turns 1` on `95faec15` with the eval's plugin, `--isolate` | turn 1 invokes the plugin's skill; graded on turn 1 only | `dev-team2:idea-refine` invoked, $0.10; `check.py --upto 1` 4/4, 25 not graded; `compare.py --turns 1` cuts both runs to T01 | ✅ after `--upto`/`--turns` |
| dev-team2 `runviz.py --run` / `iteration-6` via the plugin's scripts | same pages as before | single run and all four trajectories plus the index, 1.3s | ✅ |

## Verdict

Holds. Fixes made during the run: `pathlike` rejects `/dev/*` and parentheses;
`python_file_ops` reads literal paths out of Python heredocs; replays trust their per-turn git
commits for files changed; partial replays are graded and compared on their own turns; the ⛔
mark is only for hooks that blocked.
