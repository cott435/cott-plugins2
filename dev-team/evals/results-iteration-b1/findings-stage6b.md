# Build eval iteration b1: stage 6b (rl9 again, with the fixes; minilab A3 check)

Claude Code 2.1.302, every agent `claude-opus-5-5`, one run at a time. Same targets as [findings-stage6.md](findings-stage6.md), rerun after its fixes. Runs: `dev-team-workspace/iteration-b1/<name>/`; pages here under the same names.

**What changed since stage 6.** dev-team: the contract-gap fixes (2a8b8e0: shape-only contract tests with a `stub-pinned` floor check, an interface review before anything builds on it, the system task runs each fake's contract cases on the real provider, stops on the Critical count dt records; then two-sided invariants and no golden-input edits), and `dt escalate` keeps an earlier escalation on the same claim (4407078). Harness (4407078): port_bar adds a whole-project `pkg_scope` case for the plan's package and the driver refuses an unknown one; a run stops when one task is rejected for the same reason 3 times, after 2 h with nothing landed, or past its `max_seconds` (minilab 1.5 h, rl9 3 h); rl9 `max_turns` 24; persona rules for bar faults, offers, approvals and several contract changes at once. Persona fixes made between the runs below: 14ecb57, ca4ceb2, 7c514ab.

## Runs

| Run | Tasks | Wall (s) | Cost ($) | Turns | Stop | Design checks |
|---|---|---|---|---|---|---|
| minilab-A3-r4 | 21/21 | 1,551 | 16.59 | 5 | exit | 22/22 |
| rl9-incremental-A3-r2 | 33/34 | 10,113 | 74.32 | 22 | stalled at the last task | 14/17 |
| **rl9-all-at-once-A3-r2** | **30/30** | **5,094** | **47.47** | 9 | exit | 16/17 |

Total $138. minilab A3-r4 sits inside A3's stage-5 range (1,248–1,791 s, $15.04–16.98), so the interface review and the other fixes cost nothing visible there.

## Go / no-go (interface-first-design.md §12, stage 6)

**Still open.** At n = 1, all-at-once built its M1 in half the time (5,094 vs 10,113 s) at 64% of the cost, with no contract change after the freeze, where incremental needed three Revise-plus-re-freeze cycles. But the two M1s are not the same job:
- Incremental's M1 carries the real-training quality bar (TC-26, EVAL-04: an agent beats the scripted player), which alone took 3,943 s and stalled the run. All-at-once defers its equivalent (TC-24) to M2 (`tasks/plan.md` line 7, `roadmap.md` M2's Exit). Leaving the system task out, the gap is 6,231 s vs 5,094 s.
- All-at-once reached its exit but not its own `**Exit:**` line: the exit review found no `rllab` console script and `check.sh full --exit` failing (pyright 3, vulture 21); the persona recorded the 21 Important findings won't-fix. No design check reads the Exit line.

So the difference is plan content (where the milestone is cut, which seams the contracts cover) and persona misfires, not a measured planning-mode effect. A fair test plans one spec both ways, or builds all-at-once through M2 so it meets TC-24.

## What the fixes did (rl9-incremental r1 → r2)

| | r1 (stage 6) | r2 |
|---|---|---|
| Landed / stop | 22/32 at max_turns 16 | 33/34, stalled at the system task |
| Interface M1-T01 | 6,109 s, 8 attempts, 2 gate rejects (rc 64) | 2,440 s, 4 attempts, 0 gate rejects |
| Review before fan-out | none (fan-out 13 s after T01) | 274 s, 12 findings, 0 Critical |
| After the freeze | 4 types revised, 1 re-frozen, 2 classes grown in place, T26 blocked | 7 types in 3 cycles, all re-frozen (T32–T34) |
| Tokens | 121 M | 126 M (T01: 18.7 M cache read vs 54.7 M) |

The `pkg_scope` port removed stage 6's costliest defect (−3,669 s on the interface). The interface review ran in both rl9 runs (272–274 s) and works as a barrier, but it checks the interface against the contract, not against what downstream tasks will need: it caught all-at-once's missing verdict seam (M1-R02, hit later by M1-T26) and missed all five of incremental's test-seam gaps (TabularAgent, Replay, DQNAgent, Snake `teams`, the reference adapter), each found by a builder within 570 s of the fan-out. No stub-pinning test was written in either run: the interface agents followed the documented rule, so the floor check never fired.

## Where the time goes: the build does too much for its size

