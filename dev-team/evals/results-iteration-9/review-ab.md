# Iteration 9: does a final plan review raise the blind judge's scores?

**Question.** A final reviewer agent gets the user's own words and the finished docs, and lists defects. A fixer then applies them. Does the pair raise the blind judge's scores enough to be worth adding to the skills?

**Method.**
- **Copies.** Iteration 9's four finished projects were copied to `dev-team-workspace/review-ab/<traj>/with_skill/`, laid out like a driver run: `project/` with its git history, the run's `plugin/`, `turns.json` and `grading.json`. The originals were never touched. Packaging the untouched copies with `package.py` reproduced `iteration-9/bench` byte for byte. So every score change below comes from the review edits alone.
- **Reviewer.** `harness/plan_review.py` runs it with the prompt in `harness/plan_review_prompt.md`: `claude -p`, Opus 5.5, Read/Glob/Grep only, started in `project/`. It reads:
  - `.review/user_messages.md`: every `turns.json` user message, in order.
  - `docs/`, `tasks/` and `references/`.
  - One `dt context` packet per task.
  - `dt lint` output.

  It returns defects in five classes (user_fact, stale, packet, milestone, domain), each with file, quote, evidence, fix and severity.
- **Fixer.** `harness/plan_fix_prompt.md`, run with Read/Edit/Glob/Grep plus Bash for the run's own `dt` only. It applies the list to `docs/` and `tasks/` (never `tests/`, `references/` or build-setup files), runs `dt lint`, and commits the result as "plan review fixes".
- **Judge.** Each fixed copy was re-packaged with `package.py`. The blind judge then ran for each trajectory with original against reviewed, in both orders (`judge_prompt.py --both`, `run`, `average`): 4 pairs, 8 calls.
  - Set-1 is the original (`iteration-9/bench`) and set-2 the reviewed copy (`review-ab/bench`).
  - Prompt folders sat in the session scratchpad. Keys and verdicts are in `results-iteration-9/review-ab/`.
  - The rl-incremental AB judge first returned malformed JSON. It was rerun once through `judge_prompt.judge`; the other seven ran once.
- **Records.** `results-iteration-9/review-ab/<traj>/` keeps each run's `review.json`, `fix.json`, `cost.json` and `fix.diff`.

## Scores (original → reviewed, mean of both orders)

