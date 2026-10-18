# Build eval iteration b1: stage 5b (minilab, A3-RT and A3-WF, n = 3)

Claude Code 2.1.302, every agent `claude-opus-5-5`, one run at a time. Runs: `dev-team-workspace/iteration-b1/minilab-<arm>-r<n>/`; pages here under `minilab-<arm>-r<n>/`. A3's numbers are stage 5's medians ([findings-stage5.md](findings-stage5.md)). Every run but A3-WF-r1 ran after 1664cac (`dt land` reads an escalation before the worktree), so its M1-T01 escalation is `escalated`, where A3's was a `harness` reject.

Kept, not counted: `aborted-minilab-A3-WF-r2-stopped` (2/21: `-p` killed the background workflow 600 s after each turn), `aborted-minilab-A3-RT-r1-maxturns` (21/22, the persona gaps fixed in 790dd8c), `aborted-minilab-A3-RT-r3-gitC` (0/21: the main session committed the approved Revise with `git -C <abs> commit`, which no allow rule matched, and the persona said "continue" nine times). Each cause is fixed (below).

## Per arm (median, min–max)

| | A3 (stage 5) | A3-RT (checkpoint after every task) | A3-WF (Workflow-run loop) |
|---|---|---|---|
| Wall clock (s) | 1,428 (1,248–1,791) | 1,815 (1,706–2,132) | **1,152** (1,076–2,039) |
| Cost ($) | 15.22 (15.04–16.98) | 23.20 (22.07–26.53) | 18.39 (17.49–20.91) |
| Tokens, all kinds (M) | 23.9 (22.6–27.5) | 40.4 (37.9–48.8) | 22.8 (20.7–24.5) |
| Main session's tokens (M) | 10.6 (9.7–12.3) | 21.1 (20.9–26.9) | 2.2 (2.0–4.5) |
| Tasks landed | 21/21 ×3 | 21, 21, 23 (Replan) | 21, 23 (Replan), 21 |
| Design checks | 21, 22, 22 /22 | 22, 22, 21 /22 | 22/22 ×3 |
| Harness failures | harness reject 1 ×3 | none | harness reject 1 (r1, before 1664cac), 0, 0 |
| Conflict / integration / gate rejects | 0 | 0 | 0 |
| Critical · Important findings | 2·15, 1·14, 0·13 | 4·17, 1·18, 0·27 | 0·15, 0·14, 0·10 |
| Golden · holdout · beliefs · mutants | 8 · 5–6 · 3 · 15–16 | 8 · 6 · 3 · 16 ×3 | 8 · 6 · 3 · 16 ×3 |
| Red for the right reason | 100% | 100%, 100%, **89%** (47/53) | 100% |
| Turns / stop | 4–7 / exit | 8, 6, 8 / exit | 5, 7, 4 / exit |

