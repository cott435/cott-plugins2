# Archive: three-skill evals (iterations 1–4)

Evals of dev-team2's **first three skills** (`idea-refine`, `spec-writing`, `architecture-design`), run 2026-10-14 to 2026-10-16. Each trajectory stopped at an approved architecture; nothing past it (pipelines, tests, plans, build setup) existed yet. They're kept as the baseline for the define/design layers and as the record of why those skills read the way they do.

The current harness (`../../harness/`) evaluates the whole planning flow through `build-setup`, with merged quant stages. Its results aren't comparable one-to-one with these.

## What was run

| | |
|---|---|
| Skills | `idea-refine`, `spec-writing`, `architecture-design` |
| Harness | `evals/harness/` at commit `6e335e5` (`git show 6e335e5:evals/harness/driver.py`) |
| Scenarios | [scenarios.json](scenarios.json): rl in 3 stages (snake, fish, foraging); quant in 6 (data, statistics, portfolio_classical, features_ml, forecasting_nn, agents) |
| Assertions | [evals.json](evals.json): 26 for rl, 28 for quant (brief size and goals, Given/When/Then, no vendors in spec, `arch-status` coverage, gate discipline, …) |
| Models | agent `claude-opus-5-5`, simulated user `sonnet`, n = 1 per configuration |
| Raw runs | `../dev-team2-workspace/iteration-{2,3,4}/` (outside the repo; iteration-1 raw output wasn't kept) |

## Iterations

| Iteration | Skills at | Ran | What it tested | Result |
|---|---|---|---|---|
| 1 | `9041ad6` | all 4 trajectories | First version of the three skills | All-at-once 100%; incremental 91%. Found doc growth from superseded content kept in full, vendor leakage into the spec, gates not stopping |
| 2 | `00e1b86` | all 4 | Append-only growth rules, spec hygiene check, gate stops, skill routing | Incremental 96.5%; brief goals still grow per stage |
| 3 | `cd01171` | incremental only | Out-of-scope sweep, Changelog-based change detection (`arch-status.py`), revise-in-place for partly changed decisions | Only brief-goal checks fail; change detection worked live for the first time |
| 4 | `380ba67` | incremental only | architecture-design Changelog IDs, Context revisions, Extend sweep | rl 25/26, quant 27/28; the only failures are brief goals (fixed by `docs/roadmap.md` in the planning stage) |

Each `results-iteration-N/` holds the grading, doc stats, blind-judge outputs and (from 2 on) `comparison.md`, which lists exactly what changed and why.

## Cost and time (iteration 4, Opus agent, through architecture only)

| Run | Turns | Agent cost | Wall clock |
|---|---|---|---|
| rl incremental | 17 | $7 | 27 min |
| quant incremental | 30 | $21 | 71 min |

Per quant stage this was 4–6 turns, about 10 minutes and $2.50–5, rising as the session's context grew. (`summary.json` files from these runs overstate cost about 10×: they summed a cumulative figure per turn. `grading.json` and `turns.json` are right.)
