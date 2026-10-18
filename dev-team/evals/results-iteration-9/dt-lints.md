# Iteration 9: the review-ab lint table as dt lints

`review-ab.md` (branch `claude/review-ab-noise`), §"Defects that could be deterministic dt lints instead", listed lints that would catch part of what the final reviewer found, and most of what it missed. These landed in `dt` (rules in `scripts/README.md`). Each was run over the four iteration-9 final projects, read from clones: quant-all-at-once at `9ece2e6` (turn 50), the rest at HEAD. R = reviewer finding, J = judge defect, as in `review-ab.md`.

| Lint | Sev | rl-inc | rl-aao | quant-inc | quant-aao |
|---|---|---|---|---|---|
| packet closure in `dt context` | — | 132 sections pulled, 24 of 31 packets | 191, 26 of 30 | 168, 36 of 46 | 75, 38 of 48 |
| `(from M1-Txx)` in `dt context` | — | 3 paths | 1 | 10 | 22 |
| `packet-type-closure` | W | 0 | 6 | 19 | 17 |
| `milestone-lines` | E | 2 | 0 | 9 | 7 |
| `milestone-order` | E | 0 | 0 | 0 | 0 |
| `parallel-step` | W | 1 | 2 | 0 | 0 |
| `exit-cases-in-scope` | E | 0 | 2 | 0 | 1 |
| `kind-title` | E | 0 | 0 | 12 | 0 |
| `covers-vs-deferred` | E / W | 0 / 2 | 0 / 3 | 3 / 6 | 0 / 4 |
| `closed-open-question` | W | 0 | 2 | 3 | 0 |
| `process-narration` | W | 4 | 0 | 0 | 8 |

## What each caught

- **Packet closure (`packet-type-closure`, the "better still" half).** `dt context` now pulls every contract section a packet's symbols' signatures name, until nothing new is named. It finds the named cases:
  - rl-inc M1-T06 gets `core.Transition`; M1-T13 gets `core.TeamSpec` and `core.ActionSpace`.
  - rl-aao M1-T09 gets `methods.Transition` and `runlog.Checkpoint`.

  Packets grow by a mean of 13 to 54 lines. The largest is 551 lines, well under the 2,000 budget.

  The lint flags names that no section defines, so no packet can show them:
  - quant-inc `CompanyMsg` and `ActionMsg`, given only as "mirrors…" (R05).
  - rl-aao's preamble aliases `Direction`, `Array` and `Settings`. They are defined above the first section, so no packet shows them.
  - Exceptions and dataframe schemas named in signatures with no section: `LedgerRefused`, `CoverageError`, `BarsSchema`, `StagedRun` and others.
- **`new-but-written`** (now part of `dt context`, not a lint). The packet marks a Writes path `(from M1-Txx)` when an upstream task names that exact path. All five report cases now carry the mark:
  - rl-aao M1-T30 (from M1-T21).
  - quant-inc M1-T45 (from M1-T39).
  - quant-aao M1-T37, M1-T39 and M1-T48 (from M1-T06, M1-T12 and M1-T33).
- **`milestone-lines`.** Every case the report names:
  - rl-inc M2 and M3 have no Exit.
  - quant-inc M2–M10 have no Exit.
  - quant-aao M2–M8 have no Exit; M4, M5, M7 and M8 also have no Skills/References (R11).
- **`milestone-order`.** Nothing in the originals: the defect was the v1 fixer's. On `review-ab/rl-all-at-once` it reports both "M4 comes after M6" and "M4 depends on M6".
- **`parallel-step`** (the half of `parallel-writes` that `writes` lacked).
  - It catches rl-inc M1-T26/T27 (`PL-01.DQNAgent`) and rl-aao M1-T28/T29 (`PL-05.learning_curve`).
  - It also finds rl-aao M1-T25/T26 (`PL-06.final_evaluation`), which the report didn't name.
  - The existing `writes` lint fired nowhere: in these plans, no two tasks without a path between them had overlapping Writes.
- **`exit-cases-in-scope`.** Three finds, none of them named in the report:
  - rl-aao M2's Exit names TC-24 and M3's names TC-25. Both are PL-06's, which neither milestone lists.
  - quant-aao M1's plan Exit names TC-13, which is PL-13's.
- **`kind-title`.** quant-inc M1-T06 (J), plus 11 more of the same fold pattern: a task titled "… spine" with Kind thicken. `phase0.md` says a fold is "never a spine".
- **`covers-vs-deferred`.**
  - E: quant-inc M1-T04 and M1-T05 cover DATA-01, and M1-T18 covers CHECK-09. All three are Deferred (R45).
  - W: rl-aao M1-T12's TRAIN-01 (R25) and 14 more tasks that cover an ID another step's Covers cell owns.
- **`closed-open-question`.**
  - rl-aao pipelines.md: both bullets (R24).
  - quant-inc qrisk pipelines.md (R43), plus qfcst and qfeat, which the report didn't name.
- **`process-narration`.**
  - rl-inc: AD-09 and AD-13 "adopted before M1" (R28), "golden values don't change", and "TC-01–TC-49 don't change" (R29).
  - quant-aao: "revised 2026-10-18" (R24, R25), six "confirmed / decided / chosen by the user, <date>", and "TC-30–TC-33's answers are unchanged".

## Not caught, and why

- **quant-aao M1-T05/T06 `parts.py`.** The tasks are on different steps, and only the acceptance prose ("appended as parts") shows the dependency.
- **rl-aao M1 Exit: fish TCs inside a snake range.** The fish and snake cases share M1's pipelines, so pipeline membership can't separate them.
- **rl-inc `core.SOLO`.** It is a constant named only in Invariants prose. The closure reads code and the Errors bullet only.
- **quant-inc M1-T03's api messages.** The explorer's `api.Schema` is a generated TypeScript type and names no contract type.
- **The Replan notes in plan.md (R30, R47).** Left alone on purpose: build-planning `replan.md` requires a dated `## Replan notes` log in the plan. Only a Replan notes section outside a plan is flagged.
- **"(assumed: …)" Open questions with no route** (quant-aao R22, R23). Nothing in the docs shows the assumption is settled.
- **covers-vs-deferred's "Covers and Deferred account for every ID".** That is `dt status`'s `uncovered`, which already exists.
