# Iteration 8: blind judge and mode comparison

**Judge:** Opus 5.5, four fresh subagents (rl and quant, each in both orders, AB and BA). Prompts came from `judge_prompt.py --both --labels incremental all_at_once`. That copied each packaged `outputs/` folder to a neutral `set-1` (incremental) or `set-2` (all-at-once), without `transcript.md` and `doc_evolution.md`. Subagents can't write files, so each returned its verdict as JSON, which was saved as `judge-<project>.AB.json` / `.BA.json`. `judge_prompt.py average` then wrote `judge-<project>.json`. The judges used 276k–454k tokens each and took 6–9 minutes.

## Scores (averaged over both orders)

**rl.** Incremental 7.7, all-at-once 7.25. Incremental won **both** orders, and no item's two scores differ by more than 1.

| Item | incremental | all-at-once | Per order (inc / aao) | Iteration 7 (inc / aao) |
|---|---|---|---|---|
| rl_soundness | **5** | 3.5 | 5,5 / 3,4 | 5.0 / 3.0 |
| stage_completeness | **5** | 4.5 | 5,5 / 4,5 | 3.0 / 4.0 |
| internal_consistency | 3 | 3 | 3,3 / 3,3 | 3.0 / 2.5 |
| right_sizing | 3 | **3.5** | 3,3 / 3,4 | 3.0 / 3.5 |
| milestone_quality | **4.5** | 3 | 4,5 / 3,3 | 3.0 / 4.0 |
| pipeline_clarity | 3.5 | **4** | 4,3 / 4,4 | 4.0 / 3.0 |
| interface_quality | **4** | 3 | 4,4 / 3,3 | 4.0 / 2.5 |
| dependency_graph_soundness | **3.5** | 3 | 3,4 / 3,3 | 2.5 / 4.0 |
| task_buildability | **3.5** | 2.5 | 3,4 / 2,3 | 4.0 / 2.5 |
| organization | 4 | 4 | 4,4 / 4,4 | 4.0 / 4.0 |
| readability_for_solo_learner | 3.5 | **4** | 3,4 / 4,4 | 3.0 / 4.0 |
| ease_of_finding_next_build_step | 3.5 | **4** | 4,3 / 4,4 | 4.0 / 4.0 |
| layout_sensibility | **4** | 3.5 | 4,4 / 3,4 | 4.0 / 4.0 |
| content / structure | 3.9 / 3.8 | 3.35 / 3.9 | | |
| **overall** | **7.7** | 7.25 | 7.6, 7.8 / 6.9, 7.6 | 7.3 / 7.2 |

**quant.** Incremental 7.8, all-at-once 7.45. Incremental won **both** orders, and no item's two scores differ by more than 1.

| Item | incremental | all-at-once | Per order (inc / aao) | Iteration 7 (inc / aao) |
|---|---|---|---|---|
| quant_soundness | **4.25** | 3.5 | 4,4.5 / 3,4 | 5.0 / 4.5 |
| null_hypothesis_handoff | **5** | 4.25 | 5,5 / 4,4.5 | 5.0 / 5.0 |
| reference_use | 4 | 4 | 4,4 / 4,4 | 3.5 / 4.0 |
| stage_completeness | **4.75** | 4 | 5,4.5 / 4,4 | 4.0 / 3.0 |
| internal_consistency | **3.25** | 3 | 3,3.5 / 3,3 | 3.0 / 3.5 |
| right_sizing | 3 | **3.75** | 3,3 / 4,3.5 | 3.0 / 4.0 |
| milestone_quality | **3.25** | 2.5 | 3,3.5 / 2,3 | 4.0 / 3.5 |
| pipeline_clarity | **4.75** | 4 | 5,4.5 / 4,4 | 5.0 / 4.0 |
| interface_quality | **4.25** | 3.5 | 4,4.5 / 3,4 | 4.0 / 3.5 |
| dependency_graph_soundness | 4 | **4.25** | 4,4 / 4,4.5 | 4.0 / 4.0 |
| task_buildability | **3.75** | 3.25 | 4,3.5 / 3,3.5 | 4.0 / 3.5 |
| organization | 4 | 4 | 4,4 / 4,4 | 4.0 / 4.0 |
| readability_for_solo_learner | 3 | **4** | 3,3 / 4,4 | 3.0 / 4.0 |
| ease_of_finding_next_build_step | 3.75 | **4** | 4,3.5 / 4,4 | 4.5 / 5.0 |
| layout_sensibility | **4.25** | 3 | 4,4.5 / 3,3 | 4.0 / 4.0 |
| content / structure | 4.0 / 3.8 | 3.65 / 3.8 | | |
| **overall** | **7.8** | 7.45 | 7.8, 7.8 / 7.3, 7.6 | 7.95 / 8.15 |

