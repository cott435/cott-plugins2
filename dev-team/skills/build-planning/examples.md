# Build Planning Templates

The plan, todo and roadmap milestone templates. Each mode's worked example is named in its `references/<mode>.md`; `references/examples-cut.md`, `examples-phase0.md` and `examples-routing.md` illustrate the cut, an interface-first milestone and its graph, and skill and reference routing.

## Templates

### `tasks/plan.md` skeleton

A queued plan (`tasks/queued/M<n>-<slug>.md`) uses the same skeleton and has no todo until it's promoted.

`**Base:** —` means pending. build-planning always writes `—`; `build-setup` runs `dt base` after its bar is approved and committed, which sets it to HEAD's short sha.

````markdown
# M<n>: <Milestone name> — Plan

**Milestone:** M<n> · **Status:** Draft · **Base:** — · **Last updated:** YYYY-MM-DD · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** <the capability, and the cases that prove it, in one sentence>
**Covers:** <spec IDs; ranges use an en dash, STAT-01–STAT-04> · **Deferred:** <ID (to M<k>: reason)>, or none
**Skills:** <skill (which steps)>, or none

## Phase 0: Interface

### M<n>-T01: <the milestone's interface>
…

## Phase 1: Step spines

### M<n>-T02: <step> spine (<baseline>)
…

## Phase 2: Wiring and thicken

### M<n>-T05: Wire PL-NN
…

### M<n>-T06: <one step upgrade>
…

### Checkpoint after M<n>-T06
…

## Phase 3: System

### M<n>-T07: <system: fakes swapped for real providers>
…

### Checkpoint: milestone exit
…

## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M<n>-T06 <title> | M<n>-T02 <its step's spine> | code | none: thickens the same module |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| <risk> | <what goes wrong> | <the task or case that catches it> |

## Open questions

## Replan notes
````

Status runs Draft → Approved → In progress → Done, then `dt archive` replaces the file with the stub.

### Task templates

The interface, wiring and system tasks are worked in `references/examples-phase0.md`.

**Step spine.** One step, solo, its owner module only; no smoke yet.

```markdown
### M2-T02: allocate spine (equal split)
**Package:** gridload · **Step:** PL-03.allocate · **Kind:** spine · **Covers:** — · **Size:** S · **Mode:** solo
**Skills:** —
**Read:** PL-03, reserve.allocate, reserve.Allocation, profile.Profile
**Acceptance:**
- [ ] `allocate` returns an equal reserve split on the profile.Profile sample; the output validates as reserve.Allocation
**Verify:** `pytest tests/unit/gridload -k allocate` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Writes:** src/gridload/reserve/allocate.py, tests/unit/gridload/test_allocate.py
```

**Thicken task.** One step, one package, at most 3 bullets; it starts once its step's spine lands, beside the wiring, so no smoke yet.

```markdown
### M2-T06: Optimized reserve allocation
**Package:** gridload · **Step:** PL-03.allocate · **Kind:** thicken · **Covers:** RES-01 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-03, TC-04, RES-01, reserve.allocate, reserve.Allocation
**Acceptance:**
- [ ] TC-04 passes within tolerance; the equal split stays selectable as the baseline
**Verify:** `pytest tests/intent/gridload tests/unit/gridload -k allocate` · `scripts/check.sh gate`
**Depends on:** M2-T02 · **Writes:** src/gridload/reserve/allocate.py, tests/intent/gridload/test_allocate.py, tests/unit/gridload/test_allocate.py
```

