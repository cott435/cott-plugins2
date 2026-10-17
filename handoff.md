# Handoff: dev-team2 planning-skill evals (iterations 5–6) and the stage-rows redesign

_stages-and-contract-phase0 · 2026-10-17 · iterations 5 and 6 committed; 31-file stage/contract redesign uncommitted, tests green, never eval-run_

## Goal

Get dev-team2's planning skills (idea-refine → spec-writing → architecture-design → pipeline-design → test-planning → build-planning → build-setup, backed by `dt` in `scripts/`) to produce well-sized, fully designed milestones in both incremental and all-at-once planning. This is measured by the eval harness in `evals/` ([evals/README.md](evals/README.md)). Done means an iteration where:
- all four trajectories (rl/quant × incremental/all-at-once) fail no checks except known noise;
- quant all-at-once designs every milestone;
- the blind judge runs for both projects and `milestone_quality` scores no lower than the other items.

The user's own requirements, settled this session:
- Milestones are vertical slices, and a stage may be cut into several.
- Independent tracks (e.g. prices+technicals vs financials+fundamentals) stay in one milestone as parallel groups, because only one milestone is active at a time.
- Size is capped per track (about 15 tasks), not by total task count.
- Doc budgets are per unit, not per file.
- Incremental and all-at-once must end at the same bar (first milestone planned, the rest Designed), so their milestone quality can be compared.

## Current state

- **Branch:** HEAD is `stages-and-contract-phase0` at `8f6562e`.
  - `planning-stage-build` is at `1947e13` and lacks `8f6562e`, the iteration-6 results.
  - Someone switched branches after iteration 6; it wasn't this session.
  - Nothing is pushed. `master` = `origin/master` = `6e335e5`.
- **Uncommitted redesign (31 files plus `scripts/tests/fixtures/staged-roadmap.md`):** not written by this session; edited 2026-10-16 18:07–18:10 by the user or another session.
  - Roadmap gets stage rows (`S<n>`, unsized outcomes from idea-refine) plus milestone rows (`M<n>`) that build-planning cuts once a stage's pipelines are approved. Stage status gains `Cut`.
  - Phase 0 goes contract-first: a frozen cross-package contract (schema, fixtures, a fixture-backed fake) under `tests/contracts/<pkg>.<symbol>/`, then package spines in parallel against the fake, with the system spine last.
  - The per-track size counts only the serial Phase 0 tasks (contract, system spine) plus the longest `Depends on` chain. This answers iteration 6's S1 cause.
  - The grader and dtprobe were adapted (`stage_name`/`stage_outline`, stage references).
  - **Verified now:** `python3 -m pytest scripts/tests -q` → `279 passed`; `python3 evals/harness/dryrun.py` → `46/58` (same as before the redesign). Never run in a real eval.
- **Eval results** (all committed):

  | Run | Iteration 6 | Iteration 5 (re-graded) | Milestones (iter. 5) |
  |---|---|---|---|
  | rl incremental | 47/47 | 46/47 | 4 (7) |
  | rl all-at-once | 46/47 | 43/47 | 4 (4) |
  | quant incremental | 54/58 | 52/58 | 10 (5) |
  | quant all-at-once | 52/58 | 53/58 | 5 (5) |

  - **rl blind judge:** all-at-once 8.0, incremental 7.9. The quant judge is skipped because of S3.
  - Full detail: [evals/results-iteration-6/findings.md](evals/results-iteration-6/findings.md), which covers S1–S8 status and new findings N1–N4.
- **Open issues from iteration 6:**
  - **S1:** idea-refine pre-splits stages, and rl all-at-once's spine-count carve-off made a leftover M4. The redesign appears to address both.
  - **S3 quant:** pipeline-design wrote `pipelines.md` for only 2 of 6 packages. Not addressed by the redesign: no `dt status` check flags up-front packages that have no `pipelines.md`.
  - **S5 harness:** `docstats.py` still uses the old fixed budgets.
  - **N1–N4:** see findings.
- **Raw runs:** `../dev-team2-workspace/iteration-{5,6}/<trajectory>/with_skill/`, holding `project/` (git, one commit per turn), `turns.json`, `grading.json` and `agent_stream.jsonl`. Packaged copies are in `<iteration>/bench/`.

## Active files

```
evals/harness/driver.py        — committed; re-asks blocked stage moves, STALL_LIMIT=4 stall stop
evals/harness/grade.py         — committed changes + UNCOMMITTED redesign edits (stage rows); stage→milestone mapping, first_planned_rest_designed, milestone_depends
evals/harness/dtprobe.py       — committed (outline, depends) + UNCOMMITTED (stage fields)
evals/harness/docstats.py:54   — BUDGETS = {"contract": 60, "pipelines": 120, ...}: stale fixed budgets (S5 harness defect)
evals/harness/judge_prompt.py, blind_judge_prompt.md — milestone_quality item committed; prompt has an uncommitted 2-line edit
evals/harness/scenarios.json   — per-stage "keywords" used to map all-at-once rows to stages
evals/results-iteration-{5,6}/ — findings.md, grading-*.json, docstats-*.json, judge-rl*.json (read first)
scripts/devteam/commands/lint.py — contract-heading, milestone-size, per-unit budget, grow-size (committed) + UNCOMMITTED redesign
scripts/devteam/model.py, commands/roadmap.py — UNCOMMITTED: stage rows, Cut status
skills/*/SKILL.md, design/planning-stage.md, README.md — UNCOMMITTED redesign wording
```

