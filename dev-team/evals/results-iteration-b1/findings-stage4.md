# Build eval iteration b1: stage 4 (minilab, n = 1)

Claude Code 2.1.302, every agent `claude-opus-5-5`, one run at a time. Runs: `dev-team-workspace/iteration-b1/s4-minilab-<arm>-r1/`; pages here under `s4-minilab-<arm>-r1/`.

## Go / no-go (interface-first-design.md §12, stage 4)

| Criterion | Result | |
|---|---|---|
| A3 ≥ 1.5× faster than A0 | A3 1,340 s vs A0 1,069 s: **0.80×** | **no-go** |
| No merge conflicts | 0 in every arm | go |
| ≤ 1 mid-build interface change | 0 in every arm (the planted flaw was caught before the freeze) | go |

| | A0 (one session) | A1 (build skill, cap 1) | A3 (build skill, cap 6) |
|---|---|---|---|
| Wall clock | 1,069 s | 3,648 s | 1,340 s |
| Cost | $8.18 | $20.84 | $15.84 |
| Design checks | 21/21 | 21/21 | 22/22 |
| Golden · holdout · beliefs · mutants | 8/8 · 6/6 · 3/3 · 16/16 | all pass | 8/8 · 6/6 · 3/3 · 16/16 |
| Peak agents in flight | 1 | 1 | 6 |
| Harness rejects (driver read the status line too strictly; fixed 66c2755) | — | 8 | 1 |
| Findings recorded | 2 Important, 1 Suggestion (its own exit note) | 18 Important, 1 Critical overridden | 24 Important |

**Where A3's time went** (from `dt-build/log.jsonl`): contract change and revision 154 s; the interface task 406 s (A0: 174 s); the barrier interface review 100 s; **the 19 parallel tasks and 7 testers 341 s (A0: 735 s for the same tasks, 2.2× slower)**; the system task 108 s (A0: 93 s); the two exit reviews 180 s (A0 runs no reviews). The parallel part delivers; the fixed costs (a cold-context interface agent, the barrier and exit reviews, per-agent start-up) eat the gain on a 21-task milestone. A0 also reviews nothing, so it is the floor on overhead, not on quality.

## What the live runs found (all fixed and committed before the runs graded here)

- **The planted flaw is caught before the freeze.** A0, A1 and A3 all saw `risk.Drawdown` lacks `trough_date` while doing the interface task and escalated (A1, A3: `CONTRACT-CHANGE` from M1-T01) or asked (A0); one aborted run caught it at the barrier review instead. So `interface_changes ≤ 1` measures nothing here: the flaw needs to be one an interface task can't see (e.g. a field only a golden case reveals).
- **Smoke tests that pin spine values deadlock the thickens** (A1's first full run stalled at 15/21): the wiring tasks' smoke tests asserted the spine output, the thickens must change it and can't edit those files, and `--test-stands` left no way through. The minilab plans now say a smoke test checks the run and its shape only (3bfadbe). build-planning's tasks.md should say the same; that skill is the iteration-9 session's, so it is not changed here.
- **Plugin fixes:** reviewer/tester/implementer templates now say to run commands in the form the allow rules match (Opus used `git -C <abs>` and absolute script paths, refused for background agents; 6fd848d); the build skill reads the status line as the final message's last line (66c2755); `dt land` lets a re-freeze task's frozen contract folders pass the merged-tree gate (67be1df).
- **Harness fixes:** the persona (a revision before the freeze needs no re-freeze; an open escalation decides before any wording), cumulative session cost, the suite judged on intent tests over the build's own exports, `git add`/`git commit` allowed for the build arms.
- **A real bug the review caught and the persona overrode** (A1): `max_drawdown` reports the wrong peak date on a tie (RISK-05); the holdout cases don't cover ties.

## Validity

n = 1. A0 ran on the plan before the smoke-test rule (it wrote shape-only smoke tests anyway); A1 before the status-line fix. The iteration-9 planning evals ran in parallel during A0, sharing rate limits. Stage 5 reruns every arm fresh with all fixes, n = 3, arm order rotated.
