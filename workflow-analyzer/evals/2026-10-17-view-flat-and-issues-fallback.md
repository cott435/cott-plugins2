# view --flat and the audits/issues fallback, for plugin-dev

**Tested against:** `69509e2` (`workflow-analyzer/scripts/trace.py`, `workflow-analyzer/scripts/flow.py`) · model: none (scripts only; driven by `claude-opus-5-5`) · 2026-10-17
**Set:** none · **Baseline:** `431319f`

## What was tested

Two additive changes that plugin-dev needs now that it runs these scripts through a link:
`trace.py view --flat` builds each session into `ROOT/<id8>/`, and `flow.py`'s
`default_issues` uses `<plugin>/audits/issues/` when only that exists. Also that the defaults
are unchanged.

## Method and results

| Check | Result |
|---|---|
| `view --plugin toy --agent writer --root <plugin>/evals/workspace/audit --flat --sessions 0a0d17f0,0f10d17f` on the planted fixtures | workspaces at `<root>/0a0d17f0/`, `<root>/0f10d17f/`; view links `../<id8>/units/U<nn>.html`; 4 writer rows in time order |
| `build` into `<plugin>/evals/workspace/audit/0a0d17f0/` with a ledger at `<plugin>/audits/issues/` | `+ TO-001` and `✓ TO-002` on the box and on `units/U01.html`, the same as plugin-dev's deleted `flow.py` |
| `view --agent implementer --sessions 8e72d69e` (dev-team2 iteration-6 eval run), no `--flat` | still `<root>/<project>/<id8>/` |
| `build c9bf15e9` (an interactive chat) | builds as before (1 turn, 110 driver steps) |

With neither ledger present, or with `runs/audits/issues/` present, `default_issues` returns
`runs/audits/issues/` as before.

## Verdict

Holds. plugin-dev's own record of the switch is
`plugin-dev/evals/2026-10-17-run-flow-on-workflow-analyzer-mechanical.md`.
