# Build overhead: what to cut

**Status:** Decided 2026-10-19 · **Date:** 2026-10-19 · **Branch:** `build-overhead` (from `build-phase`)
**Evidence:** [findings-stage5.md](../evals/results-iteration-b1/findings-stage5.md),
[findings-stage6.md](../evals/results-iteration-b1/findings-stage6.md),
[findings-stage6b.md](../evals/results-iteration-b1/findings-stage6b.md), and each run's
`.git/dt-build/log.jsonl` and `agent_stream.jsonl` under `dev-team-workspace/iteration-b1/` (times below are
seconds from `dt build start`).

**Decision (the user, 2026-10-19):** make cuts 1, 2, 3 and 6 on this branch; 4 and 5's planning parts go to
[build-overhead-proposals.md](build-overhead-proposals.md) (5's spec-writing line with them, not made here);
7 isn't made; no small-milestone path for now: measure these cuts in the next build eval first.

## The problem

The contract-first parallel build is correct but slower than one session on small projects, because of what it
spends around the building:

| Share of wall clock | minilab A3 (median 1,490 s) | rl9-all-at-once r2 (5,094 s) | rl9-incremental r2 (10,113 s) |
|---|---|---|---|
| Interface task, its contract changes and its review | 40% | 46% | 27% |
| Re-freeze cycles and stop handling | — | 5% | 17% |
| Exit review and wrap-up | 19% | 8% | <1% |
| Building every other task | 33% | 40% | 17% (+39% real training in the system task) |

One session (minilab A0) builds the same 21 tasks in 848–894 s.

## What the runs show

- **Lost interface attempts are short and all were preventable from the docs.** rl9-incremental threw away three
  attempts (123, 228, 402 s) plus 285 s of main-session Revise turns between them; all-at-once one attempt
  (179 s) plus 246 s. Every one was a contract change visible before the build: `evaluate.evaluate` and
  `DQNAgent.__init__` with 7 arguments against `max-args = 5`, `compare.run_claims` taking a `viz.Chart` where
  `compare` doesn't depend on `viz`, and `runlog` types naming `train` and `methods` types (AD-12). minilab's one
  change (the planted `Drawdown` flaw, 50–77 s plus 118 s) is semantic and not visible to a tool.
- **The landing interface attempt is mostly contract tests and samples**: 1,402 and 1,644 s on rl9, of which
  orientation was 174–256 s, the source stubs for every component 190–225 s, and `tests/contracts` 831–1,040 s
  (60–64%, about 11,400 lines, 60 sample files). Splitting per component mostly splits that last part.
- **The interface review checks the contract, not what downstream tasks need.** It ran 248–253 s on rl9. Of the
  contract gaps builders hit in the first 15 minutes after fan-out, four were checkable from the task's `Read:`
  and TC cases against the frozen surface (incremental T15 `TabularAgent`, T20 `viz.Replay`, T26 `DQNAgent`; later
  T29 and T31), and all-at-once's T26 verdict seam the review *did* find (R02) but filed as Important, so it didn't
  stop the fan-out. Two more (incremental T07 `Snake`, all-at-once T13 `RulePolicy`) were frozen concrete classes
  missing a Protocol attribute, so they couldn't be instantiated. Incremental then paid three re-freeze cycles
  (T32 307 s, T33 520 s, T34 297 s, each plus a Revise, a Replan and a go).
- **Testers find seam gaps fastest** (T15's at +30 s after fan-out), but the barrier holds them for the review
  (127 s on minilab, 272–274 s on rl9).
- **Real training in the system task** (incremental M1-T31): 3,808 s, 88% of it `sleep` waits on training runs
  and a sweep, ending in a TEST-WRONG: TC-26 asks to beat a scripted player that no agent, the library reference
  included, beats.
- **The exit review repeats the checkpoint reviews.** minilab: two exit reviewers, 158–234 s, over every task,
  though the T10 and T20 checkpoints already reviewed and mutation-checked T02–T20. Exit phase median 292 s vs
  A0's 54 s.
- **Orientation per agent** is 45–260 s: each re-reads CONSTRAINTS, the packet, the plan, `pyproject.toml`,
  `check.sh`, `floor_guard` and `conftest`, and one interface attempt spent about 300 s grepping plugin docs.

## Cuts

Savings are from the b1 numbers above, per run, wall clock. "Here" means this branch would make the change; "proposal"
means it belongs to `build-planning`, which another session owns, and goes into
[build-overhead-proposals.md](build-overhead-proposals.md) instead.

| # | Cut | Where | minilab A3 | rl9-aao | rl9-inc |
|---|---|---|---|---|---|
| 1 | Contract limits checked at planning | here: `dt lint`, architecture-design | 0 | −425 | −1,040 |
| 2 | Interface review aimed at downstream needs | here: dt, CONSTRAINTS, agents, build skill | 0 | −250 | −1,100 |
| 3 | Testers start during the interface review | here: dt, build skill | −100 | −270 | −270 |
| 4 | Split the interface: types first, then contract tests per component | proposal, plus a dt test | ≈0 | −600 to −850 | −600 to −850 |
| 5 | Long runs in their own budgeted task, a reachability source first | proposal; spec-writing line here | 0 | 0 | −2,500 to −3,000 |
| 6 | Exit review covers only what no checkpoint reviewed | here: dt, reviewer agent | −80 to −120 | −100 | 0 |
| 7 | Agents read only the packet and CONSTRAINTS | here: agent templates | uncertain, ≈ −50 to −150 | same | same |
| | **Total, if each lands as estimated** | | **≈ −250 (to ≈1,240 s)** | **≈ −1,700 (to ≈3,400 s)** | **≈ −5,700 (to ≈4,400 s)** |

### 1. Contract limits checked at planning

Two `dt lint` errors over every `contract.md`, so architecture-design's Draft fails before approval
(its step 6 already requires `dt lint docs/` clean):
- `contract-args`: a signature with more arguments than the bar's `max-args`, or more positional ones than
  `max-positional-args` (from `pyproject.toml`'s `[tool.ruff.lint.pylint]`, else build-setup's 5 and 4), counted as
  Ruff counts them (`self`/`cls` and `*args`/`**kwargs` excluded).
- `contract-depends`: a symbol whose signature or fields name another component's type when its component
  doesn't depend on that one, directly or not, in the architecture's Components (or Packages) table.

A prototype over the base commits found exactly the five escalated problems in both rl9 runs, one more
(`agents.gae`, 5 positional arguments), one layering question (`notes.scaffold` naming `core.Output`; `notes`
lists no dependency), and nothing on minilab. architecture-design's `contracts.md` gets one line saying the limits
hold for every signature and that a type is named only across a declared dependency.

### 2. Interface review aimed at downstream needs

- `dt` gives the interface reviewer what to check against: its prompt names a `dt build needs <checkpoint>`
  listing, for each task after the barrier, its `Read:` symbols, acceptance bullets and TC cases (one compact
  block per task).
- CONSTRAINTS' Interface item 4 becomes that check: for each listed task, every type, method, attribute and state
  its tests must call or observe is public in the frozen surface. A gap is **Critical**: it is a contract
  change, found before anyone builds on it.
- escalation.md's Critical row: an interface-review Critical that names a missing seam goes the CONTRACT-CHANGE way
  (architecture-design Revise, a re-freeze task), all such findings in one Revise.
- The implementer template: an interface task's contract tests instantiate each frozen concrete class from its
  sample, so a class missing a Protocol member fails at the interface task (incremental T07, all-at-once T13).

The review may take 60–120 s longer. The saving assumes it catches the four Read-checkable gaps and the two
instantiation gaps, turning incremental's three re-freeze cycles into one before fan-out (about 520 s instead of
about 1,700 s). The next build eval measures the hit rate.

### 3. Testers start during the interface review

The barrier holds implementer and solo halves only. Tester halves start once their interface tasks land (as
`dt` already computes): they read only the frozen surface, so they are the review's fastest downstream check, and
their tests are red by design. If the review records a Critical, testers already running finish and land their
tests branches, and the hold stops everything else, as today. The cost: a re-freeze can make a landed tester's
tests stale, which the implementer reports as TEST-WRONG. That already happens to any contract change after the
fan-out.

### 4. Split the interface (proposal for build-planning)

`phase0.md` allows one interface task per provider across packages, all independent. Per component they
can't be independent, because components' signatures import each other's types. Proposed shape: one **types**
interface task (every `types.py`, Protocol, signature and stub, about 400–450 s on rl9 with orientation),
then one **contract** interface task per component (its schemas, samples, fakes, replay doubles and contract
tests), all depending only on the types task and running in parallel. A contract change then redoes the types
task or one component, never the whole interface. rl9 estimate: about 450 + 350 s against 1,402–1,644 s. The
proposal also asks why one milestone's contract tests run to 11,400 lines, with a hand-built sample generator
written inside the interface task each time (all-at-once spent 380 s on one). `dt` already handles a chain of
interface tasks (one added barrier after the last, testers waiting on their interface ancestors); this branch adds
a test that pins it.

### 5. Long runs and unreachable requirements (proposal; one spec-writing line here)

- Proposal for build-planning: real training and other long runs get their own task after the system task, with
  a time budget in its acceptance and a feasibility run first (a short run whose curve shows the target is in
  reach), never inside the system task.
- spec-writing, here: a requirement to beat a baseline under a compute limit names a source showing it is
  reachable (a paper, a reference result, a probe), or is written in the reported or stretch form.
  test-planning takes its oracle from that source.

The saving is incremental's system task falling from 3,808 s to the budget plus the probe. All-at-once deferred its
equivalent to M2 and isn't measured.

### 6. Exit review covers only what no checkpoint reviewed

`dt`'s exit review row lists the tasks a recorded checkpoint review already covered. The reviewer runs the
Milestone exit list over the whole diff as today, but mutation-checks and reviews code only for the tasks no
checkpoint covered. minilab's exit reviewers then mutation-check T21 alone instead of T02–T21.

### 7. Agents read only what they need

The tester, implementer and reviewer templates say what to read: the packet and CONSTRAINTS.md. `scripts/`,
`pyproject.toml`, the plugin's own docs and other tasks' code aren't theirs to read. This is low-confidence: the
orientation time is partly the model reading the packet carefully, and the next eval should measure it before
anyone counts the saving.

## What this doesn't fix

These cuts close most of rl9's overhead but not minilab's gap to one session (about 1,240 s against 870 s). What
remains on a small milestone is the cold interface agent (about 350 s against A0's 208 s), the contract change
going through a stop and the main session (118 s against 50 s), the interface review (127 s) and the exit review.
Each is a correctness feature: testers blind to code, reviewers that land nothing and a frozen interface are in
`PURPOSE.md`. Closing the rest would need a small-milestone path, for example one agent building every task in
order under the same gates and only the exit review, below some task count. That changes what the build promises,
so it is the user's call and isn't designed here.

## Not proposed

- Dropping the interface review: it found all-at-once's stub-pinning test in stage 6 and the verdict seam here.
- Making `dt land` faster: 10–23 s each, serialized by its lock, but it's the integration gate and runs off the
  critical path except for the critical-path tasks' own landings.

## Order and checks

1, 2, 3 and 6 are independent and land as separate commits with tests in `scripts/tests`. 7 and 5's spec-writing
line are skill text. 4 and 5's build-planning part go into `build-overhead-proposals.md` for that skill's owner.
Done means `python3 -m pytest -q scripts/tests`, `python3 ../plugin-dev/scripts/check.py .` and
`python3 evals/harness/dryrun_build.py` pass from `dev-team/`. No version bump: the release level (minor:
new lint errors and a changed review flow) is the user's call afterwards.
