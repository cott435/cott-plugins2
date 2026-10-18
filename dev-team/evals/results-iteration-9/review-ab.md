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

So +0.86 is the size of the fix as this judge sees it side by side, and +0.5 is closer to what the reviewed plans would score in a normal run. Re-judging the reviewed incremental against the reviewed all-at-once for each project (4 calls) would settle the absolute number on iteration 9's own scale.

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
- **quant-incremental.** "every model trains on the user's machine" (spec, ideas) contradicts turn 2 ("an occasional rented GPU") and turn 47 ("I can rent a cloud GPU for a few dollars").
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

**A final review pays off.** It raised every trajectory in both orders, by +0.86 paired, or about +0.5 on iteration 9's scale. The gain lands on exactly the content items the skills have been stuck on: internal_consistency, task_buildability, interface_quality and milestone_quality. It costs about a quarter of a planning run.

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
