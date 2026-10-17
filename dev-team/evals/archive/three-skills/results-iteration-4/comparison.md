# Iteration 4 vs iteration 3

**Iteration 4:** skills at `skill-snapshot-v4` (commit 380ba67). **Iteration 3:** `skill-snapshot-v3` (cd01171).

Only the two incremental trajectories were re-run. As in iteration 3, the gap comparisons use iteration 2's all-at-once docs. Harness, scenarios, models and n=1 are unchanged, so treat deltas as directional.

## What changed in the skills

All three edits are in architecture-design:

1. **Changelog IDs.** A row lists only its new decisions. It copies spec IDs only for a spec row with no source file, which needs them for matching.
2. **Revising in place** now covers the decision's Context, not just its Decision and Consequences.
3. **Extend step 5 sweep.** It now covers section headings and text the round didn't set out to touch. It names stage lists, falsified superlatives ("the top of the dependency chain") and "later stage" or "milestone" framing.

## Programmatic grading

| Run | It 3 | It 4 | It 4 failures |
|---|---|---|---|
| rl incremental | 25/26 | 25/26 | brief has 7 goals |
| quant incremental | 26/28 | 27/28 | brief has 6 goals (the brief is exactly 500 words, so it passes the size check at the limit) |

**Grader fix.** rl's first grade failed "CPU training-time budget is a quality requirement". QR-01 reads "finishes in 60 minutes or less on a MacBook Pro with Apple Silicon, using the processor only", and the regex only knew `CPU|laptop`. It now accepts `MacBook|processor` too. Re-grading the iteration-2 rl runs (both modes) and iteration-3 rl gives the same results as before.

## Targeted defects

Counts come from the judges' defect lists, plus a regex scan for milestone, superlative and stage-list wording. The iteration-3 column also uses the iteration-4 quant-fix judge's list. That judge re-read the same v3 docs and flagged every item again.

| Defect | It 3 | It 4 |
|---|---|---|
| Spec IDs copied into the architecture Changelog (`changelog_spec_ids`) | rl 97, quant 170 | rl **0**, quant **1** (`COV-02 (changed)`, a row with no idea file, as the rule asks) |
| Places a round's ID list appears | 3 (spec Changelog, architecture Changelog, idea `**Spec:**` line) | 2 |
| "Milestone" framing in the architecture | quant 2 ("Milestone-1 notebook", "milestone 1" in the layout) | **0** |
| Falsified superlatives | quant: AD-29 "the top of the dependency chain" | **0** |
| Stale stage lists in headings or lead-ins | quant 3: "**Run folders for Stages 2 and 3**", `stats.run` "Stage 2, 3 and 4 runs", AD-10 "Stage 2 and Stage 3 run reports" | quant 1: "Within Stages 2–4:" heads dependency rules that include Stages 5 and 6 |
| Revised decision whose Context still names old stages | quant: AD-19 | **0** flagged |
| Decisions revised in place / with Context rewritten | quant 7 / 2 | quant 12 / 10 |

**Still flagged in iteration 4:**

- **Stale requirement-coverage columns.** In the quant architecture, the `claims` component row and its Interfaces heading say "EDA-06, OOS-10", but the module carries 26 families (both quant judges). The `reporting` row leaves out PRPT, FRPT, VRPT and S6RPT. The sweep covers counts, lists and ranges, but these "Covers" cells didn't get updated.
- **Past-tense history notes.** The rl architecture has "unchanged since the Snake stage", "unchanged since the tank stage", AD-08 "Since the arena stage, the core itself runs on TeamEnv", and "Older single-learner TOML files load into this form" (both rl judges). The sweep looks for stages framed as future, not as past.
- **Stale spec feature text.** spec-writing was not changed this round. Examples: the SYN Behavior line still covers only Stages 2–3; the REF Source and Serves lines; PPO-03 contradicts AD-34.
- **Issues owned by planning-stage.md:** Stage-1-shaped briefs, and tombstoned goals in rl.

**New defect: an unbalanced code fence (quant).** The Stage 4 architecture round (turn 20) appended its storage paths after the storage block's closing fence, leaving an odd number of fences. The Stage 5 and 6 rounds kept the pattern, which ended at 27 fences. From Decisions through the Changelog, the doc renders as code. Both quant judges cite this, and the fix-pair judge calls it the biggest structural difference (organization 3, readability 3). `docstats.py` now reports `code_fences_unbalanced`. No earlier run has one.

## Blind judges

These are fresh judges with the iteration-3 prompts (only the paths differ). A and B were shuffled, and the keys are in `blind-*.json`.

