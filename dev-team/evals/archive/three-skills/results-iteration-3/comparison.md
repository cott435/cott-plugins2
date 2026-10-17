# Iteration 3 vs iteration 2

**Iteration 3:** skills at `skill-snapshot-v3` (commit cd01171). **Iteration 2:** `skill-snapshot-v2` (00e1b86).

Only the two incremental trajectories were re-run. The four fixes only change extend rounds, so all-at-once runs had nothing new to test. The gap comparisons therefore use iteration 2's all-at-once docs. Harness, scenarios, models and n=1 are the same as before, so treat deltas as directional.

## What changed in the skills

1. **Out-of-scope check.** spec-writing's hygiene check reads every out-of-scope line against the round's new features, and drops or narrows the lines they bring into scope.
2. **Change detection.** There are no inline `(changed)` markers any more.
   - `arch-status.py` takes `changed_since` from spec Changelog rows the architecture hasn't absorbed.
   - Rows dated on the same day as the architecture's Last updated are ordered by matching the architecture Changelog's cited idea files, or IDs when a row has no idea file.
3. **Partly changed decisions.** When a new decision changes only part of an Accepted one, the old decision is revised in place, along with the Overview and interfaces. It is superseded only on a full reversal.
4. **Specced idea files are frozen records.** spec-writing adds a banner and removes review-only wording when it marks an idea Specced.

**The old change detection never worked in the evals.** Replaying arch-status on every turn of both iteration-2 runs, the old date-only check reported `changed_since = []` on every turn, because every changelog row has the same date. The new script reports each stage's widened requirements until the architecture's Changelog row cites that idea file. It also did this live in both iteration-3 runs; in rl, an `EVAL-04 (changed)` tweak with no idea file was matched by its IDs.

## Programmatic grading

| Run | It 2 | It 3 | It 3 failures |
|---|---|---|---|
| rl incremental | 26/26 | 25/26 | brief has 7 goals |
| quant incremental | 26/28 | 26/28 | brief 561 words; 6 goals |

All three iteration-3 failures are brief-goal checks, which design/planning-stage.md owns.

**The quant live-trading FAIL was a grader bug.** The first grade showed a new failure, "Real-money / live trading is explicitly out of scope". The line was never dropped:

- From turn 4 on, the spec lists "Live or real-money trading, brokerage connections" as out of scope.
- At stage 6, fix 1 did its job. It removed the now-false "…backtests, paper trading — later stages" line, and kept the live-trading line, narrowed with "(PAPER-07)".
- That line ended up as item 25 of 26, 1,871 characters after the heading. `grade.py` only searched 1,500 characters. In iteration 2 it was the first item.

`grade.py` now searches the whole Out-of-scope list and the brief's Not-doing section. That gives the same result on every iteration-2 run, and 26/28 for iteration 3.

## Targeted defects in the blind judges' lists (incremental docs)

| Defect class | It 2 | It 3 |
|---|---|---|
| Out-of-scope lines contradicting a later stage | quant: 3, plus a duplicate | **0** |
| Inline `(changed …)` tags | rl 17, quant 23 | **0** (`changed_markers_above_changelog` = 0 in both) |
| Stale count in an Accepted decision or Overview ("two holdouts") | quant: AD-20, Overview, Testing | **0 stale counts**, but stale *stage lists* remain (below) |
| Stale text in Specced idea files | quant 4, rl 3 ("for you to check", old holdout dates) | quant **0**, rl 2–3 |
| Specced ideas without the banner | — | 0 of 7 |

**Still flagged in iteration 3:**

- **Stale stage framing in architecture text that a round didn't revise.** Examples: AD-29 "the top of the dependency chain" after AD-34 added a layer above it; AD-19's Context naming only Stages 2–4; "Run folders for Stages 2 and 3"; "Milestone-1 notebook". The revised decisions (AD-19 and AD-20) had their Consequences updated but not their Context.
- **Frozen idea files disagree with later brief edits.** rl `fish-tank.md` "Serves: new Goal 6" was flagged after Goal 6 merged into Goal 1. The rubric asks that ideas agree with the other docs, so a frozen record will always cost some consistency points. The banner doesn't change that.
- **The same long ID lists appear in several places.** They are repeated in the spec Changelog, the architecture Changelog, and each idea's `**Spec:**` line. The v3 Changelog rule told architecture rows to copy the spec IDs.
- **Cross-stage requirements stay in the section of the stage that first needed them.** Iteration 2's widen-in-place rule moved them nowhere (EVAL-09 and SIG-01 sit inside Stage 2 features). The spec also has no per-stage headings.
- **Issues owned by planning-stage.md.** Stage-1-shaped briefs and tombstoned goals ("3. *(Merged into Goal 2.)*").