## Findings

### J1. Incremental wins both projects, outside the position bias

Margins are 0.45 (rl) and 0.35 (quant), and incremental won both orders in both projects. Iteration 7 was a tie in both projects (margins 0.1 and 0.2, with Set A winning every order). The ~0.3 position bias seen then doesn't explain a win in both orders.

**Both all-at-once plans lost on content, not structure.** Structure is level or better for all-at-once.
- **rl all-at-once never defines a reward for any world:** rl_soundness 3.5. It also went multi-package (findings-interface F14). It added a reference-library package and per-milestone comparisons nobody asked for, and its brief invents a cloud-GPU budget.
- **quant all-at-once:**
  - It scores Stage 2 on Sharpe after costs instead of the realized out-of-sample variance the user asked for.
  - It defers the user's ten delisted names.
  - It splits Stage 1 by layer (M1 backend, M2 app), so there's no walking skeleton to the app. That's milestone_quality 2.5.
  - M2–M8 have no Exit.
  - Its probes were waived after the "ran it" loop (findings-flow F2), so its data facts were never checked.

### J2. Against iteration 7

- **rl** went up: incremental 7.3 → 7.7 (stage_completeness 3 → 5 now that the stall is gone, milestone_quality 3 → 4.5); all-at-once 7.2 → 7.25.
- **quant** went down: incremental 7.95 → 7.8; all-at-once 8.15 → 7.45 (milestone_quality, quant_soundness, ease_of_finding_next_build_step).
- quant all-at-once's drop lines up with the 18-turn probe loop and the waived probes. Both quant runs gained probe work, five-stage plans (quant incremental) and bigger docs.
- findings-examples.md finds no quality change from the domain move.

### J3. The judge band holds

`judge_within_1` is ok in both projects:
- **rl:** interface_quality Δ −1.0 and dependency_graph_soundness Δ −0.5.
- **quant:** −0.75 and +0.25.
- **task_buildability:** −1.0 in rl and −0.5 in quant.

### J4. Blinding was weaker than in iteration 7

Iteration 7 ran each judge as `claude -p` with only Read, Glob, Grep and Write, and no CLAUDE.md. Iteration 8's judges were general-purpose subagents with every tool. They loaded the repo's CLAUDE.md and could have reached `judge-<project>.key.json` in this folder, which maps sets to modes. They were told to read only the files the prompt names. Nothing in their output names a mode, but nothing prevented it.

**Fix (harness):**
- `judge_prompt.py --both` writes the key outside the folder tree the judge can reach.
- The README names a judge runner: `claude -p` with read-only tools in the prompt folder.

## Mode comparison (`mode_delta.json`)

| Band | rl inc / aao | quant inc / aao |
|---|---|---|
| N/CP within 20% | 3.38 / 3.29: ok | 6.33 / 5.0: **out** (21%) |
| max width within 1 | 18 / 12: **out** | 26 / 17: **out** |
| interface_coverage, types_in_contract, writes_disjoint pass in both | **out**: types (aao), writes (both) | **out**: types (both), writes (inc) |
| judge within 1 | ok | ok |
| frozen_interface_churn (aao ≤ inc) | 0 ≤ 32: ok | 0 ≤ 0: ok |

What explains each miss, and whether it's a mode effect:
- **rl max width (18 vs 12): not a mode effect.**
  - All-at-once went multi-package (findings-interface F14), which put 3 interface tasks in wave 0, and its one `cli` spine covers 8 steps.
  - All-at-once's wiring also waits on an unfaked `learn.train` (F2).
  - These are skill defects that all-at-once happened to hit.
- **quant max width (26 vs 17) and N/CP (21%): mostly a milestone-cut difference, in part a defect.**
  - Incremental's M1 spans all four Stage 1 packages, app included (38 tasks).
  - All-at-once cut Stage 1 by layer (M1 backend only, 25 tasks), which the judge marks as a defect (J1).
  - With every stage designed up front, all-at-once split the first stage differently. That is a mode-driven choice, but the resulting cut breaks the walking-skeleton rule, so it counts as a defect, not an acceptable effect.
- **Must-pass checks: real defects in both modes, not mode effects.** Undefined nested field types (findings-interface F10) and spine Writes outside the owner module (F11).
- **Cost and context can't be read as mode effects in this iteration.** Every skill shared one session (findings-flow F9). With fresh sessions, the incremental/all-at-once context ratio drops from 1.90 to 1.07 (rl) and from 1.28 to 1.06 (quant).
