# Build eval iteration b1: stage 5 (minilab, A0–A4, n = 3)

Claude Code 2.1.302, every agent `claude-opus-5-5`, one run at a time, arm order rotated (r1 A0→A4, r2 A1→A0, r3 A2→A1). Runs: `dev-team-workspace/iteration-b1/minilab-<arm>-r<n>/`; pages here under `minilab-<arm>-r<n>/`. Three runs hit `max_turns` on scripted-persona gaps (fixed in 91073db), marked `*`: A0-r2 stopped at 19/23 and A2-r3 at 11/12, so their wall clock is incomplete. A4-r2 had landed 21/21 and finished its exit review, so its wall clock covers the whole build plus about 210 s of fix-task drafting.

## Per arm (median, min–max)

| | A0 (one session) | A1 (cap 1) | A2 (spine plan, cap 6) | A3 (cap 6) | A4 (solo, cap 6) |
|---|---|---|---|---|---|
| Wall clock (s) | 894 (848–902*) | 3,099 (3,028–3,115) | 1,327 (1,283–1,662*) | 1,428 (1,248–1,791) | 1,353 (1,237*–1,435) |
| Cost ($) | 7.62 (6.89–8.58) | 17.75 (17.65–18.21) | 13.55 (13.52–16.06) | 15.22 (15.04–16.98) | 13.95 (13.92–16.12) |
| Tokens, all kinds (M) | 19.2 (16.5–23.7) | 33.0 (32.1–33.8) | 20.9 (20.5–29.8) | 23.9 (22.6–27.5) | 21.9 (20.9–26.9) |
| Tasks landed | 21/21, 19/23*, 21/21 | 21/21 ×3 | 13/13, 12/12, 11/12* | 21/21 ×3 | 21/21 ×3 |
| Design checks | 21/21, 16/21*, 21/21 | 21, 20, 21 /21 | 21, 20, 15* /22 | 21, 22, 22 /22 | 20/20 ×3 |
| Harness failures | dirty checkout (r2) | harness reject 1, 0, 1 | harness reject 2, 1, 1 | harness reject 1 ×3 | harness reject 1 ×3; dirty checkout (r2) |
| Peak agents in flight | 1 | 1 | 6 | 6 | 6 |
| Other rejects | — | escalated 1 (r2) | escalated 1, 0, 2; writes 0, 0, 2 | escalated 1 (r1) | none |
| Conflict / integration / gate rejects | 0 | 0 | 0 | 0 | 0 |
| Critical · Important findings | 0·1, 0·0, 0·3 (no reviews) | 0·16, 2·7, 2·15 | 3·19, 0·17, 0·8 | 2·15, 1·14, 0·13 | 0·13, 1·10, 1·12 |
| Golden visible (of 8) | 8, 7*, 8 | 8 ×3 | 8, 8, 7* | 8 ×3 | 8 ×3 |
| Holdout (of 6) | 6, 4*, 6 | 6, **5**, 6 | 6, 6, 4* | **5**, 6, 6 | 6 ×3 |
| Planted beliefs (of 3) | 3, 1*, 3 | 3 ×3 | 3, 3, 1* | 3 ×3 | 3 ×3 |
| Mutants killed (of 16) | 16, 14*, 16 | 16 ×3 | 15, 16, 13* | 16, 15, 16 | 16 ×3 |
| Red for the right reason | 100% | 100% | 56%, 69%, 61% | 100% | (no testers) |

**Escalations (kind, at which task).** A0 asks in chat: r1 and r3 at M1-T01, r2 at M1-T20 (after the freeze). A1: CONTRACT-CHANGE `risk.Drawdown` at M1-T01 in every run. A3: the same in every run, plus in r1 a CONTRACT-CHANGE `mdata.load_prices` at M1-T21 (the real function ignores `tickers`; the fakes filter). A4: M1-T01 in every run. A2: r1 at the M1-T12 tester (after the freeze), then twice at the re-freeze task M1-T13; r2 at M1-T04; r3 at M1-T04, then twice at the M1-T11 tester (TC-07, below).

A0-r2, A2-r3 and the 1/3 belief counts: the missing beliefs and holdouts belong to tasks that never landed (the report and summary), not to wrong beliefs. The two **bold** holdout misses are a real bug (see Validity).

## Pre-registered effects (§9.2) and the stage 4 gate

