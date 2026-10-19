# Build-overhead proposals for build-planning

**For:** the owner of `skills/build-planning` (and spec-writing / test-planning for §2). **From:**
[build-overhead.md](build-overhead.md), from the b1 build-eval timings. **Date:** 2026-10-19. **Branch:**
`build-overhead`, which changes nothing under `skills/build-planning`.

## 0. What this branch changes that build-planning's text describes

- **Testers run during the interface review** (`dispatch.py`, the barrier hold): the barrier holds implementer
  and solo halves only. `references/tasks.md:31` says "behind the barrier nothing else starts until the
  interface review passes"; proposed: "behind the barrier no code starts until the interface review passes;
  testers start once their interface tasks land". `phase0.md:15` ("Tester halves of split tasks start right after
  the interface") already holds.
- **The interface review checks what later tasks need** (`dt build needs <checkpoint>`, CONSTRAINTS' Interface
  item 5), so a plan's barrier checklist needs no per-task "its tester can write its tests" lines.
- **`dt lint` `contract-args` and `contract-depends`** fail an architecture whose contract signatures break the
  bar's argument limits or name a type across an undeclared dependency. Nothing is needed from build-planning.

## 1. Split the interface: types first, then contract tests per component

**Evidence.** The landing interface attempt took 1,402 s (rl9-incremental) and 1,644 s (all-at-once). Orientation
was 174–256 s and the source stubs for all 9–11 components 190–225 s; `tests/contracts` took 831–1,040 s
(60–64%: about 11,400 lines, 60 sample files, and in all-at-once a 380 s shared sample generator). A contract
change made the agent redo all of it.

**Why not one task per component as they stand.** `phase0.md:24` lets a milestone across packages have one
interface task per provider, none depending on another. Within one package, components' signatures import each
other's types, so independent per-component tasks would write against types that aren't there yet.

**Proposed shape.**
- One **types** interface task (`**Step:** contract`): every component's `types.py`, Protocols, step signatures
  and stubs, the exports and `__main__.py`, checked by the gate's type check. No samples or contract tests.
- One **contract** interface task per component with contract types: its schemas, samples, fakes, replay doubles
  and contract tests (`Writes:` its `tests/contracts/<component>.<Type>/` folders), each depending only on the
  types task. They run in parallel.
- A later task depends on the contract tasks of the components whose samples its tests load, so its tester
  waits for them (dt computes this from `Depends on`).
- The barrier checkpoint goes after the last of them; `dt` reviews them together. `phase0.md:24`'s "interface
  tasks never depend on each other" becomes "a contract task depends only on the types task".

`dt` already supports this shape: test `test_a_chain_of_interface_tasks` in `scripts/tests/test_build.py`
pins it (one barrier after the last interface task reviews both, and a tester waits on the interface tasks its
task depends on). `dt lint` `writes` stays satisfied, because each contract task writes only its own folders.

**Expected saving.** rl9: about 450 s for the types task (orientation plus stubs) and 350 s for the slowest
contract task, against 1,402–1,644 s, so 600–850 s. A contract change redoes the types task or one component's
contract task, not the whole interface. minilab (2 packages, 9 types, 227–314 s): about 0.

**Also worth asking.** Why one milestone's contract tests run to 11,400 lines. If most of it is sample
generators each interface task writes again, a small sample-writing helper in build-setup's scripts, or a rule
that samples are literal JSON per case, may cut more than the split does.

## 2. Long runs in their own task, and a reachability source for beats-baseline requirements

**Evidence.** rl9-incremental's system task M1-T31 took 3,808 s, 88% of it `sleep` waits on real training runs
and a hyperparameter sweep, and ended in a TEST-WRONG: TC-26 / EVAL-04 asks an agent to beat a scripted player
that none beat (scripted 18.7; tabular 17.3–18.3; dqn-compact 18.9; the library reference 19.0; about +0.7
needed after the Holm correction). Stage 6b's planning findings trace it: spec-writing asks for a metric,
threshold and baseline but no evidence the threshold is reachable under the compute limit, and test-planning
took the spec line as the oracle's source.

**Proposed for build-planning.** Real training or any run longer than a few minutes gets its own task after the
system task (`**Kind:** system`, `**Reason:** long run`), never inside the system task. Its acceptance names a
time budget and starts with a feasibility run: a short run whose curve shows the target is in reach, escalating
TEST-WRONG with the evidence if it isn't, before the full runs.

**Proposed for spec-writing and test-planning** (held for the user's decision; not made on this branch):
a requirement to beat a baseline under a compute limit names a source showing it is reachable (a paper, a
reference result, a probe), or is written in the reported or stretch form; test-planning takes its oracle
from that source.

**Expected saving.** On rl9-incremental, the system task drops from 3,808 s to its budget plus the probe, roughly
2,500–3,000 s, and the unreachable claim surfaces at planning or in the probe instead of after an hour of runs.