A3-WF's tokens add every transcript under the session's `subagents/**`: `flow/index.json` has no units for workflow agents (workflow-analyzer doesn't read `subagents/workflows/`), so its token total there is the main session alone. A3-RT-r3's red misses are all six tests of M1-T23, the task its Replan added: they pin what `validate_rows` already did; only the narrowing tests were red.

## Effects

| Contrast | Numbers | Ranges overlap? | Reading |
|---|---|---|---|
| Per-task vs per-phase review (A3-RT − A3) | wall 1.27×, cost 1.52×, tokens 1.69× | wall: yes (A3 max 1,791 > RT min 1,706); cost, tokens: no | per-task review costs more and buys nothing measurable here: correctness is equal |
| Workflow-run loop vs main-session loop (A3-WF − A3) | wall 0.81×, cost 1.21×, tokens 0.95×; main session 0.21× | wall: yes (WF-r2 2,039 holds a 496 s Replan) | faster in 2 of 3 runs and cheaper on the main session's context, dearer overall |
| A3-WF vs A0 (stage 4 gate) | 1,152 vs 894: **1.29× slower** | no (A0 max 902 < WF min 1,076) | still no-go: the fixed costs stay |

## Where the time goes (median per phase, s)

| Phase | A3 | A3-RT | A3-WF |
|---|---|---|---|
| Setup (session start → first claim) | 33 | 22 | 22 |
| Contract change (escalation → re-claim M1-T01) | 123 | 98 | 97 |
| Interface task M1-T01 (minus the contract change) | 330 | 471 | 297 |
| Barrier review (T01 landed → first parallel claim) | 124 | 128 | 111 |
| M1-T02–T20 | 360 | **515** (499–721) | 321 (289–377) |
| M1-T20 landed → M1-T21 claim | 25 | 14 | 20 |
| System task M1-T21 | 117 | 148 (r3: 528, a Replan) | 87 (r2: 704, a Replan) |
| Exit (T21 landed → end) | 273 | 277 | 230 |

**A3-RT's parallel phase is slower because its reviewers share the cap.** The 19 per-task reviews total 1,471–1,915 s per run (median 74–101 s each). None is a barrier and nearly all overlap builders, but from reserve to finish reviewers held 2.3–2.7 of the 6 slots during T02–T20 (A3: 0.6–0.7), leaving builders 2.1–2.6 (A3: 3.8). Builder claim → finished is unchanged (31–52 s; A3 38–47 s). The main session's tokens double: 156–174 requests against A3's 98–119, 44–48 of them spawning or recording a review (A3: 14). A3-RT's longer interface phase (471 s) is agent variance (first attempt + second: 115+347, 255+290, 58+308).

**A3-WF saves main-session time, then spends it on landing.** The main session works 124–346 s per run (12–28 s from a turn's start to its `Workflow` call); the workflows run 921–1,681 s. Its control agents (dispatch, land, status, low effort) number 73–86 per run and use 18–19% of the tokens, and their fresh contexts raise cache writes, so cost per token is $0.80–0.85/M against A3's $0.62–0.64/M. In T02–T20 the cap is full for only 16–34% of the phase (A3: 34–41%): one land agent lands one finish at a time, so a builder's finish waits 22–43 s for `dt land` (A3: 10 s), and up to 10–12 finished halves queue.

## Escalations and stops

- **The planted flaw:** a CONTRACT-CHANGE on `risk.Drawdown` from the M1-T01 agent in all six runs, before the freeze, answered by a yes and a Revise (79–123 s).
- **The `load_prices` bug is now fixed in the build.** A3-WF-r2 and A3-RT-r3 escalated a CONTRACT-CHANGE at M1-T21: the real `validate_rows` never narrows to the requested tickers, while the frozen fakes do (the bug A3-r1 escalated in stage 5). The persona now follows a contract change through (790dd8c): Revise, a Replan adding M1-T22 (re-freeze `mdata.load_prices`) and M1-T23 (`validate_rows` narrows), then the go. It cost 496 s (WF-r2) and 388 s (RT-r3) and gave each run its one interface change (`wrong boundary`), and holdout h05 passes in both. RT-r3's Replan also added a barrier checkpoint after M1-T22 (73 s).
- **Criticals, all overridden by the persona:** RT-r1 4: the `risk.Returns` sample isn't the log returns of the Prices sample (M1-R01), and `calendar._fill` raises IndexError when a ticker has no close on the first calendar date (M1-R20, a real crash no golden or holdout case covers); both again at the exit. RT-r2 1: drawdown's tie rule compares cumulative log sums exactly, so float drift breaks "the first if tied" (WF-r2 filed the same as Important). A3-WF: none.
- **A reviewer's status line can disagree with its file.** In RT-r2 (M1-R23) and RT-r3 (M1-R08) the reviewer ended with `… 1 Critical` while its findings file filed the finding as Important. `skills/build/references/loop.md:45` stops on the status line's count, so the main session held dispatch (about 120 s and 75–100 s) and asked; the persona's generic "Continue the build." was recorded as the finding's resolution. Taking the count from what `dt finding --from` records would remove the stop. That is a build skill change, not made in this iteration.
- **A3-WF-r1's kill:** its second workflow was killed at 605 s (the `-p` background-wait ceiling); the main session landed M1-T19 by hand and relaunched 18 s later, re-running two lost M1-T10 reviewers.

## Stage 5's truncated runs, rerun

A0-r2, A2-r3 and A4-r2 were rerun with every fix above (the truncated runs kept as `aborted-minilab-<arm>-r<n>-maxturns`). A2-r3's first rerun stalled at 11/13: its Replan rewrote the pending M1-T13 into the re-freeze task instead of adding one, and the persona, which read a Replan as a new task ID, kept asking for it instead of giving the go (kept as `aborted-minilab-A2-r3-replan`; the persona now reads any `plan.md` change as the Replan, 329e17a). A2-r1 and A2-r2 were regraded with the fixed `planted_flaw_contract_change`; A2-r2 rises to 21/22.

| Run | Wall (s) | Cost ($) | Tasks | Design checks | Notes |
|---|---|---|---|---|---|
| A0-r2 | 1,040 | 9.69 | 22/22 | 20/21 | caught the flaw after the freeze again; the Replan's re-freeze M1-T22 wrote two contract samples its Writes didn't name (`writes_respected`; A0 lands without `dt land`) |
| A2-r3 | 1,233 | 13.15 | 12/12 | 21/22 | flaw caught at M1-T04, before the freeze; red for the right reason 68% (the spine cut, as in stage 5); 1 Critical overridden |
| A4-r2 | 1,227 | 13.91 | 21/21 | 20/20 | clean; 2 Criticals overridden |

Stage 5's medians with the reruns: A0 894 s (848–1,040), $8.58; A2 1,283 s (1,233–1,327), $13.52; A4 1,353 s (1,227–1,435), $13.92; A1 and A3 unchanged. The stage 4 gate still fails without overlap (A3 min 1,248 > A0 max 1,040), and A3 ≤ 0.5 × A1 still holds at the medians. No verdict in [findings-stage5.md](findings-stage5.md) changes.

## Harness fixes made for these runs

- `build_driver.py` sets `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` to the turn timeout: `claude -p` otherwise kills a background Workflow 600 s after the main turn ends (1664cac; [smoke test](../../design/evidence/2026-10-18-workflow-smoke.md)).
- The driver adds the `git -C * <verb> *` form of each git allow rule, plus status, log, diff and show; `progress()` counts branches, not `refs/eval/turns`, which grows every turn and kept the three-turn stall stop from ever firing (2698e6b).
- `run_build.sh`'s `keep()` no longer ends on a false `[ -f port_bar.json ]`, which made `set -e` stop the script before the summary and the flow index (2e8d71d).

## Validity

- **n = 3 per arm, one Replan each.** WF-r2 and RT-r3 built 23 tasks; without their Replans (496 s, 388 s) they sit inside their arms' other runs. The Replans exist because the persona now follows contract changes, which stage 5's A3 runs did not (A3-r1 got "retry once"), so A3's medians are slightly flattered against both.
- **Persona overrides still decide correctness.** Every Critical was overridden and the exit approved with no fix tasks; RT-r1's `calendar._fill` crash ships.
- **Permission denials** (8–47 per run, none on a protected path) are ad-hoc `python3 -c`, heredocs, `git grep` and scratchpad writes; RT-r2's 47 include 19 from its main session.
- **Flow pages** don't show workflow agents yet; A3-WF's plan maps and token totals there understate the run.