| Pair | It 3 | It 4 |
|---|---|---|
| quant: incremental new vs old skills | **v3 7.0** vs v2 6.6 | v4 6.8 vs **v3 7.9** (content 3.8 vs 4.2; structure 3.0 vs 3.7) |
| rl: incremental new vs old skills | v3 7.6 vs **v2 7.7** | v4 7.6 vs **v3 7.9** (content 3.6 vs 4.2; structure 4.0 vs 3.7) |
| quant: all-at-once vs incremental | 8.4 vs 6.5 (gap 1.9) | 8.4 vs 6.7 (gap 1.7) |
| rl: all-at-once vs incremental | 8.0 vs 6.6 (gap 1.4) | 7.6 vs **8.0** (incremental wins) |

- **v4 loses both direct comparisons, but judge noise is as large as the margins.** The same v3 docs scored 7.0 and 7.9 for quant, and 7.6 and 7.9 for rl, depending on the judge.
- **The content losses are about plan choices, not residue.**
  - rl: the 1,000-step time limit is treated as terminal, and the main significance test is left unresolved at 5 seeds.
  - quant: three years of data can't be used by Stages 4–6, the PPO check runs on discrete CartPole, and the Stage 5 volatility networks ignore the Stage 4 features.
- **quant's structure loss is mostly the broken fence.**
- **rl is the first incremental run to beat all-at-once** (gaps: 0.8 in it2, 1.4 in it3). The judge credits its pedagogy, testability and build order. It still scores it lower on right_sizing and consistency (3 vs 4), citing the Snake-shaped brief and the history notes.

## Doc size (`docstats.json`)

| | rl inc it3 → it4 | quant inc it3 → it4 |
|---|---|---|
| Total words | 20.3k → 18.2k | 39.5k → 43.8k |
| Spec words / requirements | 9.3k / 103 → 9.0k / 115 | 18.2k / 217 → 19.8k / 234 |
| Architecture words / decisions | 8.9k / 19 → 7.0k / 14 | 15.6k / 38 → 18.5k / 36 |
| Architecture Changelog words (section only) | 147 → 57 | 265 → 179 |
| Incremental ÷ all-at-once | 2.3× → 2.0× | 3.9× → 4.3× |

**Where quant grew:**

- **Revising in place, now with Context, adds about 0.7k words over it3's rate.** That is about a quarter of the architecture's 2.85k growth.
  - After their first drafts, decisions grew by +1,041 words (it3: +371).
  - The same shared decisions are revised in every round: the Changelog lists AD-09–AD-12 and AD-14 as revised in each of Stages 3–6.
  - Examples: AD-10 129 → 362 words, AD-12 218 → 392, AD-19 166 → 316, AD-11 207 → 313.
- **The rest is more content, which the edits don't touch.**
  - Decisions were longer at first draft (184 words on average, against 148).
  - Components grew +0.5k, Cross-cutting +0.25k and Risks +0.2k.
  - The spec added 17 requirements, and spec-writing was unchanged, so that is most likely run-to-run variance.
- **rl shrank:** it has 5 fewer decisions, and revision growth was +264 (it3: +376).

## Cost

| Run | It 3 → it 4 |
|---|---|
| rl inc | $8.72 → $6.92; 18 → 17 turns; 1824 → 1520 agent seconds |
| quant inc | $14.95 → $20.97; 26 → 30 turns; 3141 → 3488 agent seconds |

`summary.json`'s `agent_cost_usd` adds up per-turn costs, but those are already cumulative for a resumed session, so it overstates (rl $51.59, quant $272.50). The table uses the last turn's cost, as iteration 3 did.

## Verdict

- **Repeated ID lists: fixed.** The architecture Changelog carries only AD ranges, and no judge flagged repeated lists.
- **Stale stage framing: the named forms are gone.** Milestones, falsified superlatives, stage-list headings and decision Context were all clean in v4 quant, and rl had none. Two related forms remain: coverage columns and past-tense history notes.
- **Size: not neutral.**
  - rl shrank 10%, and quant grew 11%.
  - About a quarter of quant's architecture growth comes from revising more decisions every round, Context included.
- **Direct scores went down.** The broken fence and plan-content choices drove this, and the edits touch neither.

## Still open

1. **Shared decisions revised every stage** (quant AD-09–AD-12, AD-14). Revising Context makes each revision bigger. These need a split, or a cap on how much one decision covers. This is more pressing now than in iteration 3.
2. **Fence breakage in extend rounds.** An extend round should insert into a fenced block, not append after it, and check that fences balance. That could be an `arch-status.py` check. `docstats.py` detects it now.
3. **Sweep gaps:** requirement-coverage columns in Components, and "since the X stage" or "unchanged since" notes.
4. **Stale spec feature intros** (Behavior, Source and Serves lines). spec-writing's hygiene check covers requirements and out-of-scope lines, but not these.
5. **Brief shape and tombstoned goals** (planning-stage.md).
6. **`driver.py` summary cost** double-counts cumulative per-turn costs.