| Share of wall clock | minilab A3 (stage 5) | rl9-all-at-once r2 | rl9-incremental r2 |
|---|---|---|---|
| Interface task, its contract changes and its review | 40% | 46% | 27% |
| Re-freeze cycles and stop handling | — | 5% | 17% |
| Exit review and wrap-up | 19% | 8% | <1% |
| Building every other task | 33% | 40% | 17% (+39% in the system task's real training) |

On minilab one session working alone (A0) builds the same 21 tasks in 894 s; A3 spends 477 s building and about 950 s around it. On rl9 the interface task alone is 35–40 minutes: one cold agent writes every type, signature, sample and fake for 30 tasks, and both runs threw away a whole attempt to a contract change found while writing it. The places to cut, by size of the saving:
1. **The interface task.** Split it per component (each its own solo interface task, all first, as phase0.md already allows across packages) so a contract change redoes one component, and make the agent check the contract against CONSTRAINTS' limits before writing code (both rl9 runs lost an attempt to a 7-parameter signature or a forbidden import that was visible in the docs).
2. **Contract problems at planning time.** Every pre-freeze contract change in both rl9 runs (parameter limits, layering, missing types) was checkable against CONSTRAINTS before the build; an architecture-design check would remove the attempts they cost.
3. **The review before fan-out** costs 4.5 minutes and earns it only partly; checking each downstream task's Read and acceptance against the frozen surface (does every type and method a task's tests need exist?) would aim it at the gaps builders actually hit.
4. **The system task's real training** (incremental) belongs in its own task with a time budget and a feasibility probe first (below).

## Planning findings

- **An unreachable requirement frozen as a golden case** (incremental). TC-26 / EVAL-04 asks that an agent beat the scripted player within QR-01..QR-03. The system agent's evidence: scripted 18.7; tabular 17.3–18.3 over many settings; dqn-compact 18.9; the library reference DQN 19.0; clearing scripted after Holm over about 7 claims needs about +0.7. A beats-baseline result was written as a pass condition with no source that it is reachable. spec-writing (`references/spec.md:79`) asks for a metric, threshold and baseline but no evidence the threshold is reachable under the spec's compute limits; architecture-design named the risk (`architecture.md:201`) without a probe; test-planning took the spec line as the oracle's source (`references/cases.md:40`); build-planning put all real training in one size-S system task. Proposal for the planning owners: a beats-baseline requirement under a compute cap needs a source (paper, reference result, probe) or the reported/stretch form.
- **Solo tasks with `tests/intent/` paths in Writes** (incremental M1-T21, M1-T31): the implementer's path guard blocks them (CR-06), so both agents moved the tests to `tests/unit/`. build-planning's Mode rule makes such a task split; `dt lint` doesn't check it.
- **Writes and order gaps** (all-at-once M1-T13, T28, T29): four cheap stops, all fixed by one Replan.
- **The Exit line isn't checked by the build** (all-at-once): the build reached the exit with a missing console script and a failing `check.sh full --exit`.

## Persona and harness

- **Misfires, by cost.** Incremental turns 2–3: "fix the bar" on a CONTRACT-CHANGE that cited CONSTRAINTS; the main session refused once, then added exception EX-02 letting `compare` import `viz` with import-linter alerts silenced, which the architecture forbids and which fails when EX-02 expires at the M1 exit (fixed in 7c514ab: an open contract change is never answered with the bar). Incremental turns 20–22: "fix the bar" on TC-26's TEST-WRONG because its evidence said "the bar is reachable" (fixed in ca4ceb2: a stop about a golden case is the oracle's). All-at-once turns 3–5: the same misfire as turns 2–3; the main session held the bar each time but recorded the false note "the bar was fixed". A contract change answered from the single `type` field when the escalation named two types cost incremental a 402 s attempt (7c514ab splits them). Still open: a planning gap the main session called a Replan was sent to architecture-design Revise (incremental M1-T31, about 400 s), and "go with your recommendation" took a retry of M1-T28 that r1 had already shown was delivered.
- **Stops:** the stall stop ended incremental's last loop after 3 turns; no run reached its time budget; the looping stop never fired (no gate rejects at all).
- **minilab A3-r4:** its exit report mentioned a build-setup note and got the bar answer (one 92 s turn; fixed in 14ecb57).

## Grading notes

- `interface_changes` = 3 for incremental r2 is the full count (no class grew in place this time); r1's "none" was a false pass. `INTERFACE_PATHS` still covers only `types.py`, `protocols.py` and `tests/contracts`.
- `red_right_reason` 78/92 for all-at-once: M1-T27's tests were red at the tester's base only because another task's stub (M1-T18) raised; `red_check` accepts any `NotImplementedError`, so it should count only the task's own stubs. M1-T09's spine had already built T27's behaviour, so its implementer landed with no changes.
- `protected_edit_attempts` (incremental) is the solo-intent-path conflict above, blocked, nothing landed.
- No check reads a milestone's `**Exit:**` line.

## Validity

- **n = 1 per plan, two projects planned separately** from the same brief; their M1s differ in content, so this is not a planning-mode comparison.
- **Persona answers still decide outcomes:** three misfire patterns appeared for the first time in these runs, each fixed only after it cost a run turns. Every run since stage 4 has found a new one; the scripted persona is the least reliable part of the harness.
- **Each rl9 run ran under a different persona version** (incremental under 4407078 + 14ecb57; all-at-once also, started before ca4ceb2 and 7c514ab).