| Effect | Numbers | Ranges overlap? | Verdict |
|---|---|---|---|
| A3 wall ≤ 0.5 × A1 | 1,428 / 3,099 = **0.46×** at the median; worst pairing 1,791 / 3,028 = 0.59× | no | **met** at medians (A3-r1 on its own misses 0.5×) |
| A3 tokens ≤ 1.3 × A1 | 23.9 M / 33.0 M = **0.72×** (cost 0.86×) | no | **met** |
| A3 merge conflicts = 0, interface changes ≤ 1 | 0 conflicts and 0 interface changes in all 3 | — | **met**, but measures little: the flaw is caught at M1-T01, before the freeze, every time |
| A2 shows more integration failures or rework than A3 | integration failures 0 vs 0. Rework isn't graded. Proxies: A2-r1 had one post-freeze interface change (re-freeze M1-T13); A2 spent 361–755 s per run waiting on escalations after the freeze, A3 0–87 s | — | **not met** as graded; the proxies lean towards A2 being worse |
| A3 catches ≥ 1 more planted belief than A4 in 2 of 3 runs | 3 vs 3 in every run | equal | **not met**: the beliefs don't separate A3 from A4 |
| Stage 4 gate: A3 ≥ 1.5× faster than A0 | A3 1,428 vs A0 894: A3 is **1.60× slower** (0.63× the speed) | no: A0 max 902 < A3 min 1,248 | **no-go**, now firmly |

§12's "done means" also fails on beliefs (A4 catches all three). A3's holdout median equals A0's (6/6).

## Where the time goes (median per phase, s)

| Phase | A0 (r1, r3) | A1 | A3 | A4 |
|---|---|---|---|---|
| Setup (session start → first claim / `build started`) | 4 | 25 | 33 | 34 |
| Contract change (escalation → re-dispatch; A0: ask → Revise commit) | 50 | 99 | 123 | 116 |
| Interface task M1-T01 (minus the contract change) | 208 | 381 | 330 | 407 |
| Barrier review (T01 landed → first parallel claim) | — | 100 | 124 | 127 |
| M1-T02–T20 | 500 (serial) | 1,612 (serial) | **360** (314–396) | 287 |
| M1-T20 checkpoint → M1-T21 claim | — | 333 | 25 | 20 |
| System task M1-T21 | 54 | 110 | 117 (r1: 410, a second escalation) | 108 |
| Exit (T21 landed → end; A0 runs no reviews) | 54 | 384 | 273 | 241 |

The parallel phase is 1.4× faster than A0's serial run of the same tasks (stage 4: 2.2×, but A0's T02–T20 fell from 735 s to about 500 s). Everything around it costs more. A3's fixed phases add up to about 1,000 s against A0's 370 s: a cold-context interface agent (+120 s), a contract change routed through an agent stop and the main session (+70 s), the barrier review (124 s) and the exit reviews (+220 s). Parallelism saves about 140 s, so A3 loses about 530 s net. In A1 the serial T02–T20 phase is 1,612 s and the checkpoint reviews run in line (333 s), which is why A3 clears 0.5× of A1 but not of A0.

A2 (median): setup 26, M1-T01 90, barrier 81, the rest 961 (escalation waits included), exit 227. Its plan has 12 tasks against 21, so it is quick, but its time goes to escalations raised after dispatch.

## The planted flaw (`risk.Drawdown` lacks `trough_date`)

