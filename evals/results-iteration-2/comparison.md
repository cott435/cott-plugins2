# Iteration 2 vs iteration 1

**Iteration 2:** skills at `skill-snapshot-v2` (commit 00e1b86). **Iteration 1:** `skill-snapshot-v1` (9041ad6).

Both iterations used the same harness, scenarios, assertions, models (agent claude-opus-5-5, simulated user sonnet) and n=1 per configuration, so treat deltas as directional.

## What changed in the skills

1. **Append-only growth.**
   - A changed requirement is rewritten in place and gets a date-only marker on its ID line.
   - Removed requirements and superseded decisions collapse to one struck line.
   - Risks is one consolidated list.
   - Changelog rows are one line, with IDs as ranges.
   - Extend mode widens existing requirements instead of adding per-stage near-duplicates, and rewrites the Summary and Scope for the whole spec.
2. **Vendor leakage.** spec-writing runs a hygiene check for library, vendor and format names, including names the user used, before every review gate. Tool preferences live in the idea file.
3. **Script name.** `arch-status.sh` → `arch-status.py`.
4. **Gates.** An approval that comes with changes ends the turn, in all three skills. Nothing is planned or built after the architecture is approved.
5. **Skill routing** (from the earlier agent's plan, item 3). A step owned by an installed skill names that skill. `spec-status.sh` and `arch-status.py` now list installed skills.

The brief-goal/stage relationship was deliberately left alone, because `docs/roadmap.md` (design/planning-stage.md) will own it.

## Programmatic grading

| Run | It 1 | It 2 | It 2 failures |
|---|---|---|---|
| rl all-at-once | 26/26 | 26/26 | — |
| quant all-at-once | 28/28 | 28/28 | — |
| rl incremental | 25/26 | **26/26** | — (it 1: `stable-baselines` in spec) |
| quant incremental | 24/28 | **26/28** | brief 617 words; 9 goals (both brief-goal, deferred) |
| **Incremental mean** | 91% | **96.5%** | |

The four quant-incremental failures from iteration 1 went as follows:
- Final architecture left at Draft: **fixed**.
- Vendors in the spec (numpy, pytorch, scikit, stable-baselines): **fixed**.
- One turn drafted the brief and spec together: **fixed**.
- 10 brief goals: **still failing**, as 9 goals.

## Doc size and history residue (`docstats.json`)

| | rl inc it1 → it2 | quant inc it1 → it2 |
|---|---|---|
| Total words | 18.9k → **17.3k** | 42.0k → **32.0k** |
| Spec words / requirements | 10.1k / 139 → **7.5k / 111** | 19.8k / 259 → **13.7k / 189** |
| Architecture words / decisions | 6.4k / 17 → 7.7k / 17 | 17.4k / 35 → **13.6k / 29** |
| Incremental ÷ all-at-once size | 2.3× → **1.9×** | 4.0× → **3.1×** |
| `(changed …)` markers off requirement lines | 1 → **0** | 35 → **0** |
| Words per superseded decision | 195 → **23** | 190 → **34** |
| Specced ideas still listing open questions | 2 → **0** | 1 → **0** |
| Library or vendor names in the spec | 1 → **0** | 4 → **0** |
| Docs written past the architecture | — | `plan.md` → **none** |

All-at-once sizes barely moved: rl 8.3k → 9.0k, quant 10.5k → 10.2k.

The RL architecture grew because its Interfaces section went from 1.7k to 2.8k words of code. That is design content, not residue.

## Blind judges

These are fresh judges with the iteration-1 rubric. Absolute scores aren't comparable across judges; gaps and winners are.

| Pair | It 1 | It 2 |
|---|---|---|
| rl: all-at-once vs incremental | 8.9 vs 7.1 (gap 1.8) | 7.7 vs 6.9 (**gap 0.8**) |
| quant: all-at-once vs incremental | 9.1 vs 5.7 (gap 3.4) | 8.0 vs 6.8 (**gap 1.2**) |
| rl: incremental v2 vs v1 | — | **v2 8.0** vs v1 7.3 |
| quant: incremental v2 vs v1 | — | v2 6.7 vs **v1 7.1** |

**About the quant v2-vs-v1 result:**
- v2 won content 4.0 vs 2.8. It hands off to the null-hypothesis skill (5 vs 2), follows the stage plan, and has less residue.
- v1 won structure 4.3 vs 2.7. Its credit came from `plan.md` (which fix 4 now forbids) and from a per-stage architecture split.
- v2 keeps a single 13.6k-word architecture file, and its spec has no per-stage headings. That last point is a real gap.

## Cost

| Run | It 1 → it 2 |
|---|---|
| rl inc | $7.98 → $7.38, 18 → 17 turns |
| quant inc | $18.07 → $14.14, 28 → 27 turns, 3711 → 2858 agent seconds |
| all-at-once | about unchanged ($2.03 → $2.13, $2.95 → $2.80) |

## Still open (from the judges' defect lists)

1. **The brief stays stage-1-shaped** in both incremental runs (quant: 9 goals, 617 words). This is the roadmap design's job.
2. **Earlier-stage out-of-scope lines contradict later stages** (quant: "deep learning", "Machine-learning portfolio methods"). The rule exists ("drop anything now in scope"), but the agent didn't apply it. Add it to the hygiene check explicitly.
3. **Judges read `(changed …)` markers as noise** (rl 17, quant 23). Move change detection into `arch-status.py`, reading changed IDs from the changelog, and drop the inline markers.
4. **Partly superseded decisions aren't revisited.** Example: quant AD-20 still says "two holdouts" after AD-26 made three. The Overview also goes stale. In Extend mode, re-read every Accepted decision the new one touches.
5. **Specced idea files go stale**: old holdout dates, "Brief changes" diff text, leftover review wording ("for you to check"). Decide whether idea files are frozen records with a banner, or kept current.
6. **Large single files.** The quant architecture is 13.6k words in one file, and no run triggered Grow. These are the Grow triggers in planning-stage.md §5.1, plus per-stage spec sections.

## Caveats

- Iteration 2 ran locally on macOS (CLI 2.1.292), not on the iteration-1 cloud box. The host's CLAUDE.md was disabled for the nested sessions. The `sonnet` alias may resolve to a newer model than in iteration 1.
- The judge rubric item "ease of finding next build step" rewards a build plan, which these skills now deliberately don't write.
