# CLAUDE.md

Instructions for working on the `workflow-analyzer` plugin's own source. The rules every
plugin here is held to are printed by plugin-dev's SessionStart hook with this plugin's
`PURPOSE.md`; this file holds only what is specific to this plugin.

`VERSIONING.md` holds this plugin's own versioning decisions: its per-agent `model:` choices.

## Specific to workflow-analyzer

- `scripts/` is shared by every skill and by dev-team's `evals/harness/runviz.py`, which
  imports `trace`, `flow`, `charts` and `compare` from `../workflow-analyzer/scripts` in this
  marketplace, and ends every dev-team eval run with it. Keep `trace.build(session, plugin,
  out, quiet)`, `trace.PROJECTS`, `compare.write(specs, page)`, `compare.delta`,
  `flow.load_eval`, `flow.run_stats`, `flow.CSS`, `charts.CHART_CSS`, `charts.dur`,
  `charts.kt`, `charts.esc` and `planmap.write(out) -> Path | None` stable, or update runviz.py
  with them.
- The `plan-map/2` schema of `plan.json` (documented in `scripts/planmap.py`) is a contract with
  dev-team's `planexport.py` and `dt plan --json`: read it without knowing dev-team, accept what
  older producers leave out (`plan-map/1` has no goals, features or requirements), and change it
  only with a new schema version both sides agree on. `tests/test_planmap.py` renders the
  `plan-map/1` sample `tests/fixtures/plan.json` and a `plan-map/2` plan built in the test; run it
  after a change.
- Scripts use the standard library only.
- Test a change against two real sessions: one interactive chat and one dev-team eval run
  (`trace.py find --all --project dev-team-workspace`). `check.py <eval> <original
  workspace>` must pass every non-budget check for an eval `to_eval.py` just made.
- Nothing writes outside `$RUN_FLOW_HOME` (default `~/.claude/run-flow/`).