## Changes made

Commits made this session or by its side sessions, oldest first, on `planning-stage-build` and carried into the current branch:

- `ec9b430` **Driver fixes and iteration-5 results:**
  - A stage move blocked by `readiness()` used to send a message that already introduced the next stage. Now it re-asks the simulated user.
  - The simulated user used to end incremental runs at stage 1's build setup. Now it introduces the next stage.
  - The run stops as `stalled: …` after 4 blocked moves in a row with no doc change.
  - `gate_discipline` ignores pipeline-design's `**Used by:**` appends.
- `8f2dd62` **Grader maps milestones to stages:** a stage may have several milestones. They're matched by Source in incremental runs and by keywords in all-at-once. `first_planned_rest_designed` replaces the two per-mode plan checks. `refs_milestones` accepts reuse on later milestones.
- `55e91af` **Merge of the S3/S4 side-session branch** (`4f26a36`, `ea9ad2a`, `cd125be`):
  - a `contract-heading` lint error, since multi-symbol headings had made build-planning rewrite contracts;
  - up-front scope rules in spec-writing, pipeline-design and build-planning;
  - the per-track `milestone-size` cap of 15;
  - per-unit budgets (contract 8 lines per symbol + 12, pipelines 35 per pipeline + 10 + layout, tests 10 per case + 15) plus a `grow-size` warning.
- `1947e13` **Milestone checks:** a `milestone_depends` grader check (every milestone after the first has valid, acyclic Depends) and a `milestone_quality` blind-judge item.
- `8f6562e` **Iteration-6 results:** made by the iteration-6 session, on the current branch only.

A `git checkout` or stash would discard the uncommitted redesign; see Current state.

## Failed attempts

- **Counting the whole Phase 0 spine in the per-track cap (`ea9ad2a`):** a milestone with 9 independent pipelines counts as 9 serial tasks, so build-planning and idea-refine still carved off leftovers. This happened in iteration 6, and quant incremental went to 10 milestones. The redesign counts only the serial Phase 0 tasks.
- **The spec-writing up-front rule alone (S3):** it fixed rl but not quant. The agent proposed "start with `data` and `core`, which M1 needs" at the pipeline gate, and the simulated user agreed. A wording rule doesn't hold without a `dt status` check.
- **Expanding `IDs: all` in dt's `inferred_pipelines`:** rejected, because every brief-sourced row would infer every pipeline and mark them Designed off M1's pipelines.
- **Killing a looping driver with `pkill`:** this cost `summary.json`, so `finished` fails for iteration-5 quant incremental. The stall limit makes that unnecessary now.
- **Red herrings:**
  - A macOS "access data from other apps" prompt during iteration 5: no eval command touched other apps' data, and the source is unknown.
  - The account's 5-hour usage stayed at 3% despite about $100 of API-priced eval use, even though the runs do use the subscription (`apiKeySource: "none"`).
  - Auto mode blocked a read-only `grep` right after the `pkill`.

## Next steps

BLOCKED (needs user): the uncommitted redesign isn't this session's. Its author should confirm it's finished, and choose a branch: `stages-and-contract-phase0`, or bring it to `planning-stage-build`, which also lacks `8f6562e`. Related unmerged worktree branches whose status is unknown: `claude/quizzical-khorana-8b0877` ("Enforce frozen boundary contracts (CR-09)") and `claude/flow-script-eval-viz-fc9417` ("runflow + runviz" run visualisation).

1. Add the S3 guard the redesign lacks. In up-front mode, `dt status --skill pipeline-design` should report every package with no `pipelines.md` (with its uncovered IDs), and the pipeline gate should fail while any remain. Proposal: iteration-6 findings S3.
2. Point `evals/harness/docstats.py:54` at `dt lint`'s per-unit budgets instead of the fixed `BUDGETS`.
3. Re-run the zero-cost checks (`plugin.py`, `simulate.py`, `dryrun.py`, expect 46/58) and a smoke run. Then run `evals/harness/run.sh iteration-7` in the background: about $90, about 1.5 h, and the user approves the spend.
4. Grade, write `evals/results-iteration-7/findings.md` in the iteration-6 format, and run the blind judge for both projects (`judge_prompt.py`, A/B shuffled, key kept). Whether S1 and S3 are really fixed decides what comes next. n=1, so a single run's milestone count is noisy.
