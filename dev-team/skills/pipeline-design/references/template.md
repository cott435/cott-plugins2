# pipelines.md template

The file format every mode writes. `dt` parses it: keep the header line, the `## PL-NN: Title` headings, the six step-table columns and the `(pre-build — removed by spine task)` headings exactly. The rules for filling it are in `steps.md`.

````markdown
# <pkg> — Pipelines

**Package:** <pkg> · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Contract:** [contract.md](contract.md)

## PL-NN: <Workflow name>
**Entry:** `src/<path>/<entry module>::run_<workflow>` · **Trigger:** `python -m <module> <command>`
**Covers:** <spec IDs, ranges with an en dash>
**References:** <optional: RF-NN (step) for each reference that informs a step>

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `<function>` | <component[.module]> | <contract types> → <contract type> | <real, minimal baseline> | <spec IDs> |
| 2 | `<Class>` | <component.module> | <constructor input> → <Protocol> | <minimal real class> | <spec IDs> |

### Entry sketch (pre-build — removed by spine task)
```python
def run_<workflow>(cfg: <Config>) -> <Result>:
    a = step_one(cfg.x)
    b = step_two(a)
    return step_three(b, cfg.out)
```

## Planned layout (pre-build — removed by spine task)
```
src/<pkg>/
  __init__.py   contract exports only
  __main__.py   CLI: each trigger → its entry
  pipeline.py   PL-NN entry; with several pipelines here, pipelines/pl<NN>_<workflow>.py each
  <owner modules, one per step owner; a folder for one with private helpers>
tests/intent/<pkg>/  tests/unit/<pkg>/
```

## Open questions
- <question> (assumed: <the default used>)

## Retired
- ~~PL-NN: <title>~~ Retired YYYY-MM-DD: <reason>
````

- Row 2 is a library class its factory in row 1 returns (`steps.md`); drop it when there is none.
- Multi-package segment of a system pipeline: add `· **Part of:** PL-NN` to the pipeline's Entry/Trigger line.
- Multi-package layout: the code block starts at the package's path from the root architecture (`packages/<pkg>/src/<pkg>/`); the test line stays `tests/intent/<pkg>/  tests/unit/<pkg>/`, at the repo root (`steps.md`, Layout).
- After the wiring task, `dt prebuild-clear` replaces each entry sketch with `Layout: \`dt layout <pkg>\`` and drops the planned layout.