## Blind judges

Fresh judges with the iteration-2 rubric and prompt template. A and B were shuffled; the keys are in `blind-*.json`.

| Pair | It 2 | It 3 |
|---|---|---|
| quant: incremental new vs old skills | v2 6.7 vs v1 **7.1** | **v3 7.0** vs v2 6.6 (content 4.0 vs 3.6; structure 3.0 each) |
| rl: incremental new vs old skills | **v2 8.0** vs v1 7.3 | v3 7.6 vs **v2 7.7** (v3 wins structure 4.0 vs 3.7, loses content 3.6 vs 4.0) |
| quant: all-at-once vs incremental | 8.0 vs 6.8 (gap 1.2) | 8.4 vs 6.5 (gap 1.9) |
| rl: all-at-once vs incremental | 7.7 vs 6.9 (gap 0.8) | 8.0 vs 6.6 (gap 1.4) |

- **Direct comparison:** v3 beats v2 on quant and ties it on rl. The rl content loss is about what the plan says, not residue: the brief relaxes "beat the scripted player" to 75% of it, and reward experiments are out of scope.
- **Gap to all-at-once:** it widened in both projects. The losses are in right_sizing (2/5 in both) and consistency (2/5). The judges cite size and the stale framing listed above. Different judges score each iteration, so the gap is noisy at n=1.

## Doc size (`docstats.json`)

| | rl inc it2 → it3 | quant inc it2 → it3 |
|---|---|---|
| Total words | 17.3k → 20.3k | 32.0k → 39.5k |
| Spec words / requirements | 7.5k / 111 → 9.3k / 103 | 13.7k / 189 → 18.2k / 217 |
| Architecture words / decisions | 7.7k / 17 → 8.9k / 19 | 13.6k / 29 → 15.6k / 38 |
| Incremental ÷ all-at-once | 1.9× → 2.3× | 3.1× → 3.9× |

**Where the growth comes from:**

- **Fix 3 (revise in place):** roughly 0.5–0.75k words per run.
  - In iteration 2, decisions shrank after their first draft (rl −372 words, quant −153), because superseding collapses them.
  - In iteration 3 they grew (+376 and +371).
  - In quant this is mostly AD-19 and AD-20, two shared decisions widened every stage: 131 → 250 and 106 → 281 words.
- **Fixes 1 and 4:** negligible. The banners add about 13 words per idea, and the out-of-scope edits add +11 to +49 words.
- **The rest is more content, which none of the changed rules touch.**
  - quant: 28 more requirements, and 9 more decisions (five are one-per-stage package decisions). Assumptions grew from 183 to 763 words, edge cases from 0.7k to 1.5k, and the Summary and Overview grew 1.7–1.9×.
  - rl: requirements average 66 words against 46.
  - At n=1 this is most likely run-to-run variance. For scale, iteration 1 → 2 moved quant by 10k words.

## Follow-up edits after this eval (not yet tested)

- **Architecture Changelog IDs:** only the new decisions are listed. Spec IDs are copied only for a spec row with no idea file, which still needs them for matching.
- **Revising in place:** it now covers the decision's Context too.
- **Extend step 5 sweep:** it now names stage lists, falsified superlatives ("the top of the dependency chain") and "later stage" or "milestone" framing, including in section headings.

## Cost

| Run | It 2 → it 3 |
|---|---|
| rl inc | $7.38 → $8.72, 17 → 18 turns |
| quant inc | $14.14 → $14.95, 27 → 26 turns, 2858 → 3141 agent seconds |

## Still open

1. Stale stage framing in text a round doesn't touch: decision Context, section headings, milestone wording. Step 5 is now sharper, but this needs a test.
2. Size: incremental runs are 2.3–3.9× the all-at-once size. Revising in place adds a little. Shared decisions widened every stage (AD-19 and AD-20) are the main in-place growth. It may need a cap, or a rule to split a shared decision once it covers several stages.
3. Cross-stage requirements live in the first stage's feature section. A shared "Across stages" feature, or per-stage headings, belongs with planning-stage.md's per-stage spec work.
4. Frozen idea files vs the consistency rubric. Either accept the cost, or make the judge rubric treat bannered records as history.
5. The brief stays Stage-1-shaped (planning-stage.md).
