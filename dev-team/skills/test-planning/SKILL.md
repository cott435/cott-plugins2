---
name: test-planning
description: Plans how each package's pipelines are proven correct - a test strategy per pipeline in docs/packages/{pkg}/tests.md, and golden-case fixtures in tests/fixtures/{pkg}/TC-NN/ whose expected outputs come from outside the agent. Use when pipelines are approved and you want golden cases before the build, when the user brings known input/output pairs, when a new pipeline needs cases, when a bug needs a regression case, or when an expected output must change.
---

# Test Planning

A golden case is an oracle: an input and the output the code must produce, recorded before the code exists, from a source outside the agent that will build it. This skill writes `docs/packages/<pkg>/tests.md` (strategy and case index) and the fixtures under `tests/fixtures/<pkg>/TC-NN/`, and mints the `TC-NN` IDs. It's optional: when skipped, `build-planning` still requires a smoke test per pipeline and test-backed acceptance per task. The tester writes test code in the build.

**Not for:** test code (the build's), pipeline design (`pipeline-design`), task order (`build-planning`). A change another skill owns (a contract, a pipeline, a spec ID) is recorded for its Revise, never made here: `dt route <owner> "<change>" --from test-planning`, and listed at the gate.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. `examples.md` here has the `tests.md` template, fixture shapes and a routed case; each mode file names its own examples.

## Modes

Start with `dt status --skill test-planning`: the mode per package, its gap keys and `next ids`. Read only the mode's file.

| Mode | When | Do |
|---|---|---|
| **Blocked** | The package's `pipelines.md` isn't Approved | Say so. Stop |
| **New** | No `tests.md` | `references/new.md` |
| **Extend** | A new pipeline, new user pairs, or a regression case after a bug | Add cases; existing ones untouched: `references/extend.md` |
| **Revise** | An expected output or tolerance must change, or `routed_changes` lists a change | Approval required: `references/revise.md` |
| **Grow** | The package split; cases move with their pipelines | Move sections and fixtures; content unchanged: `references/grow.md` |
| **Current** | Nothing to do | Say so; next is `build-planning`. Stop |

**Read:** `pipelines.md`, `contract.md`, the spec's DATA-, QR- and model-quality criteria for the IDs in scope (`dt section …`), and the milestone's `docs/references.md` entries (if `dt status` lists references waiting, route to `reference-intake` first). **Don't read** `tasks/plan.md`: cases follow the pipelines and the spec, not the task order.

## Asking

One question at a time, with your guess and a default, and only about what only the user knows. Infer the rest (names, seeds, sizes, tolerances) as ASSUMPTIONS. **The user's words:** record them and honour yours (`requests_open`) per `../idea-refine/references/requests.md`.

## Rules

- Every case has a Source outside the agent and a Tolerance with its reason.
- Each ID comes from `dt next-id TC`, the section written before the next; never count by hand.
- Fixtures are kilobytes; large data is a path plus hash. CSV for tables, JSON for structure and parameters.
- **Every write of an `expected.json` brings a `dt guard` permission prompt**, here and in the build: the user approves every oracle write. Never route around it (no Bash `echo >`, no copying over).
- `expected.json` changes only through Revise with the user's approval, never by a builder to make a test pass. `build-setup` puts this in the `CONSTRAINTS.md` floor.
- Write only `docs/packages/*/tests.md` and `tests/fixtures/**`. Never create or run anything under `src/`, `tests/intent/`, `tests/unit/` or `tests/contracts/`, nor a generator.

## Review Gate (CRITICAL)

Fix what `dt lint docs/packages/<pkg>/tests.md` reports. Rerun `dt status --skill test-planning`: every gap key empty, except `pipelines_no_golden` gaps under Open questions with a reason. The expected outputs are the oracle, so show them, not a summary. The mode file adds what its round shows.
1. **What was written:** the Strategy table, then one line per case: ID, pipeline, kind, source, expected, tolerance and why. Show each transcription next to its raw source.
2. **ASSUMPTIONS:** seeds, sizes, tolerances, case names and transcriptions you chose.
3. **Open questions,** including any skill you'd route to that isn't installed.
4. **Uncovered:** pipelines with no golden case; spec IDs with no case.
5. Ask the user to approve the expected outputs. **STOP YOUR TURN.**

**No live user** (headless): write the doc and fixtures, put every oracle confirmation under Open questions, leave Draft, and stop.

| The user says | Do | Then |
|---|---|---|
| An unambiguous yes to the expected outputs | Set `Status: Approved` and the date; `dt route --done test-planning` if `routed_changes` listed any. Offer to commit `tests.md` and the fixtures; commit only on a yes | Stop. Next: `build-planning` |
| "Approved, go ahead" | As above | Start `build-planning` (run its `dt status`). Never start code |
| A hedge on any oracle ("looks fine I guess") | Keep Draft. Ask again, naming the cases and values | Repeat this gate |
| Changes to a case, or a case dropped | Edit; list drops explicitly; keep Draft | Repeat this gate |
| Approved, plus an upstream change (a contract, a pipeline, a spec ID) | Set Approved; record it with `dt route` (Not for), never make it this turn | Stop; the owner's Revise is next |
