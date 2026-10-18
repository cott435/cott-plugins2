# M1: Summary — Plan

**Milestone:** M1 · **Status:** Approved · **Base:** — · **Last updated:** 2026-10-17 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** `python -m mini summarize` prints count, total and mean; TC-01 passes.
**Covers:** SUM-01, SUM-02 · **Deferred:** none
**Skills:** —

## Phase 0: Interface

### M1-T01: Freeze the M1 interfaces
**Package:** mini · **Step:** contract · **Kind:** interface · **Size:** M · **Mode:** solo
**Read:** PL-01, core.Numbers, core.Summary, core.summarize
**Acceptance:**
- [ ] `Numbers` and `Summary` in `types.py`, one sample each under `tests/contracts/`
- [ ] `summarize` and `run_summary` signatures with bodies `raise NotImplementedError("<task>")`
- [ ] `python -m mini summarize [--smoke]` dispatches to `run_summary`, passing `smoke`; `__init__` exports
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/mini/__init__.py, src/mini/__main__.py, src/mini/types.py, src/mini/summary.py, src/mini/pipeline.py, tests/contracts/**

### Checkpoint after M1-T01 (barrier)
- [ ] The interface code matches contract.md exactly: types, signatures, stubs, samples, exports
- [ ] M1-T03's tester can write its tests from what is frozen

## Phase 1: Spine, wiring and thicken

### M1-T02: summarize spine (count, total)
**Package:** mini · **Step:** PL-01.summarize · **Kind:** spine · **Covers:** SUM-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, core.Numbers, core.Summary, core.summarize, SUM-01
**Acceptance:**
- [ ] `summarize` returns the count and total of the core.Numbers sample, mean None; signature unchanged
**Verify:** `pytest tests/unit/mini -k summarize` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/mini/summary.py, tests/unit/mini/test_summary.py

### M1-T03: Mean in the summary
**Package:** mini · **Step:** PL-01.summarize · **Kind:** thicken · **Covers:** SUM-02 · **Size:** XS · **Mode:** split
**Read:** PL-01, TC-01, SUM-02, core.Summary, core.summarize
**Acceptance:**
- [ ] TC-01 passes
**Verify:** `pytest tests/intent/mini tests/unit/mini -k summarize` · `scripts/check.sh gate`
**Depends on:** M1-T02 · **Writes:** src/mini/summary.py, tests/unit/mini/test_summary.py, tests/intent/mini/test_tc01.py

### M1-T04: Wire PL-01
**Package:** mini · **Step:** PL-01 · **Kind:** wiring · **Covers:** SUM-01 · **Size:** XS · **Mode:** solo
**Read:** PL-01, core.Numbers, core.Summary
**Acceptance:**
- [ ] `python -m mini summarize --smoke` runs end to end on a synthetic file
- [ ] PL-01 entry sketch replaced by a `dt layout` pointer
**Verify:** `python -m mini summarize --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02 · **Writes:** src/mini/pipeline.py, tests/unit/mini/test_pipeline.py

### Checkpoint: milestone exit
- [ ] `python -m mini summarize --smoke` runs end to end
- [ ] TC-01 passes; no `NotImplementedError` stub is left
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T02 summarize spine | M1-T01 interface | code | none: replaces its stub |
| M1-T03 mean | M1-T02 summarize spine | code | none: thickens the same module |
| M1-T04 wire PL-01 | M1-T02 summarize spine | order | none: integration: the smoke runs the real summarize |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|

## Open questions

## Replan notes
