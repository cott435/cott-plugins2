# Contract-gap proposals for build-planning

**For:** the owner of `skills/build-planning`. **From:** the contract-first gap review of build eval b1
([contract-first-gaps.html](../evals/results-iteration-b1/contract-first-gaps.html),
[findings-stage5.md](../evals/results-iteration-b1/findings-stage5.md),
[findings-stage5b.md](../evals/results-iteration-b1/findings-stage5b.md)). **Date:** 2026-10-18.

The fixes that live outside build-planning are on branch `claude/contract-gap-fixes-398dd0`. Each proposal
below names what that branch already does, so the planning text can point at it instead of restating it.
None of this is implemented in `skills/build-planning`, because another session owns that skill.

## 1. Interface acceptance that invites a stub test

**Evidence.** rl9-all-at-once r1: M1-T01's acceptance read "Every M1 step and entry function imports with its
contract signature, body `raise NotImplementedError("<its spine or wiring task>")`". The interface agent turned
that bullet into `tests/contracts/test_interface.py`, which calls every stub inside
`pytest.raises(NotImplementedError, match=task)`. Once a spine replaced its stub, that frozen test failed, so no
builder could pass the gate: 1 of 30 tasks landed, about 1.45 agent-hours lost, 4,409 s, $36.

**Done on the branch.** `floor_guard.py` fails a changed test that names `NotImplementedError` (`stub-pinned`,
CR-02), so the interface task itself can't land such a test. The implementer template says what an interface
task's contract tests check (shape only), and the Interface review makes a contract test pinning a transient
state Critical.

**Proposed for build-planning.**
- `references/phase0.md` §a, the stub bullet and its Acceptance sentence, and `references/examples-phase0.md:21`
  (also `examples-advance.md:54`): keep the stub as what the code holds, never as what a test checks. For
  example: "every step and entry function imports with its contract signature (its body is the CR-02 stub
  naming its task; no test checks the body)". Acceptance: "every sample validates against its type; every
  signature imports and matches the contract; each fake passes its contract's cases".
- `references/tasks.md:50`, the interface task's `Verify:`: "the schema check over every sample, and each
  fake's contract cases", nothing about stubs.

## 2. The barrier checkpoint after the interface task

**Evidence.** Neither rl9 plan had a checkpoint after M1-T01, though `references/tasks.md:31` asks for
`### Checkpoint after M<n>-T<nn> (barrier)`. So `dt` scheduled no interface review, and the stub-pinning test
went straight to six builders. The minilab plans had the barrier, and its review cost 111–128 s.

**Done on the branch.** `dt` reviews every interface before building on it: a checkpoint straight after an
interface task counts as a barrier, and where the plan follows an interface task straight with another task,
`dt` adds the barrier (`dispatch.added_barriers`). `dt finding` writes that added checkpoint into the plan with
the review's first finding.

**Proposed for build-planning.** The rule in `tasks.md:31` stands. The plan should still write the block,
because its checklist items guide the reviewer and the plan map shows it. Two optional additions:
- one line in `tasks.md:31`: "a plan without it still gets the review: `dt` adds the barrier", so a planner
  knows the cost is paid anyway;
- a `dt lint` warning `interface-barrier` (an interface task followed straight by a non-interface task with no
  checkpoint between), to catch the drift at Draft rather than at the build. This is a `scripts/` change, but
  it enforces build-planning's rule, so it's that owner's call. A warning, not an error: dt covers the gap.

## 3. Fakes that do more than their cases show

**Evidence.** minilab A3-r1, A3-WF-r2, A3-RT-r3: the frozen `mdata.load_prices` fake narrowed its result to the
requested tickers, and the real `validate_rows` didn't. No task's acceptance asked the real code to narrow. It
surfaced only when the system task M1-T21 happened to notice, and cost a CONTRACT-CHANGE, a Revise, a Replan
(re-freeze M1-T22, narrowing M1-T23) and a new go: 388 s and 496 s. Where nobody noticed, holdout h05 failed
(A1-r2, A3-r1).

**Done on the branch.** The Interface review checks that whatever a fake does beyond echoing a fixture
(filtering, ordering, an error) is a case the real provider must pass too, and the implementer template has the
interface task write each fake's cases as one test that takes the provider. `dt context` gives a system task a
Conformance block: each contract folder with a fake that it reads or crosses, and the instruction to run those
cases on the real provider, escalating a CONTRACT-CHANGE when the failing code isn't its own.

**Proposed for build-planning.** This is still late: the system task is the last one. Two planning rules would
move the finding to the task that builds the behaviour:
- Every case of a `**Boundary:**` fake maps to an acceptance bullet on a task that builds the real provider
  (a spine, a thicken or the wiring). A case with no such task is a plan gap, like an uncovered requirement.
  A `dt status --skill build-planning` list (`fake_cases_unbuilt`) could report it, if the cases can be read
  from the contract's `**Cases:**` line.
- `phase0.md` §d: the system task's `Writes:` name the conformance test the Conformance block asks for
  (`tests/unit/<pkg>/test_<symbol>_conformance.py`), and its acceptance reads "each fake's contract cases pass
  on the real provider" in place of "the boundary samples still validate against real output".

## 4. A real vertical slice before the contracts freeze

**Evidence.** The stock-data brief proposes building one real source end to end. Its order freezes the
contracts first, then the slice. b1 shows contract problems cost little when found while the contracts are
written (the planted `Drawdown` flaw: about 2 minutes, caught by every interface-plan run) and much more once
real code runs: 6–8 minutes for the fake drift, about 13 minutes for a field found after the freeze, and the
rl9 stall.

**Proposed for build-planning, as a decision for the user first.** For a milestone whose pipeline reads an
external source and has no probe sample of it, Phase 0 starts with a solo **slice** task: one source, the real
fetch, the canonical record and the sink, end to end, written as production code under the bar. The interface
task depends on it and derives its samples and fakes from the slice's real output instead of from the contract
text alone.

Not done here, and why it needs a decision:
- It adds one task to the critical path of every such milestone. b1 already finds contract-first slower than one
  session at this size (A3 1,428 s against A0 894 s), and the gap is fixed costs, so this makes it slower still.
- It overlaps `api-probe`: a probe's redacted samples already feed the interface task (`phase0.md` §a). A slice
  pays off only where no probe ran, or where the record shape comes from our own code (the minilab fake drift
  was not about an external API at all, and conformance (proposal 3) covers that case).
- It changes the milestone shape that `PURPOSE.md` describes ("contract first"), so it needs the user's yes on
  the goal before it goes into the skill.

A cheaper alternative to try first: when a milestone's pipeline reads an external source and no `PB-NN` sample
backs its record type, build-planning asks for an `api-probe` before the plan, rather than adding a slice task.

## Release level for the branch

Minor: `dt` adds interface reviews the plan didn't ask for, the bar gains a floor rule (`stub-pinned`), and
`dt context` gains a block. Nothing breaks an existing plan or bar, and older bars take the new rule through
build-setup Extend.