| Field | Rule (lint code) |
|---|---|
| `Package` | One package id (`task-fields`) |
| `Step` | `PL-NN.<function>` from the step table (`task-step`) on spine and thicken tasks; `PL-NN` on wiring and system tasks; `contract` on the interface task |
| `Kind` | `interface`, `spine`, `wiring`, `thicken` or `system` (`phase0.md`) |
| `Covers` | Spec IDs the task satisfies |
| `Size` | XS = 1, S = 1–2, M = 3–5 `Writes:` entries outside `tests/`, a folder glob counting as one (`task-size`) |
| `Mode` | `split` for checkable behavior, `solo` for interface, spine, wiring, system, refactor, glue, doc-sync |
| `Skills` | Skill names, or `—`. Every skill on the milestone's `**Skills:**` line (else its stage's) lands on at least one task (`skills_unrouted`). A missing skill is still named |
| `Read` | IDs and repo paths, comma-separated. Everything the builder needs, nothing more (`missing-ref`). References by ID with an optional selector: `RF-01:deseasonalize`, `RF-01:outline`, `RF-03:<heading>`, `PB-01:probe.py:sync_all`, `PB-01:samples`; a long one with none warns (`ref-large`). Every milestone reference lands on at least one task (`references_unrouted`) |
| `Acceptance` | ≤ 3 checkbox bullets, each test-backed (`task-acceptance`) |
| `Verify` | Backticked commands joined by ` · `. Includes the smoke command once the `Depends on` path reaches the pipeline's wiring (`verify-smoke`) |
| `Depends on` | Task IDs earlier in the plan, or `—`; unmitigated edges only, each with a graph row (`depends`, `edges`) |
| `Writes` | Comma-separated paths or folder globs, exclusive: no other task off its `Depends on` path writes them; none under `tasks/` (`writes`) |
| `Reason` | Optional one line: a mode override, or a second package or step |
| `Blocked` | Added when a task is paused; Replan removes it once resolved |

Title rule: no " and " (`task-title`). Required fields: Package, Step, Kind, Size, Mode, Read, Acceptance, Verify, Writes (`task-fields`).

### Checkpoint blocks

At the end of a wave:

```markdown
### Checkpoint after M2-T06
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition
```

Last, after the final task: the same list under `### Checkpoint: milestone exit`, with `scripts/check.sh full --exit` (which also fails on any interface stub left), plus `- [ ] The Scope's Exit holds`.

Findings are not written by this skill or by builders. The orchestrator records the reviewer's findings with `dt finding`, and they look like this:

```markdown
**Findings:**
- M2-R01 Important · CR-21 · `reserve/compare.py::compare` complexity 14 → fix task M2-T05
- M2-R02 Nit · readability · column names → won't fix: match the utility's report notation
```

A finding whose disposition is a fix task means Replan adds that task.

### `tasks/todo.md`

One line per task, `<ID> <title> (<package>, <size>, <mode>)`. No checkpoints. Lines start unchecked; only `dt tick` checks them.

```markdown
# M2: Seasonality & baselines — Todo

- [ ] M2-T01 PL-03 interface (gridload, S, solo)
- [ ] M2-T02 allocate spine (equal split) (gridload, S, solo)
- [ ] M2-T03 compare spine (realized shortfall) (gridload, S, solo)
- [ ] M2-T04 Wire PL-03 (gridload, S, solo)
- [ ] M2-T05 Out-of-sample comparison (gridload, S, split)
- [ ] M2-T06 Optimized reserve allocation (gridload, S, split)
- [ ] M2-T07 Fourier profile as the allocation default (gridload, XS, solo)
```

### Stub plan (between milestones)

Written by `dt archive`. Never deleted; replaced only by the next plan.

```markdown
# Between milestones

**Status:** Between milestones · **Last updated:** 2026-11-02 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)
```

### Milestone rows

`idea-refine` adds the stage (`S<n>`: Name, Source, and a section with Outline and Skills). When the stage's pipelines are approved, this skill cuts it: one milestone row per slice under the milestone table (add the table below the stage table if it's missing), and a section with the slice's `**Outline:**`, then `**Exit:**`, `**Plan:**` and outcome text once planned. `dt roadmap` writes both `Status*` columns; never edit them.

```markdown
| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | Ingest & clean | brief | Building |
| S2 | Seasonality & baselines | ideas/seasonality-baselines.md | Planned |

| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Ingest & clean | gridload | PL-01, PL-02 | — | Building |
| M2 | S2 | Seasonality & baselines | gridload | PL-03 | M1 | Planned |

## M2: Seasonality & baselines
**Outline:** A walk-forward evaluation over held-out weeks compares an optimized reserve allocation with an equal split.
**Exit:** The optimized allocation beats the equal split on held-out reserve shortfall; TC-04 passes.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

A stage that fits one milestone gets one, and the milestone inherits the stage's Skills and references. A stage cut into several gives each milestone `**Skills:**` and `**References:**` lines from the stage's (`references/examples-cut.md`). Later milestones get only the row and a 3–6 line section (Outline, Exit, and Plan once a plan exists).