| Item | rl-incremental | rl-all-at-once | quant-incremental | quant-all-at-once | mean Δ |
|---|---|---|---|---|---|
| dependency_graph_soundness | 3.5 → 4 (**+0.5**) | 3.5 → 4 (**+0.5**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | +0.75 |
| interface_quality | 3 → 4 (**+1**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | +1.00 |
| internal_consistency | 2 → 4 (**+2**) | 2.5 → 4 (**+1.5**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | +1.38 |
| milestone_quality | 3 → 4 (**+1**) | 3 → 3.5 (**+0.5**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | +0.88 |
| pipeline_clarity | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4.5 (**+0.5**) | +0.12 |
| right_sizing | 3 → 4 (**+1**) | 3.5 → 3.5 | 4 → 4 | 4 → 4 | +0.25 |
| rl_soundness | 3 → 4.5 (**+1.5**) | 4 → 4.5 (**+0.5**) | — | — | +1.00 |
| stage_completeness | 4 → 4.5 (**+0.5**) | 4 → 4.5 (**+0.5**) | 3.5 → 4 (**+0.5**) | 3 → 4.5 (**+1.5**) | +0.75 |
| task_buildability | 3 → 4 (**+1**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | 3 → 4 (**+1**) | +1.00 |
| quant_soundness | — | — | 4 → 4 | 3 → 5 (**+2**) | +1.00 |
| null_hypothesis_handoff | — | — | 4 → 4 | 4 → 5 (**+1**) | +0.50 |
| reference_use | — | — | 4 → 4 | 3 → 4 (**+1**) | +0.50 |
| ease_of_finding_next_build_step | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4.5 (**+0.5**) | +0.12 |
| layout_sensibility | 4 → 4 | 3.5 → 4 (**+0.5**) | 4 → 4 | 4 → 4 | +0.12 |
| organization | 4 → 4 | 4 → 4 | 4 → 4 | 4 → 4 | +0.00 |
| readability_for_solo_learner | 3 → 3.5 (**+0.5**) | 3.5 → 3.5 | 3.5 → 3.5 | 4 → 4 | +0.12 |
| **content_score** | 3.15 → 4.1 (**+0.95**) | 3.4 → 4 (**+0.6**) | 3.5 → 4 (**+0.5**) | 3.3 → 4.3 (**+1**) | +0.76 |
| **structure_score** | 3.8 → 3.9 (**+0.1**) | 3.75 → 3.9 (**+0.15**) | 3.9 → 3.9 | 4 → 4.15 (**+0.15**) | +0.10 |
| **overall** | 6.95 → **8.0** (+1.05) | 7.15 → **7.9** (+0.75) | 7.4 → **7.9** (+0.5) | 7.3 → **8.45** (+1.15) | **+0.86** |

- **The reviewed copy won all 8 verdicts**, both orders in every pair. No item's two orders differ by more than 1.
- **The gain is almost all content**, mean +0.76 against +0.10 for structure. The items that move are the ones the reviewer's classes target:
  - internal_consistency +1.4.
  - interface_quality and task_buildability +1 everywhere.
  - milestone_quality +0.9.
  - dependency_graph_soundness +0.75. It was flat at 4 in all eight iteration-9 scorings, and here it moved.
- **Structure barely moves.** Organization, layout and readability are untouched by fixes that keep each doc's shape.

### Position effect

The review effect is the mean of the two orders' (reviewed − original) margins. The position effect is half their difference.

| | rev − orig, AB (rev is B) | rev − orig, BA (rev is A) | Review effect | Position effect (for Set A) |
|---|---|---|---|---|
| rl-incremental | +0.9 | +1.2 | **+1.05** | 0.15 |
| rl-all-at-once | +0.6 | +0.9 | **+0.75** | 0.15 |
| quant-incremental | +0.5 | +0.5 | **+0.5** | 0.0 |
| quant-all-at-once | +1.0 | +1.3 | **+1.15** | 0.15 |

- The position effect is about 0.1 here, against 0.4–0.45 in iteration 9's mode comparison.
- The review effect is 3–10 times the position effect in every pair. Unlike the mode comparison, this one is not noise.

### Caveat: a pair of near-twins inflates the paired margin

The two sets differ only by the fix diff, so the judge scores the diff. The judges said so: "The two sets are near-identical in skeleton… B comes out ahead because of a number of concrete fixes."

This cuts both ways.

**1. The original scores lower beside its fixed twin than beside the other mode.**

| | Original in iteration 9 (vs other mode) | Original here (vs reviewed) | Reviewed here |
|---|---|---|---|
| rl-incremental | 7.65 | 6.95 (−0.7) | 8.0 |
| rl-all-at-once | 7.45 | 7.15 (−0.3) | 7.9 |
| quant-incremental | 7.7 | 7.4 (−0.3) | 7.9 |
| quant-all-at-once | 7.45 | 7.3 (−0.15) | 8.45 |

Measured against iteration 9's own scores, the reviewed sets gain +0.35, +0.45, +0.2 and +1.0, a **mean of +0.5**, not +0.86.

**2. A defect both sets share goes unpunished.** rl-all-at-once's square tank, hits-per-fish scoring and two predators survive in the reviewed copy (§What the reviewer missed). No verdict here cites them. stage_completeness for that original is 4 here, against 3 in iteration 9.

So +0.86 is the size of the fix as this judge sees it side by side. Re-judging the reviewed incremental against the reviewed all-at-once puts the gain on iteration 9's own scale at about zero, not +0.5 (§Calibration).

## What the reviewer found, and the judge's lists

The reviewer listed 152 defects across the four runs. By trajectory:

| | Defects | user_fact | stale | packet | milestone | domain | high / med / low | Applied |
|---|---|---|---|---|---|---|---|---|
| rl-incremental | 46 | 2 | 21 | 14 | 2 | 7 | 4 / 23 / 19 | 45, 1 skipped |
| rl-all-at-once | 27 | 4 | 6 | 11 | 4 | 2 | 1 / 20 / 6 | 27 |
| quant-incremental | 47 | 5 | 12 | 11 | 13 | 6 | 6 / 26 / 15 | 47, 7 only partly |
| quant-all-at-once | 32 | 3 | 11 | 9 | 5 | 4 | 4 / 13 / 15 | 32 |

`dt lint` reports 0 errors on every fixed copy.

The fixer skipped two kinds of fix:
- **Re-splitting rl-incremental's S2 and S3.** The user approved one milestone row per stage at turns 24 and 36.
- **Seven quant-incremental fixes, only partly.** Their golden fixtures live under `tests/`, which the fixer may not edit.

### Matches against iteration 9's judge defects

Iteration 9's judge listed 60 distinct defects and unbuildable tasks over both orders, in `judge-{rl,quant}.{AB,BA}.json`. Seven of them were out of the reviewer's reach:
- Three are facts the user never said in that run.
- Two are cuts the user agreed to in their own words.
- One is the missing CONSTRAINTS.md, which is build setup and out of scope.
- One is AGENTS.md, a file outside the reviewer's scope.

Of the remaining 53, the reviewer found **30 (57%)**.

| | Judge defects | Reviewer found | Out of reach | Missed |
|---|---|---|---|---|
| rl-incremental | 16 | 10 | 0 | 6 |
| rl-all-at-once | 16 | 9 | 0 | 7 |
| quant-incremental | 15 | 7 | 3 | 5 |
| quant-all-at-once | 13 | 4 | 4 | 5 |
| **total** | **60** | **30** | **7** | **23** |

**Found, and fixed in the reviewed copy.** The new judges no longer cite these:
- **rl-incremental:**
  - "TC-01–TC-49 don't change" (R29).
  - AD-09's process narration (R28).
  - The plan Exit's TC-15 (R44).
  - `with_seed` missing from the contract (R25).
  - M1-T06's missing core.Transition (R03) and M1-T13's missing TeamSpec/SOLO/ActionSpace (R24).
  - M2 and M3 without Exit (R04).
  - M1-T05 sized XS (R18).
  - M1-T26 and M1-T27 sharing `agent.py` (R17).
- **rl-all-at-once:**
  - The M2 leftover milestone (R18). The Outline was rewritten around the DQN work; the milestone wasn't re-cut.
  - Stale pipeline Open questions (R24).
  - The unfrozen snake observation layout behind M1-T15 (R16).
  - TC-17's "at most 1 of 20 seeds" (R20).
  - M1-T12 Covers TRAIN-01 (R25).
  - M1-T09's missing Transition and Checkpoint (R08).
  - M1-T28 and M1-T29 missing `curve.py` (R14).
- **quant-incremental:**
  - SSE instead of WebSocket (R02).
  - yfinance instead of yahooquery (R01).
  - The $49 Sharadar line against the $50 budget (R33).
  - No qdata golden cases (R23): TC-74–TC-79 were added, without fixtures.
  - M1-T18 Covers a deferred CHECK-09 (R45).
  - CompanyMsg and friends given only as "mirrors…" (R05, partly).
  - M1-T45/T39 still calling `mark_books` (R10, partly).
- **quant-all-at-once:**
  - SSE (R01).
  - No ML information-gain test in S3 (R02, now SIG-05).
  - No References/Skills lines on M4–M8 (R11).
  - `check_moves` seeing only a ReturnsPanel (R07).

**Out of reach (not a reviewer failure).**
- **quant-all-at-once: yahooquery, the 10 delisted names, api.sharadar.com.** In this run the simulated user never mentioned them; `grep` over its 50 messages finds no "yahoo", "delisted list" or "sharadar.com". The judge knows them from the scenario's facts. Iteration 9's finding "the run lost them" is wrong for this trajectory: the user never gave them.
- **quant-incremental: PPO agents cut from S4.** Turn 47 has the user say "Two stages: forecasting first (S4), agents later as a separate idea". That's a cut in the user's own words, which the judge's scenario facts don't know about. The reviewer was right not to flag it.
- **quant-all-at-once: CONSTRAINTS.md missing.** The run was truncated, and build setup was out of the fixer's scope.

### What the reviewer missed

**1. User facts from the first message (the costliest miss).**
- **rl-all-at-once.** The spec's "FISH-01 The tank is a square with walls", "FISH-04 … hits per fish per episode" and "PREY-01 … 2 predators", with no opponent pool, all contradict turn 1: "a circular tank", "survive as long as possible", "a learning predator", "co-evolution / self-play". No later message changes them.
  - The reviewer read all 16 messages and still filed only four user_fact defects, none of these. It seems to have read turn 2's "go ahead and converge" as approving whatever the brief then said.
  - This was the judge's top rl-all-at-once complaint, and it survives in the reviewed copy.
- **quant-incremental: not a miss.** "every model trains on the user's machine" follows turn 48: offered a constraint edit for the GPU, the user answered "Keep training local on Apple Silicon, no brief change." That is a cut in the user's own words, like the PPO cut. The judge's scenario facts don't know it, so the judge keeps citing it (§Facts-checklist reviewer v2).
- **Fix for the prompt:** a separate first step that lists every fact, number and named choice in each user message as a checklist, then checks each against spec and architecture by grep, before any other class. Free-form reading lets packet defects crowd out the user's facts. 35 of rl-incremental's 46 defects were stale or packet.

**2. Stale brief framing.**
- rl-incremental's "Not doing: Designing future environments now" and "For Snake, the first environment".
- quant-incremental's "Real-money trading — … not in this first stage".
- The reviewer seems to have taken the approved brief as settled, not as a doc that can go stale as later stages land.

**3. "(new)" on a file an earlier task already wrote.** This happens five times:
- rl-all-at-once: M1-T30 writes `pl03_batch.py` (new), already written by M1-T21.
- quant-incremental: M1-T45 writes `runs/pipeline.py` (new), already written by M1-T39.
- quant-all-at-once: M1-T37 `fetch.py`, M1-T39 `moves.py` and M1-T48 `pl27_membership.py`.

The reviewer never caught one; the new judges still cite two. The packet is generated, so the reviewer probably didn't question the "(new)" marker.

**4. Plan shape the reviewer saw but didn't report.**
- quant-incremental: M1-T06 is titled a spine but has "Kind: thicken".
- quant-all-at-once: M2 holds 16 pipelines while M5 holds 2.
- quant-all-at-once: M1-T01 is one M-size interface task spanning three packages.
- quant-all-at-once: references.md has "**Milestones:** S2".
- rl-incremental: M1 is the whole of S1.
- rl-incremental: PL-01's step table lists steps its entry never calls.
- rl-incremental: frozen private helpers (`gae`, `returns_to_go`).
- rl-incremental: AD-16 cites CR-12 without saying what it is.
- rl-all-at-once: M1-T27's wrong Covers, and `evaluate.compare` with no Boundary line.

### What the fixes broke

The new judges cite these in the reviewed sets, and they weren't in the originals:
- **rl-all-at-once: milestone IDs out of build order.** R01 split S2 into "One fish", "Many fish" and "Local sight". The fixer's no-renumbering rule made them M3, M5 and M6, sitting before M4, so the build reads M3 → M5 → M6 → M4. Both orders cited it. It held that set's milestone_quality to 3.5. The fixer rule needs an exception: new milestones in a stage may renumber Designed milestones that have no plan yet.
- **rl-incremental: the M1 interface now freezes M2/M3 symbols.** The reviewer saw M1-T21's packet listing FishTank, PPOAgent and OpponentPool. It offered two fixes: freeze them all in M1-T01, or keep only M1 types. The fixer took the first, which is the defect iteration 9's judge had named ("context__M1-T21.md: … symbols not in M1 (bloat)").
- **rl-incremental: a brief/spec contradiction resolved by weakening the brief.** "each environment's ladder matches or beats a simple scripted player" now reads below the user's "beats … a simple scripted baseline". The reviewer quoted turn 4's finer bars for some rungs; the judge's facts say "beats". This is a judgment call, but the fix should have kept the user's words and narrowed the spec's exceptions.
- **quant-incremental: interfaces serialized and edits half-propagated.**
  - R07 made M1-T03 depend on M1-T02, serializing two interface tasks.
  - PB-03 still lists yfinance's docs after the yahooquery switch.
  - AD-07 now says "the brief asks for a WebSocket", which it doesn't.
  - M8's Exit TC range now overlaps M9's pipelines.
- **quant-incremental: docs and fixtures disagree.** The fixer couldn't touch `tests/`. TC-72, TC-30 and the "at most 3 of 20 seeds" tolerances changed in `tests.md` but not in their fixtures, and TC-74–TC-79 have no fixture folders. The judge doesn't read fixture contents, so this cost nothing here, but a builder would trip on it. A reviewer that changes expected outputs must route them through test-planning (the golden-case rule), not the fixer.

## Cost

| | Reviewer | Fixer | Total | Minutes | Planning run cost | Review as % of run |
|---|---|---|---|---|---|---|
| rl-incremental | $3.03 (29 turns) | $3.10 (124) | $6.13 | 15.2 | $24.46 | 25% |
| rl-all-at-once | $1.71 (19) | $2.21 (79) | $3.92 | 8.9 | $14.80 | 26% |
| quant-incremental | $4.88 (62) | $4.03 (170) | $8.91 | 19.9 | $42.57 | 21% |
| quant-all-at-once | $3.86 (46) | $5.54 (191) | $9.40 | 19.8 | $35.22 | 27% |
| **total** | $13.48 | $14.88 | **$28.36** | | $117.05 | 24% |

- Mean **$7.09** per run, about **$8 per overall point gained**: $7.09 / 0.86, or $14 per point on the +0.5 absolute estimate.
- The judge calls aren't in this table, because `judge_prompt.py run` doesn't record cost.

## Verdict

**Not yet.** Side by side with its own original, the reviewed copy won every verdict by +0.86. The gain lands on the content items the skills have been stuck on: internal_consistency, task_buildability, interface_quality and milestone_quality. But judged against the other mode, as iteration 9 was, the reviewed plans score the same as the originals (§Calibration). The cross-set verdicts turn on user-fact and scope defects that v1 left in place, and on the fixer's own regressions. The review costs about a quarter of a planning run.

What it needs before it goes into the skills:
1. **A user-facts checklist pass first** (missed item 1). That is where the largest single defect in iteration 9 sits, and free reading missed it.
2. **Fixer rules:**
   - Let a new milestone renumber unplanned ones.
   - When the reviewer offers two fixes, take the narrower one.
   - Keep the user's words when a brief and a spec disagree.
   - Route expected-output changes to test-planning.
3. **Move the mechanical half into dt (below).** About a third of the reviewer's list, and most of what it missed, needs no model. A lint that runs on every edit beats a $7 pass at the end.

## Defects that could be deterministic dt lints instead

Each is checkable from the parsed docs alone. Each lists the defects in this run it would have caught (R = reviewer, J = iteration-9 judge).

| Lint | Rule | Caught here |
|---|---|---|
| `new-but-written` | A Writes path marked new in `dt context` while an ancestor task in the plan already writes it. dt already knows both, so the packet should say "(from M1-Txx)". | J: rl-aao T30; quant-inc T45; quant-aao T37, T39, T48. Missed by R. |
| `parallel-writes` | Two tasks with no path between them in the graph write the same file, or a task's acceptance needs a file only a non-ancestor writes. | J and R: rl-inc T26/T27; quant-aao T05/T06 `parts.py`; rl-aao T28/T29 `curve.py` (R14). |
| `packet-type-closure` | Every type named in a Read symbol's signature or fields, or in the task's step In/Out cell, is either in the packet or a library type. Better still, `dt context` pulls the nested types itself. | R: 45 packet defects across the four runs, e.g. T06 Transition, T09 Checkpoint, T13 TeamSpec, quant-inc T03 api.*, T19, T46. J: most of the 15 unbuildable tasks. |
| `milestone-lines` | Every Designed or Planned milestone has an **Exit:**. In a stage split into more than one milestone, each milestone has **Skills:** and **References:** (`build-planning/references/cut.md`). | R and J: quant-inc M2–M10 Exit; quant-aao M2–M8 Exit and References; rl-inc M2/M3 Exit; quant-inc M2 Skills. |
| `milestone-order` | Roadmap milestone IDs increase in table order, and each Depends cell names lower IDs. | The fixer's M3 → M5 → M6 → M4. |
| `exit-cases-in-scope` | Each TC an Exit or Outline names belongs to a pipeline in that milestone's Pipelines cell. Each TC range has no gaps. | R: rl-aao M1 Exit (fish TCs in a snake range), rl-inc TC-15 counted twice (R44), quant-inc M8/M9 (R19). |
| `covers-vs-deferred` | A task's Covers ID is neither in its plan's Deferred list nor missing from its step's Covers cell. The plan's Covers and Deferred lists together account for every requirement of its stage. | R and J: quant-inc T04/T05 DATA-01 and T18 CHECK-09 (R45); rl-aao T12/T27 TRAIN-01 and the missing Deferred IDs (R25). |
| `kind-title` | A task title saying "spine" or "thicken" agrees with its **Kind:**. | J: quant-inc M1-T06. Missed by R. |
| `sketch-vs-steps` | Every call in an entry sketch names a step or a contract symbol, and every step-table row is called by the sketch. `dt layout` does this for code; the sketch is Python too. | J: rl-inc `with_seed` (R25) and PL-01's uncalled steps (missed). |
| `field-type-boundary` | A contract type's fields use only types from components its architecture row depends on. | New judges, top rl-aao citation: `runlog.RunRecord.config: RunConfig` breaks "`runlog` → core" (R06). |
| `closed-open-question` | An Open questions bullet that says "routed to" or "(assumed: …)" for a route `routes.md` marks closed. | R and J: rl-aao pipelines (R24); quant-aao data pipelines and engine tests (R22, R23); quant-inc qrisk (R43). |
| `process-narration` (warning) | Phrases like "adopted before M1 is built", "revised 2026-…", "Confirmed by the user, <date>", a `## Replan notes` section, or "TC-01–TC-49 don't change". | R and J: rl-inc AD-09, Risks and Replan notes (R28–R30); quant-inc Replan notes (R47); quant-aao "revised 2026-10-18" (R24, R25). |
| `no-golden-cases` (warning) | A package with pipelines in the planned milestone whose `tests.md` defines no TC. | J and R: quant-inc qdata (R23). |
| `verify-target` | A task's **Verify:** command names a test file or target that no task's Writes creates. | J: quant-inc M1-T45 `pl01_system`. Missed by R. |
| `layout-vs-writes` | Every file a task writes under a package appears in that package's Planned layout. | New judges: rl-aao `charts/` omits `check.py` and `style.py`. |

**Not lintable:**
- User facts. The closest is a facts ledger: idea-refine records each user-stated fact with its quote, and a lint checks that each fact ID is cited by the spec. That is a skill change, not a dt one.
- Sizes against work.
- Statistical tolerances (TC-17's 1 of 20).
- Domain errors.

These stay with a reviewer. The lints above would cut its list by about a third and leave it the part only a model can do.

## Calibration: the reviewed plans on iteration 9's own scale

The blind judge compared the reviewed incremental set with the reviewed all-at-once set for each project, in both orders. This is iteration 9's pairing exactly, with the same `judge_prompt.py --both`, `run` and `average`, and prompt folders `judge-rl` and `judge-quant` in the scratchpad. That is 4 calls. Keys and verdicts are in `review-ab/calibration/`. Each reviewed score is set against the same project's score in iteration 9's `judge-{rl,quant}.json`.

| Overall | Iteration 9 (original) | Reviewed | Δ | Paired Δ (above) |
|---|---|---|---|---|
| rl-incremental | 7.65 | 7.4 | −0.25 | +1.05 |
| rl-all-at-once | 7.45 | 7.35 | −0.10 | +0.75 |
| quant-incremental | 7.7 | 7.8 | +0.10 | +0.5 |
| quant-all-at-once | 7.45 | 7.65 | +0.20 | +1.15 |
| **mean** | 7.56 | 7.55 | **−0.01** | +0.86 |

- **The review gain on iteration 9's scale is about zero.** The four Δs fall on both sides of zero, and none is bigger than the 0.4–0.45 position effect iteration 9 measured. The +0.5 estimate above, which put a paired score beside an unpaired one, was an artifact of the near-twin pairing.
- **The items the paired judges moved don't move here.** Mean Δ over the four sets:
  - internal_consistency 0 (+1.38 paired).
  - interface_quality 0 (+1.0).
  - task_buildability +0.25 (+1.0).
  - milestone_quality −0.38 (+0.88).
- **The fixes are seen, then outweighed.** The calibration judges no longer cite what was fixed: SSE, yfinance, the $49 line, the missing References lines on quant-all-at-once's M4–M8. Their top complaints are the defects the review left in place:
  - rl-all-at-once's square tank, hits-per-fish scoring, 2 predators and no opponent pool. Both rl judges cite them.
  - quant-all-at-once's missing yahooquery and 10 delisted names. These are out of reach: that run's user never named them.
  - quant-incremental's deferred PPO agents and local-only training. Both are cuts in the user's own words.
- **A fixer regression costs a set points.** Both rl judges cite rl-incremental's M1 interface freezing FishTank, PPOAgent and OpponentPool, which v1's R02 fix put there (§What the fixes broke). They name it an unbuildable task. rl-incremental's interface_quality fell 4 → 3 and its milestone_quality 3.5 → 2.5, its two largest drops.
- **Winners.** rl again splits by order (incremental in AB, all-at-once in BA), as in iteration 9. In quant, incremental now wins both orders; iteration 9 split.

So against a plan from the other mode, the defects that decide a verdict are the user's facts and stage scope, not the stale text and packet gaps the reviewer mostly fixes. A review that ships has to catch the facts, and its fixer must not add a defect of its own.

## Facts-checklist reviewer v2

`harness/plan_review_prompt.md` now opens with a Step 1 that must finish before any other class:
1. List every fact, number and named choice in each user message as a checklist item with its turn.
2. Apply later overrides, only where the user names the new value in their own words. An approval of a proposal is not an override.
3. Grep each item against brief, spec, architecture, ideas and roadmap, and mark it kept, changed, dropped or later.
4. Every changed or dropped item is a user_fact defect.

The reply gains a `facts` array. The prompt names no project's facts, and its search hint is generic. v1 is the prompt at commit 7063212.

Only the reviewer was run (`plan_review.py <copy> review`), on fresh copies of the original iteration-9 projects in `dev-team-workspace/review-ab-v2/<traj>/with_skill/`, laid out as above. There is one run per project, so any single item could flip on a rerun. Records are in `review-ab/v2/<traj>/`.

**The target facts.**

| Fact (user's turn) | Doc | v1 | v2 |
|---|---|---|---|
| rl-aao: circular tank (1) | FISH-01 "a square with walls" | missed | **R01, high** |
| rl-aao: survive as long as possible (1) | FISH-04 "hits per fish per episode" | missed | **R02, high** |
| rl-aao: a learning predator (1) | PREY-01 "2 predators" | missed | **R03, medium** |
| rl-aao: co-evolution / self-play (1) | no opponent pool or past opponents | missed | missed: marked kept on TRAIN-07 "Both teams learn at the same time" |
| quant-inc: rented cloud GPU (47) | spec "every model trains on the user's machine" | not flagged | not flagged, correctly: v2's checklist records the turn-48 override "Keep training local on Apple Silicon" |

- **v2 catches 3 of the 4 real misses.** These include iteration 9's top rl-all-at-once complaint, which the calibration judges still cite in the reviewed copy.
- **Self-play is half caught.** "Both sides learn at once" is kept, but "self-play" asks for play against the agent's own past versions. The checklist matched the item on its weaker reading. The prompt could ask that a named concept be checked for its mechanism, not its label.
- **The checklist is honest.** On the rl run it marked 7 of 40 items changed. Its other changed items are real too: QR-02's 90 minutes per variant against "under ~1 hour training per env", $10 per world against "a few dollars", and the CI digest against "No CI needed" (v1 had all three). On the quant run it marked 4 of 92 items changed: WebSocket twice, yahooquery and the $49 placeholder. All four were already in v1's list.

**Cost and breadth.**

| | v1 cost | v2 cost | v1 defects | v2 defects | v1 / v2 packets read | Facts listed |
|---|---|---|---|---|---|---|
| rl-all-at-once | $1.71 (19 turns, 281 s) | $1.78 (18, 317 s) | 27 | 29 | 30 / 30 | 40 |
| quant-incremental | $4.88 (62, 642 s) | $4.25 (47, 577 s) | 47 | 31 | 46 / 14 | 92 |

- **The checklist itself costs little:** +$0.07 on rl. On quant, v2 came out $0.63 cheaper, but only because it skipped the packets.
- **On the long run it traded breadth for the facts.** On quant-incremental, v2 read 14 of 46 packets. The prompt asks for every spine and interface packet plus ten others once there are 40 or more, and v1 read all 46. Its list shrank from 47 to 31. It dropped v1's nine "no Exit" defects on M2–M10, the qdata golden cases that iteration 9's judge cited (v1's R23), and four packet defects. On the shorter rl run, breadth held: 30 packets each, with the same packet and stale findings.

**Next.** Keep the Step 1 checklist, and add two things before the skills adopt it:
1. A hard packet floor ("read every packet; if there are more than 40, read every spine and interface packet and at least ten others, and say how many you read").
2. Check each named concept for its mechanism, not its label.

The missing-Exit and other mechanical defects should move to the dt lints above, so breadth matters less. One calibration rerun after a v2 review plus fix would show whether the facts close the gap the calibration found.

## Reviewer and fixer v3: on iteration 9's scale

**What changed.**
- **Reviewer** (`plan_review_prompt.md`), on top of v2's facts checklist:
  - A hard packet floor: read every packet. Only with more than 40 may it read fewer, and never fewer than every spine and interface packet plus ten others. It reports `checked.packets` against `checked.packets_total`.
  - A named concept is `kept` only if the docs carry its mechanism, not its label. The prompt gives self-play and walk-forward as examples, so the self-play catch below is partly taught.
- **Fixer** (`plan_fix_prompt.md`), with the four rules from §Verdict:
  - A new milestone may renumber milestones that have no tasks.
  - Of two offered fixes, take the narrower.
  - When brief and spec disagree, keep the user's words.
  - Expected outputs (golden numbers, tolerances, fixture values, a case's expected result) are skipped as "route to test-planning".

**Method.** Fresh copies of the four iteration-9 projects went to `dev-team-workspace/review-ab-v3/<traj>/with_skill/`. Packaged untouched, they matched `iteration-9/bench` byte for byte. Each copy then got `plan_review.py <copy> all` and was packaged with `package.py review-ab-v3`. The blind judge ran reviewed incremental against reviewed all-at-once per project, in both orders, as §Calibration did, from scratchpad folders `judge-rl` and `judge-quant`. The quant AB judge first returned malformed JSON and was rerun once through `judge_prompt.judge`. There is one run per project, so any single item could flip on a rerun. Records, keys and verdicts are in `review-ab/v3/`.

**Scores (overall, mean of both orders).**

| | Iteration 9 | v1 reviewed (§Calibration) | v3 reviewed | v3 Δ vs iteration 9 |
|---|---|---|---|---|
| rl-incremental | 7.65 | 7.4 | 7.7 | +0.05 |
| rl-all-at-once | 7.45 | 7.35 | 7.35 | −0.10 |
| quant-incremental | 7.7 | 7.8 | 7.65 | −0.05 |
| quant-all-at-once | 7.45 | 7.65 | 7.95 | +0.50 |
| **mean** | 7.56 | 7.55 | **7.66** | **+0.10** |

- **Still inside the noise.** The mean moves +0.10, against v1's −0.01. Only quant-all-at-once's +0.50 clears iteration 9's 0.4–0.45 position effect.
- **Winners.**
  - rl: incremental now wins both orders (iteration 9 and v1 split by order).
  - quant: split by order, as in iteration 9.
- **v1's regression is gone.** rl-incremental's interface_quality is back to 4, from v1's 3. No judge cites M2/M3 symbols frozen in M1.

**Packets read and facts caught.**

| | Packets read | user_fact defects | Facts listed (changed) | Defects | Applied / skipped or partial |
|---|---|---|---|---|---|
| rl-incremental | 31 / 31 | 2 | 78 (2) | 40 | 37 / 6 |
| rl-all-at-once | 30 / 30 | 7 | 42 (8) | 27 | 25 / 13 |
| quant-incremental | 46 / 46 (v2: 14) | 3 | 90 (4) | 35 | 34 / 5 |
| quant-all-at-once | 48 / 48 | 4 | 72 (6) | 31 | 31 / 5 |

- **The floor held:** every packet, on every run. quant-incremental's list is 35 defects against v2's 31, but still short of v1's 47. It still misses qdata's "No golden cases yet", M1-T06's spine/thicken title and M1-T23's "SSE" title. iteration 9's judge cited all three, and the v3 judges cite two of them.
- **rl-all-at-once: all four turn-1 facts caught:** the circular tank, survival scoring, one predator and, for the first time, self-play. R04 was flagged on the mechanism: "Self-play needs each side to train against its opponent's past versions." The fixer added PREY-12, an `OpponentPool` in `RunConfig` and the pool in M6's Outline. Both rl judges now credit rl-all-at-once's spec, and stage_completeness went 3 → 4 and rl_soundness 3.5 → 4.
- **quant-all-at-once:** four user facts. Three are new against v1: covariance compared on real data, ML information gain over residual returns, and ML portfolios beating every classical one. It gained most, +0.50. The yahooquery and 10-names complaints remain; they are out of reach, because that run's user never gave them.
- **quant-incremental:** PPO deferred and local-only training were again correctly left alone (the user's own cuts), and both judges still cite them.
- **The renumbering rule worked.** rl-all-at-once's fish split now reads M3 One fish → M4 Many fish → M5 Local sight → M6 Predator-prey, not v1's M3 → M5 → M6 → M4.

**Why rl-all-at-once didn't move: the test-planning rule left the tests behind.** The fixer changed the spec's facts but skipped their test cases as expected outputs. So `tests.md` still has TC-07 and TC-25 "hits per fish (lower)", TC-08 respawn, TC-09 "2 predators" and TC-24 "≤ 90 minutes". Both rl judges list all five as spec/test contradictions. internal_consistency fell 3.5 → 2.0, cancelling the facts' gain. rl-incremental shows the same pattern once: EVAL-07 now keeps the user's "every rung beats the scripted fish", but TC-46 still says rungs 2 and 3, and both judges cite it. The rule is right that golden numbers belong to test-planning, but nothing in this harness runs test-planning after the fixer. So "route it" became "leave it contradicting".

**Fixer regressions this time.**
- **rl-all-at-once, plan order.** To satisfy lint's dependency order, the fixer moved task blocks so M1-T13 sits after M1-T15 and M1-T24 after M1-T26. It also inserted PREY-12 between PREY-09 and PREY-10. Both judges call the order confusing. One also calls M1-T13's new dependency false serialization.
- **quant-incremental, M1-T03 depends on M1-T02 again** (v1's R07 regression). R09 offered "add Depends on M1-T02, or move the fake to a task depending on both". The fixer took the first as the narrower edit, which serialized two interface tasks: dependency_graph_soundness 4 → 3. "Narrower" has to mean less frozen and less serialized, not fewer words changed.

**Cost.**

| | Reviewer | Fixer | Total | Minutes | v1 total |
|---|---|---|---|---|---|
| rl-incremental | $2.86 (25 turns) | $2.29 (95) | $5.15 | 13.3 | $6.13 |
| rl-all-at-once | $3.08 (52) | $3.15 (118) | $6.23 | 14.2 | $3.92 |
| quant-incremental | $5.24 (83) | $4.41 (179) | $9.65 | 19.1 | $8.91 |
| quant-all-at-once | $4.17 (55) | $5.50 (175) | $9.68 | 20.4 | $9.40 |
| **total** | $15.35 | $15.35 | **$30.71** | | $28.36 |

Mean $7.68 per run, against v1's $7.09. The four judge calls aren't counted.

**Verdict.** Still not ready for the skills, but the reason has narrowed.
- The reviewer now catches the user's facts and reads every packet, at about v1's cost.
- What holds the score flat is propagation: a corrected fact must reach its test cases in the same pass.

Next, either:
1. Let the fixer rewrite a case's wording when it only restates a changed spec fact (score direction, a count, a shape, a time limit), and list the fixtures to regenerate. Golden numbers still go to test-planning.
2. Or run test-planning's Extend on the changed cases right after the fixer, before re-judging.

Also define "narrower" in the fixer prompt as "freezes and serializes less", and forbid moving task blocks out of ID order.

## Fixer v4: facts reach the tests, narrower by the plan, no reordering

**What changed.** Only `plan_fix_prompt.md` changed, and the reviewer did not run again.
- **A changed fact reaches every doc and test case.**
  - The fixer greps `docs/`, `tasks/` and `tests/fixtures/` for the old value and brings every restatement into line, including the case's title, Source, Expected and Tolerance.
  - An expected value that *is* the user's fact (a count, a limit, a shape, a direction) is changed in `tests.md` and `expected.json`, with the user's turn listed in `oracle_edits`.
  - A value that must be computed is deleted, never written. The case is then marked in test-planning's own headless form: `tests.md` Status to Draft, an Open questions bullet, and `dt route test-planning … --from plan-review`.
  - Before replying, the fixer re-greps each old value and reports what it left in `leftovers`.
- **Narrower is measured on the plan:** fewer frozen symbols and fewer edges. No edge may join two interface tasks or two spines; move the fake or symbol instead.
- **No reordering.** New IDs go last in their section, a new edge points only at an earlier task, and a fix that would need either is skipped. v3's milestone exception stays.
- **`plan_review.py`:** a `prepare` step writes `.review/` without running the reviewer, and `fix` also commits `tests/fixtures/`.

**`dt guard`.** The fixer runs without the plugin (`--setting-sources project,local`, no `--plugin-dir`), so the guard hook that asks the user before every `expected.json` write never fires. In its place, the prompt allows only Edit writes of the user's own value, and `fix.json` lists each one under `oracle_edits` with its turn.

**Method.** Fresh copies of the four iteration-9 projects went to `dev-team-workspace/review-ab-v4/`. Packaged untouched, they matched `iteration-9/bench` byte for byte. Each copy got `plan_review.py <copy> prepare`, with v3's `review.json` put where the fixer reads it, then `fix`. The blind judge then ran as in v3, from scratchpad folders `v4/judge-rl` and `v4/judge-quant`. The rl BA judge first returned malformed JSON and was rerun once. Records are in `review-ab/v4/`.

**Scores (overall, mean of both orders).**

| | Iteration 9 | v1 | v3 | v4 | v4 Δ vs iteration 9 |
|---|---|---|---|---|---|
| rl-incremental | 7.65 | 7.4 | 7.7 | 7.4 | −0.25 |
| rl-all-at-once | 7.45 | 7.35 | 7.35 | **7.9** | **+0.45** |
| quant-incremental | 7.7 | 7.8 | 7.65 | 7.6 | −0.10 |
| quant-all-at-once | 7.45 | 7.65 | 7.95 | 7.75 | +0.30 |
| **mean** | 7.56 | 7.55 | 7.66 | **7.66** | **+0.10** |

- **rl-all-at-once is fixed. It wins both orders**, where iteration 9 split.
  - internal_consistency 2.0 → 4.0 (v3 → v4), task_buildability 3.5 → 4, dependency_graph_soundness 3 → 4, right_sizing 3 → 4.
  - The facts' gains from v3 stay: stage_completeness 4, rl_soundness 4.
- **The mean doesn't move:** rl-incremental gives back what rl-all-at-once gains. quant-all-at-once's 7.95 → 7.75 has the same top complaints as v3, so it's judge noise.
- **Mean item Δ vs iteration 9, v4 (v3):**
  - task_buildability +0.38 (+0.38).
  - right_sizing +0.25 (−0.12).
  - internal_consistency +0.12 (−0.25).
  - milestone_quality +0.12 (−0.25).
  - dependency_graph_soundness −0.25 (−0.50).
  - pipeline_clarity −0.25 (0).

**Are v3's three failures gone? Yes.**
- **Spec/test contradictions: gone.**
  - rl-all-at-once's TC-07/08/09/24 now say survival time, circle reflection, 1 predator and 60 minutes, in `tests.md` and `expected.json`. TC-07's worked score and TC-17's seed bound were deleted and routed.
  - rl-incremental's TC-46 now matches EVAL-07.
  - Neither rl judge cites a spec/test contradiction. One cites TC-07's open re-derive as "a stale fixture left open", which is the intended trace.
- **M1-T03 → M1-T02: gone.** M1-T03 depends on nothing, and quant-incremental's dependency_graph_soundness is back to 4.
- **Reordering: gone.** Task headings are in ID order in all four plans, and PREY-12 sits after PREY-11. The fixer instead skipped or narrowed five rl-all-at-once fixes whose edges pointed at later tasks (R13, R14, R15, R17, R21), each with its reason.

**New failures.**
- **rl-incremental: moving work instead of adding an edge broke M1-T26.** R09 offered "M1-T27 depends on M1-T26, or move the CNN selection into M1-T26". The edge rule pushed the fixer to the move. But M1-T26 then builds from `networks.py`, which M1-T27 writes in parallel. Both judges list M1-T26 as unbuildable, and dependency_graph_soundness fell 4 → 3. The edge was real. "Fewer edges" has to mean no edge a task's inputs don't need, not none at all: a move must carry its inputs with it.
- **quant-incremental: the fixer wrote computed oracles.** It changed TC-19, TC-38, TC-58 and TC-72 from "≤ 1 of 20 seeds" to "≤ 3" in `expected.json`, citing turns 24, 35, 50 and 51. None of those messages says it: "≤ 3" is the reviewer's binomial bound (R22). The rule says to delete such a value and route it, and rl-all-at-once's fixer did exactly that for TC-17. So in one run of four, `oracle_edits` would have needed the user's approval it was standing in for. With `dt guard` off, the turn citation is the only check, and nothing verifies it.
- **quant-incremental: "keep every heading" blocks a fix.** "M1-T23: mount_runs spine (start, cancel, SSE)" stays. The fixer reported it as a leftover ("Headings must stay exactly as they are"), and both judges still cite it.

**Leftovers reported.** 6, 7, 8 and 5 per run, all with a reason, and each one checked by hand. Most are legitimate:
- Rejected options in Alternatives lines (SSE, yfinance).
- Probe history.
- The same word with another meaning ("square" for the pairing grid, "lower is better" for other scores, pellets that reappear).
- Re-derive notes that quote the old value on purpose.

Two point at work only test-planning can do: rl-incremental's TC-42 and TC-65 `input.json`, which the fixer may not edit, so both were routed. Routed changes: 2, 2, 2 and 6. Six `tests.md` files went to Draft.

**Fixer cost.**

| | v4 fixer | v3 fixer |
|---|---|---|
| rl-incremental | $2.86 (108 turns, 6.8 min) | $2.29 |
| rl-all-at-once | $3.01 (116, 7.7 min) | $3.15 |
| quant-incremental | $4.56 (171, 9.1 min) | $4.41 |
| quant-all-at-once | $6.50 (211, 13.8 min) | $5.50 |
| **total** | **$16.93** | $15.35 |

Adding v3's reviewer ($15.35), a full v4 pass is $32.28, about $8.07 per run.

**Verdict.** The fixer now does what it was told on the three named failures, and where nothing else broke (rl-all-at-once) the judge rewards it: +0.45 on iteration 9's scale, the first review gain larger than the position effect on a set the review had to fix. The mean is still +0.10, because each version trades one regression for another.

Before another run:
1. Allow an edge when the moved work's input is written by the other task.
2. Restrict `oracle_edits` to values whose quoted turn contains the new value: a check `plan_review.py` can make itself.
3. Let a task title change when only its stale words change.