- **At the interface task, before the freeze:** A1 ×3, A3 ×3 and A4 ×3, each a CONTRACT-CHANGE from the M1-T01 agent within 55–245 s of the run's start. A0-r1 and A0-r3 asked in their first turn. Under the spine plan the flaw is visible where Drawdown is frozen (M1-T04): A2-r2 and A2-r3 caught it there.
- **The barrier review never caught it,** because there was nothing left to catch.
- **After the freeze:** A2-r1, at the M1-T12 tester (TC-08 needs both dates). That cost a Revise, a Replan adding the re-freeze task M1-T13 (the run's one interface change), and two more escalations at M1-T13 before it landed: 755 s in all.
- **A0-r2's late catch:** it skipped the gap at M1-T01, built M1-T02 to M1-T19, and saw the missing field at M1-T20 (588 s). Revise and Replan followed, adding M1-T22 (re-freeze) and M1-T23. M1-T22 had to list the frozen folders in `.claude/.task_writes`, and that Write was denied in every one of the remaining 8 turns. The run ended at 19/23 with uncommitted M1-T22 edits in the main checkout (`types.py`, `drawdown.py`, two samples). TC-08, both report holdouts and two mutants failed as a result.

## Why `harness_rejects` remain after 66c2755

The status line is not the cause. All 13 harness rejects in stage 5 have the same detail: `the worktree … is gone`. Each one follows an escalation by an agent that edited nothing. The final message of every one of those agents (subagent transcripts, A1–A4) is the single line `STOPPED M1-T01 solo: see dt escalate`, or the same line for M1-T12 tester, M1-T13 solo or M1-T04 solo. That is exactly the status line. Claude Code removes a worktree with no changes when the agent ends. `dt land` (`scripts/devteam/commands/land.py:148–152`) tests `wt.is_dir()` before it reads the escalation record, so a clean escalation is classed `harness`. When the escalating agent had written something, its worktree survived and the reject came out correctly as `escalated` (A1-r2, A2-r1 M1-T12, A2-r3 M1-T11, A3-r1 M1-T21). Fix: check the escalation before the worktree. With that, every arm's harness reject count drops to 0.

## A2-r3's TC-07 conflict

The tester claimed that TC-07's input (`vol.values.X = [null, null, 0.2, 0.25, 0.18, null]`, window 2, expected `last_vol` 0.18) cannot be built as a `risk.VolSeries`, because `VolSeries.__post_init__` raises "a value once 2 earlier returns exist". It asked for either the fixture or the contract to change. The main session recommended changing the fixture ("0.18 for both"), and the persona never picked an option.

**This is the agent's doing, helped by the contract's wording.** The contract says only "None until `window` earlier returns exist". That is one-sided: it never says the values after the window must be numbers. The fixture (`tests/fixtures/risk/TC-07/`) deliberately has a later gap, and `last_vol` means the last non-null value. The reference solution has no validator. The M1-T03 spine agent in A2-r3 alone added a two-sided `__post_init__` (commit df2d2e0); A2-r1, A2-r2 and every interface-plan run left `VolSeries` unchecked and pass TC-07. The plan is not the cause. Two points still stand:
- The M1-T04 agent had already flagged this TC-07 clash in its own escalation, and the Revise didn't take it up.
- Recommending an edit to a golden input runs against test-planning's rule that expected outputs come from outside the agent.

A one-line contract fix ("later values may be None, e.g. after a gap") removes the ambiguity.

## Validity

- **n = 3, three runs truncated.** The truncations come from persona gaps (A0-r2 `.task_writes`, A2-r3 the TC-07 choice, A4-r2 fix tasks after the exit), not from the design. A0 and A3 don't overlap on wall clock even if A0-r2 is dropped.
- **Persona overrides decide some correctness numbers.** The two holdout `h05` misses (A1-r2, A3-r1) are a real bug: `load_prices` ignores `tickers`. A1-r2's exit review raised it as Critical, and A3-r1 escalated it at M1-T21 and its exit review raised a Critical. The persona answered "accepted for this eval" or "retry once". As in stage 4, reviews find real bugs and the no-fix exit ships them.
- **Planted beliefs and the planted flaw don't discriminate.** Every finished run caught all three beliefs. Every interface-plan run but A0-r2 caught the flaw before the freeze. The TDD contrast (A3 vs A4) and `interface_changes` have no headroom on this fixture: A4 is cheaper and faster with equal correctness.
- **Grader false negative:** `planted_flaw_contract_change` looks for the field only in `types.py`. The spine plan puts `Drawdown` in `drawdown.py`, so A2-r2 and A2-r3 are marked failed although `trough_date` is there and TC-08 passes. A2's check counts are one low.
- **A2's low red-for-the-right-reason** (56–69%): the thickens' intent tests already pass on the spine code (mostly error paths), so the spine cut weakens test-first.
- **Plan defect in both plans:** acceptance asks for the `dt layout` pointer in `pipelines.md`, but `pipelines.md` isn't in `Writes:`. Most agents skip it; A2-r3's M1-T02 and M1-T03 did it and were rejected for writes.
- **A0 is not like-for-like:** it runs no reviews, so its finding counts are not comparable. Wall clock includes the main session's persona turns in every arm (up to 7 turns in A3-r1). Stage 5's runs didn't overlap one another; A3-RT ran afterwards.
